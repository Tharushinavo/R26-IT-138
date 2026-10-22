"""Component D's bilingual recommendation text (Component D authorization, D-011; plan v5
Phase 2).

Ported from compD's ``server/app/services/recommendation.py`` -- both ``generate_recommendation``
and ``generate_insight``, which compD joined with a blank line to form one ``recommendation``
string. That join is preserved here (``build_recommendation``), because the frontend renders one
block of text and splitting it now would be a contract change nobody asked for.

**THE STRINGS BELOW WERE EXTRACTED FROM compD'S SOURCE BY SCRIPT, NOT RETYPED.** Half of them
are Sinhala, and nobody on this integration reads Sinhala; transcribing them by hand would have
risked silently corrupting text that goes in front of a child. They were pulled out of compD's
own AST as ``(en, si)`` pairs and written here verbatim. The structure around them is new; not
one character inside them is.

**NOT REVIEWED FOR ACCURACY.** Plan v5 and the BE-000 log already record this and it is repeated
where the text actually lives: compD's Sinhala strings have never been checked by anyone who
reads Sinhala. This port does not change that, and it is not a claim that the translations are
correct -- only that they are unaltered.

WHY THE TEXT IS BUILT ON READ AND NEVER STORED. ``d_cognitive_profiles`` deliberately has no
``recommendation`` column. The wording depends on the language the READ asks for, so a learner
who switches to Sinhala sees their whole history in Sinhala; a stored string would have frozen
each profile in the language it was generated in. See ``DCognitiveProfileRecord``'s docstring.

WHO THIS TEXT IS FOR. compD wrote it for teachers and parents -- it says "the student" and
prescribes interventions. It is not child-facing copy, and the frontend is responsible for not
putting it in front of a Grade 2 child as-is. Owner decision D-010 keeps compD's own labels on
the child-facing page as a research prototype; this is the longer-form text behind them.
"""

from __future__ import annotations

from app.domain.d_profile import DCognitiveProfileFeatures, Language, Level, SpeedLevel


# compD's thresholds, verbatim (`recommendation.py::generate_insight`).
ACCURACY_LOW_BELOW = 0.5
ACCURACY_MODERATE_BELOW = 0.75
RESPONSE_TIME_HIGH_ABOVE_MS = 8000
RESPONSE_TIME_MODERATE_ABOVE_MS = 5000

# A tip is offered for `low` and `medium` only. compD offers none for `high` or `Fast`, and that
# is deliberate: there is nothing to support. A learner who is `high` on all four gets the
# single encouragement string instead (`_NO_TIPS_NEEDED`).
_TIPS: dict[tuple[str, str], dict[Language, str]] = {
    ("memory_level", "low"): {
        "en": "Memory support: Provide repeated practice with step-by-step guidance. Use visual aids and break problems into smaller steps.",
        "si": "මතකය වර්ධනයට: දෘශ්‍ය ආධාරක භාවිතා කරන්න, ගැටළු කුඩා කොටස් වලට කඩා පියවරෙන් පියවර මඟ පෙන්වන්න.",
    },
    ("memory_level", "medium"): {
        "en": "Memory support: Continue practice with moderate repetition. Introduce memory games to strengthen recall.",
        "si": "මතකය වර්ධනයට: මතක ක්‍රීඩා හඳුන්වා දෙන්න. සාමාන්‍ය පුනරාවර්තන අභ්‍යාස දිගටම කරගෙන යන්න.",
    },
    ("attention_level", "low"): {
        "en": "Attention support: Use shorter activities with more visual cues. Reduce distractions and provide frequent breaks.",
        "si": "අවධානය වර්ධනයට: කෙටි ක්‍රියාකාරකම් සහ වැඩි දෘශ්‍ය ඉඟි භාවිතා කරන්න. බාධා කිරීම් අවම කර නිතර විවේක ලබා දෙන්න.",
    },
    ("attention_level", "medium"): {
        "en": "Attention support: Maintain engaging activities with moderate length. Use interactive elements to keep focus.",
        "si": "අවධානය වර්ධනයට: අවධානය තබා ගැනීම සඳහා මධ්‍යම ප්‍රමාණයේ අන්තර්ක්‍රියාකාරී ක්‍රියාකාරකම් භාවිතා කරන්න.",
    },
    ("number_sense_level", "low"): {
        "en": "Number sense support: Focus on counting, number comparison, and number recognition activities. Use concrete objects and visual representations.",
        "si": "සංඛ්‍යා ඥානය වර්ධනයට: ගණන් කිරීම, සංඛ්‍යා හඳුනාගැනීම සහ සංසන්දනය කිරීම කෙරෙහි අවධානය යොමු කරන්න. සංයුක්ත වස්තූන් භාවිතා කරන්න.",
    },
    ("number_sense_level", "medium"): {
        "en": "Number sense support: Continue with number comparison and basic arithmetic practice. Gradually increase difficulty.",
        "si": "සංඛ්‍යා ඥානය වර්ධනයට: මූලික අංක ගණිත පුහුණුව දිගටම කරගෙන යන්න. ක්‍රමානුකූලව දුෂ්කරතා මට්ටම වැඩි කරන්න.",
    },
    ("processing_speed_level", "Slow"): {
        "en": "Processing speed support: Avoid time-limited questions. Allow more thinking time and use untimed practice sessions.",
        "si": "වේගය වර්ධනයට: කාලය සීමිත ප්‍රශ්න මඟ හරින්න. සිතීමට වැඩි කාලයක් ලබා දෙන්න.",
    },
    ("processing_speed_level", "Moderate"): {
        "en": "Processing speed support: Gradually introduce gentle time targets. Encourage confident answering without rushing.",
        "si": "වේගය වර්ධනයට: සෙමින් කාල ඉලක්ක හඳුන්වා දෙන්න. කලබලයකින් තොරව පිළිතුරු දීමට දිරිමත් කරන්න.",
    },
}

