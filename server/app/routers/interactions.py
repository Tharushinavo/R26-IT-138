from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, HTTPException

from app.schemas import InteractionBatch, SingleInteraction, MessageResponse
from app.services import supabase_client
from app.services.validation import validate_interaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=MessageResponse)
def log_interactions(batch: InteractionBatch) -> MessageResponse:
    """Save a batch of student interaction events (plan Section 7.2)."""
    if not batch.events:
        raise HTTPException(status_code=400, detail="No events provided")

    logger.info(
        "Interaction batch received: student_id=%s session_id=%s events=%s",
        batch.events[0].student_id,
        batch.events[0].session_id,
        len(batch.events),
    )

    validated = []
    for e in batch.events:
        cleaned = validate_interaction(e.model_dump(mode="json"))
        if cleaned:
            validated.append(cleaned)

    if not validated:
        logger.warning("Interaction batch validation failed: all events rejected")
        raise HTTPException(status_code=400, detail="All events failed validation")

    try:
        result = supabase_client.insert_interactions(validated)
    except Exception as e:
        logger.error(f"Failed to insert interactions: {e}")
        logger.error(traceback.format_exc())
        # Still return success - data was received even if DB insert failed
        return MessageResponse(
            message=f"Received {len(validated)} events (DB insert failed: {str(e)[:50]})",
            id=batch.events[0].session_id,
        )

    if result.get("skipped"):
        logger.warning(
            "Interaction batch not persisted: student_id=%s session_id=%s events=%s",
            batch.events[0].student_id,
            batch.events[0].session_id,
            len(validated),
        )
        return MessageResponse(
            message=f"Received {len(validated)} events (Supabase not configured; not persisted)",
            id=batch.events[0].session_id,
        )
    logger.info(
        "Interaction batch persisted: student_id=%s session_id=%s inserted=%s",
        batch.events[0].student_id,
        batch.events[0].session_id,
        result.get("inserted", 0),
    )
    return MessageResponse(
        message=f"Stored {result.get('inserted', 0)} interaction events",
        id=batch.events[0].session_id,
    )


@router.post("/single", response_model=MessageResponse)
def log_single_interaction(interaction: SingleInteraction) -> MessageResponse:
    """Save a single interaction record (plan Section 7.2)."""
    logger.info(
        "Single interaction received: student_id=%s question_id=%s",
        interaction.student_id,
        interaction.question_id,
    )
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
