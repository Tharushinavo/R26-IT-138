from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import InteractionBatch, SingleInteraction, MessageResponse
from app.services import supabase_client
from app.services.validation import validate_interaction

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=MessageResponse)
def log_interactions(batch: InteractionBatch) -> MessageResponse:
    """Save a batch of student interaction events (plan Section 7.2)."""
    if not batch.events:
        raise HTTPException(status_code=400, detail="No events provided")

    validated = []
    for e in batch.events:
        cleaned = validate_interaction(e.model_dump(mode="json"))
        if cleaned:
            validated.append(cleaned)

    if not validated:
        raise HTTPException(status_code=400, detail="All events failed validation")

    result = supabase_client.insert_interactions(validated)

    if result.get("skipped"):
        return MessageResponse(
            message=f"Received {len(validated)} events (Supabase not configured; not persisted)",
            id=batch.events[0].session_id,
        )
    return MessageResponse(
        message=f"Stored {result.get('inserted', 0)} interaction events",
        id=batch.events[0].session_id,
    )


@router.post("/single", response_model=MessageResponse)
def log_single_interaction(interaction: SingleInteraction) -> MessageResponse:
    """Save a single interaction record (plan Section 7.2)."""
    cleaned = validate_interaction(interaction.model_dump(mode="json"))
    if not cleaned:
        raise HTTPException(status_code=400, detail="Interaction failed validation")

    result = supabase_client.insert_interactions([cleaned])

    if result.get("skipped"):
        return MessageResponse(
            message="Interaction received (Supabase not configured; not persisted)",
            id=interaction.question_id,
        )
    return MessageResponse(
        message="Interaction saved successfully",
        id=interaction.question_id,
    )
