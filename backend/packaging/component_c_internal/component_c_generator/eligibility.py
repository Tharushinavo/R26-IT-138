"""Grade gate + deferred fail-closed activation for Component C templates (Phase C2.1).

Mirrors ``component_b_generator.generation.activation.decide_activation`` /
``component_b_generator.sequencing.eligibility``: an explicit decision over multiple inputs,
never inferred solely from the absence of the word ``RETIRED``. A template is active for a
requested grade only when it is grade-eligible (per the loader's normalized grade gate),
curriculum-active (``BASELINE_ACTIVE`` or ``BASELINE_CONDITIONAL`` -- never
``DEFERRED_EXTENSION`` or ``RETIRED``), and generation-supported (a template registry entry
exists, Phase C2.1 concern). Genuinely ambiguous cases are reported (``active`` False with an
explanatory ``reason``) rather than resolved by invention.
"""

from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict

from .catalogue.loaded_models import LoadedCatalogue, LoadedGameTaskTemplate

RECOGNIZED_CATALOGUE_STATUSES = ("PROPOSED_FOR_APPROVAL", "BASELINE_ACTIVE", "APPROVED", "ACTIVE")


class ActivationDecision(BaseModel):
    """Explicit runtime-activation decision for one template (never inferred solely from the
    absence of ``RETIRED``). Records every input that produced ``active``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    game_task_template_id: str
    recognized: bool
    generation_supported: bool
    grade_eligible: bool
    curriculum_active: bool
    catalogue_status_ok: bool
    calibration_restricted: bool
    active: bool
    reason: str


def decide_activation(
    template: LoadedGameTaskTemplate,
    supported_template_ids: Tuple[str, ...],
    grade: int,
    catalogue_status: str,
) -> ActivationDecision:
    recognized = True  # a loaded LoadedGameTaskTemplate is, by construction, a recognized id
    generation_supported = template.game_task_template_id in supported_template_ids
    grade_eligible = template.is_eligible_for_grade(grade)
    curriculum_active = template.is_active()  # BASELINE_ACTIVE / BASELINE_CONDITIONAL only
    catalogue_status_ok = str(catalogue_status).upper() in RECOGNIZED_CATALOGUE_STATUSES
    # The grade gate encodes the resolved eligible grades already; a CALIBRATION_PENDING gate
    # only restricts grades OUTSIDE that resolved set. A request for a grade that IS in
    # eligible_grades is not calibration-restricted (mirrors B's decide_activation).
    calibration_restricted = template.grade_gate_status == "CALIBRATION_PENDING" and not grade_eligible

    active = (
        recognized
        and generation_supported
        and grade_eligible
        and curriculum_active
        and catalogue_status_ok
        and not calibration_restricted
    )

    if active:
        reason = "active: recognized, generation-supported, grade-eligible, curriculum-active, status ok"
    elif not generation_supported:
        reason = "inactive: no implemented Phase-C2.1 generator/evaluator for this template"
    elif not grade_eligible and calibration_restricted:
        reason = "inactive: requested grade falls in a CALIBRATION_PENDING (unresolved) grade range"
    elif not grade_eligible:
        reason = f"inactive: template not grade-eligible for grade {grade}"
    elif not curriculum_active:
        reason = "inactive: template is RETIRED or DEFERRED_EXTENSION"
    elif not catalogue_status_ok:
        reason = f"inactive: unrecognized catalogue status {catalogue_status!r}"
    else:
        reason = "inactive: ambiguous -- reported rather than resolved by invention"

    return ActivationDecision(
        game_task_template_id=template.game_task_template_id,
        recognized=recognized,
        generation_supported=generation_supported,
        grade_eligible=grade_eligible,
        curriculum_active=curriculum_active,
        catalogue_status_ok=catalogue_status_ok,
        calibration_restricted=calibration_restricted,
        active=active,
        reason=reason,
    )


def eligible_templates(
    catalogue: LoadedCatalogue,
    grade: int,
    supported_template_ids: Tuple[str, ...],
) -> Tuple[LoadedGameTaskTemplate, ...]:
    """The eligible template set for one grade: grade gate + deferred fail-closed +
    generation-support only. Deterministic, canonically ordered by template id -- no seed, no RNG.
    """
    eligible = []
    for template in catalogue.templates:
        decision = decide_activation(template, supported_template_ids, grade, catalogue.catalogue_status)
        if decision.active:
            eligible.append(template)
    return tuple(sorted(eligible, key=lambda t: t.game_task_template_id))
