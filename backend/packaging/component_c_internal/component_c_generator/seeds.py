"""Deterministic hierarchical seed management for Component C (SPEC §22).

Seed hierarchy (SPEC §22, sequential, fixed named branches):

    global -> learner -> scheduled_intervention_slot -> component_c_session
           -> task_opportunity -> game_task_instance -> gameplay_process -> attempt
           -> {substream}

Substreams (union of SPEC §11 and §22): ``selection``, ``instance_content``, ``outcome``,
``latency``, ``attempts``, ``actions``, ``inactivity``, ``scaffold``, ``policy_exploration``,
``technical_issue``. Changing one substream key must not perturb another (independent
streams off the same attempt lineage).

Guarantees (mirrors the proven ``component_b_generator.seeds`` approach; independently
implemented here so Component C carries no runtime dependency on Component B's internal
modules, per SF-041):

- same global seed + same path => identical derived seed (pure function of the path);
- no dependence on unordered set/dict iteration (paths are explicit ordered tuples);
- learner *generation order* never affects any learner's output (a learner's seeds derive
  only from ``(global_seed, student_id, ...)``, never from position);
- ``population`` / ``dd_subtype`` never appear in any path component, so population-label
  rotation cannot change any derived seed (SF-039);
- every derived seed is traceable via a ``CSeedLineage`` (the full derivation path).

Derivation uses BLAKE2b over a canonical UTF-8 encoding of the path -- stable across
processes and platforms (unlike Python's built-in ``hash``); no timestamps ever enter the
path.
"""

from __future__ import annotations

import hashlib
import random
from typing import Tuple

from .models.seed import CSeedLineage

_MASK_63 = (1 << 63) - 1

SUBSTREAMS: Tuple[str, ...] = (
    "selection",
    "instance_content",
    "outcome",
    "latency",
    "attempts",
    "actions",
    "inactivity",
    "scaffold",
    "policy_exploration",
    "technical_issue",
)


def _derive_seed(global_seed: int, path: Tuple[Tuple[str, str], ...]) -> int:
    canonical = f"{int(global_seed)}|" + "|".join(f"{level}={key}" for level, key in path)
    digest = hashlib.blake2b(canonical.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") & _MASK_63


class SeedManager:
    """Derives traceable, order-independent seeds down the fixed C hierarchy."""

    def __init__(self, global_seed: int) -> None:
        self.global_seed = int(global_seed)
        self._root: Tuple[Tuple[str, str], ...] = (("global", str(self.global_seed)),)

    def _lineage(self, path: Tuple[Tuple[str, str], ...]) -> CSeedLineage:
        return CSeedLineage(global_seed=self.global_seed, path=path, seed=_derive_seed(self.global_seed, path))

    def learner(self, student_id: str) -> CSeedLineage:
        return self._lineage(self._root + (("learner", student_id),))

    def scheduled_intervention_slot(self, student_id: str, intervention_session_number: int) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
        )
        return self._lineage(path)

    def component_c_session(
        self, student_id: str, intervention_session_number: int, c_session_index: int
    ) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
        )
        return self._lineage(path)

    def task_opportunity(
        self,
        student_id: str,
        intervention_session_number: int,
        c_session_index: int,
        task_index: int,
    ) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
            ("task_opportunity", str(int(task_index))),
        )
        return self._lineage(path)

    def game_task_instance(
        self,
        student_id: str,
        intervention_session_number: int,
        c_session_index: int,
        task_index: int,
        instance_index: int,
    ) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
            ("task_opportunity", str(int(task_index))),
            ("game_task_instance", str(int(instance_index))),
        )
        return self._lineage(path)

    def gameplay_process(
        self,
        student_id: str,
        intervention_session_number: int,
        c_session_index: int,
        task_index: int,
        instance_index: int,
        process_index: int,
    ) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
            ("task_opportunity", str(int(task_index))),
            ("game_task_instance", str(int(instance_index))),
            ("gameplay_process", str(int(process_index))),
        )
        return self._lineage(path)

    def attempt(
        self,
        student_id: str,
        intervention_session_number: int,
        c_session_index: int,
        task_index: int,
        instance_index: int,
        process_index: int,
        attempt_index: int,
    ) -> CSeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
            ("task_opportunity", str(int(task_index))),
            ("game_task_instance", str(int(instance_index))),
            ("gameplay_process", str(int(process_index))),
            ("attempt", str(int(attempt_index))),
        )
        return self._lineage(path)

    def substream(
        self,
        student_id: str,
        intervention_session_number: int,
        c_session_index: int,
        task_index: int,
        instance_index: int,
        process_index: int,
        attempt_index: int,
        substream_name: str,
    ) -> CSeedLineage:
        if substream_name not in SUBSTREAMS:
            raise ValueError(f"substream_name must be one of {SUBSTREAMS}, got {substream_name!r}")
        path = self._root + (
            ("learner", student_id),
            ("scheduled_intervention_slot", str(int(intervention_session_number))),
            ("component_c_session", str(int(c_session_index))),
            ("task_opportunity", str(int(task_index))),
            ("game_task_instance", str(int(instance_index))),
            ("gameplay_process", str(int(process_index))),
            ("attempt", str(int(attempt_index))),
            ("substream", substream_name),
        )
        return self._lineage(path)


def rng_from(lineage: CSeedLineage) -> random.Random:
    """A deterministic stdlib RNG seeded from a lineage (stable, dependency-free)."""
    return random.Random(lineage.seed)


def derive_child_lineage(parent: CSeedLineage, level: str, key: str) -> CSeedLineage:
    """Append one ``(level, key)`` component to an existing lineage and re-derive the seed.

    Pure function of ``(parent.global_seed, parent.path, level, key)`` -- for branches not
    covered by the fixed named methods above. Same inputs => same child seed.
    """
    path = parent.path + ((str(level), str(key)),)
    return CSeedLineage(global_seed=parent.global_seed, path=path, seed=_derive_seed(parent.global_seed, path))
