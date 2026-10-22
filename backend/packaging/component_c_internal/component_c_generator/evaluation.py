"""Pure Component C task evaluator (Phase C2.1, SPEC §11).

``evaluate(task_instance, learner_action)`` is pure: its signature admits only the instance
already generated (which carries its own deterministic ``correct_answer_payload`` -- never
re-derived from population, C latent state, B mastery, or policy state) and the learner's
submitted action. There is no other parameter, no module-level mutable state read, and no
clock/RNG call anywhere in this module -- the same ``(task_instance, learner_action)`` pair
always produces the same ``EvaluationResult`` (SPEC §11: "Stored correctness always equals
evaluator output").
"""

from __future__ import annotations

from typing import Any, Dict

from .models.task_instance import EvaluationResult, GameTaskInstance
from .tasks.registry import get_task_definition


class UnknownTemplateError(RuntimeError):
    """Raised when a task instance references a template with no registered evaluator."""


def evaluate(task_instance: GameTaskInstance, learner_action: Dict[str, Any]) -> EvaluationResult:
    """Pure evaluation: reads only ``task_instance`` and ``learner_action``."""
    task_def = get_task_definition(task_instance.game_task_template_id)
    if task_def is None:
        raise UnknownTemplateError(
            f"no Phase-C2.1 evaluator for template {task_instance.game_task_template_id!r}"
        )
    is_correct = task_def.evaluate(task_instance.correct_answer_payload, learner_action)
    return EvaluationResult(
        game_task_instance_id=task_instance.game_task_instance_id,
        game_task_template_id=task_instance.game_task_template_id,
        correctness_function_id=task_instance.correctness_function_id,
        learner_action=dict(learner_action),
        is_correct=bool(is_correct),
    )
