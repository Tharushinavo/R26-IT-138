"""Caller-supplied provenance for the C→3 adapter (SPEC §21 identifiers/provenance group).

``student_id``, ``intervention_session_id(/number/date)``, and ``c_session_id`` are NOT
collected here -- ``emit_c_to_3`` reads them straight off the validated
``SharedInterventionSessionMapping`` row (the single source of truth for those identifiers, per
the committed C0 mapping model), so there is no second place they could drift out of sync.
``CToComponent3Provenance`` carries only the three values the mapping row does not already
carry: the C-session's own ordinal number, the policy version string, and the production
timestamp.

``production_timestamp`` is REQUIRED and caller-supplied -- this module never calls
``datetime.now()``/``time.time()``/``hash()``/any timestamp-derived seed (SPEC §22
determinism). Same inputs (including the same ``production_timestamp``) always produce a
byte-identical payload.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROVENANCE_VERSION = "c5.1-provenance-1.0.0"


class CToComponent3Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    c_session_number: Annotated[int, Field(ge=1)]
    policy_version: str
    production_timestamp: datetime

    @field_validator("policy_version")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("policy_version must be non-empty")
        return v
