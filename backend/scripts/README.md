Delete this directory when FE-1b (teacher classroom + approval UI) lands. It exists solely
because there is no in-app way to perform the teacher half of learner onboarding.

## What this is

`dev_fixture_learner.py` provisions a Grade-2 learner with an APPROVED classroom membership so
the learner-side screens can be built and tested against the real backend, one screen at a time,
without needing a real teacher app. It is HTTP-driven only — it authenticates as two real
Supabase users and drives the real FastAPI routes exactly as the Expo app would. It never opens a
database connection or writes a row directly.

## Usage

From `backend/`, with the API running (`docker compose up -d`):

```
python scripts/dev_fixture_learner.py --test-fixture-only
```

`--test-fixture-only` is required — it is the explicit confirmation that this script creates real
test data via the live API. The script also refuses to run if `APP_ENV=production` (read from
`backend/.env`, or the process environment).

### Getting a join code for a SEPARATE real account

The normal run above skips minting an invite once the fixture learner's own membership is
already `APPROVED` (the steady state after the first successful run) — so it prints no code to
copy. To get a fresh, real join code for a *different* account (e.g. your own) to paste into the
app's own join-code screen:

```
python scripts/dev_fixture_learner.py --test-fixture-only --mint-invite-only
```

This signs in as the fixture teacher and mints one fresh invite for the `FIXTURE Grade 2`
classroom, then exits — it never touches the fixture learner's profile, membership, or session.
The code is valid for 24h and works for any number of separate learners until it expires; it is
not consumed by a single use.

### Flags

- `--test-fixture-only` — required, see above.
- `--mint-invite-only` — see above; skips everything except signing in as the fixture teacher and
  minting one fresh invite.
- `--keep-session` — skip both the stale-session reset (step 4) and the self-verify session's
  final abandon (step 5), so a session survives the run for you to resume manually in the app.
- `--api-base` — override the backend API's base URL (default `http://localhost:8000`; also
  settable via the `DEV_FIXTURE_API_BASE` environment variable). This is a script argument only,
  not backend configuration — nothing is written to `backend/.env`.

## Fixture credentials

```
Teacher: dev-fixture-teacher@example.com / Fixture-Dev-Pass-2026!
Learner: dev-fixture-learner@example.com / Fixture-Dev-Pass-2026!
```

`example.com` is IANA-reserved and can never route real mail. Both are real Supabase users on the
project (email confirmation is off, so signup returns a usable session immediately); the learner
identity is shared with anyone else working against this Supabase project, so re-running this
script is always safe — it never creates a duplicate.

Sign into the Expo app as the learner to exercise the real, non-bypassed onboarding/auth path by
hand.

## Re-run / reset behavior

The script is designed to be run many times a day as the entry point for an iterative
build-test loop, not once:

- **Identity.** Each run signs up (fresh database) or signs in (everything after) as both fixture
  users — no duplicate accounts are ever created.
- **Classroom + membership.** A duplicate-name classroom create returns 409; the script then looks
  the existing classroom up by name. A learner who already holds this classroom's one allowed
  APPROVED membership (`uq_classroom_memberships_one_approved_per_learner`) skips the whole
  invite/request/approve sequence entirely — attempting it again would 409. A learner mid-flight
  (a PENDING request from an earlier partial run) skips straight to approval instead of minting a
  second invite.
- **Invites are always freshly minted when needed**, never reused: the plaintext join code is
  returned exactly once per idempotency key, and invites expire after 24h, so from day two onward
  minting a fresh invite is the normal path, not a fallback.
- **Stale sessions.** `b_sessions` enforces one active session per learner. If a developer killed
  the app mid-question, the previous run's session is still `active`; this script detects and
  abandons it before proceeding, unless `--keep-session` is passed.
- **Self-verification.** After onboarding, the script starts a session and requests one
  opportunity, asserting `201`. A `409` here means BE-G1's fix (assigning `Learner.grade` on
  membership approval) is missing from the running image; a `401` means the backend's Supabase
  JWT configuration doesn't match this token. The self-verify session is abandoned afterward
  unless `--keep-session` is passed.

## Honest limitations

**`source_class`.** Because this script goes through HTTP rather than direct database writes, the
rows it creates carry whatever `source_class` the production routes write (`REAL`, not `TEST`) —
there is no way for an HTTP client to stamp them otherwise. The only mitigation is naming: the
reserved `example.com` email domain and the `FIXTURE` name prefixes on the classroom/teacher/
learner records. The operational rule that makes this acceptable: this script only ever runs
against a local development database, never a pilot or production database.

**Running the full backend test suite wipes this fixture's data — this is expected, re-run the
script afterward.** `docker compose exec api pytest -q` and the running API share one Postgres
database (there is no separate test database). Several tests exercise migration reversibility by
downgrading all the way to the base revision and back up — `test_be2_persistence.py` in
particular downgrades to `20260722_0001`, which drops every table any later migration created
(`app_users`, `b_learners`, `classrooms`, `classroom_memberships`, everything), then
`alembic upgrade head` recreates them empty. That means every full-suite run silently erases this
fixture's teacher/learner profiles, classroom, and membership — not a bug in this script, just a
consequence of tests and the dev API sharing one database. This script is fully idempotent, so
the fix is simply: re-run it after running the full suite, and it recreates whatever was lost.

**Runtime-bundle "most recent" tie-break.** Separately, `POST /api/v1/b/sessions` pins to
whichever `PUBLISHED`+`APPROVED` `RuntimeBundleRecord` was created most recently
(`RuntimeBundleRecordRepository.find_current_approved_published`), and opportunity selection can
currently only actually serve from one specific TEST-provenance DRAFT fixture bundle version
(`be3b-test-fixture-1.0`, see `app/application/opportunity_selection.py`'s module docstring — this
is a documented, pre-existing engineering-only bridge, not something this script can or should
fix). Backend tests insert their own throwaway `RuntimeBundleRecord` rows with later timestamps as
a side effect, which can shadow `be3b-test-fixture-1.0` and make self-verify (and the app itself)
409 on opportunity selection for a reason that looks identical to BE-G1 regressing, but isn't.
There is no API route to publish or approve a bundle (out of scope for this batch), so if this
happens, an operator has to restore `be3b-test-fixture-1.0` as the most-recently-created
`PUBLISHED`+`APPROVED` bundle directly in the dev database — this script deliberately cannot do
that itself, since it is HTTP-only by design.
