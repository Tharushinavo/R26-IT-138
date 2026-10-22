"""Component C Phase 6a, T1 (SUPERVISOR RULING -- OWNER-RULED, record as a ruling, not an
engineering default): derivation is wired to ``completed_correct`` in 6a, and no other terminal
reason is built.

Owner ruling, quoted verbatim: "One opportunity carries one ``correct_answer_payload`` and the
evaluator returns one verdict against it. I cannot construct a coherent reading in which a
correctly-answered opportunity stays open -- a follow-on activity is a new opportunity, not a
continuation of a solved one. And it needs no unsigned parameter: a correct answer on attempt 2 of
a cap of 3 is ``completed_correct``, so the attempt bound never enters. The cap only governs the
incorrect path, which is exactly why your asymmetry is real rather than an oversight." And: "record
it as an owner ruling with that reasoning attached, not as an engineering default. Someone will
read this later and need to know it was decided rather than assumed."

T1-1 -- THE OTHER EIGHT FAIL CLOSED, NOT DOCUMENTED. ``_BLOCKER_BY_TERMINAL_REASON`` below
enumerates all nine terminal reasons (mirroring, not importing, ``component_c_generator.models.
gameplay.TERMINAL_REASON_EVENT_TYPE`` -- this file is not ``app/infrastructure/live_engine_c/
adapter.py``, the ONE file permitted a ``component_c_generator`` import root anywhere under
``app/`` (X-1), so the package's own dict cannot be read here; ``persistence_models.py``'s own
``ck_c_gameplay_events_terminal_reason``/``ck_c_task_opportunity_summaries_terminal_reason`` CHECK
constraints already hand-copy this exact nine-value vocabulary for the identical reason, cited
from the package rather than read from it -- this file follows that same, already-established
convention). ``tests/test_c6a_summary_derivation.py`` verifies this mapping's key set against the
package's live dict AT RUNTIME (the R-I pattern, R-7's precedent) so a future upstream change
cannot silently leave this mapping's coverage stale.

Owner's words: "An enumeration that falls through silently is a comment with extra steps. 6b then
removes exactly one entry, and removing it is a visible diff rather than a discovery."

T1-5 -- THE RECORD STATES WHAT IS NOT BUILT. Owner's words: "no terminal rule exists for eight of
nine reasons, so no session can currently end by any route other than a correct answer. That is a
conspicuous incompleteness and it belongs in the batch record, not inferred from the mapping." That
statement is recorded here, plainly: as of this batch, the ONLY way a ``c_task_opportunity`` can
ever reach a terminal state in this codebase is a correctly-evaluated ``submit_action`` call. A
session that is abandoned, quit, times out, or is answered incorrectly forever (no attempt cap
exists to close it) simply never terminates -- there is no code path anywhere under ``app/`` that
writes ``game_task_skipped`` or ``game_task_quit``, and ``game_task_completed`` is reachable only
via ``completed_correct``. This is not a bug to silently work around; it is this batch's named,
disclosed boundary.
"""

from __future__ import annotations

from typing import Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.session_lifecycle import _provenance
from app.core.errors import ConflictError
from app.infrastructure.persistence_models import CGameplayEventRecord
from app.infrastructure.repositories import CGameplayEventRecordRepository

# T1-1: the built-vs-blocked status of each of the nine terminal reasons. "BUILT" marks the one
# reason this batch writes; every other value names the SPECIFIC blocker preventing it, quoted
# from the owner's own T1 conditions -- never a generic "not yet implemented".
_BLOCKER_BY_TERMINAL_REASON: Mapping[str, str] = {
    "completed_correct": "BUILT",
    "completed_incorrect": (
        "reachable only via attempt-cap exhaustion or a quit terminal reason, both themselves "
        "blocked below -- there is no third route to an incorrect-but-terminal task"
    ),
    "attempt_cap_exhausted": (
        "I4 / unsigned attempt bound -- no governed maximum-attempts value exists anywhere in "
        "this codebase for any template"
    ),
    "skipped": (
        "Phase 8 untrusted-input ingestion -- no client-reported terminal reason may be trusted "
        "before Phase 8's telemetry validator exists to check it on arrival"
    ),
    "quit_after_error": (
        "Phase 8 untrusted-input ingestion -- no client-reported terminal reason may be trusted "
        "before Phase 8's telemetry validator exists to check it on arrival"
    ),
    "quit_without_recent_error": (
        "Phase 8 untrusted-input ingestion -- no client-reported terminal reason may be trusted "
        "before Phase 8's telemetry validator exists to check it on arrival"
    ),
    "technical_issue": (
        "Phase 8 untrusted-input ingestion -- no client-reported terminal reason may be trusted "
        "before Phase 8's telemetry validator exists to check it on arrival"
    ),
    "timeout_no_response": (
        "unsigned timeout parameter -- no governed inactivity-timeout value exists anywhere in "
        "this codebase"
    ),
    "safe_session_stop": (
        "6b's hard safety controller -- decide_adaptation/apply_safety are not wired to any "
        "caller until Phase 6b"
    ),
}


class TerminalReasonNotBuiltError(Exception):
    """T1-1: raised by ``assert_terminal_reason_built`` for any of the eight terminal reasons this
    batch does not build, carrying the SPECIFIC blocker (never a generic message) so a future
    reader -- or a future phase's code attempting to close a task opportunity by one of these
    routes -- learns exactly what must be resolved first, not merely that the call failed."""

    def __init__(self, terminal_reason: str, blocker: str) -> None:
        self.terminal_reason = terminal_reason
        self.blocker = blocker
        super().__init__(f"terminal_reason={terminal_reason!r} is not built: {blocker}")


