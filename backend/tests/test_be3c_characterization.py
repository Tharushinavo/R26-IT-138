"""BE3c characterization tests (BEplan BE3.4).

Fixed, TEST-FIXTURE-ONLY provenance only — no live learner flow, no real approved runtime
bundle, no crossing the BE4 scientific gate. ``tests/fixtures/runtime_bundle/test_catalogue.md``
covers all 36 template ids from ``backend/provenance/component-b-coverage.json`` (29 implemented
+ 7 deferred), so every implemented/deferred partition claim in that provenance file can be
exercised directly against the adapter.
"""

from __future__ import annotations

import json
import random

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from app.domain.live_engine.errors import HintUnavailableError, TemplateNotActiveError
from app.domain.live_engine.types import (
    ScoredCandidate,
    SequencingCandidate,
    SequencingFeatures,
    TaskConstructionRequest,
)
from app.infrastructure.live_engine.adapter import LiveEngineAdapter

FIXTURE_CATALOGUE_PATH = "tests/fixtures/runtime_bundle/test_catalogue.md"
COVERAGE_PROVENANCE_PATH = "provenance/component-b-coverage.json"


@pytest.fixture(scope="module")
def adapter() -> LiveEngineAdapter:
    return LiveEngineAdapter()


@pytest.fixture(scope="module")
def catalogue(adapter: LiveEngineAdapter):
    return adapter.load(FIXTURE_CATALOGUE_PATH)


@pytest.fixture(scope="module")
def catalogue_checksum(adapter: LiveEngineAdapter) -> str:
    return adapter.checksum(FIXTURE_CATALOGUE_PATH)


