"""Component D's trained model (owner direction, 2026-10-21; ``app/application/d_model_profile.py``).

What is pinned here, and why each matters:

- the shipped artifact is the one ``MANIFEST.json`` names, and a tampered file is refused BEFORE it
  is unpickled -- unpickling runs code, so the hash check is the security boundary;
- every feature the four pipelines expect is produced (a renamed feature would otherwise surface
  as a silent fallback to the rules);
- golden predictions for fixed runs, so a change to the features or the artifact cannot move a
  child's levels unnoticed;
- the profile route stores the model's levels and its ``model_version``, and falls back to the
  rule-based profile -- never a 500 -- when the model cannot be used.

The 262,000-value parity of ``_features`` against compD's pandas ``extract_student_level_features``
was checked when this was written (identical to 7e-15); compD's source is not in this image, so
that check is recorded in compD/logs rather than repeated here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application import d_model_profile
from app.application.d_model_profile import (
    D_MODEL_DIR,
    DModelArtifactError,
    _features,
    clear_cache,
    load_model,
    predict_levels,
)

from tests.test_d2_component_d_api import (
    body,
    client_for,
    close_client,
    headers,
    setup_learner,
    upgrade,
)

MODEL_VERSION = "mathsmate-rf-from-scratch-v1"


def run(n: int = 10, *, matched: bool = True, attempts: int = 1, assist: bool = False, clicks: int = 1, rt: float = 3.0):
    """The same shape as test_d2's ``event``, as attribute objects (``_features`` reads attributes)."""
    return [
        SimpleNamespace(
            question_id=f"q{i}",
            topic=["Counting", "Addition", "Subtraction", "Division"][i % 4],
            difficulty=["Easy", "Medium", "Hard"][i % 3],
            response_time_sec=rt,
            attempts=attempts,
            response_matched=matched,
            assist_used=assist,
            click_count=clicks,
            session_time_sec=30.0,
            time_between_actions=1.25,
            error_type="none" if matched else "calculation",
        )
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


def test_the_shipped_artifact_matches_its_manifest() -> None:
    manifest = json.loads((D_MODEL_DIR / "MANIFEST.json").read_bytes())
    entry = manifest["artifacts"]["cognitive_model"]
    raw = (D_MODEL_DIR / entry["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert len(raw) == entry["bytes"]
    assert load_model()["model_version"] == entry["model_version"] == MODEL_VERSION


def test_a_tampered_artifact_is_refused_before_it_is_unpickled(tmp_path: Path, monkeypatch) -> None:
    shutil.copy(D_MODEL_DIR / "cognitive_model.pkl", tmp_path / "cognitive_model.pkl")
    manifest = json.loads((D_MODEL_DIR / "MANIFEST.json").read_bytes())
    manifest["artifacts"]["cognitive_model"]["sha256"] = "0" * 64
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    import joblib

    def never(*_args, **_kwargs):
        raise AssertionError("a file that failed its hash check must never be unpickled")

    monkeypatch.setattr(joblib, "load", never)
    with pytest.raises(DModelArtifactError):
        load_model(directory=tmp_path)
    assert predict_levels(run(), directory=tmp_path) is None


def test_a_missing_artifact_means_no_model_levels(tmp_path: Path) -> None:
    assert predict_levels(run(), directory=tmp_path) is None
    assert predict_levels([]) is None


def test_every_feature_the_pipelines_expect_is_produced() -> None:
    artifact = load_model()
    produced = set(_features(run()))
    for target, pipeline in artifact["models"].items():
        missing = set(pipeline.feature_names_in_) - produced
        assert not missing, (target, sorted(missing))


def test_golden_predictions_for_fixed_runs() -> None:
    """Recorded from this artifact and these features on 2026-10-21. If either changes, these
    move -- which is the point: re-record them only on purpose."""
    cases = {
        "strong": (run(rt=1.0), ("medium", "high", "high", "Fast")),
        "struggling": (
            run(matched=False, attempts=4, assist=True, clicks=9, rt=14.0),
            ("low", "low", "low", "Fast"),
        ),
        "slow on every question": (run(rt=30.0), ("high", "high", "high", "Slow")),
        "a single question": (run(1), ("medium", "high", "high", "Fast")),
    }
    for name, (events, expected) in cases.items():
        levels = predict_levels(events)
        assert levels is not None, name
        got = (levels.memory_level, levels.attention_level, levels.number_sense_level, levels.processing_speed_level)
        assert got == expected, (name, got)
        assert levels.model_version == MODEL_VERSION


def test_the_profile_route_stores_the_models_levels() -> None:
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    client = client_for(subject)
    try:
        response = client.post(f"/api/v1/d/sessions/{uuid4()}/profile", json=body(), headers=headers())
        assert response.status_code == 200, response.text
        profile = response.json()["profile"]
        assert profile["model_version"] == MODEL_VERSION
        expected = predict_levels(run())
        assert (
            profile["memory_level"],
            profile["attention_level"],
            profile["number_sense_level"],
            profile["processing_speed_level"],
        ) == (
            expected.memory_level,
            expected.attention_level,
            expected.number_sense_level,
            expected.processing_speed_level,
        )
    finally:
        close_client(client)


def test_an_unusable_model_falls_back_to_the_rules_not_a_500(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(d_model_profile, "D_MODEL_DIR", tmp_path)  # empty: no MANIFEST, no file
    upgrade()
    subject = f"d-learner-{uuid4()}"
    setup_learner(subject)
    client = client_for(subject)
    try:
        response = client.post(f"/api/v1/d/sessions/{uuid4()}/profile", json=body(), headers=headers())
        assert response.status_code == 200, response.text
        assert response.json()["profile"]["model_version"] == "rule-based-v2"
    finally:
        close_client(client)
