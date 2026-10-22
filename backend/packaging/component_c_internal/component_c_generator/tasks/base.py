"""Shared per-template generator/evaluator contract (Phase C2.1, SPEC §11).

Each ``tasks/*.py`` family module implements one ``generate`` + one ``evaluate`` function per
template and registers them as a ``TaskDefinition`` (``tasks/registry.py`` aggregates all
family modules, mirroring ``component_b_generator.samplers.registry``).

``generate(rng, difficulty_level, params) -> GeneratedContent`` reads ONLY the seeded RNG, the
requested difficulty level, and this template's ``TemplateGenerationParams`` -- never
population, C latent state, B mastery, or policy state (SPEC §11 evaluator-purity rule applies
equally to generation content, which must be reproducible from seed + config alone).

``evaluate(correct_answer_payload, learner_action) -> bool`` reads ONLY the two arguments
given -- the instance's own stored ground truth and the submitted action -- which is what
makes ``evaluation.evaluate`` (the public pure evaluator) structurally unable to read
population/mastery/latent/policy/future information: those values are never in scope.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Dict

GenerateFn = Callable[[random.Random, int, Any], "GeneratedContent"]
EvaluateFn = Callable[[Dict[str, Any], Dict[str, Any]], bool]


class TaskGenerationTechnicalError(RuntimeError):
    """Raised after bounded invalid/ambiguous-generation retries are exhausted (SPEC §11:
    "bounded retry on invalid generation with a hard technical failure after repeated
    failure"). Never silently produces a fabricated or ambiguous instance."""


@dataclass(frozen=True)
class GeneratedContent:
    """One template's generated mathematical content, prior to instance-envelope assembly
    (identity/lineage/provenance fields are added by ``generation.build_task_instance``)."""

    difficulty_vector: Dict[str, Any]
    prompt_payload: Dict[str, Any]
    correct_answer_payload: Dict[str, Any]
    valid_action_space: Dict[str, Any]
    interactive_assets: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.interactive_assets is None:
            object.__setattr__(self, "interactive_assets", {})


@dataclass(frozen=True)
class TaskDefinition:
    game_task_template_id: str
    generate: GenerateFn
    evaluate: EvaluateFn
