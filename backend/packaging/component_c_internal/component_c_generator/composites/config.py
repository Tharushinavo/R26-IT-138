"""Versioned governance tag for the ``C-COMP-v1``/``C-LS-v1`` composite+state machinery
(Phase C5.0). The weights and thresholds themselves are NOT configurable fields here: C
Parameters §9/§10/§11 fix them as exact approved v1 values, and -- critically -- the committed,
uneditable oracle (``models.contracts.CToComponent3Payload``) hardcodes the identical weights as
bare literals in its own validator. Making them tunable here would risk a silent drift from the
oracle's frozen re-derivation; the weights are therefore transcribed verbatim as module-level
constants in ``engagement_frustration.py``/``learner_state.py`` (cited by section), and this
config carries only the governance version/status tag (mirroring the Phase C4.2
``CRecoveryConfig`` precedent, whose frozen structural facts were likewise not made
configurable). Research status remains ``CALIBRATION_PENDING`` (C Parameters §9/§10/§11); nothing
here is written to any governance document.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

COMPOSITE_CONFIG_VERSION = "c5.0-composite-1.0.0"


class CCompositeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v


def default_composite_config() -> CCompositeConfig:
    return CCompositeConfig(config_version=COMPOSITE_CONFIG_VERSION, parameter_source_status="TEST_FIXTURE_ONLY")
