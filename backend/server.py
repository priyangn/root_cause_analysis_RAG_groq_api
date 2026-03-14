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
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from orchestrator import AnalysisPipeline
from vector_store import VectorStore
from agents.base_agent import BaseAgent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    return {"status": "healthy", "database": "connected"}

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
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
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
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
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
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

async def run_analysis_pipeline(analysis_id: str, user_id: str, file_ids: List[str]):
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
        
        async def update_progress(progress: int, message: str):
            await db.analyses.update_one(
                {"id": analysis_id},
                {"$set": {
                    "progress": progress,
                    "status": "processing" if progress < 100 else "completed",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        result = await pipeline.run(file_paths, update_progress)
        
        await db.analyses.update_one(
            {"id": analysis_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "anomalies": result["anomalies"],
                "hypotheses": result["hypotheses"],
                "ml_results": result["ml_results"],
                "causal_analysis": result["causal_analysis"],
                "root_cause": result["root_cause"],
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
        "status": "processing",
        "progress": 0,
        "anomalies": None,
        "hypotheses": None,
        "ml_results": None,
        "causal_analysis": None,
        "root_cause": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.analyses.insert_one(analysis_doc)
    
    background_tasks.add_task(run_analysis_pipeline, analysis_id, user_id, request.file_ids)
    
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
    ).sort("created_at", -1).to_list(50)
    
    return analyses

@api_router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, user_id: str = Depends(get_current_user)):
    try:
        analysis_context = ""
        root_cause_info = "No analysis selected"
        
        if message.analysis_id:
            analysis = await db.analyses.find_one(
                {"id": message.analysis_id, "user_id": user_id},
                {"_id": 0}
            )
            if analysis and analysis.get('root_cause'):
                root_cause = analysis.get('root_cause', {})
                root_cause_info = f"""Root Cause: {root_cause.get('root_cause', 'Not determined')}
Confidence: {root_cause.get('confidence_score', 0) * 100:.0f}%
Anomalies Detected: {len(analysis.get('anomalies', []))}"""
        
        try:
            agent = BaseAgent()
            chat_session = await agent.create_chat(
                "You are a technical assistant. Provide concise answers about machine failure analysis.",
                f"chat_{user_id}_{message.analysis_id or 'general'}"
            )
            
            query = f"Context: {root_cause_info}\n\nQuestion: {message.message}\n\nProvide a brief answer (2-3 sentences)."
            response = await agent.send_message(chat_session, query)
            
        except Exception as llm_error:
            logger.error(f"LLM error in chat: {llm_error}")
            response = f"Based on the analysis: {root_cause_info}\n\nRegarding your question about '{message.message}', please refer to the analysis results in the Overview tab for detailed information."
        
        await db.chat_messages.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "analysis_id": message.analysis_id,
            "message": message.message,
            "response": response,
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
    analysis = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    report_content = f"""# Root Cause Analysis Report

## Analysis ID: {analysis_id}
## Date: {analysis.get('created_at', '')}

## Executive Summary
{analysis.get('root_cause', {}).get('root_cause', 'Not determined')}

Confidence Score: {analysis.get('root_cause', {}).get('confidence_score', 0) * 100}%

## Evidence
"""
    
    for evidence in analysis.get('root_cause', {}).get('evidence', []):
        report_content += f"- {evidence}\\n"
    
    report_content += "\\n## Preventive Actions\\n"
    for action in analysis.get('root_cause', {}).get('preventive_actions', []):
        report_content += f"- {action}\\n"
    
    report_content += f"""
## Detected Anomalies
Total: {len(analysis.get('anomalies', []))}

## ML Validation Results
"""
    
    for ml_result in analysis.get('ml_results', []):
        report_content += f"\\n### {ml_result.get('model_name')}\\n"
        report_content += f"Accuracy: {ml_result.get('accuracy', 0) * 100}%\\n"
    
    report_path = UPLOAD_DIR / f"report_{analysis_id}.md"
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    return FileResponse(
        path=report_path,
        filename=f"RCA_Report_{analysis_id}.md",
        media_type="text/markdown"
    )

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
