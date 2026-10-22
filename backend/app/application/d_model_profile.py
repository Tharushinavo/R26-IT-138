"""Component D's TRAINED cognitive profile model (owner direction, 2026-10-21: "we have the model
file ... fix that issue now"). It is tried first; ``d_rule_profile`` stays as the fallback.

THE ARTIFACT. ``provenance/d_model/cognitive_model.pkl``, the owner's ``mathsmate-rf-from-scratch-v1``:
four scikit-learn Pipelines (SimpleImputer(median) -> SelectKBest -> RandomForestClassifier), one per
label, trained on 63 students x 20 questions (nested CV mean accuracy 0.69, recorded in the artifact).
It was pickled under scikit-learn 1.6.1, so ``requirements.in`` pins exactly that version.

FAIL CLOSED ON THE FILE, FAIL SOFT ON THE PREDICTION. Like ``live_engine_c.q_policy``, the file is
hash-checked against ``MANIFEST.json`` BEFORE it is unpickled: unpickling runs code, so only the
exact bytes the owner supplied may ever be loaded. Unlike Q policy, a problem here does not refuse
the request -- ``predict_levels`` returns ``None`` and the caller uses the rule-based profile, which
is exactly what compD's own ``predict_profile`` did (``server/app/services/model.py:370-438``).

THE FEATURES. The model consumes 158 student-level features. ``_features`` is compD's
``extract_student_level_features`` (``model.py:117-302``) rewritten in numpy -- every formula,
default and threshold is compD's, and pandas is not needed for any of them. Three groups differ:

1. **23 features compD's server never computed**, because the model was trained by a newer notebook
   that is not available. Only ``label_memory`` uses them (its selector keeps all 158); the other
   three labels' selected features are all compD-computed, so their inputs are exact. 21 of the 23
   follow unambiguously from their names and compD's own conventions (``*_trend`` is
   ``*_late_minus_early``, as compD defines ``response_time_trend``). Two do not --
   ``high_click_rate`` (which threshold?) and ``error_pattern_entropy`` (over which categories, which
   base?) -- so they are passed as NaN and the pipeline's own median imputer supplies the training
   median. Guessing a formula would be worse than the imputer.
2. **"Number Comparison".** The model was trained on it; MathMingo has no such topic (it has
   Division). Its four topic features are NaN -> imputed, rather than compD's ``0.0`` default,
   which would read a topic the child never saw as zero accuracy.
3. **``topic_accuracy_std`` / ``topic_accuracy_range``** are taken over the topics actually present
   in the run (0.0 with fewer than two), for the same reason.

No learner identifier is logged anywhere in this module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from app.domain.d_profile import DInteractionEvent, Level, SpeedLevel

logger = logging.getLogger(__name__)

# backend/provenance/d_model  (this file: backend/app/application/d_model_profile.py)
D_MODEL_DIR = Path(__file__).resolve().parents[2] / "provenance" / "d_model"
_ARTIFACT_NAME = "cognitive_model"

_TARGETS = ("label_memory", "label_attention", "label_number_sense", "label_processing_speed")
_LEVELS: dict[str, Level] = {"low": "low", "medium": "medium", "high": "high"}
_SPEEDS: dict[str, SpeedLevel] = {"slow": "Slow", "moderate": "Moderate", "fast": "Fast"}

# compD's topic loop (`model.py:210-215`). "Number Comparison" is kept so the feature NAMES match
# the model; MathMingo never sends it, so its features are imputed (module docstring, point 2).
_TOPICS = (
    ("Counting", "counting"),
    ("Addition", "addition"),
    ("Subtraction", "subtraction"),
    ("Number Comparison", "number_comparison"),
)
_ABSENT_TOPIC_KEYS = frozenset({"number_comparison"})


class DModelArtifactError(RuntimeError):
    """The model file is missing, unreadable, or its sha256 does not match MANIFEST.json."""


@dataclass(frozen=True)
class DModelLevels:
    memory_level: Level
    attention_level: Level
    number_sense_level: Level
    processing_speed_level: SpeedLevel
    model_version: str


_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}


def clear_cache() -> None:
    _CACHE.clear()


def load_model(*, directory: Optional[Path] = None) -> dict[str, Any]:
    """Load (and cache after the first success) the artifact, verifying its sha256 first."""
    base = Path(directory) if directory is not None else D_MODEL_DIR
    key = str(base)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        try:
            manifest = json.loads((base / "MANIFEST.json").read_bytes())
            entry = manifest["artifacts"][_ARTIFACT_NAME]
            raw_path = base / entry["file"]
            raw = raw_path.read_bytes()
        except (OSError, ValueError, KeyError) as exc:
            raise DModelArtifactError(f"model artifact unavailable: {type(exc).__name__}") from exc
        if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
            raise DModelArtifactError("model artifact sha256 mismatch (file does not match MANIFEST.json)")
        import joblib  # deferred: only paid for when the model is actually used

        artifact = joblib.load(raw_path)
        if not isinstance(artifact, dict) or not isinstance(artifact.get("models"), dict):
            raise DModelArtifactError("model artifact is not compD's multi-target RF format")
        if any(target not in artifact["models"] for target in _TARGETS):
            raise DModelArtifactError("model artifact is missing a target")
        _CACHE[key] = artifact
        return artifact


# ---------------------------------------------------------------------------------- features


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))


def _masked_mean(values: Sequence[float], mask: Sequence[bool], default: float) -> float:
    picked = [v for v, keep in zip(values, mask) if keep]
    return _mean(picked) if picked else default


def _features(events: Sequence[DInteractionEvent]) -> dict[str, float]:
    """compD's ``extract_student_level_features`` (``model.py:117-302``), plus the derived features
    the model also needs. Section numbers follow compD's."""
    import numpy as np

    f: dict[str, float] = {}
    n = len(events)
    rt = np.array([e.response_time_sec for e in events], dtype=float)
    att = np.array([e.attempts for e in events], dtype=float)
    corr = np.array([1 if e.response_matched else 0 for e in events], dtype=int)
    hint = np.array([1 if e.assist_used else 0 for e in events], dtype=int)
    click = np.array([e.click_count for e in events], dtype=float)
    gap = np.array([e.time_between_actions for e in events], dtype=float)
    std = (lambda a: float(np.std(a))) if n > 1 else (lambda a: 0.0)

    # 1. Response time statistics. np.quantile's default is pandas' linear interpolation.
    f["avg_response_time"] = float(rt.mean())
    f["median_response_time"] = float(np.median(rt))
    f["response_time_std"] = std(rt)
    f["response_time_q25"] = float(np.quantile(rt, 0.25))
    f["response_time_q75"] = float(np.quantile(rt, 0.75))
    f["response_time_iqr"] = f["response_time_q75"] - f["response_time_q25"]
    f["response_time_range"] = float(rt.max() - rt.min())
    f["response_time_cv"] = (
        float(f["response_time_std"] / (f["avg_response_time"] + 1e-6)) if f["avg_response_time"] > 0 else 0.0
    )

    # 2. Attempts statistics.
    f["avg_attempts"] = float(att.mean())
    f["attempts_std"] = std(att)
    f["max_attempts"] = float(att.max())
    f["first_attempt_rate"] = float((att == 1).mean())
    f["retry_rate"] = float((att > 1).mean())
    f["multi_retry_rate"] = float((att > 2).mean())
    for k in (2, 3, 4, 5):
        f[f"attempt_ge_{k}_rate"] = float((att >= k).mean())

    # 3. Correctness and assistance.
    f["correct_rate"] = float(corr.mean())
    f["hint_rate"] = float(hint.mean())
    no_hint = hint == 0
    f["accuracy_without_hint"] = float(corr[no_hint].mean()) if no_hint.sum() > 0 else 0.0
    f["no_hint_success"] = float((corr & no_hint).mean())
    f["retry_adjusted_accuracy"] = float((corr / np.clip(att, 1, None)).mean())
    f["accuracy_per_attempt"] = float(f["correct_rate"] / (f["avg_attempts"] + 1e-6))
    f["accuracy_per_response_time"] = float(f["correct_rate"] / (f["avg_response_time"] + 1e-6))
    # Derived (not in compD's server): the hint-used mirror of accuracy_without_hint.
    with_hint = hint == 1
    f["accuracy_when_hint_used"] = float(corr[with_hint].mean()) if with_hint.sum() > 0 else 0.0
    f["accuracy_no_hint_minus_hint"] = f["accuracy_without_hint"] - f["accuracy_when_hint_used"]

    # 4. Clicks and action gaps.
    f["avg_click_count"] = float(click.mean())
    f["avg_clicks_per_attempt"] = float((click / np.clip(att, 1, None)).mean())
    click_std = std(click)
    f["click_std"] = click_std  # derived: compD computed it but did not publish it
    f["click_cv"] = float(click_std / (f["avg_click_count"] + 1e-6))
    for c in (4, 6, 8, 10, 12):
        f[f"click_ge_{c}_rate"] = float((click >= c).mean())
    f["high_click_rate"] = math.nan  # threshold unknown -> imputed (module docstring, point 1)

    f["avg_time_between_actions"] = float(gap.mean())
    f["median_time_between_actions"] = float(np.median(gap))
    gap_std = std(gap)
    f["time_between_std"] = gap_std
    f["time_between_cv"] = float(gap_std / (f["avg_time_between_actions"] + 1e-6))
    f["long_gap_rate"] = float((gap > 2.0).mean())
    for g in ("1_5", "2", "2_5", "3", "4", "5"):
        f[f"gap_gt_{g}_rate"] = float((gap > float(g.replace("_", "."))).mean())

    # 5. Split by correctness.
    corr_mask = corr == 1
    inc_mask = corr == 0
    f["avg_rt_correct"] = float(rt[corr_mask].mean()) if corr_mask.sum() > 0 else f["avg_response_time"]
    f["avg_rt_incorrect"] = float(rt[inc_mask].mean()) if inc_mask.sum() > 0 else f["avg_response_time"]
    f["rt_incorrect_minus_correct"] = f["avg_rt_incorrect"] - f["avg_rt_correct"]
    f["avg_attempts_correct"] = float(att[corr_mask].mean()) if corr_mask.sum() > 0 else 1.0
    f["avg_attempts_incorrect"] = float(att[inc_mask].mean()) if inc_mask.sum() > 0 else 1.0
    f["attempts_incorrect_minus_correct"] = f["avg_attempts_incorrect"] - f["avg_attempts_correct"]

    # 6. Split by difficulty.
    difficulty = [e.difficulty.capitalize() for e in events]
    for d in ("Easy", "Medium", "Hard"):
        mask = [x == d for x in difficulty]
        key = d.lower()
        f[f"correct_rate_{key}"] = _masked_mean(corr, mask, 0.0)
        f[f"avg_rt_{key}"] = _masked_mean(rt, mask, f["avg_response_time"])
        f[f"avg_attempts_{key}"] = _masked_mean(att, mask, 1.0)
        f[f"hint_rate_{key}"] = _masked_mean(hint, mask, 0.0)
    for metric in ("avg_attempts", "avg_rt", "correct_rate", "hint_rate"):
        # compD published the first two; the correct_rate / hint_rate pairs are derived the same way.
        f[f"{metric}_hard_minus_easy"] = f[f"{metric}_hard"] - f[f"{metric}_easy"]
        f[f"{metric}_medium_minus_easy"] = f[f"{metric}_medium"] - f[f"{metric}_easy"]
        f[f"{metric}_hard_minus_medium"] = f[f"{metric}_hard"] - f[f"{metric}_medium"]

    # 7. Split by topic.
    topics = [e.topic for e in events]
    topic_rts: list[float] = []
    for name, key in _TOPICS:
        mask = [t == name for t in topics]
        if key in _ABSENT_TOPIC_KEYS:
            for prefix in ("correct_rate", "avg_rt", "avg_attempts", "hint_rate"):
                f[f"{prefix}_{key}"] = math.nan
            topic_rts.append(f["avg_response_time"])  # compD's default, kept for topic_rt_std parity
            continue
        f[f"correct_rate_{key}"] = _masked_mean(corr, mask, 0.0)
        t_rt = _masked_mean(rt, mask, f["avg_response_time"])
        f[f"avg_rt_{key}"] = t_rt
        topic_rts.append(t_rt)
        f[f"avg_attempts_{key}"] = _masked_mean(att, mask, 1.0)
        f[f"hint_rate_{key}"] = _masked_mean(hint, mask, 0.0)
    f["topic_rt_std"] = float(np.std(topic_rts))
    f["topic_rt_range"] = float(max(topic_rts) - min(topic_rts))
    present_rates = [
        _masked_mean(corr, [t == name for t in topics], 0.0) for name in dict.fromkeys(topics)
    ]
    f["topic_accuracy_std"] = float(np.std(present_rates)) if len(present_rates) > 1 else 0.0
    f["topic_accuracy_range"] = float(max(present_rates) - min(present_rates)) if len(present_rates) > 1 else 0.0

    # 8. Early vs late. `*_trend` is `*_late_minus_early`, compD's own definition for response time.
    half = max(1, n // 2)

    def early_late(values: Any, name: str) -> None:
        early = float(values[:half].mean())
        late = float(values[half:].mean()) if n > 1 else early
        f[f"{name}_early"] = early
        f[f"{name}_late"] = late
        f[f"{name}_late_minus_early"] = late - early

    early_late(corr, "accuracy")
    early_late(rt, "response_time")
    early_late(att, "attempts")
    early_late(hint, "hint")
    early_late(click, "click")
    early_late(gap, "action_gap")
    for name, trend in (
        ("accuracy", "accuracy_trend"),
        ("response_time", "response_time_trend"),
        ("attempts", "attempts_trend"),
        ("hint", "hint_trend"),
        ("click", "click_trend"),
        ("action_gap", "action_gap_trend"),
    ):
        f[trend] = f[f"{name}_late_minus_early"]

    # 9. Response time threshold rates.
    for thr in (8, 10, 12, 15, 18, 20, 22, 25, 30):
        f[f"rt_le_{thr}_rate"] = float((rt <= thr).mean())
        f[f"rt_gt_{thr}_rate"] = float((rt > thr).mean())

    # 10. Streaks and transitions.
    max_c = cur_c = max_i = cur_i = transitions = 0
    for i in range(n):
        if corr[i] == 1:
            cur_c += 1
            max_c = max(max_c, cur_c)
            cur_i = 0
        else:
            cur_i += 1
            max_i = max(max_i, cur_i)
            cur_c = 0
        if i > 0 and corr[i] == 1 and corr[i - 1] == 0:
            transitions += 1
    f["longest_correct_streak"] = float(max_c)
    f["longest_incorrect_streak"] = float(max_i)
    f["correct_transition_rate"] = float(transitions / max(1, n - 1))

    # 11. Error type rates.
    errors = [e.error_type for e in events]
    for kind in ("calculation", "conceptual", "careless", "unknown"):
        f[f"error_{kind}_rate"] = float(sum(1 for x in errors if x == kind) / n)
    f["error_pattern_entropy"] = math.nan  # definition unknown -> imputed (module docstring, point 1)

    # 12. Correlations. compD's guard uses pandas' sample std (ddof=1).
    def safe_corr(a: Any, b: Any) -> float:
        if n > 1 and float(np.std(a, ddof=1)) > 1e-8 and float(np.std(b, ddof=1)) > 1e-8:
            c = float(np.corrcoef(a.astype(float), b.astype(float))[0, 1])
            return c if math.isfinite(c) else 0.0
        return 0.0

    f["corr_rt_correct"] = safe_corr(rt, corr)
    f["corr_rt_attempts"] = safe_corr(rt, att)
    f["corr_click_correct"] = safe_corr(click, corr)  # derived
    f["corr_click_attempts"] = safe_corr(click, att)
    f["corr_gap_correct"] = safe_corr(gap, corr)
    f["corr_gap_attempts"] = safe_corr(gap, att)

    # 13. Compound efficiency scores.
    f["memory_efficiency_score"] = float(
        (f["correct_rate"] * (1.0 - f["retry_rate"])) / (f["median_response_time"] + 1e-6)
    )
    f["attention_efficiency_score"] = float(
        (f["correct_rate"] * (1.0 - f["hint_rate"])) / (f["avg_click_count"] + 1e-6)
    )
    f["processing_efficiency_score"] = float(1.0 / (f["avg_response_time"] + 1e-6))
    f["processing_gap_efficiency"] = float(1.0 / (f["avg_time_between_actions"] + 1e-6))
    return f


# ---------------------------------------------------------------------------------- predict


def _predict(artifact: dict[str, Any], features: dict[str, float]) -> dict[str, str]:
    """compD's ``_predict_with_rf_artifact`` (``model.py:305-324``), with one fix: columns come from
    each pipeline's own ``feature_names_in_``. compD read ``target_feature_cols``, which this
    artifact does not have, so compD would have sent zero columns."""
    import numpy as np

    out: dict[str, str] = {}
    for target in _TARGETS:
        model = artifact["models"][target]
        cols = list(getattr(model, "feature_names_in_", artifact.get("feature_cols", [])))
        missing = [c for c in cols if c not in features]
        if missing:
            raise DModelArtifactError(f"model expects {len(missing)} feature(s) this module does not produce")
        row = np.array([[features[c] for c in cols]], dtype=float)
        with warnings.catch_warnings():
            # Fitted on a DataFrame; an ndarray in the same column order is equivalent.
            warnings.simplefilter("ignore", UserWarning)
            out[target] = str(model.predict(row)[0])
    return out


def predict_levels(
    events: Sequence[DInteractionEvent], *, directory: Optional[Path] = None
) -> Optional[DModelLevels]:
    """The model's four levels for one run, or ``None`` if the model cannot be used -- the caller
    then falls back to the rule-based profile, as compD did."""
    if not events:
        return None
    try:
        artifact = load_model(directory=directory)
        raw = _predict(artifact, _features(events))
        return DModelLevels(
            memory_level=_LEVELS[raw["label_memory"].strip().lower()],
            attention_level=_LEVELS[raw["label_attention"].strip().lower()],
            number_sense_level=_LEVELS[raw["label_number_sense"].strip().lower()],
            processing_speed_level=_SPEEDS[raw["label_processing_speed"].strip().lower()],
            model_version=str(artifact.get("model_version", "mathsmate-rf")),
        )
    except Exception as exc:  # noqa: BLE001 -- any failure means "use the rules", never a 500
        logger.warning("d_model_profile: model unavailable, using rule-based profile (%s)", type(exc).__name__)
        return None
