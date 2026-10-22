"""No-defaults C1 config surface (SPEC §23; mirrors ``component_b_generator/bkt/config.py``).

Phase C1 owns no scientific parameter (no prior distribution, latency, outcome, policy, or
safety magnitude belongs to the typed foundation -- those are C2-C7 concerns and must not be
invented here). ``CGeneratorConfig`` therefore carries only structural versioning + the
mandatory ``parameter_source_status`` provenance tag, exactly like B's per-phase config
classes: no field has a silent numeric/string default, and unknown fields are rejected
(``extra="forbid"``). Callers building fixtures for tests use ``parameter_source_status =
"TEST_FIXTURE_ONLY"``; production callers must record ``"CALIBRATION_PENDING"`` (or a later
signed-off status) explicitly -- never a silent default.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

C1_VERSION = "c1-1.0.0"


class CGeneratorConfig(BaseModel):
    """Structural versioning for the Component C generator (Phase C1 surface only).

    ``catalogue_version`` and ``seed_manager_version`` are provenance references the C2
    catalogue loader and this module's ``SeedManager`` are expected to agree with; this
    config does not itself load or validate the catalogue (C2 concern).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    catalogue_version: str
    seed_manager_version: str
    parameter_source_status: str  # e.g. "CALIBRATION_PENDING" or a named test-fixture tag

    @field_validator("config_version", "catalogue_version", "seed_manager_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v
