"""Component C Phase 7, Z4: safe child-facing reward decisions -- THROUGH THE ADAPTER
(``RewardPort.decide_child_facing_reward``, built and unwired since Phase 1b, called for the
first time here), never reimplemented.

EPHEMERAL BY DESIGN, NOT BY OMISSION (Z4-a/Z4-b). Checked before closing this as ephemeral, per
the owner's own condition: neither the C->3 payload contract (SPEC §21, quoted below) nor the C3
gameplay/telemetry spec names a child-facing reward field anywhere.

  - ``ResearchProject/current/Boundary_Contracts_v1.0/
    R26-IT-138_Component_C_to_Component_3_Contract_Spec_v1.0.md:282``: "Q-values, action
    probabilities, policy logits, agent archetypes and reward-model internals do not cross the
    boundary." Its own "13.6 RL internals" prohibited-field list (line 813) names
    ``reward_model_state`` explicitly.
  - ``Component_C_Generator_v1.0/SPEC.md`` §21 (no commit hash -- see C-6), "C->3 payload": the
    required-groups list (identifiers, quality/technical status, count/rate fields, duration/
    timing, difficulty, engagement, friction, learner state, policy/composite/rule versions)
    names no reward field; its own Prohibited line states "RL reward" explicitly.

The absence is the evidence (Z4-a's own framing): nothing anywhere in this codebase's governed
boundary contracts expects a persisted or exported reward record, child-facing or internal. This
module therefore computes ``ChildFacingReward`` and returns it -- it writes nothing, no table
exists for it (``c_reward_events`` is not among the ten C tables the EXPECTED_TABLES/
AUTHORIZED_TABLES guard in ``tests/test_be2_architecture_guards.py`` asserts by exact equality --
Z4-b: that guard is what makes "no reward table" a DESIGN, not an omission nobody noticed), and no
migration is added.

Z4-c's OWN GUARD (``tests/test_be2_architecture_guards.py``) proves, mechanically, what this
module's own shape only implies: no reward-named file under ``app/`` writes ``c_learner_local_
state``/``prior_session_end_state``, or imports anything B-owned. This function itself has no
persistence call and no import beyond the adapter and domain types -- verified by direct read,
not merely asserted.
"""

from __future__ import annotations

from typing import Optional

from app.domain.live_engine_c.types import ChildFacingReward, RewardOutcomeContext
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter


def decide_child_facing_reward(
    adapter: LiveEngineCAdapter, context: RewardOutcomeContext
) -> Optional[ChildFacingReward]:
    """Pure pass-through to ``RewardPort.decide_child_facing_reward`` -- computed and returned,
    never persisted (Z4-b). ``context`` is caller-supplied, derived from real, already-persisted
    signals (task correctness, ``recovery_parent_instance_id is not None``, retry/continuation
    facts already available from ``CTaskOpportunitySummaryRecord``/``CSafetyEventRecord``) --
    this function invents none of them, it only decides the reward reason from whatever the
    caller determined actually happened."""
    return adapter.decide_child_facing_reward(context)
