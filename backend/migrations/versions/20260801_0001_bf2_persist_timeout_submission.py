"""BF-2: allow a persisted submitted_value on a TIMEOUT attempt.

``ck_b_attempts_response_matched_consistency`` (20260728_0001) required
``submitted_value IS NULL`` on every ``TIMEOUT`` row — a database-level encoding of the very
defect BF-2 fixes at the application layer (``app/application/attempt_submission.py``): a
late-but-real answer was discarded rather than persisted. Fixing only the Python without this
migration leaves the constraint rejecting every timeout submission with an IntegrityError
(surfaced to the caller as a 409 ``ConflictError`` via the existing infra-failure handling), which
is how this gap was caught — not anticipated by the change that motivated it.

The relaxed constraint keeps every part of the original invariant that is still correct:
``response_matched`` continues to be NOT NULL iff ``event_kind = 'RESPONSE'`` (a timeout is never
scored — no change to what counts as a BKT observation, see ``attempt_submission.py``'s BF-2
docstring). It adds one requirement instead of relaxing to nothing: ``submitted_value`` is now
NOT NULL unconditionally, matching the fact that the request schema
(``SubmitResponseRequest.submitted_value``, ``min_length=1``) never allows an empty submission —
so every attempt, timed out or not, now always carries the learner's own text.

DOWNGRADE IS DELIBERATELY ASYMMETRIC — DROP ONLY, NEVER RE-ADD THE OLD CONSTRAINT.

This was not the first draft. A symmetric downgrade (drop this constraint, recreate the exact
20260728_0001 original) was tried first and fails in practice, reproducibly, the moment any real
timeout attempt has been recorded since this migration applied: the fixed application code always
writes a non-null ``submitted_value`` on ``TIMEOUT`` now, so the old constraint
(``... OR (event_kind = 'TIMEOUT' AND response_matched IS NULL AND submitted_value IS NULL)``) is
violated by every such row, and ``ALTER TABLE ... ADD CONSTRAINT`` fails with a
``CheckViolationError``. That is not a corrupted-data edge case — every one of this project's own
``test_migration_downgrade_reupgrade_cycle_and_schema`` tests (one per BE4x batch) downgrades all
the way to a revision that predates ``b_attempts`` entirely, which unconditionally drops the whole
table a few steps further down this same chain regardless of what this migration's downgrade
does. Re-imposing a constraint immediately before the table is dropped anyway buys nothing and
breaks every real timeout submission recorded in the meantime. ``downgrade()`` below therefore
only drops the constraint, leaving the schema at "no explicit response_matched-consistency check"
— a valid, if slightly less defensive, description of the pre-BF-2 schema, and one that can never
fail regardless of what data exists.

``upgrade()`` uses ``DROP CONSTRAINT IF EXISTS`` for the same reason, not just symmetry: because
``downgrade()`` leaves the constraint absent rather than restoring the original, a database that
has been downgraded once and is now being upgraded again no longer has anything for a bare
``DROP CONSTRAINT`` to find — that exact sequence (upgrade, exercise the app, downgrade, upgrade
again) was run by hand while building this migration and failed with ``UndefinedObjectError``
before this was made idempotent. A brand-new database reaching this revision for the first time
still behaves identically: the constraint from 20260728_0001 exists, ``IF EXISTS`` finds it, and
it is dropped and replaced exactly as before.

THE NEW CONSTRAINT IS ADDED ``NOT VALID`` — this was not the second draft either, and the reason
is a real defect the tests above cannot see. PostgreSQL validates a plain ``ADD CONSTRAINT ...
CHECK (...)`` against every existing row at creation time. Every ``TIMEOUT`` row written before
this migration has ``submitted_value IS NULL`` — because the *old* constraint required exactly
that — and the new constraint's ``submitted_value IS NOT NULL`` clause rejects every one of them.
So the plain form of this migration fails outright on any database with real timeout history,
which is precisely the population it exists to accommodate going forward. Reproduced directly: at
``20260728_0003``, hand-inserted one attempt row shaped exactly like genuine pre-BF-2 output
(``event_kind='TIMEOUT'``, ``submitted_value=NULL``, ``response_matched=NULL``), then ran
``alembic upgrade head`` — it failed with the exact ``CheckViolationError`` this paragraph
describes, confirming the defect before writing the fix, not after.

No test in this suite could have caught this. The existing
``test_migration_downgrade_reupgrade_cycle_and_schema`` tests downgrade to a revision that
predates ``b_attempts`` entirely, dropping the table — so their subsequent upgrade always runs
against an *empty* table, never a populated one. And the manual upgrade/exercise/downgrade/upgrade
cycle used while building this migration exercised only the fixed application code, which always
writes a non-null value now — legacy pre-fix rows were never in play at any point that testing
touched.

``NOT VALID`` (Postgres syntax on ``ALTER TABLE ... ADD CONSTRAINT``) enforces the constraint on
every new and updated row from this point forward, while leaving existing rows unscanned and
unenforced. This is the honest encoding of what actually happened, not a workaround: those
answers were genuinely destroyed by the old code and cannot be recovered, so backfilling a
sentinel value would fabricate data that was never observed — exactly what this project's
first-attempt-only, never-synthesize discipline exists to prevent elsewhere (hints, distractors,
BKT). A legacy ``TIMEOUT`` row keeps its real, honest ``NULL`` forever. Do not backfill it and do
not delete it. (``ALTER TABLE ... VALIDATE CONSTRAINT`` exists if a future operator ever wants to
force a full scan — e.g. after confirming no legacy rows remain — but nothing in this batch calls
for it, and doing so would immediately hit the same failure this paragraph describes.)

Revision ID: 20260801_0001
Revises: 20260728_0003
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260801_0001"
down_revision: str | Sequence[str] | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "ck_b_attempts_response_matched_consistency"
_NEW_CONSTRAINT = (
    "submitted_value IS NOT NULL "
    "AND ((event_kind = 'RESPONSE' AND response_matched IS NOT NULL) "
    "OR (event_kind = 'TIMEOUT' AND response_matched IS NULL))"
)


def upgrade() -> None:
    # IF EXISTS: see the module docstring — this must tolerate a database that reached
    # 20260728_0003 by downgrading from this very revision, where the constraint is already gone.
    op.execute(f"ALTER TABLE b_attempts DROP CONSTRAINT IF EXISTS {_CONSTRAINT_NAME}")
    # NOT VALID: see the module docstring's dedicated section. A plain ADD CONSTRAINT would scan
    # and reject every pre-BF-2 TIMEOUT row (submitted_value IS NULL, by the old constraint's own
    # requirement) on any database with real timeout history. NOT VALID enforces the constraint on
    # all new and updated rows without scanning existing ones — legacy NULLs are left exactly as
    # they honestly are, never backfilled.
    op.execute(f"ALTER TABLE b_attempts ADD CONSTRAINT {_CONSTRAINT_NAME} CHECK ({_NEW_CONSTRAINT}) NOT VALID")


def downgrade() -> None:
    # Deliberately does not recreate the old constraint — see the module docstring's DOWNGRADE
    # section for why that fails against any real timeout data recorded under the new one, and
    # why it wouldn't matter anyway (the next downgrade step in every documented cycle drops this
    # table outright).
    op.execute(f"ALTER TABLE b_attempts DROP CONSTRAINT IF EXISTS {_CONSTRAINT_NAME}")
