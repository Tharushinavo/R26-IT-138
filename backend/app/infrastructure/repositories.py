"""SQLAlchemy repositories for the twelve neutral BE2 tables."""

from datetime import datetime
from typing import Generic, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence_models import (
    AppUser, AppUserLearnerLink, AttemptRecord, AuditEvent, Base, CGameplayEventRecord, Classroom,
    ClassroomInvite, ClassroomMembership, CLearnerLocalStateRecord, CPolicyDecisionRecord,
    CRuntimeBundleRecord, CSafetyEventRecord, CScaffoldEventRecord,
    CSessionRecord, CTaskInstanceRecord, CTaskOpportunityRecord, CTaskOpportunitySummaryRecord,
    CTaskOpportunityVerdictRecord,
    DCognitiveProfileRecord, DInteractionRecord, DLearnerStateRecord,
    HintEventRecord, IdempotencyRecord,
    ItemOpportunityRecord, Learner, LearnerSkillStateRecord, PresentationTokenRecord,
    RuntimeBundleRecord, SessionAggregateResultRecord, SessionEvent, SessionRecord,
    SkillCertificationResultRecord, SkillStateTransitionRecord, TaskInstanceRecord, TeacherProfile,
)


ModelT = TypeVar("ModelT", bound=Base)


class SqlAlchemyNeutralRepository(Generic[ModelT]):
    model_type: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, record: ModelT) -> None:
        self.session.add(record)
        await self.session.flush()

    async def get_by_id(self, record_id: UUID) -> ModelT | None:
        return await self.session.get(self.model_type, record_id)

    async def exists(self, record_id: UUID) -> bool:
        return await self.get_by_id(record_id) is not None


class AppUserRepository(SqlAlchemyNeutralRepository[AppUser]):
    model_type = AppUser

    async def find_by_subject(self, subject: str) -> AppUser | None:
        return await self.session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))

    async def find_with_learner_link_by_subject(
        self, subject: str
    ) -> tuple[AppUser, AppUserLearnerLink | None] | None:
        """The app user and its learner link in ONE round trip.

        Every authenticated learner request resolves the principal the same way: look the user up
        by Supabase subject, then look its learner link up by user id. As two awaits that is two
        sequential round trips before any real work begins, which against a remote database is
        pure latency (~65ms each against ap-southeast-1) on every single request.

        The join is OUTER so the three outcomes callers must distinguish stay distinguishable:
        no row at all (unknown user), a row with no link (user exists, not yet a learner), and a
        row with a link. Returning `None` vs `(user, None)` preserves exactly that, so callers
        keep raising the same not-found/forbidden errors they raised with two queries.
        """
        result = await self.session.execute(
            select(AppUser, AppUserLearnerLink)
            .outerjoin(AppUserLearnerLink, AppUserLearnerLink.user_id == AppUser.user_id)
            .where(AppUser.supabase_subject == subject)
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]


class LearnerRepository(SqlAlchemyNeutralRepository[Learner]):
    model_type = Learner


class AppUserLearnerLinkRepository(SqlAlchemyNeutralRepository[AppUserLearnerLink]):
    model_type = AppUserLearnerLink

    async def find_by_user(self, user_id: UUID) -> AppUserLearnerLink | None:
        return await self.session.scalar(select(AppUserLearnerLink).where(AppUserLearnerLink.user_id == user_id))


class RuntimeBundleRecordRepository(SqlAlchemyNeutralRepository[RuntimeBundleRecord]):
    model_type = RuntimeBundleRecord

    async def find_current_approved_published(self) -> RuntimeBundleRecord | None:
        """Resolve the bundle to pin a newly started session to.

        Tie-break is the most recently created PUBLISHED+APPROVED bundle. Multiple
        simultaneously eligible bundles are not expected in practice; the exact
        selection policy for that case is an engineering assumption, not a governed
        decision.
        """
        statement = (
            select(RuntimeBundleRecord)
            .where(
                RuntimeBundleRecord.publication_state == "PUBLISHED",
                RuntimeBundleRecord.approval_status == "APPROVED",
            )
            .order_by(RuntimeBundleRecord.created_at_utc.desc(), RuntimeBundleRecord.runtime_bundle_record_id.desc())
            .limit(1)
        )
        return await self.session.scalar(statement)


class SessionRecordRepository(SqlAlchemyNeutralRepository[SessionRecord]):
    model_type = SessionRecord

    async def find_starting_or_active_for_learner(self, learner_id: UUID) -> SessionRecord | None:
        return await self.session.scalar(
            select(SessionRecord).where(
                SessionRecord.learner_id == learner_id,
                SessionRecord.state.in_(("starting", "active")),
            )
        )

    async def find_active_for_learner(self, learner_id: UUID) -> SessionRecord | None:
        return await self.session.scalar(
            select(SessionRecord).where(
                SessionRecord.learner_id == learner_id,
                SessionRecord.state == "active",
            )
        )

    async def get_owned(self, session_id: UUID, learner_id: UUID) -> SessionRecord | None:
        return await self.session.scalar(
            select(SessionRecord).where(
                SessionRecord.session_id == session_id,
                SessionRecord.learner_id == learner_id,
            )
        )


class CRuntimeBundleRecordRepository(SqlAlchemyNeutralRepository[CRuntimeBundleRecord]):
    model_type = CRuntimeBundleRecord

    async def find_by_version(self, bundle_version: str) -> CRuntimeBundleRecord | None:
        return await self.session.scalar(
            select(CRuntimeBundleRecord).where(CRuntimeBundleRecord.bundle_version == bundle_version)
        )


