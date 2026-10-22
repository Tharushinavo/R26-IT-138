"""Deterministic hierarchical seed management (SPEC §8).

Seed hierarchy:
    global_seed -> learner_seed -> scheduled_session_seed
                -> component_b_session_seed -> item_opportunity_seed

Guarantees:
- same global seed + same path => identical derived seed (pure function of the path);
- no dependence on unordered set/dict iteration (paths are explicit ordered tuples);
- learner *generation order* never affects any learner's output (a learner's seeds derive
  only from ``(global_seed, student_id, ...)``, never from position);
- every derived seed is traceable via a ``SeedLineage`` (the full derivation path).

Derivation uses BLAKE2b over a canonical UTF-8 encoding of the path — stable across
processes and platforms (unlike Python's built-in ``hash``).
"""

from __future__ import annotations

import hashlib
import random
from typing import Tuple

from .models.session import SeedLineage

_MASK_63 = (1 << 63) - 1


def _derive_seed(global_seed: int, path: Tuple[Tuple[str, str], ...]) -> int:
    canonical = f"{int(global_seed)}|" + "|".join(f"{level}={key}" for level, key in path)
    digest = hashlib.blake2b(canonical.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") & _MASK_63


class SeedManager:
    """Derives traceable, order-independent seeds down the fixed hierarchy."""

    def __init__(self, global_seed: int) -> None:
        self.global_seed = int(global_seed)
        self._root: Tuple[Tuple[str, str], ...] = (("global", str(self.global_seed)),)

    def _lineage(self, path: Tuple[Tuple[str, str], ...]) -> SeedLineage:
        return SeedLineage(global_seed=self.global_seed, path=path, seed=_derive_seed(self.global_seed, path))

    def learner(self, student_id: str) -> SeedLineage:
        return self._lineage(self._root + (("learner", student_id),))

    def scheduled_session(self, student_id: str, scheduled_session_number: int) -> SeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_session", str(int(scheduled_session_number))),
        )
        return self._lineage(path)

    def component_b_session(self, student_id: str, scheduled_session_number: int, b_session_index: int) -> SeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_session", str(int(scheduled_session_number))),
            ("component_b_session", str(int(b_session_index))),
        )
        return self._lineage(path)

    def item_opportunity(
        self,
        student_id: str,
        scheduled_session_number: int,
        b_session_index: int,
        item_index: int,
    ) -> SeedLineage:
        path = self._root + (
            ("learner", student_id),
            ("scheduled_session", str(int(scheduled_session_number))),
            ("component_b_session", str(int(b_session_index))),
            ("item_opportunity", str(int(item_index))),
        )
        return self._lineage(path)


def rng_from(lineage: SeedLineage) -> random.Random:
    """A deterministic stdlib RNG seeded from a lineage (stable, dependency-free)."""
    return random.Random(lineage.seed)


def derive_child_lineage(parent: SeedLineage, level: str, key: str) -> SeedLineage:
    """Append one ``(level, key)`` component to an existing lineage and re-derive the seed.

    Pure function of ``(parent.global_seed, parent.path, level, key)`` — used by Phase B2A to
    branch a **task-instance content seed** off an item-opportunity seed so that content
    sampling has its own traceable, order-independent stream (distinct from the seed that
    drove template *selection*). Same inputs => same child seed.
    """
    path = parent.path + ((str(level), str(key)),)
    return SeedLineage(global_seed=parent.global_seed, path=path, seed=_derive_seed(parent.global_seed, path))