_NO_TIPS_NEEDED: dict[Language, str] = {
    "en": "Great performance! Continue with current activities and gradually increase the challenge level to maintain growth.",
    "si": "විශිෂ්ට කාර්ය සාධනයක්! වර්ධනය පවත්වා ගැනීම සඳහා වර්තමාන ක්‍රියාකාරකම් සමඟ ඉදිරියට ගොස් ක්‍රමයෙන් අභියෝග මට්ටම වැඩි කරන්න.",
}

_ACCURACY_SENTENCE: dict[str, dict[Language, str]] = {
    "low": {
        "en": "The student answered less than half of the questions correctly.",
        "si": "සිසුවා ප්‍රශ්න වලින් අඩකට වඩා අඩු ප්‍රමාණයකට නිවැරදිව පිළිතුරු ලබා දී ඇත.",
    },
    "moderate": {
        "en": "The student showed moderate accuracy in answering questions.",
        "si": "සිසුවා ප්‍රශ්නවලට පිළිතුරු දීමේදී මධ්‍යස්ථ නිරවද්‍යතාවයක් පෙන්නුම් කළේය.",
    },
    "good": {
        "en": "The student demonstrated good accuracy overall.",
        "si": "සිසුවා සමස්තයක් වශයෙන් හොඳ නිරවද්‍යතාවයක් පෙන්නුම් කළේය.",
    },
}

_RESPONSE_TIME_SENTENCE: dict[str, dict[Language, str]] = {
    "high": {
        "en": "Response times were higher than expected, suggesting the student may need more thinking time.",
        "si": "ප්‍රතිචාර කාලය අපේක්ෂිත ප්‍රමාණයට වඩා වැඩි විය, සිසුවාට සිතීමට තවත් කාලය අවශ්‍ය විය හැක.",
    },
    "moderate": {
        "en": "Response times were moderate.",
        "si": "ප්‍රතිචාර කාලය මධ්‍යස්ථ විය.",
    },
}

# The dimension names as they appear inside the "areas that may need support" sentence.
_AREA_LABEL: dict[str, dict[Language, str]] = {
    "memory_level": {
        "en": "memory",
        "si": "මතකය",
    },
    "attention_level": {
        "en": "attention",
        "si": "අවධානය",
    },
    "number_sense_level": {
        "en": "number sense",
        "si": "සංඛ්‍යා ඥානය",
    },
    "processing_speed_level": {
        "en": "processing speed",
        "si": "වේගය",
    },
}

