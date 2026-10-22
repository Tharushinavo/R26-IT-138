"""BE3b adapter tests: the domain ports call the live-engine package and correctly map
backend domain types <-> package types, and translate package exceptions into the stable
``app.domain.live_engine.errors`` hierarchy. No live learner flow, no real approved scientific
parameters — every fixture used here is explicitly a TEST-FIXTURE-ONLY catalogue, never the
governed R26-IT-138 catalogue.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from app.domain.live_engine.errors import (
    HintUnavailableError,
    LiveEngineError,
    UnknownTemplateError,
)
from app.domain.live_engine.types import (
    BktConfig,
    GuessGuardStatus,
    OpportunityResponse,
    ScoredCandidate,
    SequencingCandidate,
    SessionIdentity,
    SkillBktParams,
    SkillMasteryUpdate,
    TaskConstructionRequest,
)
from app.infrastructure.live_engine.adapter import LiveEngineAdapter

FIXTURE_CATALOGUE_PATH = "tests/fixtures/runtime_bundle/test_catalogue.md"
SEVEN_SKILLS = (
    "counting",
    "number_sense",
    "place_value",
    "addition",
    "subtraction",
    "multiplication",
    "division",
)


@pytest.fixture(scope="module")
def adapter() -> LiveEngineAdapter:
    return LiveEngineAdapter()


@pytest.fixture(scope="module")
def catalogue(adapter: LiveEngineAdapter):
    return adapter.load(FIXTURE_CATALOGUE_PATH)


@pytest.fixture(scope="module")
def catalogue_checksum(adapter: LiveEngineAdapter) -> str:
    return adapter.checksum(FIXTURE_CATALOGUE_PATH)


def _bkt_config() -> BktConfig:
    return BktConfig(
        skill_params={
            skill: SkillBktParams(p_l0=0.2, p_t=0.15, p_g=0.2, p_s=0.1) for skill in SEVEN_SKILLS
        },
        theta_b=0.8,
        floor_quantile=0.1,
        floor_min_obs=5,
        config_version="test-fixture-1.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
    )


class TestCataloguePort:
    def test_load_maps_every_template_and_the_seven_skills(self, catalogue) -> None:
        assert catalogue.catalogue_version == "TEST-FIXTURE-1.0"
        assert catalogue.skills == SEVEN_SKILLS
        assert {t.skill_id for t in catalogue.templates} == set(SEVEN_SKILLS)
        template = catalogue.by_id("B-ADD04-2D-NO-REGROUP")
        assert template is not None
        assert template.eligible_grades == (3,)
        assert template.is_active()

    def test_checksum_is_stable(self, adapter: LiveEngineAdapter, catalogue_checksum: str) -> None:
        assert adapter.checksum(FIXTURE_CATALOGUE_PATH) == catalogue_checksum
        assert len(catalogue_checksum) == 64


class TestActivationPort:
    def test_active_for_eligible_grade(self, adapter: LiveEngineAdapter, catalogue) -> None:
        decision = adapter.decide_activation(
            catalogue, "B-ADD04-2D-NO-REGROUP", adapter.supported_template_ids(), grade=3
        )
        assert decision.active
        assert decision.grade_eligible

    def test_inactive_for_ineligible_grade(self, adapter: LiveEngineAdapter, catalogue) -> None:
        decision = adapter.decide_activation(
            catalogue, "B-ADD04-2D-NO-REGROUP", adapter.supported_template_ids(), grade=2
        )
        assert not decision.active
        assert not decision.grade_eligible

    def test_unknown_template_raises_stable_error(self, adapter: LiveEngineAdapter, catalogue) -> None:
        with pytest.raises(UnknownTemplateError):
            adapter.decide_activation(catalogue, "B-DOES-NOT-EXIST", (), grade=3)


class TestTaskConstructionPort:
    def _request(self) -> TaskConstructionRequest:
        return TaskConstructionRequest(
            item_opportunity_id="STU-0001-B001-I001",
            student_id="STU-0001",
            grade=3,
            scheduled_session_number=1,
            b_session_index=1,
            item_index=1,
            event_order=1,
            item_template_id="B-ADD04-2D-NO-REGROUP",
            skill_id="addition",
            curriculum_node_id="NODE-ADD-04",
            selection_reason_internal="be3b-adapter-test",
            global_seed=20260724,
        )

    def test_deterministic_under_fixed_provenance(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        request = self._request()
        first = adapter.build_task_instance(request, catalogue, catalogue_checksum)
        second = adapter.build_task_instance(request, catalogue, catalogue_checksum)
        assert first == second

    def test_operands_and_correct_answer_are_internally_consistent(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        instance = adapter.build_task_instance(self._request(), catalogue, catalogue_checksum)
        assert instance.generated_operands["a"] + instance.generated_operands["b"] == int(
            instance.correct_answer
        )
        assert instance.correct_answer not in instance.distractor_candidates
        recomputed_raw = adapter.correct_answer_raw("B-ADD04-2D-NO-REGROUP", instance.generated_operands)
        assert adapter.normalize_answer(recomputed_raw) == instance.correct_answer

    def test_different_global_seed_changes_operands(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        request_a = self._request()
        request_b = TaskConstructionRequest(**{**request_a.__dict__, "global_seed": 999})
        instance_a = adapter.build_task_instance(request_a, catalogue, catalogue_checksum)
        instance_b = adapter.build_task_instance(request_b, catalogue, catalogue_checksum)
        assert instance_a.generation_seed != instance_b.generation_seed


class TestHintPort:
    def test_governed_hint_content_is_returned(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        hint = adapter.get_hint(catalogue, catalogue_checksum, "B-ADD04-2D-NO-REGROUP", 1)
        # Verbatim from R26-IT-138 §11. Until the hint port, the fixture carried text written for
        # the fixture itself ("Add the ones first, then the tens.") rather than the governed
        # string, so this assertion was pinning unreviewed content.
        assert hint.content == "Add ones with ones and tens with tens."
        assert hint.hint_level == 1

    def test_absent_hint_content_fails_closed(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        """Fail-closed coverage for absent hint content.

        NOTE: no catalogue template exercises the missing-content path any more. All 36 templates
        now carry governed L1/L2/L3 text, so ``B-DIV03-DIVIDE-BY-2`` — which this test used to use
        — resolves successfully. Absence is constructed explicitly below instead of being borrowed
        from a gap in the data; the guarantee itself (raise, never synthesize a fallback) is
        unchanged and still covered.
        """
        with pytest.raises(HintUnavailableError):
            adapter.get_hint(catalogue, catalogue_checksum, "B-NOT-A-REAL-TEMPLATE", 1)
        with pytest.raises(HintUnavailableError):
            adapter.get_hint(catalogue, catalogue_checksum, "B-DIV03-DIVIDE-BY-2", 4)


class TestBktPort:
    def test_predict_posterior_update_are_bounded_and_deterministic(self, adapter: LiveEngineAdapter) -> None:
        first = (
            adapter.predict(0.3, 0.2, 0.1),
            adapter.posterior(0.3, True, 0.2, 0.1),
            adapter.update(0.3, True, 0.2, 0.1, 0.15),
        )
        second = (
            adapter.predict(0.3, 0.2, 0.1),
            adapter.posterior(0.3, True, 0.2, 0.1),
            adapter.update(0.3, True, 0.2, 0.1, 0.15),
        )
        assert first == second
        assert all(0.0 <= value <= 1.0 for value in first)

    def test_incorrect_posterior_is_lower_than_correct_posterior(self, adapter: LiveEngineAdapter) -> None:
        correct_posterior = adapter.posterior(0.3, True, 0.2, 0.1)
        incorrect_posterior = adapter.posterior(0.3, False, 0.2, 0.1)
        assert incorrect_posterior < correct_posterior


class TestGuessGuardAndCertificationPorts:
    def test_triggered_when_fast_and_above_threshold(self, adapter: LiveEngineAdapter) -> None:
        status = adapter.evaluate(0.9, 2.0, [3.0, 3.2, 3.1, 2.9, 3.0], theta_b=0.8, q=0.1, n_min=5)
        assert status is GuessGuardStatus.TRIGGERED
        assert adapter.certify_skill(0.9, status, theta_b=0.8) is False

    def test_insufficient_evidence_below_min_observations(self, adapter: LiveEngineAdapter) -> None:
        status = adapter.evaluate(0.9, 2.0, [3.0], theta_b=0.8, q=0.1, n_min=5)
        assert status is GuessGuardStatus.INSUFFICIENT_EVIDENCE
        assert adapter.certify_skill(0.9, status, theta_b=0.8) is False

    def test_certifies_only_above_threshold_and_not_triggered(self, adapter: LiveEngineAdapter) -> None:
        status = adapter.evaluate(0.9, 5.0, [3.0, 3.2, 3.1, 2.9, 3.0], theta_b=0.8, q=0.1, n_min=5)
        assert status is GuessGuardStatus.NOT_TRIGGERED
        assert adapter.certify_skill(0.9, status, theta_b=0.8) is True


class TestSequencingPort:
    def test_score_uses_the_frozen_weights(
        self, adapter: LiveEngineAdapter, catalogue
    ) -> None:
        from app.domain.live_engine.types import SequencingFeatures

        candidate = SequencingCandidate(skill_id="addition", item_template_id="B-ADD04-2D-NO-REGROUP", difficulty_band=1)
        features = adapter.compute_features(
            candidate, {"addition": 0.4}, catalogue, {"addition": None}, _bkt_config()
        )
        assert features.mastery_gap == pytest.approx(0.6)
        assert features.prerequisite_readiness == pytest.approx(1.0)
        assert features.spacing_due == pytest.approx(1.0)

        score = adapter.score_candidate(features)
        assert score == pytest.approx(0.50 * 0.6 + 0.30 * 1.0 + 0.20 * 1.0)

    def test_select_target_picks_highest_score(self, adapter: LiveEngineAdapter) -> None:
        from app.domain.live_engine.types import SequencingFeatures

        low = ScoredCandidate(
            candidate=SequencingCandidate("addition", "B-ADD04-2D-NO-REGROUP", 1),
            features=SequencingFeatures(0.1, 1.0, 0.0),
            score=0.1,
        )
        high = ScoredCandidate(
            candidate=SequencingCandidate("subtraction", "B-SUB04-2D-NO-BORROW", 1),
            features=SequencingFeatures(0.9, 1.0, 1.0),
            score=0.9,
        )
        result = adapter.select_target([low, high])
        assert result.candidate.item_template_id == "B-SUB04-2D-NO-BORROW"
        assert not result.selection_reason.tie_broken


class TestAggregationPort:
    def test_aggregate_session_folds_one_opportunity(self, adapter: LiveEngineAdapter) -> None:
        identity = SessionIdentity(
            student_id="STU-0001", b_session_index=1, scheduled_session_number=1, status="attended"
        )
        opportunity = OpportunityResponse(
            learner_id="STU-0001",
            session_id="STU-0001-B-001",
            scheduled_session_index=1,
            item_opportunity_id="STU-0001-B001-I001",
            task_instance_id="STU-0001-B001-I001-X001",
            item_template_id="B-ADD04-2D-NO-REGROUP",
            skill_id="addition",
            first_attempt_correct=True,
            first_attempt_error_pattern="correct",
            total_attempts=1,
            hint_requested=False,
            hint_count=0,
            final_item_completed=True,
            assisted_completion=False,
            unassisted_completion=True,
            total_response_time_ms=3000,
            first_attempt_response_time_ms=3000,
        )
        update = SkillMasteryUpdate(
            student_id="STU-0001",
            skill_id="addition",
            b_session_index=1,
            mastery_before=0.3,
            predicted_correct_probability=0.5,
            posterior_l=0.6,
            mastery_after=0.65,
        )

        result = adapter.aggregate_session(identity, [opportunity], [update])

        assert result.status == "attended"
        assert result.opportunity_ids == ("STU-0001-B001-I001",)
        assert result.stats.first_attempt_accuracy == pytest.approx(1.0)
        assert result.skill_rollups[0].estimated_mastery == pytest.approx(0.65)

    def test_missed_session_with_opportunities_raises(self, adapter: LiveEngineAdapter) -> None:
        identity = SessionIdentity(
            student_id="STU-0001", b_session_index=2, scheduled_session_number=2, status="missed"
        )
        opportunity = OpportunityResponse(
            learner_id="STU-0001",
            session_id="STU-0001-B-002",
            scheduled_session_index=2,
            item_opportunity_id="STU-0001-B002-I001",
            task_instance_id="STU-0001-B002-I001-X001",
            item_template_id="B-ADD04-2D-NO-REGROUP",
            skill_id="addition",
            first_attempt_correct=True,
            first_attempt_error_pattern="correct",
            total_attempts=1,
            hint_requested=False,
            hint_count=0,
            final_item_completed=True,
            assisted_completion=False,
            unassisted_completion=True,
            total_response_time_ms=3000,
            first_attempt_response_time_ms=3000,
        )
        with pytest.raises(LiveEngineError):
            adapter.aggregate_session(identity, [opportunity], [])
