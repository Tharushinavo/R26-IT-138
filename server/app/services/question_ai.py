from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Literal, Optional
from urllib import request
from urllib.error import HTTPError, URLError

from app.schemas import QuestionCreate

Provider = Literal["openai", "gemini", "deepseek"]


DEFAULT_MODELS: Dict[Provider, str] = {
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-flash-latest",
    "deepseek": "deepseek-chat",
}

# Friendly messages for common HTTP errors
_FRIENDLY_ERRORS: Dict[int, str] = {
    401: "Invalid API key. Please ask the administrator to check the Gemini API key.",
    403: "API key does not have permission. Please check the API key settings in Google AI Studio.",
    404: "AI model not found. The configured model may have been deprecated.",
    429: "AI service is temporarily busy (rate limit). Please wait a moment and try again.",
    500: "AI service encountered an internal error. Please try again later.",
    503: "AI service is temporarily unavailable. Please try again in a few minutes.",
}

# Retry configuration for transient errors (429, 500, 503)
_RETRYABLE_CODES = {429, 500, 503}
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SEC = 2.0


def generate_questions(
    *,
    provider: Provider,
    api_key: str,
    topic: str,
    difficulty: str,
    count: int,
    model: Optional[str] = None,
    instructions: Optional[str] = None,
) -> List[QuestionCreate]:
    prompt = _build_prompt(topic, difficulty, count, instructions)
    selected_model = model or DEFAULT_MODELS[provider]

    if provider == "gemini":
        text = _call_gemini(api_key, selected_model, prompt)
    elif provider == "deepseek":
        text = _call_openai_compatible(
            "https://api.deepseek.com/chat/completions",
            api_key,
            selected_model,
            prompt,
        )
    else:
        text = _call_openai_compatible(
            "https://api.openai.com/v1/chat/completions",
            api_key,
            selected_model,
            prompt,
        )

    return _parse_questions(text, topic, difficulty, count)


def _build_prompt(topic: str, difficulty: str, count: int, instructions: Optional[str]) -> str:
    extra = f"\nAdditional teacher instructions: {instructions.strip()}" if instructions else ""
    return (
        "Generate cognitive math questions for children with dyscalculia.\n"
        f"Topic: {topic}\n"
        f"Difficulty: {difficulty}\n"
        f"Count: {count}\n"
        "Return only valid JSON with this shape:\n"
        '{"questions":[{"topic":"Addition","difficulty":"Easy","question_text":"2 + 3 = ?",'
        '"correct_answer":"5","options":["4","5","6","7"]}]}\n'
        "Rules: each options array must have 2 to 4 string options, must include correct_answer, "
        "and questions should be short, clear, and age-appropriate."
        f"{extra}"
    )


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a POST request with automatic retry for transient errors (429, 500, 503)."""
    data = json.dumps(payload).encode("utf-8")

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=60) as res:
                return json.loads(res.read().decode("utf-8"))
        except HTTPError as exc:
            code = exc.code
            detail_raw = exc.read().decode("utf-8", errors="ignore")

            # If retryable, wait and try again
            if code in _RETRYABLE_CODES and attempt < _MAX_RETRIES - 1:
                wait = _INITIAL_BACKOFF_SEC * (2 ** attempt)
                time.sleep(wait)
                last_exc = exc
                continue

            # Build a user-friendly message
            friendly = _FRIENDLY_ERRORS.get(code)
            if friendly:
                raise ValueError(friendly) from exc
            raise ValueError(f"AI provider returned error {code}: {detail_raw[:200]}") from exc
        except URLError as exc:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_INITIAL_BACKOFF_SEC)
                last_exc = exc
                continue
            raise ValueError(f"Could not reach AI provider: {exc.reason}") from exc

    # Should not reach here, but just in case
    raise ValueError("AI generation failed after multiple retries. Please try again later.")


def _call_openai_compatible(url: str, api_key: str, model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You create JSON-only educational math question banks."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    data = _post_json(
        url,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload,
    )
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ValueError("AI provider response did not contain generated text") from exc


def _call_gemini(api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }
    data = _post_json(url, {"Content-Type": "application/json"}, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        raise ValueError("Gemini response did not contain generated text") from exc


def _parse_questions(text: str, topic: str, difficulty: str, count: int) -> List[QuestionCreate]:
    raw = _extract_json(text)
    payload = json.loads(raw)
    items = payload.get("questions", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        raise ValueError("AI response must contain a questions array")

    questions: List[QuestionCreate] = []
    for item in items[:count]:
        if not isinstance(item, dict):
            continue
        options = [str(v) for v in item.get("options", []) if str(v).strip()]
        correct_answer = str(item.get("correct_answer", "")).strip()
        if correct_answer and correct_answer not in options:
            options.append(correct_answer)
        if len(options) < 2:
            continue
        question_text = str(item.get("question_text", "")).strip()
        if not question_text or not correct_answer:
            continue
        questions.append(
            QuestionCreate(
                question_code=item.get("question_code"),
                topic=str(item.get("topic") or topic),
                difficulty=item.get("difficulty") if item.get("difficulty") in ("Easy", "Medium", "Hard") else difficulty,  # type: ignore[arg-type]
                question_text=question_text,
                correct_answer=correct_answer,
                options=options[:4],
            )
        )

    if not questions:
        raise ValueError("AI response did not include any valid questions")
    return questions


def _extract_json(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```"):
        trimmed = trimmed.strip("`").strip()
        if trimmed.lower().startswith("json"):
            trimmed = trimmed[4:].strip()
    if trimmed.startswith("{") or trimmed.startswith("["):
        return trimmed
    start_obj = trimmed.find("{")
    start_arr = trimmed.find("[")
    starts = [i for i in (start_obj, start_arr) if i >= 0]
    if not starts:
        raise ValueError("AI response did not contain JSON")
    start = min(starts)
    end = max(trimmed.rfind("}"), trimmed.rfind("]"))
    if end <= start:
        raise ValueError("AI response JSON was incomplete")
    return trimmed[start:end + 1]
