"""Rule-based recommendation layer (plan Section 5.6).

After the ML model predicts cognitive labels, this module generates
human-readable support recommendations for teachers and parents.
"""
from __future__ import annotations

from typing import Dict


def generate_recommendation(labels: Dict[str, str], language: str = "en") -> str:
    """Generate a recommendation string based on predicted cognitive labels."""
    tips: list[str] = []
    memory = labels.get("memory_level", "medium")
    attention = labels.get("attention_level", "medium")
    number_sense = labels.get("number_sense_level", "medium")
    speed = labels.get("processing_speed_level", "Moderate")

    is_si = language == "si"

    if memory == "low":
        tips.append(
            "මතකය වර්ධනයට: දෘශ්‍ය ආධාරක භාවිතා කරන්න, ගැටළු කුඩා කොටස් වලට කඩා පියවරෙන් පියවර මඟ පෙන්වන්න." if is_si else
            "Memory support: Provide repeated practice with step-by-step guidance. Use visual aids and break problems into smaller steps."
        )
    elif memory == "medium":
        tips.append(
            "මතකය වර්ධනයට: මතක ක්‍රීඩා හඳුන්වා දෙන්න. සාමාන්‍ය පුනරාවර්තන අභ්‍යාස දිගටම කරගෙන යන්න." if is_si else
            "Memory support: Continue practice with moderate repetition. Introduce memory games to strengthen recall."
        )

    if attention == "low":
        tips.append(
            "අවධානය වර්ධනයට: කෙටි ක්‍රියාකාරකම් සහ වැඩි දෘශ්‍ය ඉඟි භාවිතා කරන්න. බාධා කිරීම් අවම කර නිතර විවේක ලබා දෙන්න." if is_si else
            "Attention support: Use shorter activities with more visual cues. Reduce distractions and provide frequent breaks."
        )
    elif attention == "medium":
        tips.append(
            "අවධානය වර්ධනයට: අවධානය තබා ගැනීම සඳහා මධ්‍යම ප්‍රමාණයේ අන්තර්ක්‍රියාකාරී ක්‍රියාකාරකම් භාවිතා කරන්න." if is_si else
            "Attention support: Maintain engaging activities with moderate length. Use interactive elements to keep focus."
        )

    if number_sense == "low":
        tips.append(
            "සංඛ්‍යා ඥානය වර්ධනයට: ගණන් කිරීම, සංඛ්‍යා හඳුනාගැනීම සහ සංසන්දනය කිරීම කෙරෙහි අවධානය යොමු කරන්න. සංයුක්ත වස්තූන් භාවිතා කරන්න." if is_si else
            "Number sense support: Focus on counting, number comparison, and number recognition activities. Use concrete objects and visual representations."
        )
    elif number_sense == "medium":
        tips.append(
            "සංඛ්‍යා ඥානය වර්ධනයට: මූලික අංක ගණිත පුහුණුව දිගටම කරගෙන යන්න. ක්‍රමානුකූලව දුෂ්කරතා මට්ටම වැඩි කරන්න." if is_si else
            "Number sense support: Continue with number comparison and basic arithmetic practice. Gradually increase difficulty."
        )

    if speed == "Slow":
        tips.append(
            "වේගය වර්ධනයට: කාලය සීමිත ප්‍රශ්න මඟ හරින්න. සිතීමට වැඩි කාලයක් ලබා දෙන්න." if is_si else
            "Processing speed support: Avoid time-limited questions. Allow more thinking time and use untimed practice sessions."
        )
    elif speed == "Moderate":
        tips.append(
            "වේගය වර්ධනයට: සෙමින් කාල ඉලක්ක හඳුන්වා දෙන්න. කලබලයකින් තොරව පිළිතුරු දීමට දිරිමත් කරන්න." if is_si else
            "Processing speed support: Gradually introduce gentle time targets. Encourage confident answering without rushing."
        )

    if not tips:
        return (
            "විශිෂ්ට කාර්ය සාධනයක්! වර්ධනය පවත්වා ගැනීම සඳහා වර්තමාන ක්‍රියාකාරකම් සමඟ ඉදිරියට ගොස් ක්‍රමයෙන් අභියෝග මට්ටම වැඩි කරන්න." if is_si else
            "Great performance! Continue with current activities and gradually increase the challenge level to maintain growth."
        )

    return " ".join(tips)


def generate_insight(labels: Dict[str, str], features: dict, language: str = "en") -> str:
    """Generate a short system insight paragraph for the profile result screen."""
    parts: list[str] = []

    accuracy = features.get("accuracy", 0)
    avg_time = features.get("avg_response_time_ms", 0)
    total = features.get("total_questions", 0)

    is_si = language == "si"
    
    if accuracy < 0.5:
        parts.append("සිසුවා ප්‍රශ්න වලින් අඩකට වඩා අඩු ප්‍රමාණයකට නිවැරදිව පිළිතුරු ලබා දී ඇත." if is_si else "The student answered less than half of the questions correctly.")
    elif accuracy < 0.75:
        parts.append("සිසුවා ප්‍රශ්නවලට පිළිතුරු දීමේදී මධ්‍යස්ථ නිරවද්‍යතාවයක් පෙන්නුම් කළේය." if is_si else "The student showed moderate accuracy in answering questions.")
    else:
        parts.append("සිසුවා සමස්තයක් වශයෙන් හොඳ නිරවද්‍යතාවයක් පෙන්නුම් කළේය." if is_si else "The student demonstrated good accuracy overall.")

    if avg_time > 8000:
        parts.append("ප්‍රතිචාර කාලය අපේක්ෂිත ප්‍රමාණයට වඩා වැඩි විය, සිසුවාට සිතීමට තවත් කාලය අවශ්‍ය විය හැක." if is_si else "Response times were higher than expected, suggesting the student may need more thinking time.")
    elif avg_time > 5000:
        parts.append("ප්‍රතිචාර කාලය මධ්‍යස්ථ විය." if is_si else "Response times were moderate.")

    low_areas = []
    if labels.get("memory_level") == "low":
        low_areas.append("මතකය" if is_si else "memory")
    if labels.get("attention_level") == "low":
        low_areas.append("අවධානය" if is_si else "attention")
    if labels.get("number_sense_level") == "low":
        low_areas.append("සංඛ්‍යා ඥානය" if is_si else "number sense")
    if labels.get("processing_speed_level") == "Slow":
        low_areas.append("වේගය" if is_si else "processing speed")

    if low_areas:
        parts.append(
            (f"අමතර සහාය අවශ්‍ය විය හැකි ක්ෂේත්‍ර: {', '.join(low_areas)}.") if is_si else
            (f"Areas that may need additional support: {', '.join(low_areas)}.")
        )
    else:
        parts.append("විශාල දුර්වලතා හඳුනාගෙන නොමැත." if is_si else "No major areas of concern were identified.")

    return " ".join(parts)
