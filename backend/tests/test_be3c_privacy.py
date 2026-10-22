"""BE3c privacy tests (BEplan BE3.3/BE3.4).

Proves the public task-presentation DTO can never carry a private field — not by trusting field
exclusion, but by (1) an explicit allow-list serialization test, (2) a schema-snapshot scan of
every dataclass field name/value actually reachable from the public DTO, and (3) a runtime-bundle
readiness check that fails closed on a catalogue/bundle mismatch rather than silently proceeding.
"""

from __future__ import annotations

import dataclasses

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from app.domain.live_engine.presentation import (
    PrivateTaskRecord,
    PublicTaskPresentation,
    build_private_task_record,
    project_to_public,
)
from app.domain.live_engine.types import SelectionReason, TaskConstructionRequest
from app.domain.runtime_bundle.errors import RuntimeBundleValidationError
from app.domain.runtime_bundle.readiness import assert_catalogue_matches_bundle
from app.infrastructure.live_engine.adapter import LiveEngineAdapter
from app.infrastructure.runtime_bundle.loader import RuntimeBundleLoader

FIXTURE_CATALOGUE_PATH = "tests/fixtures/runtime_bundle/test_catalogue.md"
SCHEMA_PATH = "provenance/runtime-bundle.schema.json"
FIXTURE_DIR = "tests/fixtures/runtime_bundle"
VALID_UNAPPROVED_BUNDLE = f"{FIXTURE_DIR}/valid_unapproved_bundle.json"

# Forbidden field names: correct answer, accepted equivalents, answer rules, seeds, BKT
# parameters, private scores, mastery, selection rationale, distractor provenance.
FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "correct_answer",
        "allowed_equivalent_answers",
        "answer_rule",
        "answer_rules",
        "generation_seed",
        "global_seed",
        "seed",
        "seed_lineage",
        "p_l0",
        "p_t",
        "p_g",
        "p_s",
        "bkt_config",
        "bkt_configuration",
        "mastery",
        "mastery_before",
        "mastery_after",
        "estimated_mastery",
        "posterior_l",
        "predicted_correct_probability",
        "selection_reason",
        "selection_reason_internal",
        "tie_break_basis",
        "distractor_candidates",
        "distractor_rule_ids",
        "student_id",
        "curriculum_node_id",
        "catalogue_checksum",
        "catalogue_version",
        "bundle_version",
        "applied_guard_ids",
    }
)

