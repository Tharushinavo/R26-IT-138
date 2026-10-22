"""BKT predict/posterior/update, Guess-Guard, and certification (reviewed live-safe subset).

PACKAGING NOTE (upadya-component-b-live-engine): intentionally minimal. The pinned Yass
source's ``component_b_generator/bkt/__init__.py`` also imports ``.orchestrator``
(``update_skill_mastery``, ``SkillMismatchError``), which is not part of the reviewed
live-safe capability closure in
``backend/provenance/component-b-live-engine-reuse-map.json`` and is not included in this
package. This file re-exports nothing; callers import ``component_b_generator.bkt.update``,
``.guess_guard``, ``.certification``, ``.config``, and ``.state`` directly.
"""

from __future__ import annotations
