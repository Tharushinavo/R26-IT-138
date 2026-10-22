"""Shared sampler types (Phase B2A)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple


@dataclass(frozen=True)
class SampledContent:
    """The deterministic output of a sampler: structured operands + renderable prompt data."""

    operands: Dict[str, Any]
    prompt: Dict[str, Any]


@dataclass(frozen=True)
class ItemSampler:
    """A registered strategy for one implemented item template.

    ``sample`` is a pure function of ``(rng, grade)``. ``guard_ids`` is the explicit guard plan
    that the generation layer must apply to every instance of this template; each id maps to a
    guard implementation in :mod:`component_b_generator.generation.guards`.
    """

    item_template_id: str
    task_type: str
    skill_id: str
    eligible_grades: Tuple[int, ...]
    response_format: str
    sample: Callable[[random.Random, int], SampledContent]
    guard_ids: Tuple[str, ...] = field(default_factory=tuple)
    # Required number of distinct mathematical distractor candidates for this template
    # (multiple-choice policy). Relation/binary formats need fewer; see distractors.registry.
    required_distractors: int = 3
    # Whether the answer is an integer (enables generic off-by-k distractor fillers).
    integer_answer: bool = True


_MAX_REJECTION_TRIES = 1000


def rejection_sample(rng: random.Random, draw: Callable[[], Any], accept: Callable[[Any], bool]) -> Any:
    """Deterministic bounded rejection sampling. Raises if no draw is accepted in the budget
    (never expected for the reviewed envelopes; a defect would surface loudly rather than loop)."""
    for _ in range(_MAX_REJECTION_TRIES):
        candidate = draw()
        if accept(candidate):
            return candidate
    raise RuntimeError("rejection sampling exhausted its budget — sampler envelope defect")
