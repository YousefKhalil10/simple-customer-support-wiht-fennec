"""Data models for the Customer Support API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    language: Optional[str] = Field("auto", description="'ar', 'en', or 'auto'")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc-123",
                "message": "What is your return policy?",
                "language": "auto",
            }
        }


class ChatResponse(BaseModel):
    session_id: str
    message: str
    route: str = Field(..., description="Detected query category")
    confidence: float = Field(..., ge=0, le=1)
    sources: List[str] = []
    suggestions: List[str] = []
    timestamp: str


class SessionInfo(BaseModel):
    session_id: str
    user_name: str
    message: str


class HealthCheck(BaseModel):
    status: str
    engine_ready: bool
    active_sessions: int
    knowledge_base_docs: int
    timestamp: str


class RAGResult:
    """Internal result from the RAG engine."""

    def __init__(
        self,
        answer: str,
        route: str,
        confidence: float,
        sources: List[str] = None,
        suggestions: List[str] = None,
    ):
        self.answer = answer
        self.route = route
        self.confidence = confidence
        self.sources = sources or []
        self.suggestions = suggestions or []
