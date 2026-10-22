"""Activation, deterministic task construction, and generation errors/guards.

PACKAGING NOTE (upadya-component-b-live-engine): intentionally minimal. The pinned Yass
source's ``component_b_generator/generation/__init__.py`` imports ``.item_opportunities``,
which imports ``..cohort.builder.CohortMember`` — cohort construction is explicitly
prohibited from the application (see
``backend/provenance/component-b-live-engine-reuse-map.json``:
``explicitly_prohibited_from_application``). ``item_opportunities.py`` and the ``cohort``
package are not included in this package. This file re-exports nothing; callers import
``component_b_generator.generation.activation``, ``.task_instances``, ``.errors``, and
``.guards`` directly.
"""

from __future__ import annotations
