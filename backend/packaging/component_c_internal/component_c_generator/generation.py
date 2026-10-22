"""Deterministic Component C task-instance generation engine (Phase C2.1, SPEC §11).

Builds a :class:`GameTaskInstance` for one (template, task_index) pair from a **task-instance
child lineage** branched off the caller's task-opportunity seed lineage, so instance content
is reproducible and independent of learner/cohort/generation order -- the same pattern as
``component_b_generator.generation.task_instances``. Unsupported templates are never
fabricated: :func:`build_task_instance` raises ``UnsupportedTemplateError``.

Generation invariants (SPEC §11): bounded template scope; deterministic mathematical truth;
valid action space; no ambiguous correct answer; bounded retry on invalid generation with a
hard technical failure after repeated failure (``TaskGenerationTechnicalError``); complete
seed lineage; no population in ids or seeds.
"""

from __future__ import annotations

from typing import Optional

from .catalogue.loaded_models import LoadedGameTaskTemplate
from .generation_config import CGenerationConfig
from .models.task_instance import GameTaskInstance
from .seeds import CSeedLineage, derive_child_lineage, rng_from
from .tasks.base import TaskGenerationTechnicalError
from .tasks.registry import get_task_definition

GENERATOR_VERSION = "c2.1-generation-1.0.0"

# SPEC §6.2: baseline scaffold state before any C4 adaptation runs (Catalogue §2.4: C0 =
# "no_scaffold" / "Normal task presentation") -- not a science value, the documented default.
_BASELINE_SCAFFOLD_STATE = "C0"

# SPEC §11: the generation-side half of the "bounded retry ... hard technical failure after
# repeated failure" rule. Structural wording, not a catalogue/governance fact.
_FAILURE_CONDITION = "technical_status=FAILED after bounded invalid/ambiguous-generation retries are exhausted"
_COMPLETION_CONDITION = "action_submitted"  # SPEC §9.1 global event vocabulary (Appendix M)


class UnsupportedTemplateError(RuntimeError):
    """Raised when no Phase-C2.1 generator/evaluator exists for a template id."""


def build_task_instance(
    template: LoadedGameTaskTemplate,
    seed_lineage: CSeedLineage,
    grade: int,
    difficulty_level: int,
    student_id: str,
    c_session_id: str,
    task_index: int,
    catalogue_version: str,
    config: CGenerationConfig,
) -> GameTaskInstance:
    """Build one validated task instance for a supported, active template.

    ``seed_lineage`` must already be the task-opportunity-level lineage for this task index
    (``SeedManager.task_opportunity(...)``); this function branches its own
    ``game_task_instance`` child lineage from it. ``grade`` is the learner's actual session
    grade and must be one of ``template.eligible_grades`` (the grade gate is enforced by
    ``eligibility.decide_activation`` upstream; this is a defensive re-check, never silently
    substituted). Raises ``UnsupportedTemplateError`` if no Phase-C2.1 strategy is
    implemented, and ``TaskGenerationTechnicalError`` if bounded retries are exhausted (SPEC
    §11).
    """
    task_def = get_task_definition(template.game_task_template_id)
    if task_def is None:
        raise UnsupportedTemplateError(
            f"no Phase-C2.1 generator/evaluator for template {template.game_task_template_id!r}"
        )
    if grade not in template.eligible_grades:
        raise ValueError(
            f"grade {grade} is not eligible for template {template.game_task_template_id!r} "
            f"(eligible_grades={template.eligible_grades})"
        )
    params = config.params_for(template.game_task_template_id)

    instance_lineage = derive_child_lineage(seed_lineage, "game_task_instance", "1")
    rng = rng_from(instance_lineage)

    attempts = 0
    last_error: Optional[Exception] = None
    content = None
    while attempts < params.max_generation_attempts:
        attempts += 1
        try:
            content = task_def.generate(rng, difficulty_level, params)
            break
        except TaskGenerationTechnicalError as exc:
            last_error = exc
            break  # the per-template generator already exhausted its own bounded retries
        except (ValueError, ArithmeticError) as exc:
            last_error = exc
            continue

    if content is None:
        raise TaskGenerationTechnicalError(
            f"template {template.game_task_template_id!r}: generation failed after "
            f"{attempts} attempt(s): {last_error!r}"
        )

    representation_mode = rng.choice(template.representations)

    instance_id = f"{c_session_id}-T{task_index:03d}-X001"

    return GameTaskInstance(
        game_family_id=template.game_family_id,
        game_task_template_id=template.game_task_template_id,
        game_task_instance_id=instance_id,
        template_version=catalogue_version,
        catalogue_version=catalogue_version,
        generator_version=GENERATOR_VERSION,
        seed_lineage=instance_lineage,
        student_id=student_id,
        c_session_id=c_session_id,
        task_index=task_index,
        skill_id=template.primary_skill_ids[0],
        curriculum_node_id=template.curriculum_node_ids[0],
        grade_scope=grade,
        difficulty_level=difficulty_level,
        difficulty_vector=dict(content.difficulty_vector),
        functional_role=template.functional_role,
        representation_mode=representation_mode,
        prompt_payload=dict(content.prompt_payload),
        interactive_assets=dict(content.interactive_assets),
        correct_answer_payload=dict(content.correct_answer_payload),
        correctness_function_id=f"{template.game_task_template_id}.correctness.v1",
        valid_action_space=dict(content.valid_action_space),
        completion_condition=_COMPLETION_CONDITION,
        failure_condition=_FAILURE_CONDITION,
        scaffold_state=_BASELINE_SCAFFOLD_STATE,
        recovery_parent_instance_id=None,
        technical_status="OK",
    )
