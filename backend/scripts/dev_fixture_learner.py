#!/usr/bin/env python3
"""BE-G2 — re-runnable dev fixture: a Grade-2 learner with an APPROVED classroom membership.

DELETE THIS SCRIPT (and backend/scripts/) WHEN FE-1b (teacher classroom + approval UI) LANDS.
It exists solely because there is currently no in-app way to perform the teacher half of learner
onboarding, and the learner-side screens still need to be built and tested against the real
backend one at a time.

HTTP-DRIVEN, ZERO DIRECT DATABASE WRITES. This module must never import a SQL toolkit or Postgres
driver, read the backend's database connection string, or open a database connection of any
kind — every state change here goes through the real FastAPI routes, which is what gets
ProvenanceMixin, the check constraints, and the one-approved-membership-per-learner index
satisfied for free instead of hand-reimplemented in a file nobody reviews. (See
backend/tests/test_dev_fixture_isolation.py, which asserts this module's source never names any
of those things.)

AUTH: real Supabase auth, using only the ordinary PUBLISHABLE key — never an elevated admin
credential. Signups are enabled and email confirmation is off on this project, so
``POST /auth/v1/signup`` with that publishable key (the same one the Expo app ships with — not a
secret) returns a session immediately; on a re-run it fails with "already registered" and this
script falls back to a password-grant sign-in instead. That fallback is what makes the whole
script idempotent across runs.

Run with ``--test-fixture-only`` (required) from ``backend/``:
    python scripts/dev_fixture_learner.py --test-fixture-only

See scripts/README.md for the fixture credentials and the re-run/reset behavior.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import NoReturn

import httpx


TEACHER_EMAIL = "dev-fixture-teacher@example.com"
LEARNER_EMAIL = "dev-fixture-learner@example.com"
FIXTURE_PASSWORD = "Fixture-Dev-Pass-2026!"
TEACHER_NAME = "FIXTURE Teacher"
LEARNER_NAME = "FIXTURE Learner G2"
CLASSROOM_NAME = "FIXTURE Grade 2"
CLASSROOM_GRADE = "GRADE_2"

DEFAULT_API_BASE = "http://localhost:8000"

# backend/scripts/dev_fixture_learner.py -> backend/ -> repo root
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
BACKEND_ENV_PATH = BACKEND_DIR / ".env"
FRONTEND_ENV_LOCAL_PATH = REPO_ROOT / "frontend" / ".env.local"


def fatal(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def fresh_key() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Config resolution: environment first, then the relevant .env file directly
# (neither backend/.env nor frontend/.env.local is loaded automatically when
# this script runs from a plain host shell, so both are read as a fallback).
# ---------------------------------------------------------------------------


def _read_dotenv_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def resolve_config_value(env_name: str, *, dotenv_path: Path) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value
    return _read_dotenv_value(dotenv_path, env_name)


# ---------------------------------------------------------------------------
# Supabase auth: signup-or-sign-in, ordinary publishable key only
# ---------------------------------------------------------------------------


def signup_or_sign_in(
    client: httpx.Client, supabase_url: str, publishable_key: str, *, email: str, password: str
) -> str:
    """Returns an access token, never logged. Tries signup first (fresh identity); falls back to
    a password-grant sign-in when the identity already exists — the mechanism that makes this
    script idempotent across runs."""
    headers = {"apikey": publishable_key, "Content-Type": "application/json"}
    signup = client.post(f"{supabase_url}/auth/v1/signup", headers=headers, json={"email": email, "password": password})
    if signup.status_code in (200, 201):
        token = signup.json().get("access_token")
        if token:
            return token
        # Signup succeeded but returned no session (e.g. if confirmation were ever turned back
        # on) — fall through to a password-grant sign-in below.
    elif signup.status_code not in (400, 401, 409, 422):
        fatal(f"Unexpected status signing up {email} via Supabase: HTTP {signup.status_code}: {signup.text}")

    token_response = client.post(
        f"{supabase_url}/auth/v1/token",
        headers=headers,
        params={"grant_type": "password"},
        json={"email": email, "password": password},
    )
    if token_response.status_code != 200:
        fatal(
            f"Could not sign in as {email}: signup returned HTTP {signup.status_code} and the "
            f"password-grant fallback then returned HTTP {token_response.status_code}: "
            f"{token_response.text}"
        )
    token = token_response.json().get("access_token")
    if not token:
        fatal(f"Password-grant sign-in for {email} returned no access_token.")
    return token


# ---------------------------------------------------------------------------
# Backend API driver
# ---------------------------------------------------------------------------


class ApiSession:
    """Thin wrapper binding one principal's bearer token to the real backend routes. Every
    state-changing call site supplies its own fresh Idempotency-Key explicitly — there is no
    shared/reused key anywhere in this script."""

    def __init__(self, client: httpx.Client, base_url: str, token: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self, *, idempotency_key: str | None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}", "X-Request-ID": fresh_key()}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def get(self, path: str, *, params: dict[str, object] | None = None) -> httpx.Response:
        return self._client.get(f"{self._base_url}{path}", headers=self._headers(idempotency_key=None), params=params)

    def post(
        self, path: str, json_body: dict[str, object] | None = None, *, idempotency_key: str | None = None
    ) -> httpx.Response:
        return self._client.post(
            f"{self._base_url}{path}", headers=self._headers(idempotency_key=idempotency_key), json=json_body
        )


# ---------------------------------------------------------------------------
# Onboarding chain (teacher side)
# ---------------------------------------------------------------------------


def ensure_teacher_profile(teacher_api: ApiSession) -> None:
    response = teacher_api.post("/api/v1/teacher/profile", {"name": TEACHER_NAME}, idempotency_key=fresh_key())
    if response.status_code in (201, 409):
        return
    fatal(f"Unexpected status creating teacher profile: HTTP {response.status_code}: {response.text}")


def ensure_classroom(teacher_api: ApiSession) -> uuid.UUID:
    response = teacher_api.post(
        "/api/v1/classrooms", {"name": CLASSROOM_NAME, "grade": CLASSROOM_GRADE}, idempotency_key=fresh_key()
    )
    if response.status_code == 201:
        return uuid.UUID(response.json()["classroom_id"])
    if response.status_code == 409:
        listed = teacher_api.get("/api/v1/classrooms")
        if listed.status_code != 200:
            fatal(f"Could not list classrooms while resolving the existing {CLASSROOM_NAME!r} classroom: HTTP {listed.status_code}: {listed.text}")
        for item in listed.json()["classrooms"]:
            if item["name"] == CLASSROOM_NAME:
                return uuid.UUID(item["classroom_id"])
        fatal(f"Classroom creation returned 409 (duplicate name) but no classroom named {CLASSROOM_NAME!r} was found in the teacher's own list.")
    fatal(f"Unexpected status creating classroom: HTTP {response.status_code}: {response.text}")


def create_fresh_invite(teacher_api: ApiSession, classroom_id: uuid.UUID) -> str:
    """A fresh Idempotency-Key always mints a brand-new invite and returns its plaintext exactly
    once (see classroom_membership.py's create_invite docstring) — from day two onward, minting a
    fresh invite here is the normal path, not a fallback, since invites expire after 24h."""
    response = teacher_api.post(f"/api/v1/classrooms/{classroom_id}/invites", {}, idempotency_key=fresh_key())
    if response.status_code != 201:
        fatal(f"Unexpected status creating classroom invite: HTTP {response.status_code}: {response.text}")
    token = response.json()["invite_token"]
    if not token:
        fatal("Classroom invite creation returned no plaintext invite_token even with a fresh Idempotency-Key.")
    return token


def find_membership_via_teacher(teacher_api: ApiSession, classroom_id: uuid.UUID, learner_id: uuid.UUID) -> dict | None:
    response = teacher_api.get(f"/api/v1/classrooms/{classroom_id}/membership-requests")
    if response.status_code != 200:
        fatal(f"Could not list membership requests for classroom {classroom_id}: HTTP {response.status_code}: {response.text}")
    for item in response.json()["requests"]:
        if item["learner_id"] == str(learner_id):
            return item
    return None


def list_pending_via_teacher(teacher_api: ApiSession, classroom_id: uuid.UUID) -> list[dict]:
    response = teacher_api.get(f"/api/v1/classrooms/{classroom_id}/membership-requests")
    if response.status_code != 200:
        fatal(f"Could not list membership requests for classroom {classroom_id}: HTTP {response.status_code}: {response.text}")
    return [item for item in response.json()["requests"] if item["state"] == "PENDING"]


def approve_all_pending(teacher_api: ApiSession, classroom_id: uuid.UUID) -> list[dict]:
    """Approves every PENDING request in the classroom via the same POST .../approve route a
    teacher already has authority to call — used standalone here so a separate real account
    (joined by hand through the app, not this script's own fixture learner) can be approved
    without needing a teacher UI (FE-1b). Returns the approved requests."""
    pending = list_pending_via_teacher(teacher_api, classroom_id)
    approved: list[dict] = []
    for item in pending:
        response = teacher_api.post(
            f"/api/v1/classroom-memberships/{item['classroom_membership_id']}/approve", {}, idempotency_key=fresh_key()
        )
        if response.status_code != 200:
            fatal(
                f"Could not approve membership {item['classroom_membership_id']} for learner "
                f"{item['learner_id']}: HTTP {response.status_code}: {response.text}"
            )
        approved.append(item)
    return approved


# ---------------------------------------------------------------------------
# Onboarding chain (learner side)
# ---------------------------------------------------------------------------


def ensure_learner_profile(learner_api: ApiSession) -> uuid.UUID:
    response = learner_api.post("/api/v1/learner/profile", {"name": LEARNER_NAME}, idempotency_key=fresh_key())
    if response.status_code == 201:
        return uuid.UUID(response.json()["learner_id"])
    if response.status_code == 409:
        existing = learner_api.get("/api/v1/learner/profile")
        if existing.status_code != 200:
            fatal(f"Learner profile already exists but could not be fetched: HTTP {existing.status_code}: {existing.text}")
        return uuid.UUID(existing.json()["learner_id"])
    fatal(f"Unexpected status creating learner profile: HTTP {response.status_code}: {response.text}")


def find_learner_membership(learner_api: ApiSession, classroom_id: uuid.UUID) -> dict | None:
    response = learner_api.get("/api/v1/learner/classrooms")
    if response.status_code != 200:
        fatal(f"Could not list the learner's classroom memberships: HTTP {response.status_code}: {response.text}")
    for item in response.json()["memberships"]:
        if item["classroom_id"] == str(classroom_id):
            return item
    return None


def resolve_invite(learner_api: ApiSession, invite_token: str) -> None:
    response = learner_api.post("/api/v1/classroom-invites/resolve", {"invite_token": invite_token}, idempotency_key=fresh_key())
    if response.status_code != 200:
        fatal(f"Unexpected status resolving invite token: HTTP {response.status_code}: {response.text}")


def request_membership(learner_api: ApiSession, invite_token: str) -> None:
    response = learner_api.post(
        "/api/v1/classroom-memberships/requests", {"invite_token": invite_token}, idempotency_key=fresh_key()
    )
    if response.status_code != 201:
        fatal(f"Unexpected status requesting classroom membership: HTTP {response.status_code}: {response.text}")


# ---------------------------------------------------------------------------
# Membership orchestration — tolerates every already-exists / already-approved state
# ---------------------------------------------------------------------------


def ensure_membership_approved(
    teacher_api: ApiSession, learner_api: ApiSession, classroom_id: uuid.UUID, learner_id: uuid.UUID
) -> str | None:
    """Returns the plaintext invite token if a fresh one was minted this run, else None (steady
    state: the learner already has this classroom's one-allowed APPROVED membership)."""
    existing = find_learner_membership(learner_api, classroom_id)
    if existing is not None and existing["state"] == "APPROVED":
        print("Classroom membership already APPROVED; skipping invite/request/approve.")
        return None
    if existing is not None and existing["state"] == "REJECTED":
        fatal(
            "The fixture learner's membership in this classroom is REJECTED and there is no "
            "endpoint to re-request after rejection. Reset the fixture's classroom_memberships "
            "row (or point this script at a fresh dev database) and re-run."
        )

    invite_token: str | None = None
    if existing is None:
        invite_token = create_fresh_invite(teacher_api, classroom_id)
        resolve_invite(learner_api, invite_token)
        request_membership(learner_api, invite_token)
        print("Requested classroom membership.")
    else:
        print("Classroom membership already PENDING; skipping invite/request, approving directly.")

    membership = find_membership_via_teacher(teacher_api, classroom_id, learner_id)
    if membership is None:
        fatal("The membership request could not be found via the teacher's membership-requests listing.")
    if membership["state"] == "APPROVED":
        return invite_token

    approve_response = teacher_api.post(
        f"/api/v1/classroom-memberships/{membership['classroom_membership_id']}/approve", {}, idempotency_key=fresh_key()
    )
    if approve_response.status_code == 200:
        print("Approved classroom membership.")
        return invite_token
    if approve_response.status_code == 409:
        # Tolerate a concurrent/prior approval rather than trusting the error at face value.
        recheck = find_membership_via_teacher(teacher_api, classroom_id, learner_id)
        if recheck is not None and recheck["state"] == "APPROVED":
            print("Classroom membership was already approved.")
            return invite_token
        fatal(f"Membership approval conflicted (HTTP 409) and the membership is still not APPROVED: {approve_response.text}")
    fatal(f"Unexpected status approving membership: HTTP {approve_response.status_code}: {approve_response.text}")


# ---------------------------------------------------------------------------
# Session reset + self-verify
# ---------------------------------------------------------------------------


def reset_stale_session(learner_api: ApiSession, *, keep_session: bool) -> None:
    if keep_session:
        print("Skipping stale-session reset (--keep-session).")
        return
    response = learner_api.get("/api/v1/b/sessions/active")
    if response.status_code != 200:
        fatal(f"Could not check for an active session: HTTP {response.status_code}: {response.text}")
    session = response.json()["session"]
    if session is None:
        return
    abandon = learner_api.post(f"/api/v1/b/sessions/{session['session_id']}/abandon", idempotency_key=fresh_key())
    if abandon.status_code != 200:
        fatal(f"Could not abandon stale active session {session['session_id']}: HTTP {abandon.status_code}: {abandon.text}")
    print(f"Abandoned stale active session {session['session_id']}.")


def self_verify(learner_api: ApiSession, *, keep_session: bool) -> None:
    start = learner_api.post("/api/v1/b/sessions", idempotency_key=fresh_key())
    if start.status_code == 401:
        fatal(
            "Session start returned HTTP 401. Check backend/.env's Supabase JWT settings "
            "(SUPABASE_URL / SUPABASE_JWT_ISSUER / SUPABASE_JWT_AUDIENCE / SUPABASE_JWKS_URL) "
            "against the running container."
        )
    if start.status_code != 201:
        fatal(f"Unexpected status starting a session: HTTP {start.status_code}: {start.text}")
    session_id = start.json()["session_id"]

    opportunity = learner_api.post(f"/api/v1/b/sessions/{session_id}/opportunities")
    if opportunity.status_code == 409:
        fatal(
            "POST .../opportunities returned HTTP 409. The backend returns this identically for "
            "two different causes (by design, to avoid leaking which safeguard fired), so check "
            "both: (1) BE-G1 regressed — Learner.grade is NULL after approval; confirm "
            "app/application/classroom_membership.py's approve_membership still assigns it. "
            "(2) The 'most recently created' PUBLISHED+APPROVED runtime bundle in this database "
            "is not the one bundle version opportunity_selection.py can actually serve "
            "(be3b-test-fixture-1.0) — this happens routinely after running the full backend "
            "test suite, which inserts its own newer throwaway bundle rows. See "
            "scripts/README.md's 'Honest limitations' section for both."
        )
    if opportunity.status_code == 401:
        fatal("Opportunity selection returned HTTP 401. Check backend/.env's Supabase JWT settings.")
    if opportunity.status_code != 201:
        fatal(f"Unexpected status selecting an opportunity: HTTP {opportunity.status_code}: {opportunity.text}")
    print(f"Self-verify OK: session {session_id} served opportunity {opportunity.json()['item_opportunity_id']}.")

    if keep_session:
        print("Leaving the self-verify session active (--keep-session).")
        return
    abandon = learner_api.post(f"/api/v1/b/sessions/{session_id}/abandon", idempotency_key=fresh_key())
    if abandon.status_code != 200:
        fatal(f"Could not abandon the self-verify session {session_id}: HTTP {abandon.status_code}: {abandon.text}")


# ---------------------------------------------------------------------------
# Safety rails + CLI
# ---------------------------------------------------------------------------


def check_safety_rails(args: argparse.Namespace) -> None:
    app_env = resolve_config_value("APP_ENV", dotenv_path=BACKEND_ENV_PATH) or "development"
    if app_env == "production":
        fatal("Refusing to run: APP_ENV=production. This script creates real test data and must never run against production.")
    if not args.test_fixture_only:
        fatal("Refusing to run without --test-fixture-only. Pass it to confirm you understand this creates real test data via the live backend API.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-runnable dev fixture: a Grade-2 learner with an approved classroom, driven "
            "entirely through the real backend API and real Supabase auth. See "
            "scripts/README.md for details; delete this script when FE-1b lands."
        )
    )
    parser.add_argument(
        "--test-fixture-only",
        action="store_true",
        help="Required. Confirms you understand this creates real test data via the live API.",
    )
    parser.add_argument(
        "--mint-invite-only",
        action="store_true",
        help="Mint and print one fresh join code for the FIXTURE classroom, then exit — skips "
        "the fixture learner's own profile/membership/self-verify steps entirely. For handing a "
        "working code to a SEPARATE real account (e.g. your own) to join by hand through the "
        "app's normal onboarding UI. Signs in as the same fixture teacher and calls the same "
        "POST /classrooms/{id}/invites route the teacher already legitimately has authority "
        "over — this does not add any new capability, just exposes the existing one standalone "
        "instead of only as a side effect of approving the fixture's own learner.",
    )
    parser.add_argument(
        "--approve-pending",
        action="store_true",
        help="Approve every PENDING membership request in the FIXTURE classroom, then exit — "
        "for approving a SEPARATE real account that joined by hand through the app's own "
        "join-code screen (e.g. after using --mint-invite-only's code). Signs in as the same "
        "fixture teacher and calls the same POST .../approve route the teacher already has "
        "authority over for this classroom.",
    )
    parser.add_argument(
        "--keep-session",
        action="store_true",
        help="Skip both the stale-session reset and the self-verify session's final abandon, "
        "so an in-progress session survives the run.",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("DEV_FIXTURE_API_BASE", DEFAULT_API_BASE),
        help=f"Base URL of the running backend API (default: {DEFAULT_API_BASE}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check_safety_rails(args)

    supabase_url = resolve_config_value("SUPABASE_URL", dotenv_path=BACKEND_ENV_PATH)
    if not supabase_url:
        fatal(f"SUPABASE_URL not found in the environment or in {BACKEND_ENV_PATH}.")
    publishable_key = resolve_config_value("EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY", dotenv_path=FRONTEND_ENV_LOCAL_PATH)
    if not publishable_key:
        fatal(f"EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY not found in the environment or in {FRONTEND_ENV_LOCAL_PATH}.")

    with httpx.Client(timeout=30.0) as client:
        print(f"Signing in as {TEACHER_EMAIL} ...")
        teacher_token = signup_or_sign_in(client, supabase_url, publishable_key, email=TEACHER_EMAIL, password=FIXTURE_PASSWORD)
        teacher_api = ApiSession(client, args.api_base, teacher_token)

        if args.mint_invite_only:
            ensure_teacher_profile(teacher_api)
            classroom_id = ensure_classroom(teacher_api)
            invite_token = create_fresh_invite(teacher_api, classroom_id)
            print()
            print("=" * 72)
            print(f"Fresh join code for {CLASSROOM_NAME} ({CLASSROOM_GRADE}):")
            print(f"  {invite_token}")
            print("Valid for 24h. Use this in the app's own join-code screen with any separate")
            print("account - it is not tied to the fixture learner.")
            print("=" * 72)
            return 0

        if args.approve_pending:
            ensure_teacher_profile(teacher_api)
            classroom_id = ensure_classroom(teacher_api)
            approved = approve_all_pending(teacher_api, classroom_id)
            print()
            print("=" * 72)
            if not approved:
                print(f"No PENDING membership requests found in {CLASSROOM_NAME}.")
            else:
                print(f"Approved {len(approved)} membership request(s) in {CLASSROOM_NAME}:")
                for item in approved:
                    print(f"  learner_id={item['learner_id']}")
            print("=" * 72)
            return 0

        print(f"Signing in as {LEARNER_EMAIL} ...")
        learner_token = signup_or_sign_in(client, supabase_url, publishable_key, email=LEARNER_EMAIL, password=FIXTURE_PASSWORD)
        learner_api = ApiSession(client, args.api_base, learner_token)

        ensure_teacher_profile(teacher_api)
        learner_id = ensure_learner_profile(learner_api)
        classroom_id = ensure_classroom(teacher_api)
        invite_token = ensure_membership_approved(teacher_api, learner_api, classroom_id, learner_id)

        reset_stale_session(learner_api, keep_session=args.keep_session)
        self_verify(learner_api, keep_session=args.keep_session)

    print()
    print("=" * 72)
    print("Dev fixture ready.")
    print(f"  Learner email:    {LEARNER_EMAIL}")
    print(f"  Learner password: {FIXTURE_PASSWORD}")
    print(f"  Classroom:        {CLASSROOM_NAME} ({CLASSROOM_GRADE})")
    if invite_token:
        print(f"  Join code:        {invite_token}")
    else:
        print("  Join code:        (not minted this run — membership already approved)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
