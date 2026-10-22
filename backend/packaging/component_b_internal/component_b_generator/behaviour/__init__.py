"""Exact catalogue hint lookup only (reviewed live-safe subset of Phase B2B behaviour).

PACKAGING NOTE (upadya-component-b-live-engine): intentionally minimal. The pinned Yass
source's ``component_b_generator/behaviour/__init__.py`` eagerly imports
``.attempt_loop``, ``.first_attempt``, ``.latency``, ``.initialization``, ``.wrong_answers``,
``.derivation``, ``.seeds``, and ``.validation`` — all synthetic/offline learner-response
generation modules that are explicitly prohibited from the application (see
``backend/provenance/component-b-live-engine-reuse-map.json``:
``explicitly_prohibited_from_application``). None of those submodules exist in this package;
only ``hints.py`` (exact catalogue hint lookup) is included. This file re-exports nothing so
that ``import component_b_generator.behaviour`` never has to reach a module this package does
not contain. Callers import ``component_b_generator.behaviour.hints`` directly.
"""

from __future__ import annotations
