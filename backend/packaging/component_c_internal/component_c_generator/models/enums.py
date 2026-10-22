"""Shared enums/literals for the Component C generator (Phase C1, SPEC §6/§7).

The seven frozen skills remain the single source of truth in ``models.contracts.SKILLS``
(shared, frozen module); not redefined here.
"""

from __future__ import annotations

from typing import Literal, Tuple

# SPEC §6.1: grade_level enum on CSessionRequest.
GradeLevel = Literal["grade_2", "grade_3"]

# SPEC §6.1: session_mode enum on CSessionRequest.
SessionMode = Literal["combined", "c_only"]

# Build plan (C1 row) / cold-start assessment §8-§9: the C-owned familiarization window.
# C-internal only -- never derived from, or exported to, Component B (no B-derived
# readiness field anywhere on a C-facing model).
SessionPhase = Literal["familiarization", "mastery_driven", "c_only"]

# SPEC §6.1: policy_mode enum on CSessionRequest.
PolicyMode = Literal["rule_based_baseline", "q_learning_offline", "frozen_q_evaluation"]

# SPEC §8.3: shared observable session context is attendance/partial/technical ONLY.
AttendanceStatus = Literal["attended", "partial", "missed"]

# Game-Task Catalogue §2.2 controlled vocabulary (template lifecycle).
TemplateStatus = Literal[
    "BASELINE_ACTIVE",
    "BASELINE_CONDITIONAL",
    "DEFERRED_EXTENSION",
    "RETIRED",
]

# Game-Task Catalogue §2.3 controlled vocabulary.
FunctionalRole = Literal["MAIN", "SUPPORT", "MAIN_SUPPORT", "RECOVERY_ONLY"]

# Game-Task Catalogue §2.4 controlled vocabulary (C scaffold ladder, C0-C4).
ScaffoldLevel = Literal["C0", "C1", "C2", "C3", "C4"]
SCAFFOLD_LEVELS: Tuple[str, ...] = ("C0", "C1", "C2", "C3", "C4")

# Deterministic learner state (C-LS-v1), reused here only as a typed reference for
# CLocalLearnerState.last_complete_learner_state -- the formula/rule machinery itself
# is a C5 concern (models.contracts.CToComponent3Payload already owns the export type).
LearnerState = Literal["engaged", "productive_struggle", "overloaded", "disengaged"]
