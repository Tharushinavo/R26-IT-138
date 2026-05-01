from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


# ---------- Questions ----------

class Question(BaseModel):
    """A math question stored in the database."""
    id: str
    question_code: Optional[str] = None
    topic: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    question_text: str
    correct_answer: str
    options: Optional[List[str]] = None
    created_at: Optional[datetime] = None


class QuestionCreate(BaseModel):
    question_code: Optional[str] = None
    topic: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    question_text: str
    correct_answer: str
    options: Optional[List[str]] = None


# ---------- Interaction events (raw data captured during activity) ----------

class InteractionEvent(BaseModel):
    """A single interaction record from a math activity."""
    student_id: str = Field(..., description="Student identifier")
    session_id: str = Field(..., description="Activity session identifier")
    question_id: str

    topic: str = Field("Addition", description="Mathematics topic")
    difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"

    response_time_sec: float = Field(..., ge=0, description="Time in seconds to answer")
    attempts: int = Field(1, ge=1)
    is_correct: bool
    hint_used: bool = False
    click_count: int = Field(0, ge=0, description="Number of taps/clicks during the question")
    session_time_sec: float = Field(0, ge=0, description="Total session duration so far")
    time_between_actions: float = Field(0, ge=0, description="Average delay between user actions")
    error_type: Literal["none", "calculation", "conceptual", "careless", "unknown"] = "none"

    expected_answer: Optional[str] = None
    given_answer: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class InteractionBatch(BaseModel):
    events: List[InteractionEvent]


class SingleInteraction(BaseModel):
    """Single interaction record (plan Section 7.2)."""
    student_id: str
    question_id: str
    topic: str = "Addition"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"
    response_time_sec: float = Field(..., ge=0)
    attempts: int = Field(1, ge=1)
    is_correct: bool
    hint_used: bool = False
    click_count: int = Field(0, ge=0)
    session_time_sec: float = Field(0, ge=0)
    time_between_actions: float = Field(0, ge=0)
    error_type: Literal["none", "calculation", "conceptual", "careless", "unknown"] = "none"


# ---------- Aggregated features (the model's input row) ----------

class CognitiveFeatures(BaseModel):
    accuracy: float = Field(..., ge=0.0, le=1.0)
    avg_response_time_ms: float = Field(..., ge=0.0)
    response_time_std_ms: float = Field(..., ge=0.0)
    avg_attempts: float = Field(..., ge=1.0)
    retry_rate: float = Field(..., ge=0.0, le=1.0)
    hint_rate: float = Field(..., ge=0.0)
    answer_change_rate: float = Field(..., ge=0.0)
    total_questions: int = Field(..., ge=0)


# ---------- Cognitive profile (model output) ----------

Level = Literal["low", "medium", "high"]
SpeedLevel = Literal["Slow", "Moderate", "Fast"]


class CognitiveProfile(BaseModel):
    model_config = {"protected_namespaces": ()}

    student_id: str
    session_id: Optional[str] = None
    memory_level: Level = "medium"
    attention_level: Level = "medium"
    number_sense_level: Level = "medium"
    processing_speed_level: SpeedLevel = "Moderate"
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    recommendation: Optional[str] = None
    model_version: Optional[str] = "rule-based-v1"
    features: CognitiveFeatures
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileRequest(BaseModel):
    """Request to compute a profile from an explicit batch of events."""
    student_id: str
    session_id: Optional[str] = None
    events: List[InteractionEvent]


class PredictRequest(BaseModel):
    """Request to predict a profile from a single interaction (plan Section 7.2)."""
    student_id: str
    question_id: str
    topic: str = "Addition"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"
    response_time_sec: float = Field(..., ge=0)
    attempts: int = Field(1, ge=1)
    is_correct: bool
    hint_used: bool = False
    click_count: int = Field(0, ge=0)
    session_time_sec: float = Field(0, ge=0)
    time_between_actions: float = Field(0, ge=0)
    error_type: str = "none"


class MessageResponse(BaseModel):
    message: str
    id: Optional[str] = None


# ---------- Auth / User ----------

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: Literal["student", "teacher", "parent", "admin"] = "student"

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "student"

class StudentSummary(BaseModel):
    student_id: str
    student_code: Optional[str] = None
    name: Optional[str] = None
    total_interactions: int = 0
    latest_profile: Optional[CognitiveProfile] = None
    last_activity_date: Optional[str] = None
