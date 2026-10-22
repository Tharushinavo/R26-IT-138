"""The C→3 adapter (Phase C5.1, SPEC §21) -- ASSEMBLES the committed oracle payload from the
committed C5.0 science outputs. This module computes nothing: every count/rate/timing field
comes from ``aggregation.derive.CSessionAggregate``; every composite/state field comes from the
committed ``composites`` package. It imports NONE of ``AdaptationDecision``'s internal fields,
the ``InternalRLReward`` model, or ``BToCMasteryPayload`` -- so there is no code path through
which an RL-internal, B-internal, or generator-latent value could ever reach the payload it
assembles (the no-leak audit tests confirm this by inspection of this module's imports/source in
addition to the field-level checks against the committed
``validators.contract_validators.C_TO_3_PROHIBITED_FIELDS``).

DETERMINISM (SPEC §22): ``production_timestamp`` is a required, caller-supplied field on
``CToComponent3Provenance`` -- this module never calls ``datetime.now()``, ``time.time()``, or
``hash()``, and derives no seed from a timestamp. Identical inputs always assemble a
byte-identical payload.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from models.contracts import CToComponent3Payload, EngagementComponents, FrustrationComponents

from ..aggregation.models import CSessionAggregate
from ..composites.engagement_frustration import CompositeFormulaVersion
from ..composites.learner_state import StateReason, TelemetryQualityStatus
from ..models.enums import LearnerState
from .inputs import CToComponent3Provenance

ADAPTER_VERSION = "c5.1-c-to-3-adapter-1.0.0"

SCHEMA_VERSION = "3.0"
COMPONENT_SOURCE = "C"
STATE_RULE_VERSION = "C-LS-v1"


class TelemetryQualityGatingError(ValueError):
    """Raised when the caller-supplied composite/state inputs disagree with the null-gating
    SPEC §20/C Parameters §12 requires for the given ``telemetry_quality_status`` (mirrors, but
    is checked BEFORE, the committed oracle's own ``C3-NL-01``/``C3-TECH-01`` rejection)."""


def _check_null_gating(
    telemetry_quality_status: TelemetryQualityStatus,
    learner_state: Optional[LearnerState],
    engagement_components: Optional[EngagementComponents],
    engagement_score: Optional[float],
    frustration_components: Optional[FrustrationComponents],
    frustration_index: Optional[float],
) -> None:
    fields = (learner_state, engagement_components, engagement_score, frustration_components, frustration_index)
    if telemetry_quality_status == "complete":
        if any(f is None for f in fields):
            raise TelemetryQualityGatingError(
                "telemetry_quality_status=='complete' requires all of "
                "learner_state/engagement_components/engagement_score/frustration_components/"
                "frustration_index to be non-null (SPEC §20/C Parameters §12)."
            )
    else:
        if any(f is not None for f in fields):
            raise TelemetryQualityGatingError(
                f"telemetry_quality_status=={telemetry_quality_status!r} requires "
                "learner_state/engagement_components/engagement_score/frustration_components/"
                "frustration_index to all be null (SPEC §20/C Parameters §12; C3-NL-01/C3-TECH-01)."
            )


def build_c_to_3_payload(
    *,
    student_id: str,
    intervention_session_id: str,
    intervention_session_number: int,
    intervention_session_date: date,
    c_session_id: str,
    provenance: CToComponent3Provenance,
    aggregate: CSessionAggregate,
    telemetry_quality_status: TelemetryQualityStatus,
    composite_formula_version: CompositeFormulaVersion,
    learner_state: Optional[LearnerState],
    state_reason: StateReason,
    engagement_components: Optional[EngagementComponents],
    engagement_score: Optional[float],
    frustration_components: Optional[FrustrationComponents],
    frustration_index: Optional[float],
) -> CToComponent3Payload:
    """Assemble the committed C0 ``CToComponent3Payload`` from C5.0 outputs.

    Raises ``TelemetryQualityGatingError`` if the caller's null-gating disagrees with
    ``telemetry_quality_status`` (checked here for a clear error message; the committed oracle's
    own validator enforces the same rule and is the final authority -- see C3-NL-01/C3-TECH-01
    in ``models.contracts.CToComponent3Payload``).
    """
    _check_null_gating(
        telemetry_quality_status, learner_state, engagement_components, engagement_score,
        frustration_components, frustration_index,
    )

    return CToComponent3Payload(
        schema_version=SCHEMA_VERSION,
        student_id=student_id,
        intervention_session_id=intervention_session_id,
        intervention_session_number=intervention_session_number,
        intervention_session_date=intervention_session_date,
        c_session_id=c_session_id,
        c_session_number=provenance.c_session_number,
        component_source=COMPONENT_SOURCE,
        production_timestamp=provenance.production_timestamp,
        policy_version=provenance.policy_version,
        composite_formula_version=composite_formula_version,
        state_rule_version=STATE_RULE_VERSION,
        telemetry_quality_status=telemetry_quality_status,
        session_technical_issue_flag=aggregate.session_technical_issue_flag,
        task_opportunity_count=aggregate.task_opportunity_count,
        completed_task_count=aggregate.completed_task_count,
        correct_task_count=aggregate.correct_task_count,
        total_attempt_count=aggregate.total_attempt_count,
        accuracy_rate=aggregate.accuracy_rate,
        avg_attempts_per_task=aggregate.avg_attempts_per_task,
        task_completion_rate=aggregate.task_completion_rate,
        inactivity_periods=aggregate.inactivity_periods,
        inactive_time_sec=aggregate.inactive_time_sec,
        session_duration_sec=aggregate.session_duration_sec,
        time_in_target_band_sec=aggregate.time_in_target_band_sec,
        consecutive_error_max=aggregate.consecutive_error_max,
        difficulty_floor_hits=aggregate.difficulty_floor_hits,
        quit_after_error=aggregate.quit_after_error,
        safety_override_count=aggregate.safety_override_count,
        c_mean_game_task_latency_sec=aggregate.c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=aggregate.c_median_game_task_latency_sec,
        current_difficulty_level=aggregate.current_difficulty_level,
        difficulty_trend=aggregate.difficulty_trend,
        engagement_components=engagement_components,
        engagement_score=engagement_score,
        frustration_components=frustration_components,
        frustration_index=frustration_index,
        learner_state=learner_state,
        state_reason=state_reason,
    )
