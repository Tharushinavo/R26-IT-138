"""Reward-safety policy (SPEC §16) -- Phase C4.2.

Child-facing reward may acknowledge ONLY four reasons: ``correct_completion``, ``persistence``,
``recovery``, ``safe_continuation``. The six SPEC §16 prohibitions are made STRUCTURALLY
impossible, not merely avoided at runtime:

1. **"reward only speed"** -- ``RewardOutcomeContext`` has no timing/latency field, and
   ``decide_child_facing_reward`` never reads one (there is nothing to read).
2. **"remove accumulated progress after error"** -- this module has no write path to any
   progress/mastery/score store at all; it only ever RETURNS a reward reason (or ``None``), it
   never mutates anything.
3. **"shame/punish"** -- ``RewardReason`` is a 4-value enum of exclusively positive
   acknowledgements; there is no negative/punitive literal anywhere, and the "no reward this
   time" case is silence (``None``), never an explicit negative signal.
4. **"rank children publicly"** -- the function takes exactly ONE learner's own outcome
   context; there is no cohort/leaderboard/comparison parameter anywhere for it to rank against.
5. **"set learner state directly"** -- ``ChildFacingReward`` has no learner-state field, and
   this module does not import ``models.enums.LearnerState`` or any C-LS-v1 machinery at all.
6. **"modify B mastery"** -- this module has no import of ``models.contracts`` and no
   B-mastery-shaped parameter anywhere; there is no code path through which a B mastery value
   could enter or be written.

``InternalRLReward`` is a strictly separate, internal-only model (SPEC §16: "RL reward is
internal only ... and never crosses C->3") -- it is never referenced by, or compatible with,
``ChildFacingReward``, and the committed C->3 payload/validator never imports this module.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

REWARD_POLICY_VERSION = "c4.2-reward-1.0.0"

# SPEC §16: the ONLY four allowed child-facing reward reasons.
RewardReason = Literal["correct_completion", "persistence", "recovery", "safe_continuation"]


class ChildFacingReward(BaseModel):
    """The ONLY thing this module ever hands to the product/UI layer: one of the four allowed
    reasons. No other field exists on this model -- extra="forbid" makes that structural."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reward_reason: RewardReason


class RewardOutcomeContext(BaseModel):
    """What just happened, from this ONE learner's own current-task perspective only. No
    timing field (prohibition 1), no cohort/ranking field (prohibition 4), no B-mastery field
    (prohibition 6), no learner-state field (prohibition 5)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_completed_correctly: bool
    is_recovery_task: bool
    retried_after_incorrect_then_continued: bool  # persistence: kept trying after a miss
    continued_after_safety_event_without_quitting: bool  # safe_continuation


class InternalRLReward(BaseModel):
    """Internal-only RL reward signal (SPEC §16: "ENGINEERING_ASSUMPTION/CALIBRATION_PENDING",
    "never crosses C->3"). Kept in a model with no relationship to ``ChildFacingReward`` and
    never imported by any C->3-facing code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reward_value: float = Field(allow_inf_nan=False)


def decide_child_facing_reward(context: RewardOutcomeContext) -> Optional[ChildFacingReward]:
    """SPEC §16 rule-based reward policy: acknowledge correct completion first (highest
    priority), then recovery, then persistence, then safe continuation; otherwise no reward
    this cycle (silence -- never a punitive signal, satisfying prohibition 3)."""
    if context.task_completed_correctly:
        return ChildFacingReward(reward_reason="correct_completion")
    if context.is_recovery_task:
        return ChildFacingReward(reward_reason="recovery")
    if context.retried_after_incorrect_then_continued:
        return ChildFacingReward(reward_reason="persistence")
    if context.continued_after_safety_event_without_quitting:
        return ChildFacingReward(reward_reason="safe_continuation")
    return None
