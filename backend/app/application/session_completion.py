"""BE4e: completion, safe progress, and recovery (BEplan §9 BE4.6).

Every scientific step goes through ``app.infrastructure.live_engine.adapter.LiveEngineAdapter``
(imported lazily, function-scope — mirrors ``AttemptSubmissionService``/``HintRequestService``):
``aggregate_session`` folds a session's own attempts/hints/first-attempt outcomes into
first-attempt accuracy, retries, assisted-opportunity count, response-time stats, and per-skill
estimated mastery; ``plausibility_floor``/``evaluate`` compute the per-skill Guess-Guard status
from the learner's own per-skill response-time history; ``certify_skill`` (called *inside*
``aggregate_session`` once ``guard_statuses``/``theta_b`` are supplied) produces the certification
decision. No formula is reimplemented here — the pinned TEST_FIXTURE_ONLY
``opportunity_selection._ENGINEERING_BKT_CONFIG`` is reused unchanged, never a GATE-B/population
value.

GATE-B DEFERRALS (do not present as approved — see the BE4e engineering-continuation
authorization and ``backend/provenance/component-b-closure-decisions.json``): the completion
policy, the safe-progress policy, θ_B, and the Guess-Guard numerics used here are all TEST-fixture
engineering placeholders.

- **Completion policy** (BEplan §9 BE4.6 step 1): "complete on command" — the learner-facing
  client explicitly signals it is done with the presented opportunity (mirrors the
  ``b_session.complete``/``abandon`` "neutral explicit client command" pattern BE2 already
  established), gated on at least one recorded attempt/timeout for that opportunity so there is
  something to complete. ``MAX_OPPORTUNITIES_PER_SESSION`` is a fixed engineering session-length
  bound, not a governed value.
- **Safe-progress policy**: no raw BKT value (``p_l``/mastery probability), no private selection
  rationale, no Guess-Guard internals, and no per-skill mastery/certification appear in either
  public DTO (``app.domain.b_completion``) — that is architecturally GATE-B UNRESOLVED. Aggregation
  and certification are computed and persisted PRIVATELY
  (``b_session_aggregate_results`` / ``b_skill_certification_results``) but never returned to the
  client by this module.

FIRST-ATTEMPT-ONLY IS UNTOUCHED: this module never imports ``LearnerSkillStateRepository`` for
writes and never inserts into ``b_skill_state_transitions`` — it only *reads* the transitions
BE4c already wrote to build the adapter's aggregation input. Completing an opportunity or a
session creates or alters no BKT observation.

NEXT-OR-COMPLETE ATOMICITY (BEplan §9 BE4.6 step 2): closing the current opportunity and either
opening the next one or transitioning the session to ``completed`` (plus, in the completed case,
persisting the aggregate/certification rows) all happen inside one ``SqlAlchemyUnitOfWork`` and
commit together exactly once, at the end of ``complete_and_advance`` — the same pattern
``AttemptSubmissionService``/``HintRequestService`` use. Any failure before that single
``uow.commit()`` rolls back every step via ``SqlAlchemyUnitOfWork.__aexit__``, leaving neither a
half-opened next opportunity nor a half-completed session.

RECOVERY (BEplan §9 BE4.6 step 6): duplicate submission of this endpoint reuses the same
``b_idempotency_records`` mechanism as BE4c/BE4d (replay returns the original response, no second
close/open/complete). App restart / a stale presentation token / a retried opportunity-select call
are handled by ``opportunity_selection.select_next_opportunity``'s resumable re-fetch path (BE4e
change there), not duplicated here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.opportunity_persistence import OpportunityPersistenceService
from app.application.opportunity_selection import (
    _B_SESSION_INDEX,
    _ENGINEERING_BKT_CONFIG,
    _SCHEDULED_SESSION_NUMBER,
    load_or_init_skill_states,
    open_adaptive_opportunity,
    package_item_opportunity_id,
    package_student_id,
    resolve_bundle_and_catalogue,
)
from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError, TechnicalFailureError
from app.domain.b_completion import (
    OpportunityAdvanceResponse,
    SessionStandingResponse,
)
from app.domain.live_engine.errors import LiveEngineError
from app.domain.live_engine.types import (
    GuessGuardStatus,
    OpportunityResponse,
    SessionIdentity,
    SkillMasteryUpdate,
)
from app.domain.principal import AuthenticatedPrincipal
from app.domain.runtime_bundle.errors import RuntimeBundleError
from app.infrastructure.persistence_models import (
    AppUser,
    IdempotencyRecord,
    ItemOpportunityRecord,
    SessionAggregateResultRecord,
    SessionRecord,
    SkillCertificationResultRecord,
)
from app.infrastructure.repositories import (
    AppUserRepository,
    AttemptRepository,
    HintEventRepository,
    IdempotencyRecordRepository,
    ItemOpportunityRepository,
    LearnerRepository,
    RuntimeBundleRecordRepository,
    SessionRecordRepository,
    SkillStateTransitionRepository,
    TaskInstanceRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


if TYPE_CHECKING:
    # Deferred for the same reason as every other BE4 service: only actually aggregating a
    # session requires the vendored component_b_generator wheel.
    from app.infrastructure.live_engine.adapter import LiveEngineAdapter


SCHEMA_REVISION = "20260728_0003"
IDEMPOTENCY_OPERATION_ADVANCE = "b_opportunity.complete_and_advance"

# ENGINEERING FAIL-SAFE PLACEHOLDER (GATE-B UNRESOLVED — completion policy). See module
# docstring. Never promoted to "approved" by this module.
MAX_OPPORTUNITIES_PER_SESSION = 5
COMPLETION_POLICY_VERSION = "be4e-engineering-explicit-command-max5-1.0"

# Reused, unaltered, for the "median" of a per-skill RT sample: the same pinned quantile function
# the adapter's plausibility_floor exposes, called at q=0.5 with n_min=1 rather than
# reimplementing a median.
_MEDIAN_QUANTILE = 0.5
_MEDIAN_MIN_OBSERVATIONS = 1


def body_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "actor_user_id": user_id,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_B_SESSION_COMPLETION_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


def _build_opportunity_response(
    opportunity: ItemOpportunityRecord,
    task_instance_id: UUID,
    attempts: list,
    raw_hint_count: int,
) -> OpportunityResponse:
    """Derive the adapter's ``OpportunityResponse`` input from our own persisted rows. Every
    field here is read, never inferred from anything but this opportunity's own attempts/hints —
    see the module docstring for the one documented engineering limitation (no error-pattern
    classifier is exposed by the adapter, so an unclassified incorrect first attempt is recorded
    as the taxonomy's generic ``"random"`` bucket rather than a fabricated specific pattern)."""
    total_attempts = len(attempts)
    first = attempts[0]
    first_attempt_correct = bool(first.response_matched) if first.event_kind == "RESPONSE" else False
    if first_attempt_correct:
        first_attempt_error_pattern = "correct"
    elif first.event_kind == "TIMEOUT":
        first_attempt_error_pattern = "timeout_no_response"
    else:
        first_attempt_error_pattern = "random"

    first_attempt_response_time_ms = first.client_elapsed_ms or 0
    total_response_time_ms = sum(a.client_elapsed_ms or 0 for a in attempts)

    # Engineering compatibility clamp: our system allows up to 3 hints independent of attempt
    # count, but the reviewed package invariant assumes at most one hint per attempt. Clamping
    # (never inflating) keeps every reported hint real while satisfying that structural
    # invariant; it never fabricates evidence.
    hint_count = min(raw_hint_count, total_attempts)
    hint_requested = hint_count > 0

    return OpportunityResponse(
        learner_id=str(opportunity.learner_id),
        session_id=str(opportunity.session_id),
        scheduled_session_index=opportunity.opportunity_index,
        # The vendored package's SessionSummary validates every opportunity_id against
        # ^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$ and requires strictly ascending item indices — the
        # same package-format identifier BE4b's build_task already derives for construction, not
        # our own DB primary key.
        item_opportunity_id=package_item_opportunity_id(opportunity.learner_id, _B_SESSION_INDEX, opportunity.opportunity_index),
        task_instance_id=str(task_instance_id),
        item_template_id=opportunity.item_template_id,
        skill_id=opportunity.skill_id,
        first_attempt_correct=first_attempt_correct,
        first_attempt_error_pattern=first_attempt_error_pattern,
        total_attempts=total_attempts,
        hint_requested=hint_requested,
        hint_count=hint_count,
        final_item_completed=True,
        assisted_completion=hint_count > 0,
        unassisted_completion=hint_count == 0,
        total_response_time_ms=total_response_time_ms,
        first_attempt_response_time_ms=first_attempt_response_time_ms,
    )


class SessionCompletionService:
    """BE4e application service: the ``POST /api/v1/b/sessions/{session_id}/opportunities/
    {item_opportunity_id}/complete`` (next-or-complete) and ``GET /api/v1/b/sessions/
    {session_id}/summary`` (SAFE standing) use cases."""

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
            {"scope": f"{user.user_id}:POST:{IDEMPOTENCY_OPERATION_ADVANCE}:{key}"},
        )
        repository = IdempotencyRecordRepository(session)
        existing = await repository.find_scoped(user.user_id, "POST", IDEMPOTENCY_OPERATION_ADVANCE, key)
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
            operation_identifier=IDEMPOTENCY_OPERATION_ADVANCE,
            idempotency_key=key,
            request_fingerprint=fingerprint_value,
            processing_status="in_progress",
            canonical_response=None,
            response_status=None,
            expires_at_utc=datetime.now(UTC) + timedelta(hours=24),
            **provenance(user.user_id, request_id, IDEMPOTENCY_OPERATION_ADVANCE, "b_idempotency_record", record_id),
        )
        await repository.add(record)
        return record, None

    @staticmethod
    def _finish(record: IdempotencyRecord, response: dict[str, object], status_code: int) -> None:
        record.processing_status = "succeeded"
        record.canonical_response = response
        record.response_status = status_code

    # ------------------------------------------------------------------------------------
    # POST .../opportunities/{item_opportunity_id}/complete — next-or-complete, atomic
    # ------------------------------------------------------------------------------------

    async def complete_and_advance(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> OpportunityAdvanceResponse:
        async with self._uow_factory() as uow:
            try:
                response = await self._complete_and_advance_unguarded(
                    uow.session, principal, session_id, item_opportunity_id, idempotency_key, request_id
                )
                # Single commit point: the opportunity close, the next-open-or-session-complete
                # decision, and (when completing) the aggregate/certification persistence all
                # land together here, or none of them do (BEplan §9 BE4.6 step 2 atomicity).
                await uow.commit()
            except IntegrityError as exc:
                raise ConflictError() from exc
            except (LiveEngineError, RuntimeBundleError) as exc:
                raise ConflictError() from exc
            except SQLAlchemyError as exc:
                raise TechnicalFailureError() from exc
            return response

    async def _complete_and_advance_unguarded(
        self,
        session: AsyncSession,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> OpportunityAdvanceResponse:
        user, learner_id = await self._require_learner(session, principal)

        session_row = await SessionRecordRepository(session).get_owned(session_id, learner_id)
        if session_row is None or session_row.state != "active":
            raise ResourceNotFoundError()

        fingerprint_value = body_fingerprint(
            {"session_id": str(session_id), "item_opportunity_id": str(item_opportunity_id)}
        )
        idem, replay = await self._reserve_idempotency(session, user, idempotency_key, fingerprint_value, request_id)
        if replay is not None:
            return OpportunityAdvanceResponse.model_validate(replay)

        opportunity = await ItemOpportunityRepository(session).get_owned(item_opportunity_id, learner_id)
        if opportunity is None or opportunity.session_id != session_id:
            raise ResourceNotFoundError()

        attempt_count = await AttemptRepository(session).count_for_opportunity(item_opportunity_id)
        if attempt_count < 1:
            # Engineering "complete on command" fail-safe (BEplan §9 BE4.6 step 1): nothing has
            # been attempted yet, so there is nothing to complete.
            raise ConflictError()

        if opportunity.state == "OPEN":
            await OpportunityPersistenceService(session).close_opportunity(item_opportunity_id)

        opportunities_completed = await ItemOpportunityRepository(session).count_for_session(session_id)

        bundle_record = await RuntimeBundleRecordRepository(session).get_by_id(session_row.runtime_bundle_record_id)
        if bundle_record is None:
            raise ConflictError()

        if opportunities_completed >= MAX_OPPORTUNITIES_PER_SESSION:
            await self._complete_session(session, user, request_id, session_row, learner_id)
            response = OpportunityAdvanceResponse(
                item_opportunity_id=item_opportunity_id,
                session_state="completed",
                opportunities_completed=opportunities_completed,
                opportunities_total_bound=MAX_OPPORTUNITIES_PER_SESSION,
                next_opportunity=None,
                request_id=request_id,
            )
        else:
            from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

            adapter: "LiveEngineAdapter" = LiveEngineAdapter()
            catalogue, catalogue_checksum = await resolve_bundle_and_catalogue(adapter, bundle_record)
            mastery = await load_or_init_skill_states(
                session, learner_id, _ENGINEERING_BKT_CONFIG, user.user_id, request_id
            )
            next_presentation = await open_adaptive_opportunity(
                session=session,
                adapter=adapter,
                catalogue=catalogue,
                catalogue_checksum=catalogue_checksum,
                grade=await self._require_grade(session, learner_id),
                mastery=mastery,
                session_id=session_id,
                learner_id=learner_id,
                runtime_bundle_record_id=session_row.runtime_bundle_record_id,
                opportunity_index=opportunities_completed + 1,
                user_id=user.user_id,
                request_id=request_id,
            )
            response = OpportunityAdvanceResponse(
                item_opportunity_id=item_opportunity_id,
                session_state="active",
                opportunities_completed=opportunities_completed,
                opportunities_total_bound=MAX_OPPORTUNITIES_PER_SESSION,
                next_opportunity=next_presentation,
                request_id=request_id,
            )

        self._finish(idem, response.model_dump(mode="json"), 201)
        return response

    async def _require_grade(self, session: AsyncSession, learner_id: UUID) -> int:
        learner_row = await LearnerRepository(session).get_by_id(learner_id)
        if learner_row is None or learner_row.grade is None:
            raise ConflictError()
        return learner_row.grade

    async def _complete_session(
        self,
        session: AsyncSession,
        user: AppUser,
        request_id: str,
        session_row: SessionRecord,
        learner_id: UUID,
    ) -> None:
        """Session-length bound reached: transition active -> completed and PRIVATELY persist
        the session aggregate + per-skill certification rows (BEplan §9 BE4.6 steps 3-4). All
        science is ``LiveEngineAdapter.aggregate_session``/``plausibility_floor``/``evaluate`` —
        no formula reimplemented here."""
        locked_session = await session.scalar(
            select(SessionRecord)
            .where(SessionRecord.session_id == session_row.session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked_session is None or locked_session.state != "active":
            raise ConflictError()

        opportunities = await ItemOpportunityRepository(session).list_for_session(session_row.session_id)
        opportunity_ids = [o.item_opportunity_id for o in opportunities]

        # Three set-based reads, not three per opportunity. This loop used to issue
        # find_by_opportunity + list_for_opportunity + count_for_opportunity for each
        # opportunity in turn, so the one request that ends a session paid 3 x
        # MAX_OPPORTUNITIES_PER_SESSION sequential round trips on top of its own work -- 34
        # statements against a mid-session complete's 18. The per-opportunity validation below is
        # unchanged, including raising ConflictError for a missing instance or an attempt-less
        # opportunity; only the number of round trips used to answer the same questions differs.
        task_instances = await TaskInstanceRepository(session).map_by_opportunities(opportunity_ids)
        attempts_by_opportunity = await AttemptRepository(session).map_for_opportunities(opportunity_ids)
        hint_counts = await HintEventRepository(session).count_by_opportunities(opportunity_ids)

        opportunity_responses: list[OpportunityResponse] = []
        for opportunity in opportunities:
            task_instance = task_instances.get(opportunity.item_opportunity_id)
            if task_instance is None:
                raise ConflictError()
            attempts = attempts_by_opportunity.get(opportunity.item_opportunity_id, [])
            if not attempts:
                raise ConflictError()
            # `.get(..., 0)`: a GROUP BY yields no row for an opportunity with no hints, where
            # count_for_opportunity returned 0.
            hint_count = hint_counts.get(opportunity.item_opportunity_id, 0)
            opportunity_responses.append(
                _build_opportunity_response(opportunity, task_instance.task_instance_id, attempts, hint_count)
            )

        transitions = await SkillStateTransitionRepository(session).list_for_opportunities(opportunity_ids)
        student_id = package_student_id(learner_id)
        skill_mastery_updates = [
            SkillMasteryUpdate(
                student_id=student_id,
                skill_id=t.skill_id,
                b_session_index=_B_SESSION_INDEX,
                mastery_before=t.p_l_before,
                predicted_correct_probability=t.predicted_probability,
                posterior_l=t.posterior_p_l,
                mastery_after=t.p_l_after,
            )
            for t in transitions
        ]

        latest_estimate_by_skill: dict[str, float] = {}
        for update in skill_mastery_updates:
            if update.mastery_after is not None:
                latest_estimate_by_skill[update.skill_id] = update.mastery_after

        from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

        adapter: "LiveEngineAdapter" = LiveEngineAdapter()
        theta_b = _ENGINEERING_BKT_CONFIG.theta_b
        guard_statuses: dict[str, GuessGuardStatus] = {}
        by_skill: dict[str, list[OpportunityResponse]] = {}
        for o in opportunity_responses:
            by_skill.setdefault(o.skill_id, []).append(o)
        # BF-1 — the floor must come from PRIOR sessions, never this session's own sample.
        #
        # Before this fix, `median_rt_sec` (this session's own q=0.5) and the floor passed into
        # `adapter.evaluate` (q=0.1) were computed from the *identical* `rt_history` list. Because
        # a quantile function is monotonically non-decreasing in q on one fixed sample,
        # quantile(S, 0.1) <= quantile(S, 0.5) always — so `evaluate`'s trigger condition
        # (`median < floor`) was false for every possible input, and `TRIGGERED` was
        # mathematically unreachable regardless of how implausibly fast a learner answered. The
        # reviewed package's own `evaluate_guess_guard` is correct; only the caller's inputs were
        # wrong. Mirrors the reference sequencing (`Yass/.../pipeline.py`): floor from history
        # strictly before this session, evaluated against this session's own per-skill median.
        #
        # Every parameter is untouched: theta_b, floor_quantile (0.1), floor_min_obs (5),
        # _MEDIAN_QUANTILE (0.5) and _MEDIAN_MIN_OBSERVATIONS (1) are exactly as before — this is a
        # wiring fix, not a science change. A learner or skill with no qualifying prior history
        # correctly yields INSUFFICIENT_EVIDENCE (no fabricated floor for a first-time learner).
        prior_rt_history_by_skill = await ItemOpportunityRepository(session).prior_session_first_attempt_rts(
            learner_id, session_row.session_id
        )
        for skill_id, skill_estimate in latest_estimate_by_skill.items():
            rt_history = [
                o.first_attempt_response_time_ms / 1000.0
                for o in by_skill.get(skill_id, ())
                if o.first_attempt_error_pattern != "timeout_no_response" and o.first_attempt_response_time_ms > 0
            ]
            if not rt_history:
                continue
            median_rt_sec = adapter.plausibility_floor(rt_history, _MEDIAN_QUANTILE, _MEDIAN_MIN_OBSERVATIONS)
            if median_rt_sec is None:
                continue
            guard_statuses[skill_id] = adapter.evaluate(
                skill_estimate,
                median_rt_sec,
                prior_rt_history_by_skill.get(skill_id, []),
                theta_b,
                _ENGINEERING_BKT_CONFIG.floor_quantile,
                _ENGINEERING_BKT_CONFIG.floor_min_obs,
            )

        aggregate = adapter.aggregate_session(
            session_identity=SessionIdentity(
                student_id=student_id,
                b_session_index=_B_SESSION_INDEX,
                scheduled_session_number=_SCHEDULED_SESSION_NUMBER,
                status="attended",
            ),
            opportunities=opportunity_responses,
            skill_mastery_updates=skill_mastery_updates,
            guard_statuses=guard_statuses or None,
            theta_b=theta_b,
        )

        stats = aggregate.stats
        aggregate_result_id = uuid4()
        session.add(
            SessionAggregateResultRecord(
                session_aggregate_result_id=aggregate_result_id,
                session_id=session_row.session_id,
                learner_id=learner_id,
                opportunity_count=len(opportunities),
                first_attempt_match_rate=stats.first_attempt_accuracy,
                completion_count=stats.completion_count,
                completion_rate=stats.completion_rate,
                total_retry_count=stats.total_retries,
                assisted_opportunity_count=stats.hint_bearing_opportunities,
                response_time_mean_ms=stats.response_time_mean_ms,
                response_time_median_ms=stats.response_time_median_ms,
                response_time_std_ms=stats.response_time_std_ms,
                outcome_pattern_distribution=dict(stats.error_class_distribution),
                skill_ids_practiced=list(aggregate.skill_ids_practiced),
                completion_policy_version=COMPLETION_POLICY_VERSION,
                **provenance(
                    user.user_id, request_id, "b_session_aggregate_result.recorded",
                    "b_session_aggregate_result", aggregate_result_id,
                ),
            )
        )
        for rollup in aggregate.skill_rollups:
            certification_id = uuid4()
            session.add(
                SkillCertificationResultRecord(
                    skill_result_id=certification_id,
                    session_id=session_row.session_id,
                    learner_id=learner_id,
                    skill_id=rollup.skill_id,
                    opportunity_count=rollup.opportunities,
                    attempt_count=rollup.attempts,
                    first_attempt_match_count=rollup.first_attempt_correct,
                    skill_estimate=rollup.estimated_mastery,
                    plausibility_status=(
                        guard_statuses[rollup.skill_id].value if rollup.skill_id in guard_statuses else None
                    ),
                    threshold_met_flag=rollup.certified,
                    **provenance(
                        user.user_id, request_id, "b_skill_certification_result.recorded",
                        "b_skill_certification_result", certification_id,
                    ),
                )
            )

        locked_session.state = "completed"
        locked_session.row_version += 1
        await session.flush()

    # ------------------------------------------------------------------------------------
    # GET .../summary — SAFE, read-only session standing
    # ------------------------------------------------------------------------------------

    async def get_session_standing(
        self, principal: AuthenticatedPrincipal, session_id: UUID, request_id: str
    ) -> SessionStandingResponse:
        async with self._uow_factory() as uow:
            _, learner_id = await self._require_learner(uow.session, principal)
            session_row = await SessionRecordRepository(uow.session).get_owned(session_id, learner_id)
            if session_row is None:
                raise ResourceNotFoundError()

            opportunities_completed = await ItemOpportunityRepository(uow.session).count_closed_for_session(session_id)
            session_state = "completed" if session_row.state == "completed" else "active"
            return SessionStandingResponse(
                session_id=session_id,
                session_state=session_state,
                opportunities_completed=opportunities_completed,
                opportunities_total_bound=MAX_OPPORTUNITIES_PER_SESSION,
                request_id=request_id,
            )
