"""Phase B5.0 — aggregation contracts (SPEC §6.11). Shape only, no aggregation logic.

Declares what the B5.1 aggregator will consume and produce so downstream adapters
(B5.2 B->C, B5.3 B->3) can be planned against a stable interface:

- input: ordered ``BOpportunityResponseSummary`` rows (:mod:`component_b_generator.models.behaviour`)
  and ``SkillMasteryUpdate`` rows (:mod:`component_b_generator.models.opportunity`) for one
  attended B-session, keyed by ``session_id`` / ``b_session_index``.
- output: one :class:`component_b_generator.models.opportunity.SessionSummary` row per
  scheduled session (``attended`` with populated totals, or ``missed`` with none — SF-040).

No aggregation math, folding, or adapter/serialization logic is implemented here.
"""

from __future__ import annotations

B5_VERSION = "b5-1.0.0"