class CSessionRecordRepository(SqlAlchemyNeutralRepository[CSessionRecord]):
    model_type = CSessionRecord

    async def lock_for_update(self, c_session_id: UUID) -> None:
        """CONNECT resume-instead-of-mint batch (supervisor ruling): closes the race where two
        concurrent ``next_task`` calls on a session with no pending instance yet could both find
        nothing to resume and both fall through to the mint path, computing the SAME
        ``task_index`` from the same pre-insert count (``CTaskOpportunityRecord`` carries no
        uniqueness constraint on ``(c_session_id, task_index)`` -- verified directly). Because
        ``task_index`` is the SOLE seed-lineage-distinguishing element
        (``task_service.py``'s own module docstring), a same-``task_index`` collision would derive
        the identical RNG seed and draw the identical template -- two indistinguishable duplicate
        opportunity rows, silently corrupting the attempt-level history Family 7 requires be
        preserved, not merely uncorrupted-looking. Locking the SESSION row here (the instance row
        may not exist yet, unlike Step 5's lock target) closes both this race and any race between
        the resume check and the mint decision -- taken once, at the top of ``next_task``, before
        either."""
        await self.session.execute(
            select(CSessionRecord.c_session_id).where(CSessionRecord.c_session_id == c_session_id).with_for_update()
        )

    async def find_starting_or_active_for_learner(self, student_id: UUID) -> CSessionRecord | None:
        return await self.session.scalar(
            select(CSessionRecord).where(
                CSessionRecord.student_id == student_id,
                CSessionRecord.state.in_(("starting", "active")),
            )
        )

    async def find_active_for_learner(self, student_id: UUID) -> CSessionRecord | None:
        return await self.session.scalar(
            select(CSessionRecord).where(
                CSessionRecord.student_id == student_id,
                CSessionRecord.state == "active",
            )
        )

    async def get_owned(self, c_session_id: UUID, student_id: UUID) -> CSessionRecord | None:
        return await self.session.scalar(
            select(CSessionRecord).where(
                CSessionRecord.c_session_id == c_session_id,
                CSessionRecord.student_id == student_id,
            )
        )

    async def get_owned_for_subject(
        self, c_session_id: UUID, subject: str, *, for_update: bool = False
    ) -> CSessionRecord | None:
        """PERF-01: ``AppUserRepository.find_with_learner_link_by_subject`` + ``get_owned`` in ONE round trip.

        The session owned by the learner linked to the Supabase subject, or ``None`` when ANY of unknown user, user
        without a learner link, or no such session for that learner holds -- the three cases every caller already turned into
        the same ``ResourceNotFoundError``. Inner joins (not outer) so ``for_update`` can lock the session row: Postgres refuses
        ``FOR UPDATE`` on the nullable side of an outer join. ``for_update`` takes the SAME row lock ``lock_for_update`` takes."""
        stmt = (
            select(CSessionRecord)
            .join(AppUserLearnerLink, AppUserLearnerLink.learner_id == CSessionRecord.student_id)
            .join(AppUser, AppUser.user_id == AppUserLearnerLink.user_id)
            .where(CSessionRecord.c_session_id == c_session_id, AppUser.supabase_subject == subject)
        )
        if for_update:
            stmt = stmt.with_for_update(of=CSessionRecord)
        return await self.session.scalar(stmt)


class CLearnerLocalStateRepository(SqlAlchemyNeutralRepository[CLearnerLocalStateRecord]):
    model_type = CLearnerLocalStateRecord

    async def find_by_student(self, student_id: UUID) -> CLearnerLocalStateRecord | None:
        return await self.session.scalar(
            select(CLearnerLocalStateRecord).where(CLearnerLocalStateRecord.student_id == student_id)
        )


class CTaskOpportunityRecordRepository(SqlAlchemyNeutralRepository[CTaskOpportunityRecord]):
    model_type = CTaskOpportunityRecord

    async def count_for_session(self, c_session_id: UUID) -> int:
        """Phase 5: the NEXT ``task_index`` for a session is ``count_for_session(...)`` -- no
        separate counter column exists on ``c_sessions``; the opportunity rows ARE the count."""
        return await self.session.scalar(
            select(func.count()).select_from(CTaskOpportunityRecord).where(
                CTaskOpportunityRecord.c_session_id == c_session_id
            )
        ) or 0

    async def list_ordered_for_session(self, c_session_id: UUID) -> Sequence[CTaskOpportunityRecord]:
        """Phase 8, J1-4: every OFFERED task opportunity for a session, ordered by ``task_index``
        -- the guarded accessor's OFFERED set (``telemetry_validation.
        get_derivable_history_for_session``'s own only caller). Never filtered, never truncated
        here -- gap detection is the accessor's own job, not this query's."""
        result = await self.session.execute(
            select(CTaskOpportunityRecord)
            .where(CTaskOpportunityRecord.c_session_id == c_session_id)
            .order_by(CTaskOpportunityRecord.task_index)
        )
        return result.scalars().all()


class CTaskInstanceRecordRepository(SqlAlchemyNeutralRepository[CTaskInstanceRecord]):
    model_type = CTaskInstanceRecord

    async def get_owned(
        self, c_task_instance_id: UUID, c_session_id: UUID, *, for_update: bool = False
    ) -> CTaskInstanceRecord | None:
        """Phase 5: ``c_task_instances`` carries no denormalized ``c_session_id`` (Phase 3a's own
        minimal-FK style, mirroring B) -- ownership is proven through the parent
        ``c_task_opportunities`` row instead.

        PERF-01: ``for_update=True`` reads AND locks the instance row in one round trip -- the same row lock
        ``lock_for_update`` takes (see its docstring for why the lock must precede the event counts)."""
        stmt = (
            select(CTaskInstanceRecord)
            .join(CTaskOpportunityRecord, CTaskInstanceRecord.c_task_opportunity_id == CTaskOpportunityRecord.c_task_opportunity_id)
            .where(
                CTaskInstanceRecord.c_task_instance_id == c_task_instance_id,
                CTaskOpportunityRecord.c_session_id == c_session_id,
            )
        )
        if for_update:
            stmt = stmt.with_for_update(of=CTaskInstanceRecord)
        return await self.session.scalar(stmt)

    async def lock_for_update(self, c_task_instance_id: UUID) -> None:
        """CONNECT Step 5 (supervisor ruling, closing the attempt_number race identified while
        planning that step): the SAME row, the SAME lock the two ``c_gameplay_events`` triggers
        already take (``PERFORM 1 FROM c_task_instances WHERE c_task_instance_id = ... FOR
        UPDATE``, migrations/versions/20260816_0003_c3b_gameplay_event_invariants.py), taken here
        EARLIER in the same transaction -- before ``task_service.submit_action`` counts existing
        ``answer_submitted`` events to derive ``attempt_number``, not after. Taking it here first
        means a second, concurrent ``submit_action`` call against the same instance blocks BEFORE
        it counts, not after -- closing the window where two racing submissions could both read
        the same count and write the same attempt_number. When the trigger later re-takes this
        exact lock inside the same transaction, it is already held by that transaction -- no
        deadlock, no second locking mechanism, no migration."""
        await self.session.execute(
            select(CTaskInstanceRecord.c_task_instance_id)
            .where(CTaskInstanceRecord.c_task_instance_id == c_task_instance_id)
            .with_for_update()
        )

    async def find_most_recent_for_session(self, c_session_id: UUID) -> CTaskInstanceRecord | None:
        """CONNECT resume-instead-of-mint batch (owner ruling): the candidate for "the pending
        task", if any -- the caller is responsible for checking
        ``CGameplayEventRecordRepository.has_terminal_for_instance`` on the result before treating
        it as resumable. Ordered by ``task_index`` descending so a session with more than one
        unterminated instance (only possible from before this batch shipped) resumes the most
        recent draw, not an arbitrary one."""
        return await self.session.scalar(
            select(CTaskInstanceRecord)
            .join(
                CTaskOpportunityRecord,
                CTaskInstanceRecord.c_task_opportunity_id == CTaskOpportunityRecord.c_task_opportunity_id,
            )
            .where(CTaskOpportunityRecord.c_session_id == c_session_id)
            .order_by(CTaskInstanceRecord.task_index.desc())
            .limit(1)
        )

    async def find_by_opportunity(self, c_task_opportunity_id: UUID) -> CTaskInstanceRecord | None:
        """Phase 8, J1-4: the 1:1 opportunity -> instance lookup (``uq_c_task_instances_opportunity``,
        persistence_models.py:827) the guarded accessor needs to reach
        ``CGameplayEventRecordRepository.has_terminal_for_instance`` from an OFFERED opportunity
        row -- an opportunity with no instance yet (task never started) is not a gap, it is simply
        absent from this lookup, and the accessor's own caller treats a ``None`` result that way."""
        return await self.session.scalar(
            select(CTaskInstanceRecord).where(
                CTaskInstanceRecord.c_task_opportunity_id == c_task_opportunity_id
            )
        )


