"""``CEvidenceWindowConfig`` (Phase C6.0) -- the ONLY new numeric parameter this phase
introduces, needed to turn the running per-task ``CTaskOpportunitySummary`` history into the
committed ``CPolicyObservableEvidence`` the C4.1 policy/safety layer requires as input.

No committed module derives ``CPolicyObservableEvidence`` from task history (every C4.1 test
supplies it directly as a fixture) -- SPEC §14.2 calls it "the current-session evidence window"
but does not fix an exact task-count for most of its "recent_*" fields. C Parameters §14 DOES
cite two concrete window sizes for two of the seven RL-state inputs: ``recent_success_rate_bucket``
over the **last N=5 completed tasks**, and ``c_rolling_strain`` over the **last w=3 completed
tasks**. This config reuses those two already-cited numbers (not new inventions) uniformly: N=5
for every other "recent_*" field on ``CPolicyObservableEvidence`` (correctness, attempts,
inactivity, scaffold use, consecutive-error max), and w=3 (hardcoded, matching Params §14's own
frozen citation, not made configurable) for the rolling-strain formula in ``evidence.py``.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVIDENCE_WINDOW_CONFIG_VERSION = "c6.0-evidence-window-1.0.0"


class CEvidenceWindowConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    # C Parameters §14: "recent_success_rate_bucket: over last N=5 completed tasks" -- reused
    # here for every "recent_*" CPolicyObservableEvidence field except rolling_strain_score
    # (which has its own distinct, separately-cited w=3 window, hardcoded in evidence.py).
    recent_window_task_count: Annotated[int, Field(ge=1)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v


def default_evidence_window_config() -> CEvidenceWindowConfig:
    return CEvidenceWindowConfig(
        config_version=EVIDENCE_WINDOW_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        recent_window_task_count=5,
    )