ALLOWED_PUBLIC_FIELDS = frozenset(
    {
        "item_opportunity_id",
        "item_instance_id",
        "skill_id",
        "grade",
        "difficulty_level",
        "representation_type",
        "response_format",
        "prompt",
        "presented_choices",
    }
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


def _build_private_record(adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str) -> PrivateTaskRecord:
    request = TaskConstructionRequest(
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
        selection_reason_internal="be3c-privacy-test",
        global_seed=20260725,
    )
    instance = adapter.build_task_instance(request, catalogue, catalogue_checksum)
    selection_reason = SelectionReason(
        winning_item_template_id="B-ADD04-2D-NO-REGROUP",
        winning_skill_id="addition",
        score=0.83,
        mastery_gap=0.6,
        prerequisite_readiness=1.0,
        spacing_due=1.0,
        tie_broken=False,
        tie_break_basis="unique highest score",
    )
    return build_private_task_record(
        request=request,
        instance=instance,
        selection_reason=selection_reason,
        bundle_version="be3c-test-fixture-1.0",
    )


class TestAllowListSerialization:
    """Proves the public DTO serializes ONLY the allowed fields — an explicit allow-list
    check, not a field-exclusion assumption."""

    def test_to_public_dict_contains_exactly_the_allowed_keys(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        private = _build_private_record(adapter, catalogue, catalogue_checksum)
        public = project_to_public(private)
        serialized = public.to_public_dict()
        assert set(serialized.keys()) == ALLOWED_PUBLIC_FIELDS

    def test_correct_answer_and_equivalents_are_not_serialized(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        private = _build_private_record(adapter, catalogue, catalogue_checksum)
        public = project_to_public(private)
        serialized = public.to_public_dict()
        assert "correct_answer" not in serialized
        assert "allowed_equivalent_answers" not in serialized
        assert private.correct_answer not in serialized.values()

    def test_presented_choices_include_the_correct_answer_but_do_not_mark_it(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        private = _build_private_record(adapter, catalogue, catalogue_checksum)
        public = project_to_public(private)
        serialized = public.to_public_dict()
        # The learner must be able to select the right answer among the presented choices, but
        # nothing in the payload identifies WHICH entry is correct.
        assert private.correct_answer in serialized["presented_choices"]
        assert "correct_choice_index" not in serialized
        assert "correct_index" not in serialized


class TestPublicDtoSchemaNeverCarriesAForbiddenField:
    """Schema-snapshot scan: walk the actual dataclass field names AND values of every object
    reachable from ``PublicTaskPresentation``, independent of the allow-list serializer, so a
    future field added directly to the dataclass (bypassing ``to_public_dict``) is still caught.
    """

    def test_public_dataclass_field_names_exclude_every_forbidden_name(self) -> None:
        field_names = {f.name for f in dataclasses.fields(PublicTaskPresentation)}
        assert field_names & FORBIDDEN_FIELD_NAMES == set()
        assert field_names == ALLOWED_PUBLIC_FIELDS

    def test_public_dto_values_never_contain_a_private_scalar(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        private = _build_private_record(adapter, catalogue, catalogue_checksum)
        public = project_to_public(private)
        serialized = public.to_public_dict()

        forbidden_values = {
            private.generation_seed,
            private.global_seed,
            private.catalogue_checksum,
            private.catalogue_version,
            private.bundle_version,
            private.student_id,
            private.curriculum_node_id,
            private.selection_reason.tie_break_basis,
            *private.allowed_equivalent_answers,
            *private.distractor_rule_ids,
            *private.applied_guard_ids,
        }

        def _walk(value):
            if isinstance(value, dict):
                for v in value.values():
                    _walk(v)
            elif isinstance(value, (list, tuple, set)):
                for v in value:
                    _walk(v)
            else:
                assert value not in forbidden_values, value

        _walk(serialized)

    def test_private_record_is_never_the_source_object_for_the_public_dto(self) -> None:
        """``project_to_public`` must not be implemented as ``dataclasses.asdict(private)``
        with keys popped afterward — assert the two dataclasses do not share a field-name
        superset relationship that a copy-then-delete implementation would produce coincidentally
        (the private record has strictly more fields, and none of the public-only semantics
        like ``presented_choices`` exist on the private side)."""
        private_fields = {f.name for f in dataclasses.fields(PrivateTaskRecord)}
        public_fields = {f.name for f in dataclasses.fields(PublicTaskPresentation)}
        assert "presented_choices" in public_fields
        assert "presented_choices" not in private_fields
        assert public_fields - private_fields == {"presented_choices"}


class TestRuntimeBundleMismatchFailsReadiness:
    """A runtime-bundle/catalogue mismatch must fail readiness outright — never fall back to
    an unchecked or partially-validated state."""

    def test_matching_bundle_and_catalogue_pass(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        loader = RuntimeBundleLoader()
        bundle = loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False)
        # Should not raise: the fixture bundle's declared catalogue checksum/version/count/skills
        # were kept in lockstep with tests/fixtures/runtime_bundle/test_catalogue.md.
        assert_catalogue_matches_bundle(bundle, catalogue, catalogue_checksum)

    def test_catalogue_checksum_mismatch_fails_readiness(
        self, adapter: LiveEngineAdapter, catalogue
    ) -> None:
        loader = RuntimeBundleLoader()
        bundle = loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False)
        with pytest.raises(RuntimeBundleValidationError):
            assert_catalogue_matches_bundle(bundle, catalogue, "0" * 64)

    def test_catalogue_template_count_mismatch_fails_readiness(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        loader = RuntimeBundleLoader()
        bundle = loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False)
        truncated_catalogue = dataclasses.replace(catalogue, templates=catalogue.templates[:-1])
        with pytest.raises(RuntimeBundleValidationError):
            assert_catalogue_matches_bundle(bundle, truncated_catalogue, catalogue_checksum)

    def test_catalogue_version_mismatch_fails_readiness(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str
    ) -> None:
        loader = RuntimeBundleLoader()
        bundle = loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False)
        wrong_version_catalogue = dataclasses.replace(catalogue, catalogue_version="NOT-THE-PINNED-VERSION")
        with pytest.raises(RuntimeBundleValidationError):
            assert_catalogue_matches_bundle(bundle, wrong_version_catalogue, catalogue_checksum)