class CGameplayEventRecordRepository(SqlAlchemyNeutralRepository[CGameplayEventRecord]):
    model_type = CGameplayEventRecord

    # Phase 6a: hand-copied from component_c_generator.models.gameplay.TERMINAL_EVENT_TYPES, the
    # same convention persistence_models.py's own ck_c_gameplay_events_terminal_reason /
    # uq_c_gameplay_events_at_most_one_terminal_per_instance already use -- this file is not
    # app/infrastructure/live_engine_c/adapter.py, the one file X-1 permits a
    # component_c_generator import root, so the package's own tuple cannot be read here at
    # runtime. tests/test_c6a_summary_derivation.py verifies this tuple against the package's
    # live value (the R-I pattern).
    _TERMINAL_EVENT_TYPES = ("game_task_completed", "game_task_skipped", "game_task_quit")

    async def max_index_and_timestamp_for_instance(self, game_task_instance_id: UUID) -> tuple[int, int]:
        """Phase 3b's own triggers require ``event_index`` to be consecutive from 1 and
        ``event_timestamp_relative_ms`` to be non-decreasing within a task -- both queried live
        here rather than assumed, so a second event for the same instance is always valid
        regardless of how many events already exist."""
        row = (
            await self.session.execute(
                select(
                    func.max(CGameplayEventRecord.event_index),
                    func.max(CGameplayEventRecord.event_timestamp_relative_ms),
                ).where(CGameplayEventRecord.game_task_instance_id == game_task_instance_id)
            )
        ).one()
        max_index, max_timestamp = row
        return (max_index or 0), (max_timestamp or 0)

    async def count_answer_submitted_for_instance(self, game_task_instance_id: UUID) -> int:
        """CONNECT Step 5 (Family 3, "each retry must receive an incrementing attempt_number";
        ESCALATIONS.md §2): the SAME derivation
        component_c_generator.behaviour.summary.derive_task_opportunity_summary already performs
        internally (``len(submitted_events)``, behaviour/summary.py:43-46 -- counts
        ``answer_submitted`` events, never reads ``attempt_number``), replicated here at WRITE
        time so the persisted column itself is honest rather than merely derivable from the event
        count downstream. The caller is responsible for holding
        ``CTaskInstanceRecordRepository.lock_for_update`` on this same instance first, in the same
        transaction, before calling this -- see that method's own docstring for why the ordering
        is what closes the concurrent-submission race, not this query alone. No ceiling is applied
        or implied here: I4's numeric attempt-count bound is BLOCKED, ESCALATED TO THE OWNER
        (persistence_models.py's own CGameplayEventRecord docstring, R-L) and is not built in any
        form by this step -- a child may submit an unbounded number of wrong answers today, and
        attempt_number will grow unboundedly along with it."""
        count = await self.session.scalar(
            select(func.count()).select_from(CGameplayEventRecord).where(
                CGameplayEventRecord.game_task_instance_id == game_task_instance_id,
                CGameplayEventRecord.event_type == "answer_submitted",
            )
        )
        return count or 0

    async def has_started_for_instance(self, game_task_instance_id: UUID) -> bool:
        """Phase 6a: LATENT DEFECT SINCE PHASE 5, found by this batch's own derivation wiring --
        no code path anywhere in this codebase ever wrote a "game_task_started" event
        (next_task writes only "game_task_offered"; submit_action wrote none at all before this
        batch), so derive_task_opportunity_summary's own invariant ("a never-started task cannot
        be completed") could never have been satisfied by any real submission. submit_action now
        writes one "game_task_started" event, guarded by this check so a second submit_action
        call against the same instance (a wrong-answer retry, still permitted -- only a
        TERMINAL instance is blocked, T1-4) does not write it twice."""
        count = await self.session.scalar(
            select(func.count()).select_from(CGameplayEventRecord).where(
                CGameplayEventRecord.game_task_instance_id == game_task_instance_id,
                CGameplayEventRecord.event_type == "game_task_started",
            )
        )
        return bool(count)

    async def has_terminal_for_instance(self, game_task_instance_id: UUID) -> bool:
        """Phase 6a, T1-3/T1-4: the service-level half of the exactly-one-terminal triple -- the
        DB-enforced half is the existing partial unique index
        (uq_c_gameplay_events_at_most_one_terminal_per_instance, persistence_models.py:923)."""
        count = await self.session.scalar(
            select(func.count()).select_from(CGameplayEventRecord).where(
                CGameplayEventRecord.game_task_instance_id == game_task_instance_id,
                CGameplayEventRecord.event_type.in_(self._TERMINAL_EVENT_TYPES),
            )
        )
        return bool(count)

    async def list_ordered_for_instance(self, game_task_instance_id: UUID) -> Sequence[CGameplayEventRecord]:
        """Phase 6a: the full, ``event_index``-ordered event stream for one task instance --
        summary derivation's own input shape (SummaryPort). Never filtered, never truncated:
        derive_task_opportunity_summary raises on an incoherent stream itself (e.g. not exactly
        one terminal event) rather than this query silently hiding one."""
        result = await self.session.execute(
            select(CGameplayEventRecord)
            .where(CGameplayEventRecord.game_task_instance_id == game_task_instance_id)
            .order_by(CGameplayEventRecord.event_index)
        )
        return result.scalars().all()

    async def list_all_events_for_session(self, c_session_id: UUID) -> Sequence[CGameplayEventRecord]:
        """Phase 9a: the full SESSION-wide event stream (every task instance), ordered by
        ``task_index`` then ``event_index`` -- ``derive_session_aggregate``'s own input shape
        (AggregationPort), which groups by ``task_index`` to sum per-task spans (FIX 1, C5.0
        revision -- see aggregation_service.py's own citation-rule flag on that comment). Deliberately
        NOT named ``list_ordered_for_session`` -- that exact method name is reserved to
        ``CTaskOpportunitySummaryRecordRepository`` and is the one string
        ``test_be2_architecture_guards.py``'s Phase 8 guard scans for; reusing it here would trip
        that guard for a call it was never meant to restrict."""
        result = await self.session.execute(
            select(CGameplayEventRecord)
            .where(CGameplayEventRecord.c_session_id == c_session_id)
            .order_by(CGameplayEventRecord.task_index, CGameplayEventRecord.event_index)
        )
        return result.scalars().all()


