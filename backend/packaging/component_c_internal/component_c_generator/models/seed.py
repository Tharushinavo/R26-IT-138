"""C-owned seed lineage record (SPEC §22).

A local equivalent of ``component_b_generator.models.session.SeedLineage`` -- kept as a
separate, independently-defined type (not imported from Component B) so Component C's
seed machinery has no runtime dependency on B's internal model modules (SF-041:
component-kernel hidden-state ownership; each component owns its own hidden state and
equations, never reading the other's beyond the frozen boundary contracts).
"""

from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict


class CSeedLineage(BaseModel):
    """Traceable record of the deterministic seed derivation for one unit of C work.

    ``path`` is the ordered chain of ``(level, key)`` components that produced ``seed``
    from the global seed, e.g. ``(("global", "20260716"), ("learner", "STU-0001"),
    ("scheduled_intervention_slot", "3"), ("component_c_session", "2"),
    ("task_opportunity", "4"))``. Same path + global seed => same ``seed``
    (order-independent; no unordered iteration; population-label rotation never appears
    in the path, so it can never change the lineage -- SF-039).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_seed: int
    path: Tuple[Tuple[str, str], ...]
    seed: int
