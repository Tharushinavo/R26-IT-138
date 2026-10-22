"""Task-definition registry (Phase C2.1), keyed by ``game_task_template_id``.

Each family module exposes an ``ALL_TASKS`` tuple (one ``TaskDefinition`` per implemented
template). The registry concatenates them and dispatches strictly by
``game_task_template_id``. Duplicate template ids are rejected at import time (mirrors
``component_b_generator.samplers.registry``).
"""

from __future__ import annotations

from typing import Dict, Tuple

from . import (
    build_and_trade,
    count_and_collect,
    equal_groups_arrays,
    join_and_bridge,
    match_compare_locate,
    number_path,
    share_fairly,
    take_away_and_compare,
)
from .base import TaskDefinition  # noqa: F401  (re-exported for callers)

TASK_REGISTRY_VERSION = "c2.1-tasks-1.0.0"

_MODULES = (
    count_and_collect, number_path, match_compare_locate, build_and_trade,
    join_and_bridge, take_away_and_compare, equal_groups_arrays, share_fairly,
)

_ALL: Tuple[TaskDefinition, ...] = tuple(t for module in _MODULES for t in module.ALL_TASKS)

TASKS: Dict[str, TaskDefinition] = {t.game_task_template_id: t for t in _ALL}

if len(TASKS) != len(_ALL):
    raise RuntimeError("task registry has a duplicate template id")


def get_task_definition(game_task_template_id: str) -> TaskDefinition | None:
    return TASKS.get(game_task_template_id)


def supported_template_ids() -> Tuple[str, ...]:
    return tuple(sorted(TASKS))
