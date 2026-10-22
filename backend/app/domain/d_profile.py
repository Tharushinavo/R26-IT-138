"""Component D's public request/response shapes (Component D authorization, owner decision
D-011; API contract v4, all six rows Agreed).

WHY THE FIELD NAMES ARE WHAT THEY ARE. Three of them were renamed under D-011 A4, each to the
host's OWN existing name for the same concept rather than to a euphemism:

- ``response_matched`` -- compD called it ``is_correct``. "correct" is in both
  ``PROHIBITED_COLUMN_TERMS`` and ``FORBIDDEN_FIELD_TERMS``, and the host already publishes
  ``b_attempts.response_matched`` in ``contract/openapi.v1.json``. Adopting a name the host
  already ships is consistency, not evasion.
- ``assist_used`` -- compD called it ``hint_used``. The host's own naming is ``assist_*``
  (``b_hint_events.assist_event_id``, ``.assist_level``).
- ``mean_clicks_per_question`` -- compD called it ``answer_change_rate``. That rename is a
  CORRECTNESS FIX, not a guard fix: the feature computes mean clicks per question and never
  observes an answer changing (compD's ``features.py:54``). It would also have tripped "answer",
  but it was wrong on its own terms first.

**No field here needed an exemption, and no change to ``test_be5a_contract_freeze.py`` is
authorized (D-011 A5).** Checked term by term against that file's ``FORBIDDEN_FIELD_TERMS``
rather than assumed:

- ``attempts`` / ``avg_attempts`` are clean -- "attempt" is a prohibited *path* term
  (``PROHIBITED_SCIENTIFIC_PATH_TERMS``), not a forbidden *field* term.
- ``error_type`` is clean -- the forbidden term is ``error_class``, not "error".
- ``hint_rate`` is clean -- "hint" is a prohibited *column* term and a prohibited *path* term,
  but it is NOT in ``FORBIDDEN_FIELD_TERMS``, and this value is a computed feature of the
  profile rather than a stored column.
- ``response_time_sec``, ``session_time_sec``, ``time_between_actions`` are clean -- the banned
  term is "latency", not "time" (compare ``b_attempts.client_elapsed_ms``, which took the same
  route, and ``c_task_opportunity_summaries.task_latency_sec``, which needed an exemption).

WHAT IS DELIBERATELY ABSENT. No learner id, user id or student id appears in any shape here, in
either direction: identity comes only from the bearer token (contract v4, "Identity comes only
from the token"). compD's ``student_id`` field is gone, as are ``expected_answer`` and
``given_answer`` -- the host never receives what the child typed, only whether it matched.

``recommendation`` is BUILT WHEN READ, in the language the read asks for, and is never persisted.
Storing it would freeze the wording of the day it was generated, so a learner who later switched
to Sinhala would see their history in English for ever. See ``DCognitiveProfileRecord``'s own
docstring for the column-level half of this decision.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.b_session import StrictModel


Language = Literal["en", "si"]
Level = Literal["low", "medium", "high"]
SpeedLevel = Literal["Slow", "Moderate", "Fast"]
Topic = Literal["Counting", "Addition", "Subtraction", "Division"]
Difficulty = Literal["Easy", "Medium", "Hard"]
ErrorType = Literal["none", "calculation", "conceptual", "careless", "unknown"]

# Contract v4: `events: DInteractionEvent[1..50]`. The lower bound is 1 because a profile with no
# evidence is not a profile; the upper bound is 50 because the activity is ten questions and a
# body five times that size is a client defect, not a long session.
MIN_EVENTS = 1
MAX_EVENTS = 50

# Contract v4: `limit` 1-100, out of range is a 422 rather than a silent clamp.
MIN_HISTORY_LIMIT = 1
MAX_HISTORY_LIMIT = 100
DEFAULT_HISTORY_LIMIT = 20


class DLearnerStateResponse(StrictModel):
    """``intro_completed`` is derived from ``d_learner_state.intro_completed_at IS NOT NULL``.

    A learner with no row reads as ``{intro_completed: false, language: "en"}`` and nothing is
    created -- the default belongs to the read, not to the table, so the table never holds a
    language the learner did not pick.
    """

    intro_completed: bool
    language: Language
    request_id: str


class DLearnerStateUpdateRequest(StrictModel):
    """At least one field is required; ``{}`` is a 422.

    ``intro_completed`` is ``Literal[True]``, so ``false`` is a 422 too. The intro is a one-way
    door: a learner who has seen it cannot un-see it, and accepting ``false`` would let a client
    reset the first-run flow for a child who had already been through it.
    """

    intro_completed: Literal[True] | None = None
    language: Language | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if self.intro_completed is None and self.language is None:
            raise ValueError("at least one of intro_completed or language is required")
        return self


class DInteractionEvent(StrictModel):
    """One question answered in a profiling run -- the raw evidence a feature vector is computed
    from, and the row shape ``d_interactions`` stores.

    The numeric bounds here are the same ones the table's CHECK constraints enforce
    (migration ``20261021_0010``), stated in both places on purpose: the API refuses a bad body
    with a 422 naming the field, and the database refuses it again if anything ever reaches it by
    another path.
    """

    question_id: str = Field(min_length=1, max_length=128)
    topic: Topic
    difficulty: Difficulty
    response_time_sec: float = Field(ge=0.0)
    attempts: int = Field(ge=1)
    response_matched: bool
    assist_used: bool
    click_count: int = Field(ge=0)
    session_time_sec: float = Field(ge=0.0)
    time_between_actions: float = Field(ge=0.0)
    error_type: ErrorType


class DProfileCreateRequest(StrictModel):
    language: Language
    events: list[DInteractionEvent] = Field(min_length=MIN_EVENTS, max_length=MAX_EVENTS)

    @model_validator(mode="after")
    def reject_a_duplicate_question_in_one_body(self) -> Self:
        """Contract v4: a duplicate ``question_id`` in one body is a 422.

        Caught here rather than left to ``uq_d_interactions_session_question``, because the
        unique constraint would surface a client's own duplicate as a 409 CONFLICT -- which means
        "someone else got there first" and would send the client into retry or reconciliation for
        a body it could have fixed itself.
        """
        seen = {event.question_id for event in self.events}
        if len(seen) != len(self.events):
            raise ValueError("question_id must be unique within one request")
        return self


class DCognitiveProfileFeatures(StrictModel):
    """The feature vector, returned as a unit because that is how it is computed and consumed.

    ``total_questions`` is an int; everything else is a ratio or a duration. ``hint_rate`` keeps
    its name -- see this module's docstring for why that is clean at the public layer.
    """

    accuracy: float = Field(ge=0.0, le=1.0)
    avg_response_time_ms: float = Field(ge=0.0)
    response_time_std_ms: float = Field(ge=0.0)
    avg_attempts: float = Field(ge=0.0)
    retry_rate: float = Field(ge=0.0, le=1.0)
    hint_rate: float = Field(ge=0.0, le=1.0)
    mean_clicks_per_question: float = Field(ge=0.0)
    total_questions: int = Field(ge=0)


class DCognitiveProfile(StrictModel):
    """The raw levels are carried as the engine produced them.

    Owner decision **D-010** keeps compD's own labels (for example "Memory: low") on the
    child-facing page, as a research prototype that needs much more development and data
    collection. How that is worded for a child is the frontend's to render and is not a contract
    concern -- this shape stays descriptive.

    ``model_version`` is a rule-based version until a trained model exists -- ``"rule-based-v2"``
    today, after the speed heuristic was corrected (``d_features.capped_mean_response_time_ms``).
    It is on the public
    shape so a reader can always tell which generation produced a profile; a history list can
    hold both.
    """

    session_id: UUID
    memory_level: Level
    attention_level: Level
    number_sense_level: Level
    processing_speed_level: SpeedLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendation: str
    model_version: str
    features: DCognitiveProfileFeatures
    generated_at: datetime


class DCognitiveProfileResponse(StrictModel):
    """The single-profile response, for both the ``POST`` and the by-session ``GET``.

    The ``POST`` returns the same 200 for a newly stored profile and for a repeat of one already
    stored (contract v4) -- a client that retries cannot tell the two apart, which is the point.
    """

    profile: DCognitiveProfile
    request_id: str


class DLatestProfileResponse(StrictModel):
    """``profile: null`` rather than a 404 when the learner has none.

    A learner who has never done a profiling run is in a normal, expected state, and the home
    screen's empty state is a render of that -- not an error to recover from.
    """

    profile: DCognitiveProfile | None
    request_id: str


class DProfileListResponse(StrictModel):
    """Newest first."""

    items: list[DCognitiveProfile]
    request_id: str