@pytest.fixture(scope="module")
def coverage() -> dict:
    with open(COVERAGE_PROVENANCE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _request(item_template_id: str, skill_id: str, grade: int, curriculum_node_id: str, seed: int = 20260725):
    return TaskConstructionRequest(
        item_opportunity_id="STU-0001-B001-I001",
        student_id="STU-0001",
        grade=grade,
        scheduled_session_number=1,
        b_session_index=1,
        item_index=1,
        event_order=1,
        item_template_id=item_template_id,
        skill_id=skill_id,
        curriculum_node_id=curriculum_node_id,
        selection_reason_internal="be3c-characterization-test",
        global_seed=seed,
    )


class TestCoverageProvenanceMatchesFixtureCatalogue:
    """Sanity check that the fixture catalogue actually implements the partition claimed by
    ``component-b-coverage.json``, before trusting the tests built on top of it."""

    def test_fixture_catalogue_has_all_36_templates(self, catalogue) -> None:
        assert len(catalogue.templates) == 36

    def test_fixture_covers_every_implemented_template_id(self, catalogue, coverage: dict) -> None:
        fixture_ids = {t.item_template_id for t in catalogue.templates}
        for template_id in coverage["implemented_template_ids"]:
            assert template_id in fixture_ids, template_id

    def test_fixture_covers_every_deferred_template_id(self, catalogue, coverage: dict) -> None:
        fixture_ids = {t.item_template_id for t in catalogue.templates}
        for entry in coverage["deferred_templates"]:
            assert entry["template_id"] in fixture_ids, entry["template_id"]


class TestAllImplementedTemplatesGenerate:
    """Every one of the 29 implemented, grade-eligible templates must build a valid instance
    for each grade it is eligible for."""

    def test_every_implemented_template_generates_for_every_eligible_grade(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str, coverage: dict
    ) -> None:
        implemented_ids = set(coverage["implemented_template_ids"])
        checked_ids: set[str] = set()
        pair_count = 0
        for template in catalogue.templates:
            if template.item_template_id not in implemented_ids:
                continue
            for grade in template.eligible_grades:
                request = _request(
                    template.item_template_id, template.skill_id, grade, template.curriculum_node_id
                )
                instance = adapter.build_task_instance(request, catalogue, catalogue_checksum)
                assert instance.item_template_id == template.item_template_id
                assert instance.grade == grade
                assert instance.correct_answer not in instance.distractor_candidates
                checked_ids.add(template.item_template_id)
                pair_count += 1
        assert checked_ids == implemented_ids, "every implemented template id must have generated at least once"
        expected_pairs = sum(len(t.eligible_grades) for t in catalogue.templates if t.item_template_id in implemented_ids)
        assert pair_count == expected_pairs


class TestDeferredTemplatesFailClosed:
    """Every one of the 7 deferred templates must fail closed — never fabricate an instance."""

    def test_every_deferred_template_fails_closed(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str, coverage: dict
    ) -> None:
        deferred_ids = [entry["template_id"] for entry in coverage["deferred_templates"]]
        assert len(deferred_ids) == 7
        for template_id in deferred_ids:
            template = catalogue.by_id(template_id)
            assert template is not None
            for grade in (2, 3):
                request = _request(template_id, template.skill_id, grade, template.curriculum_node_id)
                with pytest.raises(TemplateNotActiveError):
                    adapter.build_task_instance(request, catalogue, catalogue_checksum)


class TestDeterminismUnderFixedProvenance:
    def test_every_implemented_template_is_deterministic(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str, coverage: dict
    ) -> None:
        for template_id in coverage["implemented_template_ids"]:
            template = catalogue.by_id(template_id)
            grade = template.eligible_grades[0]
            request = _request(template_id, template.skill_id, grade, template.curriculum_node_id, seed=4242)
            first = adapter.build_task_instance(request, catalogue, catalogue_checksum)
            second = adapter.build_task_instance(request, catalogue, catalogue_checksum)
            assert first == second


class TestGradeGatesHold:
    def test_grade_2_never_receives_multiplication_or_division(self, catalogue) -> None:
        grade_2_skills = {t.skill_id for t in catalogue.eligible_for(2)}
        assert "multiplication" not in grade_2_skills
        assert "division" not in grade_2_skills

    def test_multiplication_and_division_templates_are_inactive_for_grade_2(
        self, adapter: LiveEngineAdapter, catalogue, coverage: dict
    ) -> None:
        implemented_ids = set(coverage["implemented_template_ids"])
        mul_div_templates = [
            t for t in catalogue.templates
            if t.skill_id in ("multiplication", "division") and t.item_template_id in implemented_ids
        ]
        assert mul_div_templates
        for template in mul_div_templates:
            decision = adapter.decide_activation(
                catalogue, template.item_template_id, adapter.supported_template_ids(), grade=2
            )
            assert not decision.active
            assert not decision.grade_eligible


class TestCanonicalSequencingTieBreaksAreStable:
    def _tied_candidates(self):
        features = SequencingFeatures(mastery_gap=0.5, prerequisite_readiness=0.5, spacing_due=0.5)
        addition = ScoredCandidate(
            candidate=SequencingCandidate("addition", "B-ADD99-FIXTURE", 1), features=features, score=0.5
        )
        subtraction = ScoredCandidate(
            candidate=SequencingCandidate("subtraction", "B-SUB99-FIXTURE", 1), features=features, score=0.5
        )
        addition_2 = ScoredCandidate(
            candidate=SequencingCandidate("addition", "B-ADD01-COMBINE-SETS", 1), features=features, score=0.5
        )
        return [subtraction, addition, addition_2]

    def test_tie_break_prefers_skill_order_then_lexicographic_template_id(
        self, adapter: LiveEngineAdapter
    ) -> None:
        candidates = self._tied_candidates()
        result = adapter.select_target(candidates)
        assert result.selection_reason.tie_broken
        assert result.selection_reason.tie_break_basis == "skill order, then lexicographic item_template_id"
        # addition (skill rank 3) beats subtraction (skill rank 4); within addition, lexicographic
        # "B-ADD01-COMBINE-SETS" < "B-ADD99-FIXTURE".
        assert result.candidate.item_template_id == "B-ADD01-COMBINE-SETS"

    def test_tie_break_is_stable_regardless_of_input_order_and_repetition(
        self, adapter: LiveEngineAdapter
    ) -> None:
        candidates = self._tied_candidates()
        rng = random.Random(1234)
        winners = set()
        for _ in range(5):
            shuffled = list(candidates)
            rng.shuffle(shuffled)
            result = adapter.select_target(shuffled)
            winners.add(result.candidate.item_template_id)
        assert winners == {"B-ADD01-COMBINE-SETS"}


class TestHintTextAndChecksumProvenance:
    def test_hint_content_is_exact_catalogue_text(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        hint = adapter.get_hint(catalogue, catalogue_checksum, "B-ADD04-2D-NO-REGROUP", 1)
        # Verbatim from R26-IT-138 §11. Until the hint port, the fixture carried text written for
        # the fixture itself ("Add the ones first, then the tens.") rather than the governed
        # string, so this assertion was pinning unreviewed content.
        assert hint.content == "Add ones with ones and tens with tens."
        assert hint.catalogue_checksum == catalogue_checksum
        assert hint.catalogue_version == catalogue.catalogue_version

    def test_absent_hint_content_fails_closed_never_a_generated_fallback(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        """Fail-closed coverage for absent hint content.

        NOTE: no catalogue template exercises the missing-content path any more. All 36 templates
        now carry governed L1/L2/L3 text (the fixture previously had hints on only two), so
        ``B-DIV03-DIVIDE-BY-2`` — which this test used to use — resolves successfully. Absence is
        therefore constructed explicitly below rather than borrowed from a gap in the data. The
        guarantee under test is unchanged and deliberately still covered: when content cannot be
        produced, ``get_hint`` raises rather than synthesizing, paraphrasing or approximating
        anything (``behaviour/hints.py`` documents both paths as fail-closed).
        """
        with pytest.raises(HintUnavailableError):
            adapter.get_hint(catalogue, catalogue_checksum, "B-NOT-A-REAL-TEMPLATE", 1)
        with pytest.raises(HintUnavailableError):
            adapter.get_hint(catalogue, catalogue_checksum, "B-DIV03-DIVIDE-BY-2", 4)
