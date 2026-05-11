"""
Test the question_ai module logic (prompt building, JSON parsing, validation).
Run: python test_gemini.py
"""
import sys
sys.path.insert(0, ".")

from app.services.question_ai import (
    _build_prompt, _parse_questions, _extract_json,
    DEFAULT_MODELS, _FRIENDLY_ERRORS,
)

passed = 0
failed = 0

def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")


# ── Prompt Building ──────────────────────────────────────────────────────
print("Test Suite: Prompt Building")
prompt = _build_prompt("Addition", "Easy", 3, "Use word problems with fruits")
test("Includes topic", "Addition" in prompt)
test("Includes difficulty", "Easy" in prompt)
test("Includes count", "3" in prompt)
test("Includes instructions", "Use word problems with fruits" in prompt)
test("Includes JSON schema", "question_text" in prompt and "correct_answer" in prompt)

prompt_no_inst = _build_prompt("Subtraction", "Hard", 1, None)
test("No instructions is fine", "Additional teacher" not in prompt_no_inst)


# ── JSON Extraction ──────────────────────────────────────────────────────
print("\nTest Suite: JSON Extraction")
test("From markdown block", '"questions"' in _extract_json('```json\n{"questions":[]}\n```'))
test("From plain JSON", '"test"' in _extract_json('{"test":1}'))
test("From array JSON", '"a"' in _extract_json('[{"a":1}]'))
test("JSON with prefix text", '"q"' in _extract_json('Here is the data: {"q":1}'))

try:
    _extract_json("no json here")
    test("Raises on no JSON", False)
except ValueError:
    test("Raises on no JSON", True)


# ── Question Parsing ─────────────────────────────────────────────────────
print("\nTest Suite: Question Parsing")
mock = '''{"questions":[
    {"topic":"Addition","difficulty":"Easy","question_text":"2 + 3 = ?","correct_answer":"5","options":["3","4","5","6"]},
    {"topic":"Addition","difficulty":"Easy","question_text":"What is 4 + 1?","correct_answer":"5","options":["4","5","6","7"]},
    {"topic":"Addition","difficulty":"Easy","question_text":"3 apples + 2 = ?","correct_answer":"5","options":["4","5","6"]}
]}'''
qs = _parse_questions(mock, "Addition", "Easy", 10)
test(f"Parses 3 valid questions", len(qs) == 3)
test("Correct topic", all(q.topic == "Addition" for q in qs))
test("Correct difficulty", all(q.difficulty == "Easy" for q in qs))
test("Answer in options", all(q.correct_answer in q.options for q in qs))
test("Options 2-4 items", all(2 <= len(q.options) <= 4 for q in qs))


# ── Edge Cases ───────────────────────────────────────────────────────────
print("\nTest Suite: Edge Cases")
bad_mock = '''{"questions":[
    {"topic":"S","difficulty":"Hard","question_text":"10 - 3?","correct_answer":"7","options":["5","6","7","8"]},
    {"topic":"S","question_text":"","correct_answer":"","options":[]},
    {"topic":"S","difficulty":"H","question_text":"OK?","correct_answer":"4","options":["4"]}
]}'''
qs2 = _parse_questions(bad_mock, "Subtraction", "Medium", 5)
test("Filters invalid (empty text, <2 options)", len(qs2) == 1)
test("Falls back difficulty if invalid", qs2[0].difficulty == "Hard")

count_limited = _parse_questions(mock, "Addition", "Easy", 2)
test("Respects count limit", len(count_limited) == 2)


# ── Configuration ────────────────────────────────────────────────────────
print("\nTest Suite: Configuration")
test("Gemini model is 2.0-flash", DEFAULT_MODELS["gemini"] == "gemini-2.0-flash")
test("429 has friendly message", "busy" in _FRIENDLY_ERRORS[429].lower() or "rate" in _FRIENDLY_ERRORS[429].lower())
test("401 has friendly message", "api key" in _FRIENDLY_ERRORS[401].lower())
test("404 has friendly message", "model" in _FRIENDLY_ERRORS[404].lower() or "deprecated" in _FRIENDLY_ERRORS[404].lower())


# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)
