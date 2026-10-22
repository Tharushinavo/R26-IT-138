"""BE-prompt-text batch: the child-facing question text for Component C's 30 task templates.

**CANDIDATE ONLY -- NOT OWNER-REVIEWED, NOT FROZEN AS FINAL.** Every string in
``PROMPT_TEXT_BY_TEMPLATE`` below is drafted wording produced this batch to build and prove the
machinery (the field, the artefact, the generator, the checks). The owner ruling that created
this batch requires the WORDING ITSELF to be human-reviewed before it is treated as final --
building it and reviewing it are two different steps, done by two different people, and this
batch is only the first one. Nothing about the presence of a value here, or the fact that it
passes every automated check, should be read as approval of its content. Label carried at the
top level of the generated artefact: ``TEST_FIXTURE_ONLY``.

THIS IS THE SINGLE SOURCE OF TRUTH, read by two independent consumers that must never drift
apart: (1) ``app.application.live_engine_c.task_service._task_fields`` reads
``PROMPT_TEXT_BY_TEMPLATE`` (via ``prompt_text_for``) directly at request time, because that is
what actually reaches a child on the wire (Component B's ``stem`` architecture: backend-owned,
server-supplied, the frontend relays it verbatim and never composes or rewrites it); (2) this
artefact family's third generator (its own module directly imports the same dict; not named here
by path -- naming it would put a banned substring in this file's own prose, so see that
generator's own docstring for its exact location) derives the frozen, checksummed snapshot
committed under ``contract/`` that the frontend and this backend's own drift test check against.
Runtime code reads this module, never that JSON snapshot -- the snapshot is a derived,
checksummed proof of what this module currently contains, not an alternate source; a mechanical
guard in ``tests/test_be2_architecture_guards.py`` keeps it that way by refusing any literal
reference to the snapshot's filename anywhere under ``app/`` (this module's own docstring
deliberately avoids spelling that filename out, for exactly that reason -- a literal string
constant in ANY file under ``app/``, including a docstring explaining the artefact, is what the
guard matches). See ``generate_c_prompt_wording.py``'s own docstring for why this differs from the
registry/exemplars artefacts, which are read by nothing under ``app/``: ``prompt_text`` must reach
a real response, so something under ``app/`` has to read it, and it should read the authoritative
source rather than re-open a JSON file per request.

WHY A STATIC PYTHON DICT, NOT A CALL INTO THE PINNED GENERATOR: this content is authored by the
backend, not produced by ``component_c_generator``. There is no ``default_generation_config()``
call anywhere in this module or in its one production reader
(``app.application.live_engine_c.task_service``) -- see that module's own docstring and
``tests/test_be2_architecture_guards.py::test_no_app_code_defaults_or_calls_default_generation_config``
for why that specific call is forbidden anywhere under ``app/``: it would hide a governance
dependency the generation-parameter guard exists to surface. Nothing here needs that call --
wording is not a generation parameter.

PER-TEMPLATE, WITH VARIANTS WHERE THE TEMPLATE SPEC ITSELF FORKS (30 templates, 32 entries).
``valid_action_space`` is difficulty-invariant for all 30 templates (the template-registry
artefact's own five-level invariance test proves this as a checked fact), and no template's
*interaction shape* changes by level except the blank COUNT for ``C-NP-01/02/03``. That single
exception is absorbed by phrasing those three templates' wording count-agnostically ("write what
comes next", never "write the next two numbers") rather than by keying the whole table by level.

Three templates additionally carry a ``prompt_payload`` DISCRIMINATOR -- a value that varies
across trials of the same template and changes what the child is actually being asked. The table
does not treat all three the same way, and the rule that decides is:

    IS THE DISCRIMINATOR ITSELF THE GRADED RESPONSE?

``C-EG-02`` (``direction``: ``build``/``read``) and ``C-NP-04`` (``direction``:
``ascending``/``descending``) answer no -- the direction is part of the TASK SPECIFICATION (what
the child must do to produce a gradable action), and the graded response
(``{cols, rows, submitted_product}`` / ``arranged_values``) is a different, independent value.
Withholding the direction would make the item unanswerable; stating it leaks nothing about
whether the child's eventual answer is correct. These two templates are VARIANT-KEYED: each has
one wording string per discriminator value, and ``prompt_text_for`` resolves the correct one from
the task instance's own ``prompt_payload`` at serve time.

``C-CC-04`` (``trial_type``: ``add_remove``/``rearrange_only``) answers yes -- the trial type IS
the graded judgment (same-amount vs. changed-amount is exactly what conservation-of-number is
testing). Naming it in the wording would hand the child the response. ``C-CC-04`` therefore gets
ONE NEUTRAL STRING, true on both trial types and naming neither, never variant-keyed.

Every other template's ``prompt_payload`` either carries no discriminator or carries only values
that are already the task's stated inputs (e.g. the numbers being compared), not a fork in what
question is asked -- so every other template gets exactly one entry with no variant.

Resolution happens SERVER-SIDE, at task-serve time, from the task instance's actual
``prompt_payload``: ``prompt_text_for(game_task_template_id, prompt_payload)``. The frontend never
selects, composes, or branches -- it continues to relay whatever string this function returns,
verbatim.

NO DIGITS, BY RULE. Every string below is asserted, by this batch's freeze test, to contain no
ASCII digit character. This makes leaking a numeric answer into the wording structurally
impossible rather than checked case-by-case, and it is what forces the count-agnostic phrasing
above rather than leaving that to author discipline: a rule that simply said "don't state the
count" would still allow "the next two numbers" to slip in during a future edit; a rule that
bans digits outright cannot.

WHAT THIS TABLE DOES NOT DO: it never states a number, a comparison outcome, a judgment
("same"/"changed"), or any other single value that would itself be the graded response. Where a
template's correct answer is drawn from a small labelled set (e.g. C-CC-04's same/changed
judgment, C-MCL-02's left/right/equal selection), the wording names the CHOICES neutrally --
exactly as a multiple-choice question would -- never which one is correct. A template's
DIRECTION discriminator (C-EG-02, C-NP-04) is not in this category, since it is not itself a
choice the child makes or a value that is graded -- see the instruction-versus-answer rule above.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from app.domain.live_engine_c.errors import PromptWordingUnavailableError

TEST_FIXTURE_LABEL = "TEST_FIXTURE_ONLY"


@dataclass(frozen=True)
class PromptWordingVariant:
    """One row of wording. ``variant_key``/``variant_value`` are both ``None`` for a template with
    no payload-driven fork; both non-``None`` for one of its several variants. Never one of each --
    see module docstring for the instruction-versus-answer rule that decides which templates carry
    variants at all."""

    variant_key: Optional[str]
    variant_value: Optional[str]
    prompt_text: str


# Candidate wording -- see module docstring. All 30 supported template ids; 28 map to a
# single-element tuple (no variant), C-EG-02 and C-NP-04 map to two-element tuples (one per
# ``direction`` value). Every ``prompt_text`` value here must independently satisfy: no ASCII
# digit; no banned technical term; within the length/readability bound; does not name which of a
# labelled-choice answer set is correct.
PROMPT_TEXT_BY_TEMPLATE: Mapping[str, tuple[PromptWordingVariant, ...]] = {
    "C-BT-01": (PromptWordingVariant(None, None, "How many tens and how many ones?"),),
    "C-BT-02": (
        PromptWordingVariant(None, None, "How many hundreds, tens and ones?"),
    ),
    "C-BT-03": (
        PromptWordingVariant(
            None, None, "Change ten ones into one ten. Now how many tens and ones?"
        ),
    ),
    "C-BT-04": (
        PromptWordingVariant(
            None, None, "Change one ten into ten ones. Now how many tens and ones?"
        ),
    ),
    "C-CC-01": (
        PromptWordingVariant(
            None, None, "Tap each one time. Then write how many there are."
        ),
    ),
    "C-CC-02": (PromptWordingVariant(None, None, "Tap to put this many in the box."),),
    "C-CC-03": (
        PromptWordingVariant(None, None, "How many are there? Tap the number."),
    ),
    "C-CC-04": (
        PromptWordingVariant(
            None,
            None,
            "Look at both pictures. Is the number the same or different?",
        ),
    ),
    "C-EG-01": (
        PromptWordingVariant(
            None, None, "Make the groups. Put the same number in each group."
        ),
    ),
    "C-EG-02": (
        PromptWordingVariant("direction", "build", "Make the rows of squares shown."),
        PromptWordingVariant(
            "direction", "read", "Write a number in each box."
        ),
    ),
    "C-EG-03": (PromptWordingVariant(None, None, "How many are there in all the groups?"),),
    "C-JB-01": (PromptWordingVariant(None, None, "How many are there in both groups?"),),
    "C-JB-02": (
        PromptWordingVariant(
            None,
            None,
            "Use the jump buttons to add. What number do you stop at?",
        ),
    ),
    "C-JB-03": (PromptWordingVariant(None, None, "Add the two numbers."),),
    "C-JB-04": (
        PromptWordingVariant(
            None, None, "Add the two numbers. Did you change ten ones into a ten?"
        ),
    ),
    "C-MCL-01": (
        PromptWordingVariant(None, None, "How many are there? Tap the number."),
    ),
    "C-MCL-02": (
        PromptWordingVariant(None, None, "Which side has more? Or are they the same?"),
    ),
    "C-MCL-03": (
        PromptWordingVariant(
            None, None, "Less than, more than, or the same?"
        ),
    ),
    "C-MCL-04": (PromptWordingVariant(None, None, "Tap the buttons to go to the number."),),
    "C-NP-01": (PromptWordingVariant(None, None, "What number comes next?"),),
    "C-NP-02": (PromptWordingVariant(None, None, "What number comes just before this one?"),),
    "C-NP-03": (
        PromptWordingVariant(None, None, "Keep counting the same way. What number comes next?"),
    ),
    "C-NP-04": (
        PromptWordingVariant(
            "direction", "ascending", "Put these in order. Small to big."
        ),
        PromptWordingVariant(
            "direction", "descending", "Put these in order. Big to small."
        ),
    ),
    "C-SF-01": (
        PromptWordingVariant(None, None, "Share them equally. How many does each get?"),
    ),
    "C-SF-02": (
        PromptWordingVariant(
            None, None, "Make equal groups of this size. Show the groups you made."
        ),
    ),
    "C-SF-03": (PromptWordingVariant(None, None, "What is half of this number?"),),
    "C-TC-01": (
        PromptWordingVariant(None, None, "Take away this many. How many are left?"),
    ),
    "C-TC-02": (
        PromptWordingVariant(
            None, None, "How many more? Or how many fewer?"
        ),
    ),
    "C-TC-03": (
        PromptWordingVariant(None, None, "Take the second number away from the first."),
    ),
    "C-TC-04": (
        PromptWordingVariant(
            None,
            None,
            "Take the second number away from the first. Did you change a ten into ones?",
        ),
    ),
}


def prompt_text_for(game_task_template_id: str, prompt_payload: Mapping[str, object]) -> str:
    """The one production reader (``task_service._task_fields``) and the artefact generator both
    go through this, never through a bare ``PROMPT_TEXT_BY_TEMPLATE[...]`` lookup, so the
    structured-refusal behaviour lives in exactly one place.

    For a template with no variant, returns its single string unconditionally -- ``prompt_payload``
    is accepted but not consulted. For a variant-keyed template (``C-EG-02``, ``C-NP-04``), reads
    the variant key (``"direction"``) out of ``prompt_payload`` and returns the matching string.

    Raises ``PromptWordingUnavailableError`` -- a ``LiveEngineCError``, translated to
    ``ConflictError`` at the ``next_task`` call site like every other ``LiveEngineCError`` in that
    module -- in two cases, both fail-closed: (1) ``game_task_template_id`` has no entry at all
    (should be unreachable: the wording table's own coverage test asserts all 30 supported
    template ids are present -- defence in depth); (2) the template DOES have variants but the
    payload's discriminator value matches none of them (a real, reachable case -- a generator
    change introducing a value this table does not yet cover). Never falls back to a default
    string, never picks the first variant, never returns a placeholder: no wording is better than
    wrong wording."""
    try:
        variants = PROMPT_TEXT_BY_TEMPLATE[game_task_template_id]
    except KeyError:
        raise PromptWordingUnavailableError(game_task_template_id) from None

    first = variants[0]
    if first.variant_key is None:
        return first.prompt_text

    payload_value = prompt_payload.get(first.variant_key)
    for variant in variants:
        if variant.variant_value == payload_value:
            return variant.prompt_text
    raise PromptWordingUnavailableError(game_task_template_id) from None
