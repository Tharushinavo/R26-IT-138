"""Population-neutral adaptive-sequencing configuration (Phase B4.0, SPEC B-022).

``BSequencingConfig`` pins the three FROZEN selection-score weights (B-022:
``w_mastery_gap=0.50``, ``w_prereq=0.30``, ``w_spacing=0.20``) and carries only version /
provenance metadata. Sequencing is deterministic — there is no seed field. Ownership-scoped
``extra="forbid"`` (SPEC §F, B4 row) rejects any field outside B4's ownership: ``population``,
``dd_subtype``, BKT-internal fields, and any Component-C/Component-3 field. ``item_difficulty``
is a sequencing/ordering-only concept in this package and is never accepted here as a
correctness parent.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

B4_VERSION = "b4-1.0.0"

# FROZEN (B-022): pinned selection-score weights. Not configurable per-run.
W_MASTERY_GAP = 0.50
W_PREREQ = 0.30
W_SPACING = 0.20


class BSequencingConfig(BaseModel):
    """Adaptive-sequencing configuration (Phase B4.0).

    The three weights are FROZEN and pinned (B-022): any config supplying a different value for
    ``w_mastery_gap`` / ``w_prereq`` / ``w_spacing`` is rejected, as is a set of weights that does
    not sum to 1.0. There is no seed field — the weighted-sum scoring and canonical tie-break
    (B4.3) are fully deterministic. ``extra="forbid"`` rejects any field outside B4's ownership,
    including ``population``, ``dd_subtype``, BKT-internal fields (e.g. ``theta_B``,
    ``mastery_certified``, ``guess_guard_triggered``), and any Component-C/Component-3 field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    w_mastery_gap: Annotated[float, Field(ge=0.0, le=1.0)]
    w_prereq: Annotated[float, Field(ge=0.0, le=1.0)]
    w_spacing: Annotated[float, Field(ge=0.0, le=1.0)]

    config_version: str
    parameter_source_status: str  # e.g. "CALIBRATION_PENDING" or a clearly-named test fixture tag

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @model_validator(mode="after")
    def _weights_are_frozen_and_pinned(self) -> "BSequencingConfig":
        if (self.w_mastery_gap, self.w_prereq, self.w_spacing) != (W_MASTERY_GAP, W_PREREQ, W_SPACING):
            raise ValueError(
                "FROZEN constraint violated (B-022): weights must be exactly "
                f"w_mastery_gap={W_MASTERY_GAP}, w_prereq={W_PREREQ}, w_spacing={W_SPACING}; "
                f"got w_mastery_gap={self.w_mastery_gap}, w_prereq={self.w_prereq}, w_spacing={self.w_spacing}"
            )
        total = self.w_mastery_gap + self.w_prereq + self.w_spacing
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"FROZEN constraint violated: weights must sum to 1.0, got {total}")
        return self
