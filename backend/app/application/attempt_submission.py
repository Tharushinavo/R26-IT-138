"""BE4c: attempt submission + first-attempt-only atomic BKT (BEplan §9 BE4.3 + BE4.4).

Every scientific step goes through ``app.infrastructure.live_engine.adapter.LiveEngineAdapter``
(imported lazily, function-scope — see the note on ``OpportunitySelectionService`` this mirrors):
``normalize_answer``/``answers_equivalent`` for server-side correctness, ``predict``/
``posterior``/``update`` for the BKT transition. No formula is reimplemented here. The pinned
TEST_FIXTURE_ONLY BKT config is the same ``opportunity_selection._ENGINEERING_BKT_CONFIG`` used
by BE4b — never the population-conditioned governed table.

FIRST-ATTEMPT-ONLY + ATOMIC (BE4.4): ``b_skill_state_transitions.uq_b_skill_state_transitions_
opportunity`` is simultaneously the DB-level "claim" on the unique first-attempt observation for
an opportunity and the immutable transition row itself. The insert only happens when
``attempt_index == 1`` and the event is a real ``RESPONSE`` (never for ``TIMEOUT``, never for
attempt 2+); a concurrent duplicate claim for the same opportunity loses the unique-index race
and surfaces as ``ConflictError`` — see ``LearnerSkillStateRepository.get_for_update`` for the
``populate_existing=True`` note on the skill-state row lock. The attempt insert, the transition
insert, and the skill-state update all happen in the same unit of work and commit together
(BE4.4 step 7); any failure before ``uow.commit()`` rolls back all three via
``SqlAlchemyUnitOfWork.__aexit__``.

REPLAY: reuses the same ``b_idempotency_records`` mechanism BE2's session commands use
(``app.application.b_session_lifecycle``) — a duplicate ``Idempotency-Key`` returns the original
canonical response and performs no second write of any kind.

Infra/DB failure ≠ learner failure: a genuine ``SQLAlchemyError`` (not an ``IntegrityError`` we
already understand and map to a conflict) is never allowed to leave a partially-applied attempt
or BKT observation behind — nothing commits until every step above succeeds, so the automatic
rollback on an uncaught exception is what actually enforces this; the service additionally
translates the failure to ``TechnicalFailureError`` so it is never misreported as an incorrect
learner response.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.opportunity_selection import _ENGINEERING_BKT_CONFIG
from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError, TechnicalFailureError
from app.domain.b_attempt import AttemptResponse, SubmitResponseRequest
from app.domain.live_engine.errors import LiveEngineError
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import AppUser, AttemptRecord, IdempotencyRecord, SkillStateTransitionRecord
from app.infrastructure.repositories import (
    AppUserRepository,
    AttemptRepository,
    IdempotencyRecordRepository,
    ItemOpportunityRepository,
    LearnerSkillStateRepository,
    SessionRecordRepository,
    SkillStateTransitionRepository,
    TaskInstanceRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


if TYPE_CHECKING:
    # Deferred for the same reason as OpportunitySelectionService: only actually evaluating a
    # RESPONSE attempt requires the vendored component_b_generator wheel.
    from app.infrastructure.live_engine.adapter import LiveEngineAdapter


SCHEMA_REVISION = "20260728_0001"
IDEMPOTENCY_OPERATION = "b_attempt.submit"


def body_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "actor_user_id": user_id,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_B_ATTEMPT_SUBMISSION_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


class AttemptSubmissionService:
    """BE4c application service: the ``POST /api/v1/b/sessions/{session_id}/opportunities/
    {item_opportunity_id}/responses`` use case."""

    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def _require_learner(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> tuple[AppUser, UUID]:
        found = await AppUserRepository(session).find_with_learner_link_by_subject(principal.user_id)
        if found is None:
            raise ResourceNotFoundError()
        user, link = found
        if user.profile_type != "LEARNER":
            raise ForbiddenError()
        if link is None:
            raise ResourceNotFoundError()
        return user, link.learner_id

    async def _reserve_idempotency(
        self, session: AsyncSession, user: AppUser, key: str, fingerprint_value: str, request_id: str
    ) -> tuple[IdempotencyRecord, dict[str, object] | None]:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": f"{user.user_id}:POST:{IDEMPOTENCY_OPERATION}:{key}"},
        )
        repository = IdempotencyRecordRepository(session)
        existing = await repository.find_scoped(user.user_id, "POST", IDEMPOTENCY_OPERATION, key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint_value:
                raise ConflictError()
            if existing.processing_status == "succeeded" and existing.canonical_response is not None:
                return existing, existing.canonical_response
            raise ConflictError()
        record_id = uuid4()
        record = IdempotencyRecord(
            idempotency_record_id=record_id,
            http_method="POST",
            operation_identifier=IDEMPOTENCY_OPERATION,
            idempotency_key=key,
            request_fingerprint=fingerprint_value,
            processing_status="in_progress",
            canonical_response=None,
            response_status=None,
            expires_at_utc=datetime.now(UTC) + timedelta(hours=24),
            **provenance(user.user_id, request_id, IDEMPOTENCY_OPERATION, "b_idempotency_record", record_id),
        )
        await repository.add(record)
        return record, None

    @staticmethod
    def _finish(record: IdempotencyRecord, response: dict[str, object], status_code: int) -> None:
        record.processing_status = "succeeded"
        record.canonical_response = response
        record.response_status = status_code

    async def submit_response(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
        body: SubmitResponseRequest,
    ) -> AttemptResponse:
        async with self._uow_factory() as uow:
            try:
                response = await self._submit_response_unguarded(
                    uow.session, principal, session_id, item_opportunity_id, idempotency_key, request_id, body
                )
                # Committing here, still inside the guard, means a failure injected at this last
                # step (BE4.4 step 7/8 — "commit the attempt, observation, transition, and state
                # together") is translated the same way as any earlier infra failure, and the
                # automatic rollback in SqlAlchemyUnitOfWork.__aexit__ still discards everything
                # that was only flushed, never committed.
                await uow.commit()
            except IntegrityError as exc:
                raise ConflictError() from exc
            except LiveEngineError as exc:
                raise ConflictError() from exc
            except SQLAlchemyError as exc:
                raise TechnicalFailureError() from exc
            return response

    async def _submit_response_unguarded(
        self,
        session: AsyncSession,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
        body: SubmitResponseRequest,
    ) -> AttemptResponse:
        user, learner_id = await self._require_learner(session, principal)

        session_row = await SessionRecordRepository(session).get_owned(session_id, learner_id)
        if session_row is None or session_row.state != "active":
            raise ResourceNotFoundError()

        fingerprint_value = body_fingerprint(
            {
                "session_id": str(session_id),
                "item_opportunity_id": str(item_opportunity_id),
                **body.model_dump(),
            }
        )
        idem, replay = await self._reserve_idempotency(session, user, idempotency_key, fingerprint_value, request_id)
        if replay is not None:
            return AttemptResponse.model_validate(replay)

        opportunity = await ItemOpportunityRepository(session).get_for_update(item_opportunity_id)
        if opportunity is None or opportunity.session_id != session_id or opportunity.learner_id != learner_id:
            raise ResourceNotFoundError()
        if opportunity.state != "OPEN":
            raise ConflictError()

        now = datetime.now(UTC)
        attempt_index = await AttemptRepository(session).count_for_opportunity(item_opportunity_id) + 1
        # A DEADLINE ONLY BINDS A LEARNER WHO WAS CONFIRMED TO HAVE SEEN THE QUESTION.
        #
        # `presented_at_utc is None` means no presentation acknowledgement ever landed, so the
        # deadline still in force is the FAIL-SAFE one written at SELECTION. That clock measures
        # server, prefetch and network time -- not the child's answering time. Judging a submission
        # against it charges the child for infrastructure, which is precisely what
        # `component-b-closure-decisions.json`'s timeout-policy ruling forbids and what
        # `anchor_presentation` quotes verbatim: "infrastructure failure is never learner failure.
        # Anchoring at selection charged the child for server and network time -- prefetch included
        # -- which is exactly that."
        #
        # OBSERVED IN PRODUCTION, 2026-10-10, which is why this is not theoretical: an opportunity
        # created at 13:00:09 with `presented_at_utc = NULL` and a deadline of created + 302s. The
        # child opened it later, answered in about one second, and was shown "Time's up" -- on a
        # question the system has no record of ever having shown them. Home warms Component B on
        # mount, so the opportunity can be minted minutes before the child enters; the
        # acknowledgement is what normally re-anchors the clock, and on a degraded network its four
        # attempts over ~6s can all fail.
        #
        # SO: an unacknowledged opportunity cannot time out. We have no trustworthy origin from
        # which to measure, and inventing one would be guessing against the child. The null
        # `presented_at_utc` is left exactly as it is -- it IS the audit trail of why this
        # submission was not treated as late.
        #
        # GOVERNANCE, STATED PLAINLY: this changes which attempts are eligible to become BKT
        # observations. A first attempt that would previously have been recorded as `TIMEOUT`
        # (contributing nothing) is now a `RESPONSE` (which, at `attempt_index == 1`, does observe).
        # The first-attempt gate itself is untouched. By this module's own standard that makes the
        # eligibility consequence a Gate B matter; it is recorded in buildLog2.md for the owner
        # rather than left implicit in a one-line condition.
        presentation_confirmed = opportunity.presented_at_utc is not None
        is_timeout = presentation_confirmed and now >= opportunity.timeout_deadline_utc

        response_matched: bool | None = None
        # BF-2 — persist what the learner actually submitted, even on timeout.
        #
        # Before this fix, `submitted_value` stayed `None` on the timeout branch: the request body
        # was never read, so a late-but-correct answer was destroyed the moment the request
        # completed, irrecoverably. That is now fixed, and *only* that: `response_matched` stays
        # `None` and `event_kind` stays `"TIMEOUT"` below, exactly as before, so this attempt still
        # contributes no BKT observation (the first-attempt gate is `attempt_index == 1 and
        # event_kind == "RESPONSE"` — untouched). Comparing this value for correctness, or splitting
        # "late response" from "true non-response" into separate taxonomy categories, would change
        # what counts as a BKT observation and is a Gate B governance decision, not this fix. This
        # is data preservation only.
        submitted_value: str | None = body.submitted_value if is_timeout else None
        event_kind = "TIMEOUT" if is_timeout else "RESPONSE"

        if not is_timeout:
            task_instance = await TaskInstanceRepository(session).find_by_opportunity(item_opportunity_id)
            if task_instance is None:
                raise ConflictError()

            from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

            adapter: "LiveEngineAdapter" = LiveEngineAdapter()
            submitted_value = body.submitted_value
            accepted = (task_instance.correct_answer, *task_instance.allowed_equivalent_answers)
            response_matched = any(
                adapter.answers_equivalent(submitted_value, candidate) for candidate in accepted
            )
            # BE-C2 Part B — tolerant place-value comparison, scoped to structured templates only.
            #
            # ``answers_equivalent`` is ``normalize_answer(a) == normalize_answer(b)``, which strips
            # outer whitespace only. So a child typing "100+20+3" instead of "100 + 20 + 3" was
            # marked wrong on a decomposition item, purely over spacing.
            #
            # SCOPE — this must not become the general comparison. On an arithmetic template whose
            # answer is 12, a tolerant parse would start accepting "10+2", i.e. accepting a
            # restatement of the problem as its answer. The gate is
            # ``allowed_equivalent_answers``: ``answers.registry.allowed_equivalent_answers``
            # returns a non-empty tuple exactly for the structured place-value templates and an
            # empty one for every other template, so a non-empty list here *is* the "this template
            # admits equivalent written forms" signal. That is deliberately used instead of
            # importing the package's private ``_STRUCTURED_EQUIVALENCE_TEMPLATES``: no duplicated
            # template list in the application layer means no list to drift.
            if not response_matched and task_instance.allowed_equivalent_answers:
                response_matched = any(
                    adapter.structured_forms_equivalent(submitted_value, candidate)
                    for candidate in accepted
                )

        attempt_id = uuid4()
        attempt_record = AttemptRecord(
            attempt_id=attempt_id,
            item_opportunity_id=item_opportunity_id,
            learner_id=learner_id,
            attempt_index=attempt_index,
            event_kind=event_kind,
            submitted_value=submitted_value,
            response_matched=response_matched,
            client_elapsed_ms=body.client_elapsed_ms,
            server_submitted_at_utc=now,
            **provenance(user.user_id, request_id, "b_attempt.recorded", "b_attempt", attempt_id),
        )
        session.add(attempt_record)
        await session.flush()

        if attempt_index == 1 and event_kind == "RESPONSE":
            await self._apply_first_attempt_bkt(
                session,
                user=user,
                request_id=request_id,
                learner_id=learner_id,
                skill_id=opportunity.skill_id,
                item_opportunity_id=item_opportunity_id,
                attempt_id=attempt_id,
                response_matched=bool(response_matched),
            )

        response = AttemptResponse(
            item_opportunity_id=item_opportunity_id,
            attempt_index=attempt_index,
            event_kind=event_kind,
            response_matched=response_matched,
            server_submitted_at_utc=now,
            request_id=request_id,
        )
        self._finish(idem, response.model_dump(mode="json"), 201)
        return response

    async def _apply_first_attempt_bkt(
        self,
        session: AsyncSession,
        *,
        user: AppUser,
        request_id: str,
        learner_id: UUID,
        skill_id: str,
        item_opportunity_id: UUID,
        attempt_id: UUID,
        response_matched: bool,
    ) -> None:
        from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

        adapter: "LiveEngineAdapter" = LiveEngineAdapter()

        skill_state = await LearnerSkillStateRepository(session).get_for_update(learner_id, skill_id)
        if skill_state is None:
            raise ConflictError()
        params = _ENGINEERING_BKT_CONFIG.skill_params[skill_id]

        p_l_before = skill_state.p_l
        predicted_probability = adapter.predict(p_l_before, params.p_g, params.p_s)
        posterior_p_l = adapter.posterior(p_l_before, response_matched, params.p_g, params.p_s)
        p_l_after = adapter.update(p_l_before, response_matched, params.p_g, params.p_s, params.p_t)

        transition_id = uuid4()
        transition_record = SkillStateTransitionRecord(
            skill_state_transition_id=transition_id,
            learner_id=learner_id,
            skill_id=skill_id,
            item_opportunity_id=item_opportunity_id,
            attempt_id=attempt_id,
            response_matched=response_matched,
            p_l_before=p_l_before,
            predicted_probability=predicted_probability,
            posterior_p_l=posterior_p_l,
            p_l_after=p_l_after,
            **provenance(
                user.user_id, request_id, "b_skill_state_transition.recorded", "b_skill_state_transition", transition_id
            ),
        )
        # The unique index on item_opportunity_id (the claim) is enforced here: a concurrent
        # duplicate first-attempt-BKT for the same opportunity raises IntegrityError, mapped to
        # ConflictError by the caller — never a second BKT update.
        await SkillStateTransitionRepository(session).add(transition_record)

        skill_state.p_l = p_l_after
        skill_state.observation_count += 1
        await session.flush()
