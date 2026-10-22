"""Sampler registry (Phase B2A / B2A.2), keyed by ``item_template_id``.

Each module exposes an ``ALL_SAMPLERS`` tuple (one :class:`ItemSampler` per implemented
template). The registry concatenates them and dispatches strictly by ``item_template_id`` — the
unit carried on every ``GeneratedItemOpportunity``. Duplicate template ids are rejected at
import time. ``task_type`` is intentionally NOT required to be unique: several templates share a
task type while differing in grade limits, operand ranges, regroup/borrow requirements,
representation, and distractor rules (e.g. ADD01 vs ADD03), so no ``by_task_type`` 1:1 view is
offered — resolve by template id.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .base import ItemSampler, SampledContent  # noqa: F401  (re-exported for callers)
from . import addition, counting, division, multiplication, number_sense, place_value, subtraction

# Bumped for the B2A.2 catalogue coverage expansion (7 -> 29 implemented templates).
SAMPLER_REGISTRY_VERSION = "b2a2-1.0.0"

_MODULES = (counting, number_sense, place_value, addition, subtraction, multiplication, division)

_ALL: Tuple[ItemSampler, ...] = tuple(s for module in _MODULES for s in module.ALL_SAMPLERS)

# item_template_id -> ItemSampler
SAMPLERS: Dict[str, ItemSampler] = {s.item_template_id: s for s in _ALL}

if len(SAMPLERS) != len(_ALL):
    raise RuntimeError("sampler registry has a duplicate template id")


def get_sampler(item_template_id: str) -> ItemSampler | None:
    return SAMPLERS.get(item_template_id)


def supported_template_ids() -> Tuple[str, ...]:
    return tuple(sorted(SAMPLERS))
