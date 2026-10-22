"""Explicit runtime-activation policy (Phase B2A).

Activation is an explicit decision over multiple inputs — never inferred solely from the
absence of the word ``RETIRED`` (SPEC / catalogue §12). A template is active for a requested
grade only when it is recognized, implementation-supported, grade-eligible, curriculum-active
(not RETIRED / not DEFERRED), the catalogue status is recognized, and no calibration
restriction applies to the requested grade. Genuinely ambiguous cases are reported (``active``
False with an explanatory ``reason``) rather than resolved by invention.
"""

from __future__ import annotations

from typing import Tuple

from ..models.catalogue import ItemTemplate
from ..models.task_instance import ActivationDecision

RECOGNIZED_CATALOGUE_STATUSES = (
    "PROPOSED_FOR_APPROVAL",
    "BASELINE_ACTIVE",
    "APPROVED",
    "ACTIVE",
)


def decide_activation(
    template: ItemTemplate,
    supported_template_ids: Tuple[str, ...],
    grade: int,
    catalogue_status: str,
) -> ActivationDecision:
    recognized = True  # a loaded ItemTemplate is, by construction, a recognized catalogue id
    implementation_supported = template.item_template_id in supported_template_ids
    grade_eligible = template.is_eligible_for_grade(grade)  # type: ignore[arg-type]
    curriculum_active = template.is_active()  # not RETIRED / not DEFERRED
    catalogue_status_ok = str(catalogue_status).upper() in RECOGNIZED_CATALOGUE_STATUSES
    # The grade gate encodes the resolved eligible grades already; a CALIBRATION_PENDING gate
    # only restricts grades OUTSIDE that resolved set (e.g. NS04's pending Grade-2 range). So a
    # request for a grade that IS in eligible_grades is not calibration-restricted.
    calibration_restricted = (
        template.grade_gate_status == "CALIBRATION_PENDING" and not grade_eligible
    )

    active = (
        recognized
        and implementation_supported
        and grade_eligible
        and curriculum_active
        and catalogue_status_ok
        and not calibration_restricted
    )

    if active:
        reason = "active: recognized, supported, grade-eligible, curriculum-active, status ok"
    elif not implementation_supported:
        reason = "inactive: no implemented Phase-B2A strategy for this template"
    elif not grade_eligible and calibration_restricted:
        reason = "inactive: requested grade falls in a CALIBRATION_PENDING (unresolved) grade range"
    elif not grade_eligible:
        reason = f"inactive: template not grade-eligible for grade {grade}"
    elif not curriculum_active:
        reason = "inactive: template is RETIRED or DEFERRED"
    elif not catalogue_status_ok:
        reason = f"inactive: unrecognized catalogue status {catalogue_status!r}"
    else:
        reason = "inactive: ambiguous — reported rather than resolved by invention"

    return ActivationDecision(
        item_template_id=template.item_template_id,
        recognized=recognized,
        implementation_supported=implementation_supported,
        grade_eligible=grade_eligible,
        curriculum_active=curriculum_active,
        catalogue_status_ok=catalogue_status_ok,
        calibration_restricted=calibration_restricted,
        active=active,
        reason=reason,
    )
