"""BE-C2 Part B: tolerant place-value comparison, scoped to structured templates only.

The defect: ``answers_equivalent`` is ``normalize_answer(a) == normalize_answer(b)``, which strips
outer whitespace only, so a child typing ``100+20+3`` instead of ``100 + 20 + 3`` was marked wrong on
a decomposition item purely over spacing. The reviewed parser that fixes this
(``parse_place_value_expression``) already shipped in the package and was simply never called from
the application layer.

The scope guard is the point of this file. Tolerant parsing applied everywhere would be actively
harmful: on an arithmetic template whose answer is 12, ``10+2`` would start matching, and the server
would be accepting a restatement of the problem as its answer.
"""

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from component_b_generator.answers.registry import allowed_equivalent_answers

from app.infrastructure.live_engine.adapter import LiveEngineAdapter


STRUCTURED_TEMPLATE = "B-PV04-DECOMPOSE-3D"
ARITHMETIC_TEMPLATE = "B-ADD04-2D-NO-REGROUP"


@pytest.fixture()
def adapter() -> LiveEngineAdapter:
    return LiveEngineAdapter()


# --- the gate: allowed_equivalent_answers is the structured-template signal ---------------------------


def test_allowed_equivalent_answers_is_non_empty_only_for_structured_templates() -> None:
    """The invariant the call-site scoping relies on.

    ``attempt_submission`` gates tolerant comparison on ``allowed_equivalent_answers`` being
    non-empty rather than importing the package's private ``_STRUCTURED_EQUIVALENCE_TEMPLATES``, so
    there is no duplicated template list to drift. This test is what makes that safe: it asserts the
    signal actually distinguishes the two cases.
    """
    assert allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123}) != ()
    assert allowed_equivalent_answers(ARITHMETIC_TEMPLATE, {"a": 10, "b": 2}) == ()


def test_structured_equivalents_are_the_forms_a_child_might_type() -> None:
    forms = allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123})
    assert "100 + 20 + 3" in forms
    assert "1 hundred + 2 tens + 3 ones" in forms


# --- tolerant comparison accepts the spacing variants -------------------------------------------------


@pytest.mark.parametrize("submitted", ["123", "100+20+3", "100 + 20 + 3", "100+20 + 3", " 100 + 20 + 3 "])
def test_structured_comparison_accepts_spacing_variants_of_123(
    adapter: LiveEngineAdapter, submitted: str
) -> None:
    accepted = ("123", *allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123}))
    assert any(adapter.structured_forms_equivalent(submitted, candidate) for candidate in accepted)


def test_structured_comparison_accepts_the_unit_word_form(adapter: LiveEngineAdapter) -> None:
    accepted = ("123", *allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123}))
    for submitted in ("1 hundreds + 2 tens + 3 ones", "1 hundred + 2 tens + 3 ones"):
        assert any(
            adapter.structured_forms_equivalent(submitted, candidate) for candidate in accepted
        )


def test_the_old_exact_comparison_is_what_was_rejecting_these(adapter: LiveEngineAdapter) -> None:
    # Records the actual defect: exact normalized matching fails on the unspaced form against every
    # accepted candidate, which is why a child typing it was told they were wrong.
    accepted = ("123", *allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123}))
    assert not any(adapter.answers_equivalent("100+20+3", candidate) for candidate in accepted)


# --- still rejects wrong answers ----------------------------------------------------------------------


@pytest.mark.parametrize("submitted", ["124", "100 + 20 + 4", "1 hundred + 2 tens + 4 ones", "23", "1230"])
def test_structured_comparison_still_rejects_wrong_values(
    adapter: LiveEngineAdapter, submitted: str
) -> None:
    accepted = ("123", *allowed_equivalent_answers(STRUCTURED_TEMPLATE, {"n": 123}))
    assert not any(
        adapter.structured_forms_equivalent(submitted, candidate) for candidate in accepted
    )


@pytest.mark.parametrize("submitted", ["", "   ", "abc", "12 + ", "+ 12", "100 + 20 + 3 + 4 + 5", "1 zillion"])
def test_unparseable_input_is_a_wrong_answer_not_a_server_error(
    adapter: LiveEngineAdapter, submitted: str
) -> None:
    # The adapter converts StructuredParseError into False: a child typing nonsense is wrong, not a
    # 500. Nothing here may raise.
    assert adapter.structured_forms_equivalent(submitted, "123") is False


def test_non_string_input_is_rejected_without_raising(adapter: LiveEngineAdapter) -> None:
    assert adapter.structured_forms_equivalent(None, "123") is False
    assert adapter.structured_forms_equivalent(123, "123") is False


# --- the scope guard: this must NOT apply to arithmetic templates --------------------------------------


def test_a_restatement_of_the_problem_would_match_if_scoping_were_removed(
    adapter: LiveEngineAdapter,
) -> None:
    """The reason tolerant comparison is gated rather than made the default.

    For an addition item 10 + 2 whose answer is 12, the parser happily reads "10+2" as 12. If this
    comparison were applied to every template, the server would accept the child restating the
    question instead of answering it. This test asserts the hazard is real, which is what makes the
    gate in ``attempt_submission`` load-bearing rather than decorative.
    """
    assert adapter.structured_forms_equivalent("10+2", "12") is True
    # And the gate that prevents it from ever being consulted for such a template:
    assert allowed_equivalent_answers(ARITHMETIC_TEMPLATE, {"a": 10, "b": 2}) == ()


def test_exact_comparison_still_rejects_the_restatement(adapter: LiveEngineAdapter) -> None:
    # The path an arithmetic template actually takes, unchanged by this batch.
    assert adapter.answers_equivalent("10+2", "12") is False
