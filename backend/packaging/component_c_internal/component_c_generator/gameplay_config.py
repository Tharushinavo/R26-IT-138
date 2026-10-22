"""``C3GameplayConfig`` (C3 §17) -- versioned, no-defaults gameplay-generation configuration.

Every coefficient below is either **cited verbatim** to the Component C Empirical/Statistical
Parameters (`Component_C_v1.0/...Empirical_Statistical_Parameters_v1.0.md`, sections noted per
field) or an explicit `ENGINEERING_ASSUMPTION` where the cited value is itself
population-keyed (TD/MLD/DD) and therefore **cannot** be used directly here: C3 is
population-neutral by construction (SPEC §3.5/§6 -- "no population key is permitted" -- and the
Parameters' own §1 clarification confirms direct per-population lookup is NON-EXECUTABLE in the
deployable baseline, SF-039). Where the source gives three population-conditioned values, this
config picks the **single, population-INDEPENDENT middle (MLD-anchored) value** as an
`ENGINEERING_ASSUMPTION` placeholder for structural generation/testing -- explicitly NOT a
replacement for the calibration-pending overlapping-distribution work the Parameters document
itself defers to `Simulation_v1.0/...Population_Influence_and_Leakage_Control_Register_v1.0.md`.

Every value's ``parameter_source_status`` is ``"TEST_FIXTURE_ONLY"``: the authoritative
per-parameter magnitudes remain `CALIBRATION_PENDING` pending Component C Parameters sign-off.
Nothing here is written into any governance document.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GAMEPLAY_GENERATOR_VERSION = "c3-gameplay-1.0.0"

_REJECTED_STATUSES_IN_RESEARCH_MODE = ("TEST_FIXTURE_ONLY", "SMOKE_ONLY")


class OutcomeCoefficients(BaseModel):
    """Combined-session correctness logit (C3 §7.3; cited verbatim from C Parameters §8.1
    -- these six numbers are NOT invented, they are the document's own v1 coefficients)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    beta0: float = Field(allow_inf_nan=False)
    beta_mastery: float = Field(allow_inf_nan=False)
    beta_gap: float = Field(allow_inf_nan=False)
    beta_tolerance: float = Field(allow_inf_nan=False)
    beta_session: float = Field(allow_inf_nan=False)
    beta_offday: float = Field(allow_inf_nan=False)
    p_correct_floor: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    p_correct_ceiling: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]

    @model_validator(mode="after")
    def _bounds(self) -> "OutcomeCoefficients":
        if not (self.p_correct_floor < self.p_correct_ceiling):
            raise ValueError("p_correct_floor must be < p_correct_ceiling")
        return self


class FallbackOutcomeConfig(BaseModel):
    """C-only fallback correctness model (C3 §7.4): no mastery surrogate; monotone
    non-increasing in difficulty by construction (enforced below), TEST_FIXTURE_ONLY."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # One base probability per C difficulty level (1..5); MUST be monotone non-increasing.
    base_probability_by_difficulty: tuple[float, float, float, float, float]
    tolerance_weight: float = Field(allow_inf_nan=False)
    session_weight: float = Field(allow_inf_nan=False)
    offday_weight: float = Field(allow_inf_nan=False)
    p_correct_floor: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    p_correct_ceiling: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]

    @field_validator("base_probability_by_difficulty")
    @classmethod
    def _monotone_non_increasing(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        for a, b in zip(v, v[1:]):
            if not (0.0 <= b <= a <= 1.0):
                raise ValueError(f"base_probability_by_difficulty must be non-increasing and in [0,1], got {v}")
        return v

    @model_validator(mode="after")
    def _bounds(self) -> "FallbackOutcomeConfig":
        if not (self.p_correct_floor < self.p_correct_ceiling):
            raise ValueError("p_correct_floor must be < p_correct_ceiling")
        return self


class LatencyConfig(BaseModel):
    """C-local lognormal latency (C3 §9; C Parameters §7). SF-042: no B timing field, no
    shared latent, no shared fatigue anywhere in this model or its consumers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    location_mu: float = Field(allow_inf_nan=False)  # log-sec baseline (population-neutral pick)
    scale_sigma: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    difficulty_shift_per_level: float = Field(allow_inf_nan=False)  # C Parameters §7: 0.06
    session_shift_weight: float = Field(allow_inf_nan=False)  # C Parameters §7: 0.30
    offday_shift_ln: float = Field(allow_inf_nan=False)  # C Parameters §7: ln(1.15)
    floor_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]  # C Parameters §7: 0.3
    cap_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]  # C3 §9: provisional 90s C latency safety cap
    timeout_threshold_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]

    @model_validator(mode="after")
    def _bounds(self) -> "LatencyConfig":
        if not (self.floor_sec < self.cap_sec):
            raise ValueError("floor_sec must be < cap_sec")
        if not (self.timeout_threshold_sec >= self.cap_sec):
            raise ValueError("timeout_threshold_sec must be >= cap_sec (a timeout is at/above the safety cap)")
        return self


class AttemptConfig(BaseModel):
    """Bounded attempt loop (C3 §8; C Parameters §8.3 names max attempts 10). The retry-vs-quit
    decision after a non-terminal incorrect attempt is governed entirely by ``QuitConfig``'s
    quit-after-error model (C3 §13.2) -- there is no separate retry probability: if quit does
    not fire, the loop retries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: Annotated[int, Field(ge=1, le=10)]


class PauseConfig(BaseModel):
    """Pauses/inactivity (C3 §10). Technical pauses are a SEPARATE probability from learner
    pauses -- SPEC §10: technical time must never increase learner-inactivity burden."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pause_probability_per_attempt: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    pause_duration_mean_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    pause_duration_sd_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    max_pauses_per_task: Annotated[int, Field(ge=0)]
    technical_pause_probability: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    technical_pause_duration_mean_sec: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]


