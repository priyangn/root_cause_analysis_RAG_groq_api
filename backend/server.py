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
import re

from models import *
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    create_reset_token,
    hash_reset_token,
    reset_token_expiry,
)
from orchestrator import AnalysisPipeline
from vector_store import VectorStore
from agents.base_agent import BaseAgent
from email_service import email_configured, send_password_reset_email

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

@api_router.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(payload: ForgotPasswordRequest):
    """Start password reset. Always returns a generic message (avoids email enumeration)."""
    generic = (
        "If an account exists for that email, password reset instructions are available. "
        "The link expires in 1 hour."
    )
    email = payload.email.strip().lower()
    # Case-insensitive match for legacy accounts
    user = await db.users.find_one(
        {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
        {"_id": 0},
    )

    if not user:
        # Same shape as success path when we don't return a URL
        return ForgotPasswordResponse(message=generic)

    raw_token = create_reset_token()
    token_hash = hash_reset_token(raw_token)
    expires_at = reset_token_expiry()

    await db.password_resets.delete_many({"user_id": user["id"]})
    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": email,
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
        "used": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if not frontend_url:
        # Prefer public site URL; fall back to Render web service name
        frontend_url = "https://causesense-web.onrender.com"

    reset_url = f"{frontend_url}/reset-password?token={raw_token}"

    emailed = False
    if email_configured():
        emailed = send_password_reset_email(email, reset_url)

    # Without SMTP (typical on free Render), return the link so the user can reset
    return_token = os.environ.get("PASSWORD_RESET_RETURN_TOKEN", "true").lower() in (
        "1", "true", "yes"
    )
    if emailed:
        return ForgotPasswordResponse(message=generic)
    if return_token:
        return ForgotPasswordResponse(
            message=(
                "Password reset link created. Email delivery is not configured on this server, "
                "so use the link below (expires in 1 hour)."
            ),
            reset_url=reset_url,
        )
    logger.info("Password reset requested for %s (token created; email/link not returned)", email)
    return ForgotPasswordResponse(message=generic)

@api_router.post("/auth/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest):
    """Complete password reset with a one-time token."""
    token = (payload.token or "").strip()
    if not token or len(payload.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Invalid token or password (minimum 6 characters)",
        )

    token_hash = hash_reset_token(token)
    reset_doc = await db.password_resets.find_one(
        {"token_hash": token_hash, "used": False},
        {"_id": 0},
    )
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    try:
        expires_at = datetime.fromisoformat(reset_doc["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    if datetime.now(timezone.utc) > expires_at:
        await db.password_resets.update_one(
            {"token_hash": token_hash},
            {"$set": {"used": True}},
        )
        raise HTTPException(status_code=400, detail="Reset link has expired. Request a new one.")

    await db.users.update_one(
        {"id": reset_doc["user_id"]},
        {"$set": {"password_hash": get_password_hash(payload.new_password)}},
    )
    await db.password_resets.update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
    )
    # Invalidate any other outstanding tokens for this user
    await db.password_resets.update_many(
        {"user_id": reset_doc["user_id"], "used": False},
        {"$set": {"used": True}},
    )

    return MessageResponse(message="Password updated successfully. You can sign in with your new password.")

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
    ).sort("created_at", -1).to_list(50)
    
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

        try:
            agent = BaseAgent()
            prompt = build_chat_prompt(message.message, analysis_context)
            # Pass system rules as system message; user content is the scoped prompt
            response = await agent.send_message(
                "You are CauseSense AI. Follow the safety and scope rules in the user message strictly.",
                prompt,
            )
            if not response or not str(response).strip():
                response = DECLINE_MESSAGE

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
