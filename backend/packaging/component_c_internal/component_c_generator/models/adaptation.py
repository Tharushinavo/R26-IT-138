"""``CPolicyObservableEvidence`` (SPEC §14.2 evidence window) and ``AdaptationDecision``
(SPEC §6.5) -- Phase C4.1.

``CPolicyObservableEvidence`` is the ONLY input the rule-based policy and the safety
controller may read. It is assembled entirely from current-session observable C evidence
(recent correctness, attempts, inactivity, scaffold use, current difficulty, rolling strain,
safety state); ``extra="forbid"`` is the structural guarantee that no future information,
population/dd_subtype, Component 3 risk, or B-internal field can ever be threaded through it --
there is no runtime scan needed because none is declared, and adding one is a rejected unknown
field. The caller (C6, later) is responsible for rolling up C3 ``CTaskOpportunitySummary`` rows
into this struct's pre-aggregated scalars; C4.1 does not read raw per-task summaries itself.

``AdaptationDecision`` is internal only (SPEC §6.4/§6.5): Q-values, action probabilities,
exploration state, rolling strain, and internal RL reward must never cross C->3 (enforced by
the committed ``validators.contract_validators.C_TO_3_PROHIBITED_FIELDS``, C0). This model is
never consumed by any C->3-facing code path.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import LearnerState, PolicyMode, SessionMode, SessionPhase
from .seed import CSeedLineage

# SPEC §14.1: the only three rule-based-policy actions. Skill/family/template/reward are NOT
# actions here.
DifficultyAction = Literal["decrease_difficulty", "hold", "increase_difficulty"]

# Discretized rolling-strain bucket recorded on the decision (never the raw internal score).
StrainBucket = Literal["low", "moderate", "high", "severe"]

DifficultyLevel = Annotated[int, Field(ge=1, le=5)]


class CPolicyObservableEvidence(BaseModel):
    """Current-session observable C evidence only (SPEC §14.2). No future information, no
    population/dd_subtype, no Component 3 risk, no prohibited B field -- structurally
    unreachable (``extra="forbid"``, and none of those fields is declared below)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_mode: SessionMode
    session_phase: SessionPhase
    current_difficulty_level: DifficultyLevel

    recent_correctness_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    recent_avg_attempts: Annotated[float, Field(ge=1.0)]
    recent_inactivity_periods: Annotated[int, Field(ge=0)]
    recent_scaffold_use_count: Annotated[int, Field(ge=0)]
    recent_consecutive_error_max: Annotated[int, Field(ge=0)]
    rolling_strain_score: Annotated[float, Field(ge=0.0, le=1.0)]

    prior_session_end_state: Optional[LearnerState] = None
    is_recovery_context: bool
    technical_issue_current_task: bool
    safety_increase_block_remaining: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def _session_phase_mode_consistency(self) -> "CPolicyObservableEvidence":
        if self.session_mode == "c_only" and self.session_phase != "c_only":
            raise ValueError("session_mode='c_only' requires session_phase='c_only'")
        if self.session_mode == "combined" and self.session_phase not in ("familiarization", "mastery_driven"):
            raise ValueError("session_mode='combined' requires session_phase in ('familiarization','mastery_driven')")
        return self


class AdaptationDecision(BaseModel):
    """Internal-only adaptation decision record (SPEC §6.5). Never consumed by any C->3-facing
    code path -- Q-values/exploration/rolling-strain/internal-reward stay entirely inside this
    model, which the committed C->3 payload/validator never imports or reads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    policy_mode: PolicyMode
    policy_version: str
    rl_state: Optional[dict] = None  # EXPERIMENTAL_ONLY / unused while RL is disabled (SPEC §14)
    selected_action: DifficultyAction
    applied_action: DifficultyAction
    action_overridden: bool
    safety_reason: Optional[str] = None
    difficulty_before: DifficultyLevel
    difficulty_after: DifficultyLevel
    rolling_strain_bucket: StrainBucket
    session_start_state_bucket: Optional[LearnerState] = None
    increase_block_remaining: Annotated[int, Field(ge=0)]
    internal_reward: Optional[float] = None  # EXPERIMENTAL_ONLY / unused while RL is disabled
    seed_lineage: CSeedLineage

    @model_validator(mode="after")
    def _invariants(self) -> "AdaptationDecision":
        if self.action_overridden != (self.applied_action != self.selected_action):
            raise ValueError("action_overridden must equal (applied_action != selected_action)")
        if self.action_overridden and not self.safety_reason:
            raise ValueError("action_overridden=True requires a non-empty safety_reason")
        return self