class QuitConfig(BaseModel):
    """Quit-after-error event-generation probability (C3 §13.2; C Parameters §8.4 quit model,
    single population-neutral ``q0`` -- see module docstring) + pre-attempt skip/quit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    q0: float = Field(allow_inf_nan=False)
    consecutive_error_weight: float = Field(allow_inf_nan=False)  # C Parameters §8.4: 0.40
    persistence_weight: float = Field(allow_inf_nan=False)  # C Parameters §8.4: 1.0 (on tendency-0.5)
    skip_probability: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    quit_without_recent_error_probability: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class ScaffoldConfig(BaseModel):
    """Scaffold interaction (C3 §12) -- request/shown only; C3 never decides the ladder."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_probability_per_attempt: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    show_probability_given_request: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class TechnicalIssueConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    probability_per_attempt: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class C3GameplayConfig(BaseModel):
    """Versioned, no-defaults C3 gameplay configuration (C3 §17)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str
    generator_version: str
    smoke_mode: bool
    serializer_precision: Annotated[int, Field(ge=0, le=12)]

    outcome: OutcomeCoefficients
    fallback_outcome: FallbackOutcomeConfig
    latency: LatencyConfig
    attempt: AttemptConfig
    pause: PauseConfig
    quit: QuitConfig
    scaffold: ScaffoldConfig
    technical: TechnicalIssueConfig

    @field_validator("config_version", "parameter_source_status", "generator_version")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v


def validate_not_test_fixture_in_research_mode(config: C3GameplayConfig, mode: str) -> None:
    """C3 §17: ``SMOKE_ONLY`` / ``TEST_FIXTURE_ONLY`` parameters must be REJECTED in a
    research/full mode. Raises ``ValueError`` if a fixture-tagged config is used with
    ``mode == "research"``."""
    if mode == "research" and config.parameter_source_status in _REJECTED_STATUSES_IN_RESEARCH_MODE:
        raise ValueError(
            f"C3GameplayConfig.parameter_source_status={config.parameter_source_status!r} is "
            f"rejected in research mode (C3 §17); a signed-off calibration status is required."
        )


def compute_config_checksum(config: C3GameplayConfig) -> str:
    """Stable SHA-256 over the canonical config (mirrors component_b_generator's
    ``compute_config_hash``)."""
    payload = json.dumps(config.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def default_gameplay_config() -> C3GameplayConfig:
    """The Phase C3 TEST_FIXTURE_ONLY gameplay config -- explicit builder (mirrors B's
    ``default_b1_config()`` / C2.1's ``default_generation_config()``), never a silent fallback."""
    return C3GameplayConfig(
        config_version="c3-gameplay-1.0.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
        generator_version=GAMEPLAY_GENERATOR_VERSION,
        smoke_mode=True,
        serializer_precision=6,
        outcome=OutcomeCoefficients(
            # C Parameters §8.1 v1 coefficients (cited verbatim, not invented).
            beta0=-0.50, beta_mastery=4.00, beta_gap=3.00, beta_tolerance=1.00,
            beta_session=0.30, beta_offday=0.40,
            p_correct_floor=0.02, p_correct_ceiling=0.98,
        ),
        fallback_outcome=FallbackOutcomeConfig(
            # Monotone non-increasing in difficulty (C3 §7.4 requirement); ENGINEERING_ASSUMPTION,
            # no mastery input anywhere.
            base_probability_by_difficulty=(0.75, 0.65, 0.55, 0.45, 0.35),
            tolerance_weight=0.20, session_weight=0.15, offday_weight=0.20,
            p_correct_floor=0.02, p_correct_ceiling=0.98,
        ),
        latency=LatencyConfig(
            # Population-neutral MLD-anchored pick (C Parameters §7 table has TD/MLD/DD rows;
            # see module docstring for why a single non-population value is used here).
            location_mu=1.75, scale_sigma=0.40,
            difficulty_shift_per_level=0.06,  # C Parameters §7
            session_shift_weight=0.30,  # C Parameters §7
            offday_shift_ln=0.13976194,  # ln(1.15), C Parameters §7
            floor_sec=0.3, cap_sec=90.0,  # C Parameters §7 / C3 §9
            timeout_threshold_sec=90.0,
        ),
        attempt=AttemptConfig(max_attempts=10),
        pause=PauseConfig(
            pause_probability_per_attempt=0.08, pause_duration_mean_sec=12.0, pause_duration_sd_sec=6.0,
            max_pauses_per_task=3, technical_pause_probability=0.02, technical_pause_duration_mean_sec=8.0,
        ),
        quit=QuitConfig(
            # Population-neutral MLD-anchored q0 pick (C Parameters §8.4 has TD/MLD/DD q0 rows).
            q0=-2.4423, consecutive_error_weight=0.40, persistence_weight=1.00,
            skip_probability=0.02, quit_without_recent_error_probability=0.01,
        ),
        scaffold=ScaffoldConfig(request_probability_per_attempt=0.10, show_probability_given_request=0.95),
        technical=TechnicalIssueConfig(probability_per_attempt=0.01),
    )
