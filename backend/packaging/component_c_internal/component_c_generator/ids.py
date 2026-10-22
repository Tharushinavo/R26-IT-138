"""Deterministic C id builders + patterns (SPEC §6.1).

Patterns mirror the frozen types in the shared ``Implementation_v1.0/models/contracts.py``
(``StudentId``, ``InterventionSessionId``, ``CSessionId``) -- duplicated here as plain
``re`` constants (the same approach ``component_b_generator/models/identity.py`` uses for
``STUDENT_ID_RE``) so this module has no import-time dependency on the contracts module for
simple string validation. No ``hash()``, no timestamps: every id is a pure function of its
integer components.
"""

from __future__ import annotations

import re

STUDENT_ID_RE = re.compile(r"^STU-[0-9]{4}$")
INTERVENTION_SESSION_ID_RE = re.compile(r"^STU-[0-9]{4}-I-[0-9]{3}$")
C_SESSION_ID_RE = re.compile(r"^STU-[0-9]{4}-C-[0-9]{3}$")


def build_student_id(cohort_index: int) -> str:
    """Deterministic id: 1 -> STU-0001 (index is 1-based)."""
    if cohort_index < 1:
        raise ValueError("cohort_index must be >= 1")
    return f"STU-{cohort_index:04d}"


def build_intervention_session_id(student_id: str, intervention_session_number: int) -> str:
    if not STUDENT_ID_RE.match(student_id):
        raise ValueError(f"student_id must match {STUDENT_ID_RE.pattern!r}, got {student_id!r}")
    if intervention_session_number < 1:
        raise ValueError("intervention_session_number must be >= 1")
    return f"{student_id}-I-{intervention_session_number:03d}"


def build_c_session_id(student_id: str, c_session_index: int) -> str:
    if not STUDENT_ID_RE.match(student_id):
        raise ValueError(f"student_id must match {STUDENT_ID_RE.pattern!r}, got {student_id!r}")
    if c_session_index < 1:
        raise ValueError("c_session_index must be >= 1")
    return f"{student_id}-C-{c_session_index:03d}"


def is_valid_student_id(value: str) -> bool:
    return bool(STUDENT_ID_RE.match(value))


def is_valid_intervention_session_id(value: str) -> bool:
    return bool(INTERVENTION_SESSION_ID_RE.match(value))


def is_valid_c_session_id(value: str) -> bool:
    return bool(C_SESSION_ID_RE.match(value))


def student_prefix(identifier: str) -> str:
    """The ``STU-####`` prefix shared by every session id derived from one student."""
    return identifier[:8]
