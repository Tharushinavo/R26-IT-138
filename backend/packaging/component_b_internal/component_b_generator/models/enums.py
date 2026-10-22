"""Shared enums / literals for the Component B generator (Phase B1)."""

from __future__ import annotations

from typing import Literal, Tuple

# The seven frozen skills are the single source of truth in models.contracts.SKILLS.
# They are re-validated on catalogue load; not redefined here.

Grade = Literal[2, 3]

# Audit-only labels. Present ONLY on the audit-only learner identity, never on any
# deployable output model and never used to branch runtime behaviour (SF-039).
PopulationLabel = Literal["TD", "MLD", "DD"]
DDSubtype = Literal["magnitude", "operations", "mixed", "none"]

# Template lifecycle status as carried by the authoritative catalogue.
TemplateStatus = Literal[
    "BASELINE_ACTIVE",
    "PROPOSED_FOR_APPROVAL",
    "CALIBRATION_PENDING",
    "DEFERRED_EXTENSION",
    "RETIRED",
]

# Calibration status for values not fixed by an approved source.
CalibrationStatus = Literal["ACTIVE", "ENGINEERING_ASSUMPTION", "CALIBRATION_PENDING", "DERIVED"]

# Per-scheduled-session attendance/status (SF-040). A "missed" session produces no
# opportunity/attempt/skill-update rows later; this label is modeled here, not the skip logic.
SessionAttendanceStatus = Literal["attended", "missed"]
SESSION_ATTENDANCE_STATUSES: Tuple[str, ...] = ("attended", "missed")
