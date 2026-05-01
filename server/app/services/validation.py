"""Data Processing Module (plan Section 5.2).

Validates and cleans raw interaction data received from the mobile app.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_ERROR_TYPES = {"none", "calculation", "conceptual", "careless", "unknown"}
VALID_TOPICS = {
    "counting", "number recognition", "number comparison",
    "addition", "subtraction", "multiplication", "division",
    "number_sense", "memory",
}


def validate_interaction(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate and clean a single interaction record.

    Returns the cleaned record dict, or None if the record is invalid.
    """
    # Required fields check
    required = ["student_id", "question_id"]
    for field in required:
        if not data.get(field):
            return None

    # Validate response_time_sec
    rt = data.get("response_time_sec", 0)
    try:
        rt = float(rt)
    except (TypeError, ValueError):
        return None
    if rt < 0:
        return None
    data["response_time_sec"] = rt

    # Validate attempts (must be >= 1)
    attempts = data.get("attempts", 1)
    try:
        attempts = int(attempts)
    except (TypeError, ValueError):
        attempts = 1
    if attempts < 1:
        attempts = 1
    data["attempts"] = attempts

    # Validate is_correct (must be boolean)
    is_correct = data.get("is_correct", False)
    if isinstance(is_correct, str):
        is_correct = is_correct.lower() in ("true", "1", "yes")
    data["is_correct"] = bool(is_correct)

    # Validate hint_used (must be boolean)
    hint_used = data.get("hint_used", False)
    if isinstance(hint_used, str):
        hint_used = hint_used.lower() in ("true", "1", "yes")
    data["hint_used"] = bool(hint_used)

    # Validate click_count (>= 0)
    click_count = data.get("click_count", 0)
    try:
        click_count = int(click_count)
    except (TypeError, ValueError):
        click_count = 0
    data["click_count"] = max(0, click_count)

    # Validate session_time_sec (>= 0)
    session_time = data.get("session_time_sec", 0)
    try:
        session_time = float(session_time)
    except (TypeError, ValueError):
        session_time = 0
    data["session_time_sec"] = max(0, session_time)

    # Validate time_between_actions (>= 0)
    tba = data.get("time_between_actions", 0)
    try:
        tba = float(tba)
    except (TypeError, ValueError):
        tba = 0
    data["time_between_actions"] = max(0, tba)

    # Normalize error_type
    error_type = str(data.get("error_type", "none")).lower().strip()
    if error_type not in VALID_ERROR_TYPES:
        error_type = "none"
    data["error_type"] = error_type

    # Normalize difficulty
    difficulty = str(data.get("difficulty", "Easy")).strip()
    if difficulty.lower() not in VALID_DIFFICULTIES:
        difficulty = "Easy"
    else:
        difficulty = difficulty.capitalize()
    data["difficulty"] = difficulty

    # Normalize topic
    topic = str(data.get("topic", "Addition")).strip()
    if topic.lower() not in VALID_TOPICS:
        topic = "Addition"
    data["topic"] = topic

    return data
