"""BE3b runtime-bundle load/validate tests: fail-closed on every defect class.

``valid_unapproved_bundle.json`` is a schema-valid, checksum-correct TEST-FIXTURE-ONLY manifest
that is deliberately never marked ``APPROVED`` — approving a bundle is the separate BE4
governance gate, out of scope here. It exists to prove the loader's positive paths (schema
validation, checksum verification) work, while also proving the approval gate fails closed on
exactly that same, otherwise-valid bundle.
"""

from __future__ import annotations

import json

import pytest

from app.domain.runtime_bundle.errors import (
    RuntimeBundleChecksumMismatchError,
    RuntimeBundleNotApprovedError,
    RuntimeBundleNotFoundError,
    RuntimeBundleValidationError,
)
from app.infrastructure.runtime_bundle.loader import RuntimeBundleLoader

SCHEMA_PATH = "provenance/runtime-bundle.schema.json"
FIXTURE_DIR = "tests/fixtures/runtime_bundle"
VALID_UNAPPROVED_BUNDLE = f"{FIXTURE_DIR}/valid_unapproved_bundle.json"
MISSING_FIELD_BUNDLE = f"{FIXTURE_DIR}/missing_field_bundle.json"
BAD_CHECKSUM_BUNDLE = f"{FIXTURE_DIR}/bad_checksum_bundle.json"
CATALOGUE_FIXTURE_PATH = f"{FIXTURE_DIR}/test_catalogue.md"


@pytest.fixture()
def loader() -> RuntimeBundleLoader:
    return RuntimeBundleLoader()


class TestPositivePaths:
    def test_schema_valid_checksum_correct_bundle_loads_when_approval_not_required(
        self, loader: RuntimeBundleLoader
    ) -> None:
        bundle = loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False)
        assert bundle.bundle_version == "be3b-test-fixture-1.0"
        assert bundle.generator.source_identifier == "upadya-component-b-live-engine"
        assert bundle.compatibility.skills == (
            "counting",
            "number_sense",
            "place_value",
            "addition",
            "subtraction",
            "multiplication",
            "division",
        )
        assert bundle.sequencing_configuration.weights == {
            "mastery_gap": 0.5,
            "prerequisite_readiness": 0.3,
            "spacing_due": 0.2,
        }

    def test_artifact_paths_verifies_additional_declared_checksums(
        self, loader: RuntimeBundleLoader
    ) -> None:
        bundle = loader.load_and_validate(
            VALID_UNAPPROVED_BUNDLE,
            SCHEMA_PATH,
            require_approved=False,
            artifact_paths={"catalogue": CATALOGUE_FIXTURE_PATH},
        )
        assert bundle.catalogue.version == "TEST-FIXTURE-1.0"


class TestFailClosed:
    def test_missing_required_field_fails_closed(self, loader: RuntimeBundleLoader) -> None:
        with pytest.raises(RuntimeBundleValidationError):
            loader.load_and_validate(MISSING_FIELD_BUNDLE, SCHEMA_PATH, require_approved=False)

    def test_generator_checksum_mismatch_fails_closed(self, loader: RuntimeBundleLoader) -> None:
        with pytest.raises(RuntimeBundleChecksumMismatchError):
            loader.load_and_validate(BAD_CHECKSUM_BUNDLE, SCHEMA_PATH, require_approved=False)

    def test_artifact_path_checksum_mismatch_fails_closed(
        self, loader: RuntimeBundleLoader, tmp_path
    ) -> None:
        wrong_file = tmp_path / "not_the_catalogue.md"
        wrong_file.write_text("this is not the fixture catalogue", encoding="utf-8")
        with pytest.raises(RuntimeBundleChecksumMismatchError):
            loader.load_and_validate(
                VALID_UNAPPROVED_BUNDLE,
                SCHEMA_PATH,
                require_approved=False,
                artifact_paths={"catalogue": str(wrong_file)},
            )

    def test_unapproved_status_fails_closed_by_default(self, loader: RuntimeBundleLoader) -> None:
        with pytest.raises(RuntimeBundleNotApprovedError):
            loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH)

    def test_missing_manifest_file_fails_closed(self, loader: RuntimeBundleLoader) -> None:
        with pytest.raises(RuntimeBundleNotFoundError):
            loader.load_and_validate(f"{FIXTURE_DIR}/does_not_exist.json", SCHEMA_PATH, require_approved=False)

    def test_missing_schema_file_fails_closed(self, loader: RuntimeBundleLoader) -> None:
        with pytest.raises(RuntimeBundleNotFoundError):
            loader.load_and_validate(VALID_UNAPPROVED_BUNDLE, f"{FIXTURE_DIR}/does_not_exist.schema.json")

    def test_invalid_json_manifest_fails_closed(self, loader: RuntimeBundleLoader, tmp_path) -> None:
        broken = tmp_path / "broken.json"
        broken.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(RuntimeBundleValidationError):
            loader.load_and_validate(str(broken), SCHEMA_PATH, require_approved=False)

    def test_wrong_type_for_a_required_field_fails_schema_validation(
        self, loader: RuntimeBundleLoader, tmp_path
    ) -> None:
        with open(VALID_UNAPPROVED_BUNDLE, encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["compatibility"]["required_catalogue_template_count"] = "36"  # must be an integer const
        broken = tmp_path / "wrong_type_bundle.json"
        broken.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(RuntimeBundleValidationError):
            loader.load_and_validate(str(broken), SCHEMA_PATH, require_approved=False)

    def test_never_marks_a_bundle_approved_in_this_batch(self) -> None:
        for path in (VALID_UNAPPROVED_BUNDLE, MISSING_FIELD_BUNDLE, BAD_CHECKSUM_BUNDLE):
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
            assert manifest.get("approval_status") != "APPROVED"
