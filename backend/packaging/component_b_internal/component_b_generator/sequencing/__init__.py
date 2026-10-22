"""Sequencing features and scoring (reviewed live-safe subset).

PACKAGING NOTE (upadya-component-b-live-engine): intentionally minimal. The pinned Yass
source's ``component_b_generator/sequencing/__init__.py`` also imports ``.eligibility`` and
``.select_item``. Neither is part of the reviewed live-safe capability closure in
``backend/provenance/component-b-live-engine-reuse-map.json`` (only ``compute_features``,
``SequencingFeatures``, ``score_candidate``, ``rank_candidates``, and ``select_target`` from
``.features``/``.score`` are required) and neither is included in this package. This file
re-exports nothing; callers import ``component_b_generator.sequencing.features``, ``.score``,
``.config``, and ``.models`` directly.
"""

from __future__ import annotations
