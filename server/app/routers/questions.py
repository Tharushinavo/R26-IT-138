"""Questions endpoint: serves math questions from the database or seed data.
Plan Section 7.2 - GET /questions
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas import AIQuestionGenerateRequest, MessageResponse, Question, QuestionCreate, QuestionUpdate
from app.routers.auth import get_current_teacher
from app.services import supabase_client
from app.services.question_ai import generate_questions as generate_ai_questions

router = APIRouter(prefix="/questions", tags=["questions"])


# Seed questions for when Supabase is not configured
SEED_QUESTIONS: List[Question] = [
    # Counting
    Question(id="Q001", question_code="CNT-001", topic="Counting", difficulty="Easy",
             question_text="What number comes after 8?", correct_answer="9",
             options=["7", "8", "9", "10"]),
    Question(id="Q002", question_code="CNT-002", topic="Counting", difficulty="Easy",
             question_text="What number comes before 15?", correct_answer="14",
             options=["13", "14", "16", "12"]),
    Question(id="Q003", question_code="CNT-003", topic="Counting", difficulty="Easy",
             question_text="How many fingers are on two hands?", correct_answer="10",
             options=["8", "10", "12", "5"]),

    # Number Recognition
    Question(id="Q004", question_code="NR-001", topic="Number Recognition", difficulty="Easy",
             question_text="Which one is number 12?", correct_answer="12",
             options=["21", "12", "11", "22"]),
    Question(id="Q005", question_code="NR-002", topic="Number Recognition", difficulty="Easy",
             question_text="Which one is number 9?", correct_answer="9",
             options=["6", "9", "0", "8"]),

    # Number Comparison
    Question(id="Q006", question_code="NC-001", topic="Number Comparison", difficulty="Easy",
             question_text="Which number is bigger: 7 or 12?", correct_answer="12",
             options=["7", "12"]),
    Question(id="Q007", question_code="NC-002", topic="Number Comparison", difficulty="Easy",
             question_text="Which number is smaller: 18 or 14?", correct_answer="14",
             options=["18", "14"]),
    Question(id="Q008", question_code="NC-003", topic="Number Comparison", difficulty="Medium",
             question_text="Which number is bigger: 45 or 54?", correct_answer="54",
             options=["45", "54"]),

    # Addition
    Question(id="Q009", question_code="ADD-001", topic="Addition", difficulty="Easy",
             question_text="2 + 3 = ?", correct_answer="5",
             options=["4", "5", "6", "3"]),
    Question(id="Q010", question_code="ADD-002", topic="Addition", difficulty="Easy",
             question_text="5 + 4 = ?", correct_answer="9",
             options=["8", "9", "10", "7"]),
    Question(id="Q011", question_code="ADD-003", topic="Addition", difficulty="Medium",
             question_text="8 + 7 = ?", correct_answer="15",
             options=["14", "15", "16", "13"]),
    Question(id="Q012", question_code="ADD-004", topic="Addition", difficulty="Medium",
             question_text="12 + 9 = ?", correct_answer="21",
             options=["19", "20", "21", "22"]),
    Question(id="Q013", question_code="ADD-005", topic="Addition", difficulty="Hard",
             question_text="17 + 16 = ?", correct_answer="33",
             options=["31", "32", "33", "34"]),

    # Subtraction
    Question(id="Q014", question_code="SUB-001", topic="Subtraction", difficulty="Easy",
             question_text="8 - 3 = ?", correct_answer="5",
             options=["4", "5", "6", "3"]),
    Question(id="Q015", question_code="SUB-002", topic="Subtraction", difficulty="Easy",
             question_text="10 - 6 = ?", correct_answer="4",
             options=["3", "4", "5", "6"]),
    Question(id="Q016", question_code="SUB-003", topic="Subtraction", difficulty="Medium",
             question_text="15 - 7 = ?", correct_answer="8",
             options=["7", "8", "9", "6"]),
    Question(id="Q017", question_code="SUB-004", topic="Subtraction", difficulty="Hard",
             question_text="25 - 18 = ?", correct_answer="7",
             options=["5", "6", "7", "8"]),

    # Simple Word Problems
    Question(id="Q018", question_code="WP-001", topic="Addition", difficulty="Medium",
             question_text="You have 6 apples. Your friend gives you 5 more. How many apples do you have?",
             correct_answer="11", options=["10", "11", "12", "9"]),
    Question(id="Q019", question_code="WP-002", topic="Subtraction", difficulty="Medium",
             question_text="There are 12 birds on a tree. 4 fly away. How many are left?",
             correct_answer="8", options=["7", "8", "9", "6"]),
    Question(id="Q020", question_code="WP-003", topic="Addition", difficulty="Hard",
             question_text="A box has 14 red balls and 9 blue balls. How many balls in total?",
             correct_answer="23", options=["21", "22", "23", "24"]),
]


@router.get("", response_model=List[Question])
def get_questions(
    topic: Optional[str] = Query(default=None, description="Filter by topic"),
    difficulty: Optional[str] = Query(default=None, description="Filter by difficulty"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Return available math questions. Falls back to seed data if Supabase is not configured."""
    # Try Supabase first
    db_questions = supabase_client.fetch_questions(topic=topic, difficulty=difficulty, limit=limit)
    if db_questions:
        return db_questions

    # Fallback to seed questions
    result = SEED_QUESTIONS
    if topic:
        result = [q for q in result if q.topic.lower() == topic.lower()]
    if difficulty:
        result = [q for q in result if q.difficulty.lower() == difficulty.lower()]
    return result[:limit]


@router.post("", response_model=Question, status_code=status.HTTP_201_CREATED)
def create_question(
    body: QuestionCreate,
    current_user: dict = Depends(get_current_teacher),
) -> Question:
    """Create a cognitive/math question. Requires teacher/admin role."""
    created = supabase_client.insert_question(body.model_dump(mode="json", exclude_none=True))
    if not created:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create question. Check Supabase configuration and questions table.",
        )
    return created


@router.put("/{question_id}", response_model=Question)
def update_question(
    question_id: str,
    body: QuestionUpdate,
    current_user: dict = Depends(get_current_teacher),
) -> Question:
    """Update a cognitive/math question. Requires teacher/admin role."""
    patch = body.model_dump(mode="json", exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields provided")
    updated = supabase_client.update_question(question_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Question not found or Supabase unavailable")
    return updated


@router.delete("/{question_id}", response_model=MessageResponse)
def delete_question(
    question_id: str,
    current_user: dict = Depends(get_current_teacher),
) -> MessageResponse:
    """Delete a cognitive/math question. Requires teacher/admin role."""
    ok = supabase_client.delete_question(question_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Question not found or Supabase unavailable")
    return MessageResponse(message="Question deleted", id=question_id)


@router.post("/generate", response_model=List[Question], status_code=status.HTTP_201_CREATED)
def generate_questions(
    body: AIQuestionGenerateRequest,
    current_user: dict = Depends(get_current_teacher),
) -> List[Question]:
    """Generate questions with an AI provider and save them into Supabase."""
    try:
        drafts = generate_ai_questions(
            provider=body.provider,
            api_key=body.api_key,
            topic=body.topic,
            difficulty=body.difficulty,
            count=body.count,
            model=body.model,
            instructions=body.instructions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    created: List[Question] = []
    for draft in drafts:
        row = supabase_client.insert_question(draft.model_dump(mode="json", exclude_none=True))
        if row:
            created.append(Question(**row))

    if not created:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI generated questions, but none were saved. Check Supabase configuration and questions table.",
        )
    return created