class CTaskOpportunitySummaryRecordRepository(SqlAlchemyNeutralRepository[CTaskOpportunitySummaryRecord]):
    model_type = CTaskOpportunitySummaryRecord

    async def find_by_instance(self, game_task_instance_id: UUID) -> CTaskOpportunitySummaryRecord | None:
        return await self.session.scalar(
            select(CTaskOpportunitySummaryRecord).where(
                CTaskOpportunitySummaryRecord.game_task_instance_id == game_task_instance_id
            )
        )

    async def list_ordered_for_session(self, c_session_id: UUID) -> Sequence[CTaskOpportunitySummaryRecord]:
        """Phase 6b: the full running session history (v3.0 §7.2: "history passed to
        build_policy_evidence is the full running session history including the just-finished
        task"), ordered by task_index -- never filtered, never truncated here."""
        result = await self.session.execute(
            select(CTaskOpportunitySummaryRecord)
            .where(CTaskOpportunitySummaryRecord.c_session_id == c_session_id)
            .order_by(CTaskOpportunitySummaryRecord.task_index)
        )
        return result.scalars().all()


class CTaskOpportunityVerdictRecordRepository(SqlAlchemyNeutralRepository[CTaskOpportunityVerdictRecord]):
    model_type = CTaskOpportunityVerdictRecord

    async def list_for_session(self, c_session_id: UUID) -> Sequence[CTaskOpportunityVerdictRecord]:
        """Batch 4: every verdict row for a session -- liveness is graph-resolved by
        ``telemetry_validation._live_verdict_ids``, not order-dependent, so ordering here is only
        for test/debug legibility (chronological, the same discipline
        ``CPolicyDecisionRecordRepository.list_chronological_for_session`` already uses).
        Deliberately NOT named ``list_ordered_for_session`` -- that exact method name is reserved
        to ``CTaskOpportunitySummaryRecordRepository`` and is the literal string
        ``test_be2_architecture_guards.py``'s Phase 8 AST guard scans for; reusing it here would
        trip that guard for a call it was never meant to restrict."""
        result = await self.session.execute(
            select(CTaskOpportunityVerdictRecord)
            .where(CTaskOpportunityVerdictRecord.c_session_id == c_session_id)
            .order_by(CTaskOpportunityVerdictRecord.created_at_utc)
        )
        return result.scalars().all()


class CPolicyDecisionRecordRepository(SqlAlchemyNeutralRepository[CPolicyDecisionRecord]):
    model_type = CPolicyDecisionRecord

    async def most_recent_for_session(self, c_session_id: UUID) -> CPolicyDecisionRecord | None:
        """Phase 6b, S8-b: the increase-block feedback loop's own persisted state -- the most
        recently written decision's ``increase_block_remaining`` IS
        ``evidence.safety_increase_block_remaining`` for the NEXT task. No separate counter
        column exists (same "the rows ARE the count" discipline as
        CTaskOpportunityRecordRepository.count_for_session) -- ordered by created_at_utc, the
        provenance column every record already carries, never a synthetic sequence."""
        return await self.session.scalar(
            select(CPolicyDecisionRecord)
            .where(CPolicyDecisionRecord.c_session_id == c_session_id)
            .order_by(CPolicyDecisionRecord.created_at_utc.desc())
            .limit(1)
        )

    async def list_chronological_for_session(self, c_session_id: UUID) -> Sequence[CPolicyDecisionRecord]:
        """Phase 9a: the full, chronologically-ordered decision trajectory for a session --
        ``derive_session_aggregate``'s own ``adaptation_decisions`` input (its own
        ``_decide_difficulty_trend`` reads ``decisions[0]``/``decisions[-1]`` under the assumption
        the list is in real decision order). Ordered by ``created_at_utc``, the same provenance
        column ``most_recent_for_session`` already orders by.

        UPDATED (Batch 2, correcting the register-reconciliation batch's own claim above, which
        this note replaces rather than deletes): ``task_service.submit_action`` now calls
        ``adaptation_service.decide_and_persist_adaptation`` on its correct-answer path, so this
        table is no longer written by nothing under ``app/`` -- for any session that exists (still
        only a ``smoke_mode=True``/direct-call session; production session creation still refuses
        unconditionally, X2-3), this will return a non-empty, real list once at least one task has
        been answered correctly. ``derive_and_persist_session_aggregate`` itself remains
        unreachable regardless (``_AGGREGATION_INPUTS_AVAILABLE = False``, aggregation_service.py,
        untouched by this batch) -- the pinned ``derive_session_aggregate``'s own tolerance for an
        empty decision list (``difficulty_trend`` falls back to ``"stable"``,
        ``current_difficulty_level`` to 1, an honest "no decisions occurred," not a fabrication)
        is therefore no longer the ONLY case this list can be seen in, but is still the only case
        aggregation itself can currently reach."""
        result = await self.session.execute(
            select(CPolicyDecisionRecord)
            .where(CPolicyDecisionRecord.c_session_id == c_session_id)
            .order_by(CPolicyDecisionRecord.created_at_utc)
        )
        return result.scalars().all()