# `{areas}` is filled with the comma-joined labels above.
_AREAS_SENTENCE: dict[Language, str] = {
    "en": "Areas that may need additional support: {areas}.",
    "si": "අමතර සහාය අවශ්‍ය විය හැකි ක්ෂේත්‍ර: {areas}.",
}

_NO_AREAS_SENTENCE: dict[Language, str] = {
    "en": "No major areas of concern were identified.",
    "si": "විශාල දුර්වලතා හඳුනාගෙන නොමැත.",
}

# The level at which each dimension counts as needing support in the insight paragraph.
_NEEDS_SUPPORT_AT = {
    "memory_level": "low",
    "attention_level": "low",
    "number_sense_level": "low",
    "processing_speed_level": "Slow",
}

# compD's own ordering, preserved: memory, attention, number sense, speed. The order is visible
# to the reader of the finished paragraph, so it is not an implementation detail.
_DIMENSION_ORDER = (
    "memory_level",
    "attention_level",
    "number_sense_level",
    "processing_speed_level",
)


def _support_tips(levels: dict[str, str], language: Language) -> str:
    """compD's ``generate_recommendation``: one tip per dimension that needs one, space-joined.

    A learner who needs no tip at all gets the encouragement string rather than an empty
    paragraph -- which is why this returns ``_NO_TIPS_NEEDED`` instead of ``""``.
    """
    tips = [
        _TIPS[(dimension, levels[dimension])][language]
        for dimension in _DIMENSION_ORDER
        if (dimension, levels[dimension]) in _TIPS
    ]
    if not tips:
        return _NO_TIPS_NEEDED[language]
    return " ".join(tips)


def _insight(levels: dict[str, str], features: DCognitiveProfileFeatures, language: Language) -> str:
    """compD's ``generate_insight``: what happened in the run, in three sentences at most.

    The response-time sentence is OMITTED entirely when the mean is at or below the moderate
    threshold, exactly as compD had it: there is nothing noteworthy to say about a normal pace,
    and saying so anyway would pad every report with a sentence carrying no information.
    """
    parts: list[str] = []

    if features.accuracy < ACCURACY_LOW_BELOW:
        parts.append(_ACCURACY_SENTENCE["low"][language])
    elif features.accuracy < ACCURACY_MODERATE_BELOW:
        parts.append(_ACCURACY_SENTENCE["moderate"][language])
    else:
        parts.append(_ACCURACY_SENTENCE["good"][language])

    if features.avg_response_time_ms > RESPONSE_TIME_HIGH_ABOVE_MS:
        parts.append(_RESPONSE_TIME_SENTENCE["high"][language])
    elif features.avg_response_time_ms > RESPONSE_TIME_MODERATE_ABOVE_MS:
        parts.append(_RESPONSE_TIME_SENTENCE["moderate"][language])

    needing_support = [
        _AREA_LABEL[dimension][language]
        for dimension in _DIMENSION_ORDER
        if levels[dimension] == _NEEDS_SUPPORT_AT[dimension]
    ]
    if needing_support:
        parts.append(_AREAS_SENTENCE[language].format(areas=", ".join(needing_support)))
    else:
        parts.append(_NO_AREAS_SENTENCE[language])

    return " ".join(parts)


def build_recommendation(
    *,
    memory_level: Level,
    attention_level: Level,
    number_sense_level: Level,
    processing_speed_level: SpeedLevel,
    features: DCognitiveProfileFeatures,
    language: Language,
) -> str:
    """The whole ``recommendation`` string: the insight paragraph, a blank line, then the tips.

    compD built exactly this, in exactly this order, with exactly this separator
    (``f"{insight_text}\n\n{rec_text}"``). Keyword-only arguments because four same-typed level
    strings in a row is precisely the signature where a positional swap compiles, passes every
    type check, and silently reports the wrong dimension to a teacher.
    """
    levels: dict[str, str] = {
        "memory_level": memory_level,
        "attention_level": attention_level,
        "number_sense_level": number_sense_level,
        "processing_speed_level": processing_speed_level,
    }
    return f"{_insight(levels, features, language)}\n\n{_support_tips(levels, language)}"
