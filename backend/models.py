from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    full_name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class FileMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    file_type: str
    file_size: int
    file_path: str
    uploaded_at: str

class FileUploadResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    filename: str
    file_type: str
    file_size: int
    message: str

class AnalysisRequest(BaseModel):
    file_ids: List[str]

class HypothesisItem(BaseModel):
    id: str
    title: str
    description: str
    evidence: List[str]
    probability: float

class AnomalyItem(BaseModel):
    timestamp: str
    parameter: str
    value: float
    threshold: float
    severity: str

class MLModelResult(BaseModel):
    model_name: str
    accuracy: float
    feature_importance: Dict[str, float]
    predictions: List[Dict[str, Any]]

class CausalParameter(BaseModel):
    parameter: str
    importance: float
    causality_score: float

class RootCauseResult(BaseModel):
    root_cause: str
    confidence_score: float
    evidence: List[str]
    preventive_actions: List[str]

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    file_ids: List[str]
    status: str
    progress: int
    anomalies: Optional[List[AnomalyItem]] = None
    hypotheses: Optional[List[HypothesisItem]] = None
    ml_results: Optional[List[MLModelResult]] = None
    causal_analysis: Optional[List[CausalParameter]] = None
    root_cause: Optional[RootCauseResult] = None
    created_at: str
    updated_at: str

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    status: str
    progress: int
    message: str

class ChatMessage(BaseModel):
    message: str
    analysis_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None