def assert_terminal_reason_built(terminal_reason: str) -> None:
    """T1-1's dispatch: raises ``TerminalReasonNotBuiltError`` naming the specific blocker for
    any of the eight unbuilt reasons (or an unrecognized string), and returns silently only for
    ``"completed_correct"``. Called at the top of ``write_completed_correct_terminal_event`` so
    the guard is exercised on the one real call site, not merely asserted true by construction."""
    blocker = _BLOCKER_BY_TERMINAL_REASON.get(terminal_reason)
    if blocker is None:
        raise TerminalReasonNotBuiltError(terminal_reason, "not a recognized terminal_reason")
    if blocker != "BUILT":
        raise TerminalReasonNotBuiltError(terminal_reason, blocker)


# T1-3 (owner ruling, SUPERVISOR CORRECTION applied): "derive_task_opportunity_summary raises on
# a terminal count != 1, so a double-write surfaces as a confusing failure far from its cause.
# Mirror the Phase 4b triple." The named migration (uq_c_gameplay_events_one_terminal_per_
# opportunity) already exists under a different name --
# uq_c_gameplay_events_at_most_one_terminal_per_instance, Phase 3b, migrations/versions/
# 20260816_0003_c3b_gameplay_event_invariants.py:96, model at persistence_models.py:923-930 -- so
# per the owner's own correction this batch builds only the OTHER two thirds of the triple: the
# service-level check immediately below (``has_terminal_for_instance``) and the ``IntegrityError``
# -> ``ConflictError`` catch around the insert, with that EXISTING partial unique index as the
# backstop. NO MIGRATION THIS BATCH.
#
# T1-4 (owner ruling): "A network retry or a double-tap on a correct answer is an ordinary event,
# not an edge case, and Q4 left action submission with no idempotency key -- so this check is the
# only thing standing between a retry and a duplicated terminal write. The index in (3) is its
# backstop, not its substitute." This same repository check is called a SECOND time, earlier, at
# the top of ``TaskService.submit_action`` (before ``evaluate`` is ever invoked) -- a structured
# 409 there means an already-terminal opportunity never gets scored twice, not merely never
# double-written.
async def write_completed_correct_terminal_event(
    session: AsyncSession,
    *,
    c_session_id: UUID,
    c_task_instance_id: UUID,
    task_index: int,
    seed_lineage_global_seed: int,
    seed_lineage_path: list,
    seed_lineage_seed: int,
    generator_version: str,
    config_checksum: str,
    request_id: str,
    known_max_index: Optional[int] = None,
    known_max_timestamp: Optional[int] = None,
    known_not_terminal: bool = False,
    defer_flush: bool = False,
) -> CGameplayEventRecord:
    """PERF-01 (optional, default = unchanged behaviour): a caller that ALREADY holds the instance row lock and has
    just read the instance's event stream (``submit_action``) passes what it knows -- ``known_max_index`` /
    ``known_max_timestamp`` (the stream's maximum AFTER its own pending inserts) and ``known_not_terminal=True`` (it
    checked, in the same transaction) -- so the two re-reads below are skipped; ``defer_flush=True`` returns the built row without adding
    or flushing it, so the caller can insert it together with the answer events in one statement, in event_index order (the
    caller then owns the ``IntegrityError`` -> ``ConflictError`` translation for the unique-terminal index).

    The ONE call site anywhere under ``app/`` that writes a terminal ``CGameplayEventRecord``
    (T1-2, guard-tested by ``tests/test_be2_architecture_guards.py::
    test_only_completed_correct_writes_a_terminal_gameplay_event`` -- an AST scan, not a docstring
    promise). ``terminal_reason="completed_correct"`` is a literal string constant, never a
    variable, so the guard can prove it statically."""
    assert_terminal_reason_built("completed_correct")

    event_repo = CGameplayEventRecordRepository(session)
    # T1-3/T1-4's service-level check, second half of the triple's write-time protection (the
    # first half runs earlier in submit_action, before evaluate() is ever called).
    if not known_not_terminal and await event_repo.has_terminal_for_instance(c_task_instance_id):
        raise ConflictError(
            details=[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]
        )

    if known_max_index is None or known_max_timestamp is None:
        max_index, max_timestamp = await event_repo.max_index_and_timestamp_for_instance(c_task_instance_id)
    else:
        max_index, max_timestamp = known_max_index, known_max_timestamp
    event_id = uuid4()
    terminal_event = CGameplayEventRecord(
        c_gameplay_event_id=event_id,
        c_session_id=c_session_id,
        game_task_instance_id=c_task_instance_id,
        task_index=task_index,
        event_type="game_task_completed",
        event_index=max_index + 1,
        attempt_number=None,
        event_timestamp_relative_ms=max_timestamp + 1,
        action_payload=None,
        evaluation_payload=None,
        scaffold_code=None,
        technical_flag=False,
        terminal_reason="completed_correct",
        seed_lineage_global_seed=seed_lineage_global_seed,
        seed_lineage_path=seed_lineage_path,
        seed_lineage_seed=seed_lineage_seed,
        generator_version=generator_version,
        config_checksum=config_checksum,
        **_provenance("c_gameplay_event", event_id, request_id, "c_task.completed_correct"),
    )
    if defer_flush:
        return terminal_event       # NOT added: the caller adds it after the events it must follow (insert order = add order)
    try:
        await event_repo.add(terminal_event)
    except IntegrityError as exc:
        # T1-3's backstop: the partial unique index
        # (uq_c_gameplay_events_at_most_one_terminal_per_instance) is what actually enforces
        # at-most-one under a race the two service-level checks above did not catch (no
        # advisory lock is taken here -- Q4/T1-4's own words name the check-not-lock shape).
        raise ConflictError(
            details=[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]
        ) from exc
    return terminal_event
