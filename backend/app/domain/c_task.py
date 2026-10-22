"""Public contracts for Component C's task-serving endpoints (Phase 5).

Mirrors ``app.domain.c_session``'s discipline exactly (X-4, allow-list construction -- named
fields only, never a serialised model with fields subtracted, never ``**record.__dict__``).

PRIVATE/PUBLIC SPLIT (Phase 5 work order P2, S3): the following ``c_task_instances`` columns are
NEVER exposed here, regardless of their status at the database-allow-list layer
(``AUTHORIZED_C_COLUMN_EXCEPTIONS`` governs whether a column may legitimately EXIST and hold
private content -- it says nothing about HTTP exposure; Phase 4b established this distinction
with ``mastery_context_mode`` and it applies with full force here):
  - ``correct_answer_payload`` -- the secret itself. Never public, under any name, ever.
  - ``correctness_function_id`` -- evaluator internals (P1-d).
  - ``c_task_opportunities.mastery_selected_skill`` -- the raw mastery float feeding the
    initial-difficulty formula (C-17). A real, B-mastery-derived scientific value; never public.
  - ``c_task_opportunities.mastery_context_mode`` -- same R-1 reasoning as ``c_sessions``:
    derivable client-side from ``session_mode`` alone, never re-exposed.
  - SIX COLUMNS RULED PRIVATE (S3, all six, no case-by-case judgment): ``curriculum_node_id``,
    ``functional_role``, ``completion_condition``, ``failure_condition``, ``terminal_reason``,
    ``difficulty_vector``. "Adding a field later is additive; removing one is breaking -- the
    conservative direction is the reversible one." Rendering data travels via
    ``prompt_payload``/``interactive_assets``, which is what makes ``difficulty_vector`` private
    rather than a judgment call (owner's own words).
  - ``template_version``, ``catalogue_version``, ``generator_version``, every ``seed_lineage_*``
    column -- governance/audit metadata, mirrors B's own ``project_task_instance_to_presentation``
    precedent (``b_opportunity.py``) excluding the equivalent fields.
  - ``student_id``, ``c_session_id`` on the instance -- already known from the session context
    (auth + path param); re-exposing invites the same class of bug R-5 fixed for B's identity.

PROMPT_PAYLOAD/INTERACTIVE_ASSETS ARE PUBLIC BUT PER-TEMPLATE (P3). This is necessarily what the
child is shown, and its safety was verified per-template by the Phase 5 leak-test loop (S5) --
NOT proven here by any static analysis. A template whose prompt embeds a partially-worked example
containing the final answer would be a real leak in these two fields specifically, not a naming
defect this module could catch.

R-6 (SUPERVISOR RULING, Phase 5 continuation): ``CSubmitActionResult``'s verdict field is named
``response_matched``, not ``is_correct``. Regenerating the frozen contract surfaced that
``is_correct`` contains the substring "correct", tripping BE5a's ``FORBIDDEN_FIELD_TERMS`` guard
(``tests/test_be5a_contract_freeze.py``, no allow-list mechanism, not modified here). This is NOT
a rename invented to dodge the guard (the exact pattern R-H already condemned once) -- it adopts
the name of the REVIEWED, ALREADY-FROZEN sibling field for this identical semantic:
``app/domain/b_attempt.py:34``, ``AttemptResponseFields.response_matched``. B's field is typed
``bool | None`` (``None`` for a ``TIMEOUT`` event kind, where no comparison ever happened); this
field stays plain ``bool`` -- a submitted action that reached this response has always been
evaluated, so there is no "no verdict yet" state to represent here. That typing divergence is
deliberate, not an oversight.

BE-PROMPT-TEXT BATCH (first change to this DTO since Phase 7): two additive fields, ``blanks``
and ``prompt_text``. Neither moves anything from private to public; both are read alongside the
existing allow-listed fields in ``task_service._task_fields``, never in place of the private-split
discipline stated above.

``blanks: int | None`` -- the count of values the child must supply, non-null for EXACTLY
``C-NP-01``, ``C-NP-02``, ``C-NP-03`` and ``None`` for the other 27 (asserted as a set by this
batch's tests). Five templates set the pinned generator's ``count_b_by_level`` parameter, and it
means a different thing for each: ``blanks`` for the three NP templates, ``group_size`` for
``C-EG-01``, ``cols`` for ``C-EG-02`` -- both of the latter two already public inside
``prompt_payload`` under their own names. This field is deliberately NOT "read
``count_b_by_level`` for whichever template happens to set it"; that would re-expose
``group_size``/``cols`` a second time under a name that means something else. It is sourced from
``record.difficulty_vector["blanks"]`` -- a literal key the pinned generator itself writes into
``difficulty_vector`` for exactly these three templates (verified:
``component_c_generator/tasks/number_path.py:25,46,67``; no other template file uses that key) --
gated by an explicit three-template allow-list, not a bare ``.get("blanks")``, so a future
template that happened to reuse the key name for an unrelated meaning could not silently
misreport through this field.

READ THE FOLLOWING TWO PARAGRAPHS TOGETHER; NEITHER MAKES SENSE ALONE. ``difficulty_vector``
stays on the S3 list above -- never exposed here, under any name, as itself. What ``blanks``
exposes is ONE NAMED SCALAR derived from it, for exactly the three templates named above, and
that is the full extent of the precedent this field sets: it is NOT a licence to mine
``difficulty_vector`` for further public fields by the same pattern, and no other field in this
module may be justified by pointing at this one.

The reason reading that one key at request time is safe, and reading ``difficulty_vector``
generally would not be: this is reading a value the pinned generator ALREADY COMPUTED AND
PERSISTED PER INSTANCE, not recomputing it from configuration. The record's ``difficulty_vector``
was written at generation time, under the generation-mode smoke gate
(``assert_generation_config_permitted``) that instance was generated under -- so the governance
dependency (every generation parameter is ``TEST_FIXTURE_ONLY``, none owner-assigned) was already
exercised and recorded at that moment, nothing is hidden by reading it back out afterward. This is
categorically different from calling ``component_c_generator.generation_config.
default_generation_config()`` at read time, which is forbidden anywhere under ``app/`` and
mechanically asserted so
(``tests/test_be2_architecture_guards.py::test_no_app_code_defaults_or_calls_default_generation_config``,
whose own docstring gives the governance reason: doing so "would hide that dependency exactly as
``default_selection_config()`` would have for W"). A later reader who finds a
``difficulty_vector`` read under ``app/`` and assumes it is the same class of thing as that
forbidden call should re-read this paragraph: it is not, and the distinction is the entire reason
this field is permitted.

``prompt_text: str`` -- the child-facing question, following Component B's ``stem`` architecture
(backend-owned, server-supplied; the frontend relays it verbatim and never composes or rewrites
it). Present for all 30 templates. Sourced from
``app.domain.live_engine_c.prompt_wording.PROMPT_TEXT_BY_TEMPLATE`` -- authored content, not
generator output, so nothing here is "consuming the wheel"; the pinned generator is never touched
by this field. **CANDIDATE WORDING, NOT OWNER-REVIEWED.** See that module's own docstring for the
full disclosure: every string is drafted to prove the machinery works, not approved as final
child-facing text. Governance-relevant despite not being a generation/safety/policy parameter --
wording is content, not a member of the seven gated configuration families, but it is still the
kind of thing the owner-review stop point exists for, and it must not be read as "not governance
relevant" merely because it is "not an eighth family."
"""

from typing import Any, Mapping, Optional
from uuid import UUID

from app.domain.c_session import StrictModel


class CTaskFields(StrictModel):
    c_task_instance_id: UUID
    game_family_id: str
    game_task_template_id: str
    task_index: int
    skill_id: str
    difficulty_level: int
    representation_mode: str
    prompt_payload: Mapping[str, Any]
    interactive_assets: Mapping[str, Any]
    valid_action_space: Mapping[str, str]
    scaffold_state: str
    technical_status: str
    blanks: Optional[int]
    prompt_text: str


class CNextTaskResponse(CTaskFields):
    request_id: str


class CSubmitActionResult(StrictModel):
    c_task_instance_id: UUID
    response_matched: bool
    scaffold_level: str
    request_id: str
