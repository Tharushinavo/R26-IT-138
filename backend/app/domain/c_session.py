"""Public contracts for Component C's session-lifecycle endpoints (Phase 4b).

Mirrors ``app.domain.b_session`` exactly in shape and discipline (X-4, allow-list construction --
named fields only, never a serialised model with fields subtracted). No mastery value, no B
identity field (``student_id`` in B's own space, ``intervention_session_id`` in B's own
``^STU-####-I-###$`` format), no engine internal, and no ``selection_configuration``-derived value
of any kind may appear here (owner condition 5, Phase 4b work order).

R-1 (SUPERVISOR RULING, Phase 4b continuation): ``mastery_context_mode`` is deliberately ABSENT
from ``CSessionFields``, superseding the earlier ratification that named it. It is fully
derivable client-side from ``session_mode`` alone --
``session_lifecycle.mastery_context_mode_for`` is a TOTAL function of ``session_mode`` ("fixed by
mode, never inferred from anything else", v3.0 §11 Phase 4), and ``session_mode`` is already a
field here. Exposing a redundant field whose NAME trips BE5a's frozen-contract
``FORBIDDEN_FIELD_TERMS`` guard (``tests/test_be5a_contract_freeze.py``, substring match on
"mastery", no allow-list mechanism), when the client can compute the same value from a field
already present, is strictly worse than not exposing it. Do not add it back without re-deriving
this reasoning -- the frozen-contract guard has not changed and will still reject it.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CSessionFields(StrictModel):
    c_session_id: UUID
    state: str
    session_mode: str
    session_phase: str
    grade: int
    started_at_utc: datetime
    row_version: int


class CSessionCommandResponse(CSessionFields):
    request_id: str


class CActiveSessionResponse(StrictModel):
    session: Optional[CSessionFields]
    request_id: str
