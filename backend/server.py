from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import shutil
from typing import List
import asyncio
import uuid

from models import *
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from orchestrator import AnalysisPipeline
from vector_store import VectorStore
from agents.base_agent import BaseAgent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL')
db_name = os.environ.get('DB_NAME', 'causesense')
if not mongo_url:
    raise RuntimeError(
        "MONGO_URL is not set. On Render, add MongoDB Atlas connection string "
        "in Environment (e.g. mongodb+srv://user:pass@cluster.../causesense)."
    )

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI()
api_router = APIRouter(prefix="/api")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "RCA Platform API", "status": "online", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    try:
        await client.admin.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check DB ping failed: {e}")
        raise HTTPException(status_code=503, detail="database unavailable")

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    email = user_data.email.strip().lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_dict)
    
    token = create_access_token({"sub": user_dict["id"]})
    
    user_response = UserResponse(
        id=user_dict["id"],
        email=user_dict["email"],
        full_name=user_dict["full_name"],
        created_at=user_dict["created_at"]
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    email = credentials.email.strip().lower()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if (
        not user
        or not user.get("password_hash")
        or not verify_password(credentials.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    token = create_access_token({"sub": user["id"]})
    
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"]
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"]
    )

@api_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    try:
        from data_limits import MAX_UPLOAD_BYTES

        # Stream to disk — avoid holding entire file in RAM (critical on Render free)
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lower()
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"

        file_size = 0
        chunk_size = 1024 * 1024  # 1 MB
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_BYTES:
                    buffer.close()
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File too large for free hosting memory limits. "
                            f"Maximum is {MAX_UPLOAD_BYTES // (1024*1024)}MB "
                            f"(your upload exceeded this). Split the CSV or sample rows."
                        ),
                    )
                buffer.write(chunk)

        if file_size == 0:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail="Empty file")

        file_metadata = {
            "id": file_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_type": file_extension,
            "file_size": file_size,
            "file_path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }

        await db.uploaded_files.insert_one(file_metadata)

        return FileUploadResponse(
            id=file_id,
            filename=file.filename,
            file_type=file_extension,
            file_size=file_size,
            message="File uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")

@api_router.get("/upload", response_model=List[FileMetadata])
async def list_uploads(user_id: str = Depends(get_current_user)):
    files = await db.uploaded_files.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    return files

@api_router.delete("/upload/{file_id}")
async def delete_upload(file_id: str, user_id: str = Depends(get_current_user)):
    file_doc = await db.uploaded_files.find_one({"id": file_id, "user_id": user_id}, {"_id": 0})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(file_doc["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    await db.uploaded_files.delete_one({"id": file_id})
    
    return {"message": "File deleted successfully"}

async def run_analysis_pipeline(analysis_id: str, user_id: str, file_ids: List[str], project_name: str):
    try:
        file_docs = await db.uploaded_files.find(
            {"id": {"$in": file_ids}, "user_id": user_id},
            {"_id": 0}
        ).to_list(100)
        
        if not file_docs:
            await db.analyses.update_one(
                {"id": analysis_id},
                {"$set": {"status": "failed", "progress": 0}}
            )
            return
        
        file_paths = [doc["file_path"] for doc in file_docs]
        
        pipeline = AnalysisPipeline(user_id, analysis_id)
        
        async def update_progress(progress: int, message: str, estimated_seconds: int = 0):
            await db.analyses.update_one(
                {"id": analysis_id},
                {"$set": {
                    "progress": progress,
                    "status": "processing" if progress < 100 else "completed",
                    "current_step": message,
                    "estimated_time_remaining": estimated_seconds,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        result = await pipeline.run(file_paths, update_progress)
        
        await db.analyses.update_one(
            {"id": analysis_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "current_step": "Complete",
                "estimated_time_remaining": 0,
                "anomalies": result["anomalies"],
                "hypotheses": result["hypotheses"],
                "ml_results": result["ml_results"],
                "causal_analysis": result["causal_analysis"],
                "root_cause": result["root_cause"],
                "visualizations": result.get("visualizations", {}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {e}")
        await db.analyses.update_one(
            {"id": analysis_id},
            {"$set": {
                "status": "failed",
                "progress": 0,
                "current_step": f"Error: {str(e)}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

@api_router.post("/analysis/start", response_model=AnalysisResponse)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    analysis_id = str(uuid.uuid4())
    
    analysis_doc = {
        "id": analysis_id,
        "user_id": user_id,
        "file_ids": request.file_ids,
        "project_name": request.project_name or "Untitled Analysis",
        "status": "processing",
        "progress": 0,
        "current_step": "Starting analysis...",
        "estimated_time_remaining": 30,
        "anomalies": None,
        "hypotheses": None,
        "ml_results": None,
        "causal_analysis": None,
        "root_cause": None,
        "visualizations": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.analyses.insert_one(analysis_doc)
    
    background_tasks.add_task(run_analysis_pipeline, analysis_id, user_id, request.file_ids, request.project_name or "Untitled Analysis")
    
    return AnalysisResponse(
        id=analysis_id,
        status="processing",
        progress=0,
        message="Analysis started"
    )

@api_router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str, user_id: str = Depends(get_current_user)):
    analysis = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisResult(**analysis)

@api_router.get("/analysis", response_model=List[AnalysisResult])
async def list_analyses(user_id: str = Depends(get_current_user)):
    analyses = await db.analyses.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(10)
    
    return analyses

@api_router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str, user_id: str = Depends(get_current_user)):
    result = await db.analyses.delete_one({"id": analysis_id, "user_id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"message": "Analysis deleted successfully"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, user_id: str = Depends(get_current_user)):
    try:
        from chat_guardrails import check_message_allowed, build_chat_prompt, DECLINE_MESSAGE

        allowed, decline = check_message_allowed(message.message)
        if not allowed:
            response = decline or DECLINE_MESSAGE
            await db.chat_messages.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "analysis_id": message.analysis_id,
                "message": message.message,
                "response": response,
                "blocked": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            return ChatResponse(response=response, sources=None)

        analysis_context = "No analysis selected — answer generally about RCA workflow only if relevant."
        root_cause_info = "No analysis selected"

        if message.analysis_id:
            analysis = await db.analyses.find_one(
                {"id": message.analysis_id, "user_id": user_id},
                {"_id": 0}
            )
            if analysis:
                root_cause = analysis.get('root_cause') or {}
                root_cause_info = f"""Root Cause: {root_cause.get('root_cause', 'Not determined')}
Confidence: {root_cause.get('confidence_score', 0) * 100:.0f}%
Anomalies Detected: {len(analysis.get('anomalies', []))}
Hypotheses: {len(analysis.get('hypotheses', []))}
ML models: {len(analysis.get('ml_results', []))}
Status: {analysis.get('status', 'unknown')}"""
                analysis_context = root_cause_info

        history = []
        for item in (message.history or [])[-8:]:
            role = (item.get("role") or "").strip().lower()
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                history.append({"role": role, "content": content[:2000]})

        try:
            agent = BaseAgent()
            prompt = build_chat_prompt(message.message, analysis_context)
            response = await agent.send_message(
                "You are CauseSense AI. Follow the safety and scope rules in the user message. "
                "Use prior conversation turns when the user asks follow-ups.",
                prompt,
                history=history,
            )
            if not response or not str(response).strip():
                response = (
                    "I could not generate a reply just now. "
                    "Please ask again about your analysis, anomalies, or root cause."
                )

        except Exception as llm_error:
            logger.error(f"LLM error in chat: {llm_error}")
            response = (
                f"Based on the analysis: {root_cause_info}\n\n"
                "I could not reach the AI service just now. "
                "Please check the Overview tab for your analysis results, "
                "or ask again about anomalies, ML findings, or root cause."
            )

        await db.chat_messages.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "analysis_id": message.analysis_id,
            "message": message.message,
            "response": response,
            "blocked": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        return ChatResponse(response=response, sources=None)

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return ChatResponse(
            response="I'm currently experiencing technical difficulties. Please refer to the analysis results displayed on the dashboard.",
            sources=None
        )

@api_router.get("/reports/{analysis_id}/download")
async def download_report(analysis_id: str, user_id: str = Depends(get_current_user)):
    from pdf_generator import PDFReportGenerator

    analysis = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user_id},
        {"_id": 0}
    )

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    pdf_path = str(UPLOAD_DIR / f"RCA_Report_{analysis_id}.pdf")

    try:
        pdf_gen = PDFReportGenerator(analysis, pdf_path)
        pdf_gen.generate()

        return FileResponse(
            path=pdf_path,
            filename=f"CauseSense_RCA_Report_{analysis_id}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
