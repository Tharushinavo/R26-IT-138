"""SF-040 emission gate ("A C payload is emitted only when a real C session exists") + wiring
through the committed frozen gate (``validators.contract_validators``).

``emit_c_to_3`` is the only function in this package that talks to a mapping row. It reads
identifiers straight off the row (never duplicating them from a second, driftable source), and
after assembling a payload it hands the payload back through the SAME committed
``validate_payload_against_mapping`` referential-integrity + prohibited-field gate that the rest
of the system already trusts -- so a payload this function returns is proven, not merely
asserted, to pass the frozen gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from models.contracts import CToComponent3Payload, EngagementComponents, FrustrationComponents

from validators.contract_validators import validate_payload, validate_payload_against_mapping

from ..aggregation.models import CSessionAggregate
from ..composites.engagement_frustration import CompositeFormulaVersion
from ..composites.learner_state import StateReason, TelemetryQualityStatus
from ..models.enums import LearnerState
from .adapter import build_c_to_3_payload
from .inputs import CToComponent3Provenance

EMISSION_VERSION = "c5.1-emission-1.0.0"


class NoRealCSessionError(ValueError):
    """SF-040: "A C payload is emitted only when a real C session exists." Raised -- and no
    payload is built or returned -- when the mapping row's ``c_present`` is false or its
    ``c_session_id`` is null."""


def emit_c_to_3(
    mapping_row: Mapping[str, Any],
    *,
    provenance: CToComponent3Provenance,
    aggregate: CSessionAggregate,
    telemetry_quality_status: TelemetryQualityStatus,
    composite_formula_version: CompositeFormulaVersion,
    learner_state: Optional[LearnerState],
    state_reason: StateReason,
    engagement_components: Optional[EngagementComponents] = None,
    engagement_score: Optional[float] = None,
    frustration_components: Optional[FrustrationComponents] = None,
    frustration_index: Optional[float] = None,
) -> CToComponent3Payload:
    """Build and emit a C→3 payload for ``mapping_row``, gated by SF-040.

    Raises ``NoRealCSessionError`` (and builds nothing) when no real C session exists for this
    mapping row. Otherwise assembles the payload via ``build_c_to_3_payload`` and proves it
    passes the committed frozen gate via ``validate_payload_against_mapping(..., "c_to_3")``
    before returning it.
    """
    mapping_model = validate_payload(mapping_row, "mapping")

    if not mapping_model.c_present or mapping_model.c_session_id is None:
        raise NoRealCSessionError(
            "SF-040: no C payload may be emitted for this mapping row "
            "(c_present is false or c_session_id is absent)."
        )

    payload = build_c_to_3_payload(
        student_id=mapping_model.student_id,
        intervention_session_id=mapping_model.intervention_session_id,
        intervention_session_number=mapping_model.intervention_session_number,
        intervention_session_date=mapping_model.intervention_session_date,
        c_session_id=mapping_model.c_session_id,
        provenance=provenance,
        aggregate=aggregate,
        telemetry_quality_status=telemetry_quality_status,
        composite_formula_version=composite_formula_version,
        learner_state=learner_state,
        state_reason=state_reason,
        engagement_components=engagement_components,
        engagement_score=engagement_score,
        frustration_components=frustration_components,
        frustration_index=frustration_index,
    )

    return validate_payload_against_mapping(payload.model_dump(), mapping_row, kind="c_to_3")