class CSafetyEventRecordRepository(SqlAlchemyNeutralRepository[CSafetyEventRecord]):
    model_type = CSafetyEventRecord


class CScaffoldEventRecordRepository(SqlAlchemyNeutralRepository[CScaffoldEventRecord]):
    model_type = CScaffoldEventRecord


class SessionEventRepository(SqlAlchemyNeutralRepository[SessionEvent]):
    model_type = SessionEvent


class IdempotencyRecordRepository(SqlAlchemyNeutralRepository[IdempotencyRecord]):
    model_type = IdempotencyRecord

    async def find_scoped(
        self,
        actor_user_id: UUID,
        http_method: str,
        operation_identifier: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        statement: Select[tuple[IdempotencyRecord]] = select(IdempotencyRecord).where(
            IdempotencyRecord.actor_user_id == actor_user_id,
            IdempotencyRecord.http_method == http_method,
            IdempotencyRecord.operation_identifier == operation_identifier,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
        return await self.session.scalar(statement)


class AuditEventRepository(SqlAlchemyNeutralRepository[AuditEvent]):
    model_type = AuditEvent


class TeacherProfileRepository(SqlAlchemyNeutralRepository[TeacherProfile]):
    model_type = TeacherProfile

    async def find_by_user(self, user_id: UUID) -> TeacherProfile | None:
        return await self.session.scalar(select(TeacherProfile).where(TeacherProfile.user_id == user_id))


class ClassroomRepository(SqlAlchemyNeutralRepository[Classroom]):
    model_type = Classroom

    # Both teacher-facing reads exclude soft-deleted classrooms (20260914_0009). Every
    # teacher command resolves its classroom through get_owned, so a deleted classroom cannot
    # be fetched, listed, invited to, have its requests listed, or be deleted twice.
    async def list_owned(self, teacher_profile_id: UUID) -> list[Classroom]:
        result = await self.session.scalars(select(Classroom).where(Classroom.teacher_profile_id == teacher_profile_id, Classroom.deleted_at_utc.is_(None)).order_by(Classroom.created_at_utc, Classroom.classroom_id))
        return list(result)

    async def get_owned(self, classroom_id: UUID, teacher_profile_id: UUID) -> Classroom | None:
        return await self.session.scalar(select(Classroom).where(Classroom.classroom_id == classroom_id, Classroom.teacher_profile_id == teacher_profile_id, Classroom.deleted_at_utc.is_(None)))


class ClassroomInviteRepository(SqlAlchemyNeutralRepository[ClassroomInvite]):
    model_type = ClassroomInvite

    async def find_by_token_hash(self, token_hash: str) -> ClassroomInvite | None:
        return await self.session.scalar(select(ClassroomInvite).where(ClassroomInvite.token_hash == token_hash))

    async def find_live_by_classroom(self, classroom_id: UUID, now: datetime) -> ClassroomInvite | None:
        """The classroom's one live join code, if it has one.

        A classroom has at most one non-revoked invite: the code is created with the
        classroom, never expires and is never rotated, so minting a second would leave two
        codes resolving to the same room with only one of them readable by the teacher.

        "Live" has to mean the same thing here as it does at redemption, and it did not. This
        filtered on `revoked_at_utc` alone, while `resolve_invite` and `request_membership` both
        additionally reject an invite whose `expires_at_utc` has passed. Permanent join codes
        carry `expires_at_utc = NULL`, but every invite minted BEFORE they landed carries a real
        24h expiry and was never revoked -- so for those classrooms this reported a live code that
        no learner could redeem, `create_invite` declined to mint a replacement
        (`token_already_issued=True, invite_token=None`), and the only existing code's plaintext
        had been discarded at creation. The classroom was left permanently unable to issue a
        usable join code, with no recovery path through the API.

        `order_by` + `limit(1)` because the "at most one" invariant is aspirational, not enforced
        by a constraint: databases predating this already hold several unrevoked rows per
        classroom, and an unordered `scalar()` over them picks an arbitrary one.
        """
        return await self.session.scalar(
            select(ClassroomInvite)
            .where(
                ClassroomInvite.classroom_id == classroom_id,
                ClassroomInvite.revoked_at_utc.is_(None),
                or_(
                    ClassroomInvite.expires_at_utc.is_(None),
                    ClassroomInvite.expires_at_utc > now,
                ),
            )
            .order_by(ClassroomInvite.created_at_utc.desc(), ClassroomInvite.classroom_invite_id.desc())
            .limit(1)
        )

    async def get_owned(self, classroom_invite_id: UUID, teacher_profile_id: UUID) -> ClassroomInvite | None:
        statement = (
            select(ClassroomInvite)
            .join(Classroom, Classroom.classroom_id == ClassroomInvite.classroom_id)
            .where(
                ClassroomInvite.classroom_invite_id == classroom_invite_id,
                Classroom.teacher_profile_id == teacher_profile_id,
                Classroom.deleted_at_utc.is_(None),
            )
        )
        return await self.session.scalar(statement)


class ClassroomMembershipRepository(SqlAlchemyNeutralRepository[ClassroomMembership]):
    model_type = ClassroomMembership

    async def find_by_classroom_and_learner(self, classroom_id: UUID, learner_id: UUID) -> ClassroomMembership | None:
        return await self.session.scalar(
            select(ClassroomMembership).where(ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.learner_id == learner_id)
        )

    async def get_owned(self, classroom_membership_id: UUID, teacher_profile_id: UUID) -> ClassroomMembership | None:
        statement = (
            select(ClassroomMembership)
            .join(Classroom, Classroom.classroom_id == ClassroomMembership.classroom_id)
            .where(
                ClassroomMembership.classroom_membership_id == classroom_membership_id,
                Classroom.teacher_profile_id == teacher_profile_id,
                Classroom.deleted_at_utc.is_(None),
            )
        )
        return await self.session.scalar(statement)

    async def learner_has_other_approved_membership(self, learner_id: UUID, excluding_membership_id: UUID) -> bool:
        existing = await self.session.scalar(
            select(ClassroomMembership.classroom_membership_id).where(
                ClassroomMembership.learner_id == learner_id,
                ClassroomMembership.state == "APPROVED",
                ClassroomMembership.classroom_membership_id != excluding_membership_id,
            )
        )
        return existing is not None

    async def list_for_classroom_with_learner_name(self, classroom_id: UUID) -> list[tuple[ClassroomMembership, str | None]]:
        statement = (
            select(ClassroomMembership, Learner.name)
            .join(Learner, Learner.learner_id == ClassroomMembership.learner_id)
            .where(ClassroomMembership.classroom_id == classroom_id)
            .order_by(ClassroomMembership.requested_at_utc, ClassroomMembership.classroom_membership_id)
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def list_approved_for_classroom_with_learner_name(self, classroom_id: UUID) -> list[tuple[ClassroomMembership, str | None]]:
        statement = (
            select(ClassroomMembership, Learner.name)
            .join(Learner, Learner.learner_id == ClassroomMembership.learner_id)
            .where(ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.state == "APPROVED")
            .order_by(ClassroomMembership.decided_at_utc, ClassroomMembership.classroom_membership_id)
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def list_for_learner_with_classroom(self, learner_id: UUID) -> list[tuple[ClassroomMembership, str | None, str]]:
        statement = (
            select(ClassroomMembership, Classroom.name, Classroom.grade)
            .join(Classroom, Classroom.classroom_id == ClassroomMembership.classroom_id)
            # A membership that ended with its classroom's deletion is not shown to the
            # learner: with nothing left, the app sends them back to enter a classroom code.
            .where(ClassroomMembership.learner_id == learner_id, ClassroomMembership.state != "REMOVED")
            .order_by(ClassroomMembership.requested_at_utc, ClassroomMembership.classroom_membership_id)
        )
        result = await self.session.execute(statement)
        return list(result.all())


class ItemOpportunityRepository(SqlAlchemyNeutralRepository[ItemOpportunityRecord]):
    model_type = ItemOpportunityRecord

    async def find_open_for_session(self, session_id: UUID) -> ItemOpportunityRecord | None:
        return await self.session.scalar(
            select(ItemOpportunityRecord).where(
                ItemOpportunityRecord.session_id == session_id,
                ItemOpportunityRecord.state == "OPEN",
            )
        )

    async def get_owned(self, item_opportunity_id: UUID, learner_id: UUID) -> ItemOpportunityRecord | None:
        return await self.session.scalar(
            select(ItemOpportunityRecord).where(
                ItemOpportunityRecord.item_opportunity_id == item_opportunity_id,
                ItemOpportunityRecord.learner_id == learner_id,
            )
        )

    async def count_for_session(self, session_id: UUID) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id)
        )

    async def get_for_update(self, item_opportunity_id: UUID) -> ItemOpportunityRecord | None:
        """Row-locks the opportunity so attempt-index derivation and the OPEN-state check are
        race-free under concurrent submissions (BEplan §9 BE4.3 step 4)."""
        return await self.session.scalar(
            select(ItemOpportunityRecord)
            .where(ItemOpportunityRecord.item_opportunity_id == item_opportunity_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def count_closed_for_session(self, session_id: UUID) -> int:
        """BE4e (BEplan §9 BE4.6): count of CLOSED-only opportunities — used by the SAFE
        standing view so an in-progress (still-OPEN) opportunity is never counted as
        completed."""
        return await self.session.scalar(
            select(func.count())
            .select_from(ItemOpportunityRecord)
            .where(ItemOpportunityRecord.session_id == session_id, ItemOpportunityRecord.state == "CLOSED")
        )

    async def sessions_since_practice(self, learner_id: UUID) -> dict[str, int]:
        """BE-P2: per skill, how many of this learner's later sessions have started since the most
        recent session in which that skill was practised.

        This is the input ``sequencing.features.compute_features`` documents as "sessions since last
        practice" and feeds ``spacing_due``. Only skills the learner has actually practised appear in
        the result; a skill absent from the mapping is "never practised", which the feature function
        maps to ``spacing_due = 1.0`` (maximally due).

        SEMANTICS, stated because they are a reading rather than a specification: "sessions since"
        counts DISTINCT sessions of this learner that were created strictly after the last session
        containing an opportunity for the skill. The current session therefore contributes 0 to a
        skill practised within it, which is what makes ``spacing_due`` drop immediately after
        practice and recover as later sessions accumulate.
        """
        last_practised = (
            select(
                ItemOpportunityRecord.skill_id.label("skill_id"),
                func.max(SessionRecord.created_at_utc).label("last_at"),
            )
            .join(SessionRecord, SessionRecord.session_id == ItemOpportunityRecord.session_id)
            .where(ItemOpportunityRecord.learner_id == learner_id)
            .group_by(ItemOpportunityRecord.skill_id)
            .subquery()
        )
        later_sessions = (
            select(func.count(func.distinct(SessionRecord.session_id)))
            .where(
                SessionRecord.learner_id == learner_id,
                SessionRecord.created_at_utc > last_practised.c.last_at,
            )
            .scalar_subquery()
        )
        rows = await self.session.execute(
            select(last_practised.c.skill_id, later_sessions.label("sessions_since"))
        )
        return {skill_id: int(sessions_since) for skill_id, sessions_since in rows}

    async def prior_session_first_attempt_rts(
        self, learner_id: UUID, current_session_id: UUID
    ) -> dict[str, list[float]]:
        """BF-1: per skill, the learner's first-attempt response times in **seconds** from
        sessions strictly before the current one — the practice history the guess-guard's
        plausibility floor must be computed from (mirrors the reference sequencing,
        ``Yass/.../pipeline.py``'s floor-from-prior-sessions / median-from-this-session split).

        Before this method existed, the floor and the current session's own median were computed
        from the *same* current-session-only sample, which made the guard's ``TRIGGERED`` outcome
        mathematically unreachable (the floor's quantile can never exceed the median's quantile on
        one identical sample) — see ``session_completion.py``'s BF-1 docstring at the call site.

        SEMANTICS, stated because they are a reading rather than a specification, mirroring
        ``_build_opportunity_response``'s own within-session filter exactly so the prior-session
        and current-session samples are computed the same way: only the **first** attempt
        (``attempt_index == 1``) per opportunity counts — retries are never a first-attempt
        observation, matching BKT's own first-attempt-only discipline — and only when that first
        attempt was a real ``RESPONSE`` (never ``TIMEOUT``; a timeout has no valid response time)
        with a strictly positive elapsed time. "Strictly before" is by session creation time,
        matching ``sessions_since_practice``'s own convention above. A learner or skill with no
        qualifying prior history is simply absent from the result — ``plausibility_floor`` already
        treats that as insufficient evidence (``INSUFFICIENT_EVIDENCE``, never a fabricated floor).
        """
        current_session = await self.session.get(SessionRecord, current_session_id)
        if current_session is None:
            return {}

        rows = await self.session.execute(
            select(ItemOpportunityRecord.skill_id, AttemptRecord.client_elapsed_ms)
            .join(AttemptRecord, AttemptRecord.item_opportunity_id == ItemOpportunityRecord.item_opportunity_id)
            .join(SessionRecord, SessionRecord.session_id == ItemOpportunityRecord.session_id)
            .where(
                ItemOpportunityRecord.learner_id == learner_id,
                SessionRecord.created_at_utc < current_session.created_at_utc,
                AttemptRecord.attempt_index == 1,
                AttemptRecord.event_kind == "RESPONSE",
                AttemptRecord.client_elapsed_ms.isnot(None),
                AttemptRecord.client_elapsed_ms > 0,
            )
        )
        history: dict[str, list[float]] = {}
        for skill_id, client_elapsed_ms in rows:
            history.setdefault(skill_id, []).append(client_elapsed_ms / 1000.0)
        return history

    async def list_for_session(self, session_id: UUID) -> list[ItemOpportunityRecord]:
        """BE4e (BEplan §9 BE4.6): every opportunity row for a session, ordered deterministically,
        used to build the session-aggregation input set."""
        result = await self.session.scalars(
            select(ItemOpportunityRecord)
            .where(ItemOpportunityRecord.session_id == session_id)
            .order_by(ItemOpportunityRecord.opportunity_index)
        )
        return list(result)


class TaskInstanceRepository(SqlAlchemyNeutralRepository[TaskInstanceRecord]):
    model_type = TaskInstanceRecord

    async def find_by_opportunity(self, item_opportunity_id: UUID) -> TaskInstanceRecord | None:
        return await self.session.scalar(
            select(TaskInstanceRecord).where(TaskInstanceRecord.item_opportunity_id == item_opportunity_id)
        )

    async def map_by_opportunities(
        self, item_opportunity_ids: Sequence[UUID]
    ) -> dict[UUID, TaskInstanceRecord]:
        """`find_by_opportunity` for a whole session in one round trip.

        Session finalisation needs the instance for every opportunity it is aggregating. Asking
        one opportunity at a time is an N+1 that costs a full network round trip per question --
        the single `POST .../complete` that ends a session issued 34 statements where a
        mid-session one issues 18. The mapping is 1:1 (`uq_b_task_instances_opportunity`), so a
        dict keyed by opportunity id loses nothing, and a missing key means exactly what a `None`
        from `find_by_opportunity` meant.
        """
        if not item_opportunity_ids:
            return {}
        rows = await self.session.scalars(
            select(TaskInstanceRecord).where(
                TaskInstanceRecord.item_opportunity_id.in_(item_opportunity_ids)
            )
        )
        return {row.item_opportunity_id: row for row in rows}


class PresentationTokenRepository(SqlAlchemyNeutralRepository[PresentationTokenRecord]):
    model_type = PresentationTokenRecord

    async def find_by_token_hash(self, token_hash: str) -> PresentationTokenRecord | None:
        return await self.session.scalar(
            select(PresentationTokenRecord).where(PresentationTokenRecord.token_hash == token_hash)
        )


class LearnerSkillStateRepository(SqlAlchemyNeutralRepository[LearnerSkillStateRecord]):
    model_type = LearnerSkillStateRecord

    async def list_for_learner(self, learner_id: UUID) -> list[LearnerSkillStateRecord]:
        result = await self.session.scalars(
            select(LearnerSkillStateRecord).where(LearnerSkillStateRecord.learner_id == learner_id)
        )
        return list(result)

    async def get_for_update(self, learner_id: UUID, skill_id: str) -> LearnerSkillStateRecord | None:
        """``populate_existing=True`` is required: BE4b's selection step may already have loaded
        this row into the session identity map earlier in the same request; without it SQLAlchemy
        would keep those stale pre-lock attributes instead of refreshing from this FOR UPDATE
        read (the same identity-map staleness hazard BE4c's spec calls out from the
        approve_membership carry-forward)."""
        return await self.session.scalar(
            select(LearnerSkillStateRecord)
            .where(LearnerSkillStateRecord.learner_id == learner_id, LearnerSkillStateRecord.skill_id == skill_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )


class AttemptRepository(SqlAlchemyNeutralRepository[AttemptRecord]):
    model_type = AttemptRecord

    async def count_for_opportunity(self, item_opportunity_id: UUID) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
        )

    async def list_for_opportunity(self, item_opportunity_id: UUID) -> list[AttemptRecord]:
        """BE4e (BEplan §9 BE4.6): every attempt/timeout event for one opportunity, ordered by
        ``attempt_index``, used to derive the opportunity-level aggregation summary."""
        result = await self.session.scalars(
            select(AttemptRecord)
            .where(AttemptRecord.item_opportunity_id == item_opportunity_id)
            .order_by(AttemptRecord.attempt_index)
        )
        return list(result)

    async def map_for_opportunities(
        self, item_opportunity_ids: Sequence[UUID]
    ) -> dict[UUID, list[AttemptRecord]]:
        """`list_for_opportunity` for a whole session in one round trip.

        Ordering is the load-bearing part: the per-opportunity lists must come out ordered by
        ``attempt_index`` exactly as `list_for_opportunity` returns them, because the aggregation
        summary is derived from that order. Ordering by opportunity id first keeps each group
        contiguous, and `attempt_index` second reproduces the per-group order verbatim.
        """
        if not item_opportunity_ids:
            return {}
        rows = await self.session.scalars(
            select(AttemptRecord)
            .where(AttemptRecord.item_opportunity_id.in_(item_opportunity_ids))
            .order_by(AttemptRecord.item_opportunity_id, AttemptRecord.attempt_index)
        )
        grouped: dict[UUID, list[AttemptRecord]] = {}
        for row in rows:
            grouped.setdefault(row.item_opportunity_id, []).append(row)
        return grouped


class SkillStateTransitionRepository(SqlAlchemyNeutralRepository[SkillStateTransitionRecord]):
    """No update/delete method is defined here by design — transitions are immutable (BEplan
    §9 BE4.4)."""

    model_type = SkillStateTransitionRecord

    async def find_by_opportunity(self, item_opportunity_id: UUID) -> SkillStateTransitionRecord | None:
        return await self.session.scalar(
            select(SkillStateTransitionRecord).where(SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id)
        )

    async def list_for_opportunities(self, item_opportunity_ids: Sequence[UUID]) -> list[SkillStateTransitionRecord]:
        """BE4e (BEplan §9 BE4.6): every first-attempt BKT transition across a set of
        opportunities (one session's), used to build the aggregation's
        ``SkillMasteryUpdate`` inputs. Empty input returns ``[]`` without a query."""
        if not item_opportunity_ids:
            return []
        result = await self.session.scalars(
            select(SkillStateTransitionRecord)
            .where(SkillStateTransitionRecord.item_opportunity_id.in_(item_opportunity_ids))
            .order_by(SkillStateTransitionRecord.created_at_utc, SkillStateTransitionRecord.skill_state_transition_id)
        )
        return list(result)


class HintEventRepository(SqlAlchemyNeutralRepository[HintEventRecord]):
    """BE4d (BEplan §9 BE4.5). SEPARATE from ``AttemptRepository``/``SkillStateTransitionRepository``
    — a hint event never touches attempt or BKT-transition rows."""

    model_type = HintEventRecord

    async def count_for_opportunity(self, item_opportunity_id: UUID) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(HintEventRecord).where(HintEventRecord.item_opportunity_id == item_opportunity_id)
        )

    async def count_by_opportunities(self, item_opportunity_ids: Sequence[UUID]) -> dict[UUID, int]:
        """`count_for_opportunity` for a whole session in one round trip.

        A GROUP BY returns no row for an opportunity with no hints, where
        `count_for_opportunity` would have returned 0 -- so callers must read this with a
        `.get(id, 0)` default rather than indexing it.
        """
        if not item_opportunity_ids:
            return {}
        result = await self.session.execute(
            select(HintEventRecord.item_opportunity_id, func.count())
            .where(HintEventRecord.item_opportunity_id.in_(item_opportunity_ids))
            .group_by(HintEventRecord.item_opportunity_id)
        )
        return {opportunity_id: count for opportunity_id, count in result.all()}


class SessionAggregateResultRepository(SqlAlchemyNeutralRepository[SessionAggregateResultRecord]):
    """BE4e (BEplan §9 BE4.6). No update/delete method by design — immutable, same discipline as
    ``SkillStateTransitionRepository``."""

    model_type = SessionAggregateResultRecord

    async def find_by_session(self, session_id: UUID) -> SessionAggregateResultRecord | None:
        return await self.session.scalar(
            select(SessionAggregateResultRecord).where(SessionAggregateResultRecord.session_id == session_id)
        )


class SkillCertificationResultRepository(SqlAlchemyNeutralRepository[SkillCertificationResultRecord]):
    """BE4e (BEplan §9 BE4.6). No update/delete method by design — immutable."""

    model_type = SkillCertificationResultRecord

    async def list_for_session(self, session_id: UUID) -> list[SkillCertificationResultRecord]:
        result = await self.session.scalars(
            select(SkillCertificationResultRecord).where(SkillCertificationResultRecord.session_id == session_id)
        )
        return list(result)


# =====================================================================================
# Component D (Component D authorization, owner decision D-011 A1, 2026-10-21).
#
# Added here rather than in a new `d_repositories.py` so that every repository in the backend
# stays in one place -- the host has kept B's, C's and the shared tables together in this file
# since BE2, and a separate module for D alone would make "where do repositories live" have two
# answers.
# =====================================================================================


class DLearnerStateRepository(SqlAlchemyNeutralRepository[DLearnerStateRecord]):
    """One row per learner. A learner with NO ROW is a supported state, not an error -- the
    contract reads it as ``{intro_completed: false, language: "en"}`` and creates nothing."""

    model_type = DLearnerStateRecord

    async def find_for_learner(self, learner_id: UUID) -> DLearnerStateRecord | None:
        return await self.session.get(DLearnerStateRecord, learner_id)

    async def get_for_update(self, learner_id: UUID) -> DLearnerStateRecord | None:
        """``populate_existing=True`` for the same reason ``LearnerSkillStateRepository`` gives:
        the upsert reads this row after an advisory lock, and if anything earlier in the same
        request already loaded it, the identity map would hand back the pre-lock attributes
        instead of what the locked read actually found."""
        return await self.session.scalar(
            select(DLearnerStateRecord)
            .where(DLearnerStateRecord.learner_id == learner_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )


class DInteractionRepository(SqlAlchemyNeutralRepository[DInteractionRecord]):
    """The raw per-question evidence a profile was computed from. No update or delete method by
    design: once a run is recorded, what the child did is not editable."""

    model_type = DInteractionRecord

    async def list_for_session(self, session_id: UUID) -> list[DInteractionRecord]:
        result = await self.session.scalars(
            select(DInteractionRecord)
            .where(DInteractionRecord.session_id == session_id)
            .order_by(DInteractionRecord.question_id)
        )
        return list(result)


class DCognitiveProfileRepository(SqlAlchemyNeutralRepository[DCognitiveProfileRecord]):
    """One profile per profiling run. ``session_id`` is unique GLOBALLY, which is what lets
    ``find_for_session`` be a single lookup and lets the route refuse another learner's session as
    a 404 rather than reveal that it exists."""

    model_type = DCognitiveProfileRecord

    async def find_for_session(self, session_id: UUID) -> DCognitiveProfileRecord | None:
        return await self.session.scalar(
            select(DCognitiveProfileRecord).where(DCognitiveProfileRecord.session_id == session_id)
        )

    async def find_latest_for_learner(self, learner_id: UUID) -> DCognitiveProfileRecord | None:
        return await self.session.scalar(
            select(DCognitiveProfileRecord)
            .where(DCognitiveProfileRecord.learner_id == learner_id)
            .order_by(DCognitiveProfileRecord.generated_at.desc())
            .limit(1)
        )

    async def list_for_learner(self, learner_id: UUID, limit: int) -> list[DCognitiveProfileRecord]:
        """Newest first, which is the order the history screen renders and the order
        ``ix_d_cognitive_profiles_learner_generated_at`` was created DESC to serve."""
        result = await self.session.scalars(
            select(DCognitiveProfileRecord)
            .where(DCognitiveProfileRecord.learner_id == learner_id)
            .order_by(DCognitiveProfileRecord.generated_at.desc())
            .limit(limit)
        )
        return list(result)
