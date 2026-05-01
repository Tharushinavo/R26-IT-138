"""Rule-based recommendation layer (plan Section 5.6).

After the ML model predicts cognitive labels, this module generates
human-readable support recommendations for teachers and parents.
"""
from __future__ import annotations

from typing import Dict


def generate_recommendation(labels: Dict[str, str]) -> str:
    """Generate a recommendation string based on predicted cognitive labels."""
    tips: list[str] = []

    memory = labels.get("memory_level", "medium")
    attention = labels.get("attention_level", "medium")
    number_sense = labels.get("number_sense_level", "medium")
    speed = labels.get("processing_speed_level", "Moderate")

    if memory == "low":
        tips.append(
            "Memory support: Provide repeated practice with step-by-step guidance. "
            "Use visual aids and break problems into smaller steps."
        )
    elif memory == "medium":
        tips.append(
            "Memory support: Continue practice with moderate repetition. "
            "Introduce memory games to strengthen recall."
        )

    if attention == "low":
        tips.append(
            "Attention support: Use shorter activities with more visual cues. "
            "Reduce distractions and provide frequent breaks."
        )
    elif attention == "medium":
        tips.append(
            "Attention support: Maintain engaging activities with moderate length. "
            "Use interactive elements to keep focus."
        )

    if number_sense == "low":
        tips.append(
            "Number sense support: Focus on counting, number comparison, and "
            "number recognition activities. Use concrete objects and visual representations."
        )
    elif number_sense == "medium":
        tips.append(
            "Number sense support: Continue with number comparison and basic "
            "arithmetic practice. Gradually increase difficulty."
        )

    if speed == "Slow":
        tips.append(
            "Processing speed support: Avoid time-limited questions. Allow more "
            "thinking time and use untimed practice sessions."
        )
    elif speed == "Moderate":
        tips.append(
            "Processing speed support: Gradually introduce gentle time targets. "
            "Encourage confident answering without rushing."
        )

    if not tips:
        return (
            "Great performance! Continue with current activities and gradually "
            "increase the challenge level to maintain growth."
        )

    return " ".join(tips)


def generate_insight(labels: Dict[str, str], features: dict) -> str:
    """Generate a short system insight paragraph for the profile result screen."""
    parts: list[str] = []

    accuracy = features.get("accuracy", 0)
    avg_time = features.get("avg_response_time_ms", 0)
    total = features.get("total_questions", 0)

    if accuracy < 0.5:
        parts.append("The student answered less than half of the questions correctly.")
    elif accuracy < 0.75:
        parts.append("The student showed moderate accuracy in answering questions.")
    else:
        parts.append("The student demonstrated good accuracy overall.")

    if avg_time > 8000:
        parts.append("Response times were higher than expected, suggesting the student may need more thinking time.")
    elif avg_time > 5000:
        parts.append("Response times were moderate.")

    low_areas = []
    if labels.get("memory_level") == "low":
        low_areas.append("memory")
    if labels.get("attention_level") == "low":
        low_areas.append("attention")
    if labels.get("number_sense_level") == "low":
        low_areas.append("number sense")
    if labels.get("processing_speed_level") == "Slow":
        low_areas.append("processing speed")

    if low_areas:
        parts.append(
            f"Areas that may need additional support: {', '.join(low_areas)}."
        )
    else:
        parts.append("No major areas of concern were identified.")

    return " ".join(parts)
