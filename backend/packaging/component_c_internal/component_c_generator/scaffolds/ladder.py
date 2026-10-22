"""Pure scaffold-ladder decision (SPEC §15) -- deterministic and reviewed, no RNG, no LLM,
no network. ``decide_scaffold_level`` reads only ``ScaffoldDecisionContext`` + config: it never
emits or sets ``engagement_score``/``frustration_index``/``learner_state`` (there is no such
field anywhere in this module, and the function returns a bare ``ScaffoldLevel`` string, not a
composite record) -- "scaffold use does not directly set engagement/frustration/state" (SPEC
§15) is a structural guarantee here, not a runtime check.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated

from ..models.enums import ScaffoldLevel
from .config import CScaffoldConfig

LADDER_VERSION = "c4.2-ladder-1.0.0"


class ScaffoldDecisionContext(BaseModel):
    """Current-task-only evidence for the scaffold decision (no session-wide, future, or
    B-derived field)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    consecutive_incorrect_current_task: Annotated[int, Field(ge=0)]
    safety_forces_recovery: bool


def decide_scaffold_level(context: ScaffoldDecisionContext, config: CScaffoldConfig) -> ScaffoldLevel:
    """SPEC §15: C0 (no_scaffold) through C4 (recovery_task). "Safety may force C4" -- when
    ``safety_forces_recovery`` is set, the result is unconditionally C4 regardless of the
    ordinary escalation count. Otherwise the level is a deterministic, monotone step function
    of ``consecutive_incorrect_current_task`` against the configured thresholds -- the same
    inputs always produce the same level."""
    if context.safety_forces_recovery:
        return "C4"

    n = context.consecutive_incorrect_current_task
    if n >= config.level_c4_min_consecutive_incorrect:
        return "C4"
    if n >= config.level_c3_min_consecutive_incorrect:
        return "C3"
    if n >= config.level_c2_min_consecutive_incorrect:
        return "C2"
    if n >= config.level_c1_min_consecutive_incorrect:
        return "C1"
    return "C0"
