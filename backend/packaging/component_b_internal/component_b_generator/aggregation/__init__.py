"""component_b_generator.aggregation

Internal-record aggregation to b_session_summaries (SPEC §6.11).

Phase B5.0 established the version constant and shape. Phase B5.1 adds ``session.py``
(``aggregate_session`` and its result/roll-up records) — deliberately not re-exported here;
import directly from ``component_b_generator.aggregation.session`` (no B->C/B->3 adapter or
serialization surface exists yet).
"""

from __future__ import annotations

from .contracts import B5_VERSION

__all__ = ["B5_VERSION"]
