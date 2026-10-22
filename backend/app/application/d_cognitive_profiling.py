"""Component D's cognitive profiling use cases (Component D authorization, D-011; API contract v4
rows 3-6).

FOUR OPERATIONS: store a run and get its profile back; read one run's profile; read the learner's
latest; read their history.

IDEMPOTENCY, AND WHY IT IS SHAPED THIS WAY. The ``session_id`` in the path IS the idempotency key
-- there is no ``Idempotency-Key`` header, exactly as Component C decided for the same reason: the
natural key is already in the request, and a second key would let a client claim two identities for
one run. Three mechanisms, in order:

1. ``pg_advisory_xact_lock`` scoped to the ``session_id``, taken BEFORE the existence check, so two
   concurrent submits for one run serialize instead of both deciding to insert;
2. the existence check itself, which returns the stored profile for an identical repeat;
3. ``uq_d_interactions_session_question`` and ``uq_d_cognitive_profiles_session``, which make the
   second insert impossible at the database if the lock is ever bypassed. The ``IntegrityError``
   catch turns that into a 409 rather than a 500.

A REPEAT IS NOT A RECOMPUTATION. An identical re-submit returns the STORED profile, not a freshly
computed one. If the heuristic is ever recalibrated, a retried request must not come back with
different levels than the first attempt did -- that would make a network hiccup look like the child
having changed.

WHY A FOREIGN ``session_id`` IS A 404 AND NOT A 403. ``session_id`` is unique globally, so a
profile belonging to another learner is FOUND and then refused. Refusing it as 404 rather than 403
is deliberate: a 403 would confirm that the session exists and belongs to somebody, which is a fact
about another child.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.application.d_features import capped_mean_response_time_ms, compute_features
from app.application.d_learner_access import provenance, require_learner
from app.application.d_model_profile import predict_levels
from app.application.d_recommendation import build_recommendation
from app.application.d_rule_profile import (
    MODEL_VERSION,
    attention_level,
    confidence_score,
    memory_level,
    number_sense_level,
    processing_speed_level,
)
from app.core.errors import ConflictError, ResourceNotFoundError
from app.domain.d_profile import (
    DCognitiveProfile,
    DCognitiveProfileFeatures,
    DCognitiveProfileResponse,
    DInteractionEvent,
    DLatestProfileResponse,
    DProfileListResponse,
    Language,
)
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import DCognitiveProfileRecord, DInteractionRecord
from app.infrastructure.repositories import DCognitiveProfileRepository, DInteractionRepository
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def _event_identity(event: DInteractionEvent) -> tuple:
    """Every field of one event, in a fixed order, for comparing a resubmit against what is
    stored.

    All eleven fields are included on purpose. A resubmit that differs in any of them is a
    DIFFERENT run claiming the same id, which is the 409 case -- comparing only the question ids
    would let a client silently replace a run's timings and keep the original profile.
    """
    return (
        event.question_id,
        event.topic,
        event.difficulty,
        event.response_time_sec,
        event.attempts,
        event.response_matched,
        event.assist_used,
        event.click_count,
        event.session_time_sec,
        event.time_between_actions,
        event.error_type,
    )


def _record_identity(record: DInteractionRecord) -> tuple:
    """The same tuple, from a stored row.

    The three floats compare exactly rather than approximately: ``Float`` is PostgreSQL
    ``double precision`` and a Python float is an IEEE-754 double, so the value that went in is
    bit-for-bit the value that comes back. There is no rounding to tolerate, and a tolerance here
    would quietly accept a resubmit whose timings had genuinely changed.
    """
    return (
        record.question_id,
        record.topic,
        record.difficulty,
        record.response_time_sec,
        record.attempts,
        record.response_matched,
        record.assist_used,
        record.click_count,
        record.session_time_sec,
        record.time_between_actions,
        record.error_type,
    )


class DCognitiveProfilingService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    # ------------------------------------------------------------------ reads

    async def get_for_session(
        self,
        principal: AuthenticatedPrincipal,
        request_id: str,
        *,
        session_id: UUID,
        language: Language,
    ) -> DCognitiveProfileResponse:
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            record = await DCognitiveProfileRepository(uow.session).find_for_session(session_id)
            if record is None or record.learner_id != learner_id:
                raise ResourceNotFoundError()
            return DCognitiveProfileResponse(
                profile=_to_public(record, language), request_id=request_id
            )

    async def get_latest(
        self, principal: AuthenticatedPrincipal, request_id: str, *, language: Language
    ) -> DLatestProfileResponse:
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            record = await DCognitiveProfileRepository(uow.session).find_latest_for_learner(learner_id)
            return DLatestProfileResponse(
                profile=_to_public(record, language) if record is not None else None,
                request_id=request_id,
            )

    async def list_history(
        self, principal: AuthenticatedPrincipal, request_id: str, *, limit: int, language: Language
    ) -> DProfileListResponse:
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            records = await DCognitiveProfileRepository(uow.session).list_for_learner(learner_id, limit)
            return DProfileListResponse(
                items=[_to_public(record, language) for record in records], request_id=request_id
            )

    # ------------------------------------------------------------------ write

    async def create_for_session(
        self,
        principal: AuthenticatedPrincipal,
        request_id: str,
        *,
        session_id: UUID,
        language: Language,
        events: list[DInteractionEvent],
    ) -> DCognitiveProfileResponse:
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"d_profile.create:{session_id}"},
            )

            profiles = DCognitiveProfileRepository(uow.session)
            existing = await profiles.find_for_session(session_id)
            if existing is not None:
                if existing.learner_id != learner_id:
                    raise ResourceNotFoundError()
                stored = await DInteractionRepository(uow.session).list_for_session(session_id)
                submitted_identity = sorted(_event_identity(event) for event in events)
                stored_identity = sorted(_record_identity(record) for record in stored)
                if submitted_identity != stored_identity:
                    raise ConflictError()
                # An identical repeat: the stored profile, untouched and not recomputed.
                return DCognitiveProfileResponse(
                    profile=_to_public(existing, language), request_id=request_id
                )

            features = compute_features(events)
            generated_at = datetime.now(UTC)
            profile_id = uuid4()
            # The owner's trained model first (d_model_profile); the rule-based profile whenever it
            # cannot be used, as compD's predict_profile did. `model_version` records which one.
            levels = predict_levels(events)
            if levels is not None:
                memory, attention, number_sense = (
                    levels.memory_level,
                    levels.attention_level,
                    levels.number_sense_level,
                )
                speed, version = levels.processing_speed_level, levels.model_version
            else:
                memory = memory_level(features)
                attention = attention_level(features)
                number_sense = number_sense_level(features)
                # Takes the per-response-capped mean, NOT features.avg_response_time_ms, which is
                # published uncapped on purpose. See d_features.capped_mean_response_time_ms.
                speed = processing_speed_level(capped_mean_response_time_ms(events))
                version = MODEL_VERSION
            record = DCognitiveProfileRecord(
                d_cognitive_profile_id=profile_id,
                learner_id=learner_id,
                session_id=session_id,
                memory_level=memory,
                attention_level=attention,
                number_sense_level=number_sense,
                processing_speed_level=speed,
                # compD's confidence expression is used for both paths (model.py:449-452).
                confidence_score=confidence_score(features),
                model_version=version,
                # The vector is stored, the recommendation TEXT is not -- it is rebuilt in the
                # language of each read. See DCognitiveProfileRecord's docstring.
                features=features.model_dump(),
                generated_at=generated_at,
                **provenance(
                    resource_type="d_cognitive_profile",
                    resource_id=profile_id,
                    request_id=request_id,
                    operation="d_cognitive_profile.created",
                ),
            )

            try:
                for event in events:
                    interaction_id = uuid4()
                    await DInteractionRepository(uow.session).add(
                        DInteractionRecord(
                            d_interaction_id=interaction_id,
                            learner_id=learner_id,
                            session_id=session_id,
                            question_id=event.question_id,
                            topic=event.topic,
                            difficulty=event.difficulty,
                            response_time_sec=event.response_time_sec,
                            attempts=event.attempts,
                            response_matched=event.response_matched,
                            assist_used=event.assist_used,
                            click_count=event.click_count,
                            session_time_sec=event.session_time_sec,
                            time_between_actions=event.time_between_actions,
                            error_type=event.error_type,
                            **provenance(
                                resource_type="d_interaction",
                                resource_id=interaction_id,
                                request_id=request_id,
                                operation="d_interaction.recorded",
                            ),
                        )
                    )
                await profiles.add(record)
            except IntegrityError as exc:
                # A genuine race: another request inserted this session between the lock and
                # here, or the same question id arrived twice past the DTO's own check.
                raise ConflictError() from exc

            await uow.commit()
            return DCognitiveProfileResponse(
                profile=_to_public(record, language), request_id=request_id
            )


def _to_public(record: DCognitiveProfileRecord, language: Language) -> DCognitiveProfile:
    """Build the public shape, including the recommendation text in the requested language.

    ``features`` is revalidated through the DTO rather than passed through as a raw dict: the
    column is JSONB, so what comes back is whatever was written, and a profile stored before a
    feature was added or renamed would otherwise flow into the response unchecked. A mismatch
    here is a 500 rather than a silently malformed payload, which is the right failure for a
    schema drift nobody has migrated.
    """
    features = DCognitiveProfileFeatures.model_validate(record.features)
    return DCognitiveProfile(
        session_id=record.session_id,
        memory_level=record.memory_level,  # type: ignore[arg-type]
        attention_level=record.attention_level,  # type: ignore[arg-type]
        number_sense_level=record.number_sense_level,  # type: ignore[arg-type]
        processing_speed_level=record.processing_speed_level,  # type: ignore[arg-type]
        confidence_score=record.confidence_score,
        recommendation=build_recommendation(
            memory_level=record.memory_level,  # type: ignore[arg-type]
            attention_level=record.attention_level,  # type: ignore[arg-type]
            number_sense_level=record.number_sense_level,  # type: ignore[arg-type]
            processing_speed_level=record.processing_speed_level,  # type: ignore[arg-type]
            features=features,
            language=language,
        ),
        model_version=record.model_version,
        features=features,
        generated_at=record.generated_at,
    )
