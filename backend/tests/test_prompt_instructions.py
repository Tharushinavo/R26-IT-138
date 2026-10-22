"""The authored instruction sentence added to templates whose stem is not a question on its own.

See app/domain/live_engine/prompt_instructions.py for why this text is Upadya's and lives here
rather than in the vendored generator wheel.
"""

from types import SimpleNamespace

from app.domain.b_opportunity import project_task_instance_to_presentation
from app.domain.live_engine.prompt_instructions import (
    INSTRUCTION_BY_TEMPLATE,
    INSTRUCTION_PROMPT_KEY,
    instruction_for,
)
from datetime import UTC, datetime


def task_instance(item_template_id: str, prompt: dict) -> SimpleNamespace:
    """The SAFE columns the projection reads, plus the private ones it must not project."""
    return SimpleNamespace(
        item_opportunity_id="11111111-1111-1111-1111-111111111111",
        task_instance_id="22222222-2222-2222-2222-222222222222",
        item_template_id=item_template_id,
        skill_id="counting",
        grade=2,
        difficulty_level="L1",
        representation_type="numeral",
        response_format="single_integer",
        prompt=prompt,
        presented_choices=["4", "5", "6", "7"],
        correct_answer="6",
        generated_operands={"sequence": [2, 3, 4, 5]},
    )


def project(record: SimpleNamespace):
    return project_task_instance_to_presentation(
        record,
        presentation_token="token",
        server_timeout_deadline_utc=datetime.now(UTC),
    )


def test_sequence_template_gains_an_instruction_and_its_stem_is_untouched() -> None:
    """The gap this exists to close: "2, 3, 4, 5, __" reached a child with no instruction."""
    stem = "2, 3, 4, 5, __"
    presented = project(
        task_instance("B-CNT01-SEQ-CONTINUE", {"stem": stem, "sequence_shown": [2, 3, 4, 5], "blank_position": "terminal"})
    )
    assert presented.prompt[INSTRUCTION_PROMPT_KEY] == "What number comes next?"
    # The generator's own text is relayed byte-for-byte; the instruction is additive.
    assert presented.prompt["stem"] == stem
    assert presented.prompt["sequence_shown"] == [2, 3, 4, 5]


def test_comparison_template_gets_its_own_wording_not_the_counting_one() -> None:
    """B-NS04's blank holds an operator, so "guess the next number" would be actively wrong."""
    presented = project(task_instance("B-NS04-COMPARE-NUMERALS", {"stem": "7 __ 9", "left": 7, "right": 9}))
    # "Tap the correct sign." since 2026-10-20 -- "right" was read as the DIRECTION on screens that
    # have left/right layouts, and the Sinhala table already said නිවැරදි ("correct").
    assert presented.prompt[INSTRUCTION_PROMPT_KEY] == "Tap the correct sign."
    # The POINT of this test, asserted rather than implied: whatever the wording is, it must not be
    # the counting instruction, because this blank holds an operator and not a number.
    assert presented.prompt[INSTRUCTION_PROMPT_KEY] != INSTRUCTION_BY_TEMPLATE["B-CNT01-SEQ-CONTINUE"]


def test_templates_whose_stem_already_asks_a_question_get_nothing_added() -> None:
    """Absence from the mapping is the correct default, not an oversight."""
    for template_id, stem in (
        ("B-ADD03-SINGLE-DIGIT", "6 + 1 = ?"),
        ("B-SUB05-BORROW", "85 - 77 = ?"),
        ("B-MUL03-FACTS-2-5-10", "5 x 2 = ?"),
        ("B-DIV03-DIVIDE-BY-2", "42 / 2 = ?"),
    ):
        presented = project(task_instance(template_id, {"stem": stem}))
        assert INSTRUCTION_PROMPT_KEY not in presented.prompt, template_id
        assert presented.prompt["stem"] == stem


def test_a_generator_supplied_instruction_wins_over_the_authored_one() -> None:
    """If the wheel ever emits its own, this module must become a no-op rather than overwrite it."""
    presented = project(
        task_instance("B-CNT01-SEQ-CONTINUE", {"stem": "2, 3, __", INSTRUCTION_PROMPT_KEY: "From the wheel."})
    )
    assert presented.prompt[INSTRUCTION_PROMPT_KEY] == "From the wheel."


def test_the_private_template_id_never_reaches_the_projected_dto() -> None:
    """item_template_id is read to look the instruction up and must stay off the wire, like every
    other private column the safe-DTO allow-list excludes."""
    presented = project(task_instance("B-CNT01-SEQ-CONTINUE", {"stem": "2, 3, __"}))
    serialized = presented.to_public_dict() if hasattr(presented, "to_public_dict") else vars(presented)
    flat = repr(serialized)
    assert "B-CNT01-SEQ-CONTINUE" not in flat
    assert "item_template_id" not in serialized


def test_the_projection_does_not_mutate_the_stored_prompt() -> None:
    """The record's own dict must not gain a key -- it is the persisted row, not a view model."""
    stored = {"stem": "2, 3, __"}
    record = task_instance("B-CNT01-SEQ-CONTINUE", stored)
    project(record)
    assert INSTRUCTION_PROMPT_KEY not in stored
    assert record.prompt is stored


def test_every_authored_instruction_is_non_empty_and_child_readable() -> None:
    assert INSTRUCTION_BY_TEMPLATE, "the mapping must not be silently emptied"
    for template_id, text in INSTRUCTION_BY_TEMPLATE.items():
        assert template_id.startswith("B-"), template_id
        assert text.strip() == text and text, template_id
        assert text.endswith((".", "?")), f"{template_id}: instruction should be a sentence"
        assert instruction_for(template_id) == text
    assert instruction_for("B-DOES-NOT-EXIST") is None
