"""Component D's six student-side routes (Component D authorization, D-011; API contract v4).

Covers the acceptance list plan v5 sets for Phase 2: the learner check (403/404), idempotency
including two simultaneous submits, a foreign ``session_id`` as a 404, ``latest`` with no data,
and the language of the recommendation. The guard entries themselves are asserted in
``test_d1_component_d_tables.py``, where the rest of the authorization's claims live.

Auth is overridden the way every other route test in this suite overrides it
(``test_b_session_lifecycle``'s ``client_for``): the dependency is replaced, so these tests
exercise the ROUTES and the learner resolution, not Supabase token verification, which
``test_auth.py`` owns.
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient

from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.main import app


SINHALA_RANGE = range(0x0D80, 0x0E00)


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def client_for(subject: str) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    client = TestClient(app)
    client.__enter__()
    return client


def multi_principal_client() -> TestClient:
    def resolve_principal(request: Request) -> AuthenticatedPrincipal:
        subject = request.headers.get("X-Test-Subject", "unresolved-test-subject")
        return AuthenticatedPrincipal(user_id=subject, email="verified@example.test")

    app.dependency_overrides[get_authenticated_principal] = resolve_principal
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def rules_only(monkeypatch) -> None:
    """Pin the RULE-BASED profile. The trained model is tried first (d_model_profile) and these
    tests assert the rules' own outputs, which stay the fallback; the model has its own tests in
    test_d4_model_profile.py."""
    monkeypatch.setattr("app.application.d_cognitive_profiling.predict_levels", lambda events: None)


def headers(subject: str | None = None, idempotency_key: str | None = None) -> dict[str, str]:
    """Component D's own six routes take NO ``Idempotency-Key`` -- the ``session_id`` in the path
    is the natural key, the way Component C decided it. The parameter exists only for the host's
    ``/api/v1/learner/profile`` and ``/api/v1/teacher/profile`` setup calls below, which do
    require the header."""
    result = {
        "X-Request-ID": f"req-{uuid4()}",
        "Authorization": "Bearer component-d-test-token-that-must-not-be-logged",
    }
    if subject is not None:
        result["X-Test-Subject"] = subject
    if idempotency_key is not None:
        result["Idempotency-Key"] = idempotency_key
    return result


def setup_learner(subject: str, name: str = "D Learner") -> None:
    client = client_for(subject)
    try:
        response = client.post(
            "/api/v1/learner/profile", json={"name": name}, headers=headers(idempotency_key=str(uuid4()))
        )
        assert response.status_code == 201, response.text
    finally:
        close_client(client)


def setup_teacher(subject: str, name: str = "D Teacher") -> None:
    client = client_for(subject)
    try:
        response = client.post(
            "/api/v1/teacher/profile", json={"name": name}, headers=headers(idempotency_key=str(uuid4()))
        )
        assert response.status_code == 201, response.text
    finally:
        close_client(client)


def event(
    index: int,
    *,
    matched: bool = True,
    attempts: int = 1,
    assist: bool = False,
    clicks: int = 1,
    response_time_sec: float = 3.0,
) -> dict:
    return {
        "question_id": f"q{index}",
        "topic": ["Counting", "Addition", "Subtraction", "Division"][index % 4],
        "difficulty": ["Easy", "Medium", "Hard"][index % 3],
        "response_time_sec": response_time_sec,
        "attempts": attempts,
        "response_matched": matched,
        "assist_used": assist,
        "click_count": clicks,
        "session_time_sec": 30.0,
        "time_between_actions": 1.25,
        "error_type": "none" if matched else "calculation",
    }


def body(count: int = 10, language: str = "en", **kwargs) -> dict:
    return {"language": language, "events": [event(i, **kwargs) for i in range(count)]}


# ---------------------------------------------------------------- the learner check


def test_a_teacher_is_forbidden_and_an_unknown_subject_is_not_found() -> None:
    """403 vs 404 is a distinction the contract makes on every row, so it is asserted on a read
    and a write rather than once: a teacher authenticated fine and simply is not a learner (403),
    while a subject with no account may be mid-onboarding and gets 404, which asserts nothing
    about an account that may not exist."""
    upgrade()
    teacher_subject = f"d-teacher-{uuid4()}"
    setup_teacher(teacher_subject)

    client = client_for(teacher_subject)
    try:
        assert client.get("/api/v1/d/learner/state", headers=headers()).status_code == 403
        assert client.post(
            "/api/v1/d/learner/state", json={"language": "si"}, headers=headers()
        ).status_code == 403
        assert client.get("/api/v1/d/learner/profiles/latest", headers=headers()).status_code == 403
    finally:
        close_client(client)

    client = client_for(f"d-nobody-{uuid4()}")
    try:
        assert client.get("/api/v1/d/learner/state", headers=headers()).status_code == 404
        assert client.get("/api/v1/d/learner/profiles", headers=headers()).status_code == 404
    finally:
        close_client(client)


# ---------------------------------------------------------------- learner state


def test_reading_state_for_a_learner_with_no_row_returns_the_default_and_creates_nothing() -> None:
    """The gate route calls this on every entry to the tab. A read that created rows would
    manufacture a row for every learner who ever opened it, with a language they never chose."""
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        first = client.get("/api/v1/d/learner/state", headers=headers())
        assert first.status_code == 200, first.text
        assert first.json()["intro_completed"] is False
        assert first.json()["language"] == "en"
        assert "request_id" in first.json()

        # Read again, then prove the first read did not persist anything: a POST of `si` must
        # still be the row's creation, so the language that lands is `si`, never `en`.
        client.get("/api/v1/d/learner/state", headers=headers())
        created = client.post("/api/v1/d/learner/state", json={"language": "si"}, headers=headers())
        assert created.status_code == 200, created.text
        assert created.json()["language"] == "si"
        assert client.get("/api/v1/d/learner/state", headers=headers()).json()["language"] == "si"
    finally:
        close_client(client)


def test_state_upsert_sets_the_intro_once_and_refuses_an_empty_or_false_body() -> None:
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        assert client.post("/api/v1/d/learner/state", json={}, headers=headers()).status_code == 422
        # The intro is a one-way door: `false` is refused so a client cannot reset the first-run
        # flow for a child who has already been through it.
        assert client.post(
            "/api/v1/d/learner/state", json={"intro_completed": False}, headers=headers()
        ).status_code == 422
        assert client.post(
            "/api/v1/d/learner/state", json={"language": "fr"}, headers=headers()
        ).status_code == 422

        done = client.post(
            "/api/v1/d/learner/state", json={"intro_completed": True}, headers=headers()
        )
        assert done.status_code == 200, done.text
        assert done.json() == {
            "intro_completed": True,
            "language": "en",
            "request_id": done.json()["request_id"],
        }

        # A repeat must not look like a new event, and must not lose the language.
        again = client.post(
            "/api/v1/d/learner/state", json={"intro_completed": True, "language": "si"}, headers=headers()
        )
        assert again.status_code == 200
        assert again.json()["intro_completed"] is True
        assert again.json()["language"] == "si"
    finally:
        close_client(client)


# ---------------------------------------------------------------- the profile write


def test_a_profile_is_stored_and_read_back_with_every_contract_field() -> None:
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    session_id = str(uuid4())

    client = client_for(subject)
    try:
        created = client.post(
            f"/api/v1/d/sessions/{session_id}/profile", json=body(), headers=headers()
        )
        assert created.status_code == 200, created.text
        profile = created.json()["profile"]

        assert profile["session_id"] == session_id
        assert profile["memory_level"] in {"low", "medium", "high"}
        assert profile["attention_level"] in {"low", "medium", "high"}
        assert profile["number_sense_level"] in {"low", "medium", "high"}
        assert profile["processing_speed_level"] in {"Slow", "Moderate", "Fast"}
        assert 0.0 <= profile["confidence_score"] <= 1.0
        # The owner's trained model is what produces profiles now (d_model_profile).
        assert profile["model_version"] == "mathsmate-rf-from-scratch-v1"
        assert profile["recommendation"]
        assert set(profile["features"]) == {
            "accuracy", "avg_response_time_ms", "response_time_std_ms", "avg_attempts",
            "retry_rate", "hint_rate", "mean_clicks_per_question", "total_questions",
        }
        assert profile["features"]["total_questions"] == 10
        assert profile["features"]["accuracy"] == 1.0

        fetched = client.get(f"/api/v1/d/sessions/{session_id}/profile", headers=headers())
        assert fetched.status_code == 200
        assert fetched.json()["profile"]["session_id"] == session_id

        latest = client.get("/api/v1/d/learner/profiles/latest", headers=headers())
        assert latest.status_code == 200
        assert latest.json()["profile"]["session_id"] == session_id

        history = client.get("/api/v1/d/learner/profiles", headers=headers())
        assert history.status_code == 200
        assert [item["session_id"] for item in history.json()["items"]] == [session_id]
    finally:
        close_client(client)


def test_an_identical_resubmit_returns_the_stored_profile_and_a_changed_one_conflicts() -> None:
    """The stored profile, not a recomputation: if the heuristic is ever recalibrated, a retried
    request must not come back with different levels than the first attempt did."""
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    session_id = str(uuid4())
    payload = body()

    client = client_for(subject)
    try:
        first = client.post(
            f"/api/v1/d/sessions/{session_id}/profile", json=payload, headers=headers()
        )
        assert first.status_code == 200, first.text

        repeat = client.post(
            f"/api/v1/d/sessions/{session_id}/profile", json=payload, headers=headers()
        )
        assert repeat.status_code == 200
        for field in ("memory_level", "attention_level", "number_sense_level",
                      "processing_speed_level", "confidence_score", "generated_at", "features"):
            assert repeat.json()["profile"][field] == first.json()["profile"][field], field

        # One event's timings changed: a different run claiming an id that is taken.
        altered = body()
        altered["events"][3]["response_time_sec"] = 99.0
        conflict = client.post(
            f"/api/v1/d/sessions/{session_id}/profile", json=altered, headers=headers()
        )
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["error"]["code"] == "CONFLICT"

        # The stored profile is unchanged by the refused write.
        assert (
            client.get(f"/api/v1/d/sessions/{session_id}/profile", headers=headers()).json()["profile"]
            == first.json()["profile"]
        )
    finally:
        close_client(client)


def test_two_simultaneous_submits_for_one_session_store_exactly_one_profile() -> None:
    """A real race on two connections, not a sequential stand-in: both threads are held at a
    barrier and released together, so they contend for the advisory lock. Either both succeed
    (the second finding the first's identical row) or one conflicts -- what must never happen is
    two profiles for one run, which the global UNIQUE on session_id also refuses."""
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    session_id = str(uuid4())
    payload = body()

    client = multi_principal_client()
    barrier = Barrier(2)

    def submit() -> int:
        barrier.wait(timeout=30)
        return client.post(
            f"/api/v1/d/sessions/{session_id}/profile",
            json=payload,
            headers=headers(subject=subject),
        ).status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(future.result() for future in [pool.submit(submit), pool.submit(submit)])
        assert statuses in ([200, 200], [200, 409]), statuses

        history = client.get("/api/v1/d/learner/profiles", headers=headers(subject=subject))
        assert len(history.json()["items"]) == 1, history.json()
    finally:
        close_client(client)


def test_another_learners_session_is_not_found_rather_than_forbidden() -> None:
    """404, not 403: a 403 would confirm the session exists and belongs to somebody, which is a
    fact about another child. Asserted on the read AND the write -- the write is the easier one to
    get wrong, because the row is found before ownership is checked."""
    upgrade()
    owner_subject = f"d-owner-{uuid4()}"
    other_subject = f"d-other-{uuid4()}"
    setup_learner(owner_subject)
    setup_learner(other_subject)
    session_id = str(uuid4())

    client = multi_principal_client()
    try:
        created = client.post(
            f"/api/v1/d/sessions/{session_id}/profile",
            json=body(),
            headers=headers(subject=owner_subject),
        )
        assert created.status_code == 200, created.text

        read = client.get(
            f"/api/v1/d/sessions/{session_id}/profile", headers=headers(subject=other_subject)
        )
        assert read.status_code == 404
        assert read.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

        write = client.post(
            f"/api/v1/d/sessions/{session_id}/profile",
            json=body(),
            headers=headers(subject=other_subject),
        )
        assert write.status_code == 404, write.text

        # The other learner sees no profile at all, and the owner's is untouched.
        assert client.get(
            "/api/v1/d/learner/profiles/latest", headers=headers(subject=other_subject)
        ).json()["profile"] is None
        assert client.get(
            "/api/v1/d/learner/profiles", headers=headers(subject=owner_subject)
        ).json()["items"][0]["session_id"] == session_id
    finally:
        close_client(client)


# ---------------------------------------------------------------- body validation


def test_the_request_body_is_validated_at_its_documented_bounds() -> None:
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        def post(payload: dict) -> int:
            return client.post(
                f"/api/v1/d/sessions/{uuid4()}/profile", json=payload, headers=headers()
            ).status_code

        assert post({"language": "en", "events": []}) == 422
        assert post(body(51)) == 422

        # A duplicate question id is the client's own defect, so it is a 422 naming the field --
        # not the 409 the UNIQUE constraint alone would have produced, which would send the client
        # into reconciliation for a body it could have fixed.
        duplicated = body(3)
        duplicated["events"][2]["question_id"] = duplicated["events"][0]["question_id"]
        assert post(duplicated) == 422

        negative = body(1)
        negative["events"][0]["response_time_sec"] = -1.0
        assert post(negative) == 422

        zero_attempts = body(1)
        zero_attempts["events"][0]["attempts"] = 0
        assert post(zero_attempts) == 422

        bad_topic = body(1)
        bad_topic["events"][0]["topic"] = "Algebra"
        assert post(bad_topic) == 422

        extra = body(1)
        extra["events"][0]["given_answer"] = "7"
        assert post(extra) == 422, "StrictModel must refuse a field the contract removed"
    finally:
        close_client(client)


def test_history_limit_is_bounded_and_defaults_without_being_clamped() -> None:
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        assert client.get("/api/v1/d/learner/profiles?limit=0", headers=headers()).status_code == 422
        assert client.get("/api/v1/d/learner/profiles?limit=101", headers=headers()).status_code == 422
        assert client.get("/api/v1/d/learner/profiles?limit=1", headers=headers()).status_code == 200
        assert client.get("/api/v1/d/learner/profiles?limit=100", headers=headers()).status_code == 200
        assert client.get(
            "/api/v1/d/learner/profiles?language=de", headers=headers()
        ).status_code == 422, "an unrecognised language is a 422, never a silent fallback"
    finally:
        close_client(client)


# ---------------------------------------------------------------- empty state and language


def test_latest_with_no_data_is_a_null_profile_and_not_a_404() -> None:
    """A learner who has never done a profiling run is in a normal state. The home screen's empty
    state is a render of this response, not of an error."""
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        latest = client.get("/api/v1/d/learner/profiles/latest", headers=headers())
        assert latest.status_code == 200
        assert latest.json()["profile"] is None

        history = client.get("/api/v1/d/learner/profiles", headers=headers())
        assert history.status_code == 200
        assert history.json()["items"] == []
    finally:
        close_client(client)


def test_the_recommendation_is_built_in_the_language_the_read_asks_for() -> None:
    """The text is NOT stored, so the same profile must come back in whichever language is asked
    for -- including a language different from the one the run was submitted with. A learner who
    switches to Sinhala must see their whole history in Sinhala, which a stored string could not
    do."""
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    session_id = str(uuid4())

    client = client_for(subject)
    try:
        created = client.post(
            f"/api/v1/d/sessions/{session_id}/profile", json=body(language="en"), headers=headers()
        )
        assert created.status_code == 200, created.text
        english = created.json()["profile"]["recommendation"]

        sinhala = client.get(
            f"/api/v1/d/sessions/{session_id}/profile?language=si", headers=headers()
        ).json()["profile"]["recommendation"]

        assert english != sinhala
        assert not any(ord(character) in SINHALA_RANGE for character in english)
        assert any(ord(character) in SINHALA_RANGE for character in sinhala)

        # Every read path honours it, not just the by-session one.
        latest_si = client.get(
            "/api/v1/d/learner/profiles/latest?language=si", headers=headers()
        ).json()["profile"]["recommendation"]
        history_si = client.get(
            "/api/v1/d/learner/profiles?language=si", headers=headers()
        ).json()["items"][0]["recommendation"]
        assert latest_si == sinhala
        assert history_si == sinhala

        # And the stored row carries no recommendation text to have frozen in the first place.
        assert "recommendation" not in created.json()["profile"]["features"]
    finally:
        close_client(client)


def test_a_struggling_run_and_a_strong_run_do_not_produce_the_same_profile(monkeypatch) -> None:
    """A positive control. Every assertion above would still pass if the heuristic returned a
    constant, so this one proves the levels actually respond to the evidence."""
    rules_only(monkeypatch)
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        strong = client.post(
            f"/api/v1/d/sessions/{uuid4()}/profile",
            json=body(10, matched=True, attempts=1, assist=False, clicks=1, response_time_sec=1.0),
            headers=headers(),
        ).json()["profile"]
        struggling = client.post(
            f"/api/v1/d/sessions/{uuid4()}/profile",
            json=body(10, matched=False, attempts=4, assist=True, clicks=9, response_time_sec=14.0),
            headers=headers(),
        ).json()["profile"]

        assert strong["number_sense_level"] == "high"
        assert struggling["number_sense_level"] == "low"
        assert strong["processing_speed_level"] == "Fast"
        assert struggling["processing_speed_level"] == "Slow"
        assert strong["memory_level"] == "high"
        assert struggling["memory_level"] == "low"
        assert strong["confidence_score"] > struggling["confidence_score"]
        assert strong["recommendation"] != struggling["recommendation"]
    finally:
        close_client(client)


# ---------------------------------------------------------------- the speed-outlier regression


# The two runs observed on the dev Supabase on 2026-10-20, response times in seconds. These are
# real values from real play, not invented fixtures -- `e1a9c0da` is the run whose single 66.8s
# pause was reported as a "Slow" child, and `346c770f` is the clean run from the same session that
# must NOT move as a result of the fix.
OBSERVED_OUTLIER_RUN = (66.8, 7.1, 4.6, 3.8, 3.5, 3.1, 2.5, 2.4, 2.3, 2.1)
OBSERVED_CLEAN_RUN = (9.2, 4.5, 3.9, 3.2, 2.8, 2.7, 2.6, 2.5, 2.3, 2.1)


def events_with_times(times: tuple[float, ...]) -> dict:
    return {
        "language": "en",
        "events": [
            {**event(i), "response_time_sec": seconds} for i, seconds in enumerate(times)
        ],
    }


def test_one_long_pause_does_not_relabel_a_whole_run_as_slow(monkeypatch) -> None:
    """REGRESSION, from live data. compD capped the MEAN response time at 10s; the cap belongs on
    each RESPONSE. With the old arithmetic the first run below scored 0.018 and stored `Slow`,
    because one 66.8-second pause dragged a mean of nine 2-7 second answers to 9.82s.

    Both assertions matter and the second is the one that constrains the fix: a median would also
    rescue the outlier run, but it would move the clean run from Moderate to Fast -- relabelling a
    run that was never wrong. Capping each response leaves the clean run's value bit-identical."""
    rules_only(monkeypatch)
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        outlier = client.post(
            f"/api/v1/d/sessions/{uuid4()}/profile",
            json=events_with_times(OBSERVED_OUTLIER_RUN),
            headers=headers(),
        )
        assert outlier.status_code == 200, outlier.text
        profile = outlier.json()["profile"]
        assert profile["processing_speed_level"] == "Moderate", (
            "a single long pause must not read as a slow child"
        )

        # The published feature is still the TRUE, uncapped mean, and its standard deviation is
        # still larger than it -- which is how a reader spots the outlier. Capping the feature
        # would have destroyed the only signal that the run was unusual.
        assert round(profile["features"]["avg_response_time_ms"]) == 9820
        assert profile["features"]["response_time_std_ms"] > profile["features"]["avg_response_time_ms"]

        clean = client.post(
            f"/api/v1/d/sessions/{uuid4()}/profile",
            json=events_with_times(OBSERVED_CLEAN_RUN),
            headers=headers(),
        )
        assert clean.status_code == 200, clean.text
        clean_profile = clean.json()["profile"]
        assert clean_profile["processing_speed_level"] == "Moderate", (
            "a run with no outlier must be unaffected by the fix"
        )
        assert round(clean_profile["features"]["avg_response_time_ms"]) == 3580
    finally:
        close_client(client)


def test_a_genuinely_slow_run_still_reads_slow(monkeypatch) -> None:
    """The counterpart to the test above, and the reason the fix is not simply "ignore slow
    answers": a child who is slow on EVERY question must still read Slow. Capping each response
    at 10s means ten answers of 30 seconds all become 10s, the mean is 10s, the score is 0.0, and
    the label is Slow -- the cap removes the influence of how far past 10s a response went, not the
    fact that it was past it."""
    rules_only(monkeypatch)
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)

    client = client_for(subject)
    try:
        response = client.post(
            f"/api/v1/d/sessions/{uuid4()}/profile",
            json=events_with_times((30.0,) * 10),
            headers=headers(),
        )
        assert response.status_code == 200, response.text
        assert response.json()["profile"]["processing_speed_level"] == "Slow"
    finally:
        close_client(client)
