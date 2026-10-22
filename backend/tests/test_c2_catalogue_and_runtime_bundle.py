"""Component C Phase 2 acceptance tests: catalogue loading, the C runtime-bundle chain, and the
two X-8 fail-closed rejection mechanisms.

Uses the TEST_FIXTURE_ONLY catalogue at tests/fixtures/runtime_bundle_c/test_catalogue_c.md and
the three new C bundle fixtures in the same directory -- none of which are edits to Component
B's own fixtures (COR-2's deferral is closed by these three NEW files, not modifications to B's
three). See that fixture's own header for what it proves and does not prove.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application.live_engine_c.bundle_resolution import resolve_c_bundle_and_catalogue
from app.core.errors import ConflictError, ERROR_SCHEMA_VERSION
from app.domain.live_engine_c.generation_mode_guard import (
    DISALLOWED_OUTSIDE_SMOKE_MODE,
    GenerationConfigNotPermittedError,
    assert_generation_config_permitted,
)
from app.domain.live_engine_c.types import GenerationConfig
from app.domain.runtime_bundle.errors import (
    RuntimeBundleChecksumMismatchError,
    RuntimeBundleNotApprovedError,
    RuntimeBundleValidationError,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.runtime_bundle_c.loader import CRuntimeBundleLoader

SCHEMA_PATH = "provenance/c-runtime-bundle.schema.json"
FIXTURE_DIR = "tests/fixtures/runtime_bundle_c"
CATALOGUE_PATH = f"{FIXTURE_DIR}/test_catalogue_c.md"
VALID_UNAPPROVED_BUNDLE = f"{FIXTURE_DIR}/valid_unapproved_bundle_c.json"
MISSING_FIELD_BUNDLE = f"{FIXTURE_DIR}/missing_field_bundle_c.json"
BAD_CHECKSUM_BUNDLE = f"{FIXTURE_DIR}/bad_checksum_bundle_c.json"
# Phase 6b (see test_c4b_routes_and_bundle_config.py's own header for why it exists): every
# per-field status APPROVED, TEST-ONLY. Named here (R0-d) only to couple its recorded generator
# checksum to the wheel on disk -- this file does not otherwise exercise it.
ALL_USABLE_BUNDLE = f"{FIXTURE_DIR}/all_usable_for_tests_bundle_c.json"

# Recorded once here from the disclaimer-header fixture on disk; the loader/checksum tests below
# re-derive it live rather than trusting this constant, so this is documentation, not the signal.
CATALOGUE_CHECKSUM_ON_DISK = "55709112756fed913ed24d44a21b9b54c7fd25976db8de884fbe47526082f661"


@pytest.fixture()
def adapter() -> LiveEngineCAdapter:
    return LiveEngineCAdapter()


# ---------------------------------------------------------------------------
# A1 -- catalogue loads 8 families / 30 templates; the loaded template id SET equals
# supported_template_ids()'s set (never a count comparison).
# ---------------------------------------------------------------------------


def test_fixture_catalogue_loads_8_families_30_templates(adapter: LiveEngineCAdapter) -> None:
    """SIGNAL: real family/template counts from the real loader. Would FAIL if the fixture's
    family_id_mapping or per-family template counts drifted from
    component_c_generator.catalogue.loader.EXPECTED_TEMPLATE_COUNT_BY_FAMILY."""
    catalogue = adapter.load(CATALOGUE_PATH)
    assert len(catalogue.families) == 8
    assert len(catalogue.templates) == 30


def test_fixture_catalogue_template_id_set_equals_registry_set(adapter: LiveEngineCAdapter) -> None:
    """SIGNAL: SET equality between the fixture's loaded template ids and
    supported_template_ids()'s own set -- not a count comparison, which 30 arbitrary fixture ids
    would trivially satisfy without corresponding to any real generator at all. Would FAIL if
    the fixture's ids and the registry's ids ever diverged, even if both stayed 30."""
    catalogue = adapter.load(CATALOGUE_PATH)
    loaded_ids = {t.game_task_template_id for t in catalogue.templates}
    registry_ids = set(adapter.supported_template_ids())
    assert loaded_ids == registry_ids
    assert len(registry_ids) == 30  # sanity: the cross-check above is not vacuously comparing two empty sets


# ---------------------------------------------------------------------------
# A2 -- deferred/inactive template fails closed, never silently substituted.
# ---------------------------------------------------------------------------


def test_deferred_extension_template_is_not_active() -> None:
    """SIGNAL: the one DEFERRED_EXTENSION template in the fixture (C-SF-03, an arbitrary fixture
    choice -- see the fixture's own header) reports is_active() is False. Would FAIL if a
    deferred template were ever silently treated as active."""
    from component_c_generator.catalogue.loader import load_catalogue

    catalogue = load_catalogue(CATALOGUE_PATH)
    deferred = [t for t in catalogue.templates if t.status == "DEFERRED_EXTENSION"]
    assert len(deferred) == 1
    assert deferred[0].game_task_template_id == "C-SF-03"
    assert deferred[0].is_active() is False


def test_deferred_template_excluded_from_eligible_templates(adapter: LiveEngineCAdapter) -> None:
    """SIGNAL: eligible_templates() (the fail-closed activation/eligibility path) never returns
    the deferred template for either grade -- proving the fail-closed behaviour holds through the
    adapter's own call path, not just the raw loader flag. Would FAIL if the deferred template
    were silently substituted into an eligible set for either grade."""
    catalogue = adapter.load(CATALOGUE_PATH)
    all_ids = tuple(adapter.supported_template_ids())
    for grade in (2, 3):
        eligible = adapter.eligible_templates(catalogue, grade, all_ids)
        eligible_ids = {t.game_task_template_id for t in eligible}
        assert "C-SF-03" not in eligible_ids


# ---------------------------------------------------------------------------
# A3 -- X-8 bundle level: require_approved defaults to True and RAISES on the TEST_FIXTURE_ONLY
# bundle; does NOT raise when the caller explicitly opts into require_approved=False. Both
# directions, so the gate is proven real (X-10), not merely always-raising.
# ---------------------------------------------------------------------------


def test_bundle_approval_gate_raises_by_default() -> None:
    """SIGNAL: the TEST_FIXTURE_ONLY C bundle (approval_status="CALIBRATION_PENDING") is
    refused when require_approved is left at its default (True). Would FAIL if the default gate
    stopped firing for an unapproved bundle."""
    with pytest.raises(RuntimeBundleNotApprovedError):
        CRuntimeBundleLoader().load_and_validate(VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH)


def test_bundle_approval_gate_does_not_raise_when_explicitly_opted_out() -> None:
    """SIGNAL: the SAME bundle loads successfully when the caller explicitly passes
    require_approved=False -- proving the gate discriminates on the flag rather than always
    raising regardless of input (the failure mode a vacuous 'always raises' guard would have).
    Would FAIL if the gate raised unconditionally."""
    bundle = CRuntimeBundleLoader().load_and_validate(
        VALID_UNAPPROVED_BUNDLE, SCHEMA_PATH, require_approved=False
    )
    assert bundle.approval_status == "CALIBRATION_PENDING"


def test_missing_field_bundle_fails_schema_validation() -> None:
    with pytest.raises(RuntimeBundleValidationError):
        CRuntimeBundleLoader().load_and_validate(MISSING_FIELD_BUNDLE, SCHEMA_PATH, require_approved=False)


def test_bad_checksum_bundle_fails_closed() -> None:
    with pytest.raises(RuntimeBundleChecksumMismatchError):
        CRuntimeBundleLoader().load_and_validate(BAD_CHECKSUM_BUNDLE, SCHEMA_PATH, require_approved=False)


# ---------------------------------------------------------------------------
# A6 -- missing-artifact fixture as an X-10 POSITIVE CONTROL, not a fix. v3.0 §12.3 records that
# _sha256_of lacking a try/except is not a defect, since its only caller (_verify_checksum)
# pre-checks path.exists() first. This proves that pre-check actually fires a domain error
# rather than letting a raw FileNotFoundError escape.
# ---------------------------------------------------------------------------


def test_missing_artifact_file_fails_closed_with_domain_error_not_a_raw_os_error(tmp_path: Path) -> None:
    """SIGNAL: pointing artifact_paths at a catalogue path that does not exist on disk raises
    RuntimeBundleChecksumMismatchError (a domain error), never a raw FileNotFoundError escaping
    from _sha256_of. Would FAIL (with the wrong exception type, or none at all) if the
    pre-existing path.exists() pre-check in _verify_checksum were ever removed."""
    nonexistent = tmp_path / "does_not_exist_catalogue.md"
    assert not nonexistent.exists()
    with pytest.raises(RuntimeBundleChecksumMismatchError):
        CRuntimeBundleLoader().load_and_validate(
            VALID_UNAPPROVED_BUNDLE,
            SCHEMA_PATH,
            require_approved=False,
            artifact_paths={"catalogue": str(nonexistent)},
        )


# ---------------------------------------------------------------------------
# A7 -- catalogue_file_checksum over the fixture equals the value recorded in the C bundle
# fixtures, verified live (this test runs on disk during a local pytest invocation and inside
# the rebuilt image during `docker compose run` -- the same assertion either way; a real run in
# the rebuilt image is what "inside the image" means, not a separate code path).
# ---------------------------------------------------------------------------


def test_catalogue_checksum_matches_value_recorded_in_bundle_fixtures(adapter: LiveEngineCAdapter) -> None:
    """SIGNAL: the adapter's live-computed SHA-256 of the fixture catalogue bytes equals the
    checksum value recorded inside valid_unapproved_bundle_c.json's catalogue block. Would FAIL
    if the fixture file's bytes ever changed (a CRLF conversion, a re-save, a manual edit) without
    the bundle fixture's recorded checksum being updated to match -- the C-21 failure mode in a
    new file."""
    import json

    live_checksum = adapter.checksum(CATALOGUE_PATH)
    with open(VALID_UNAPPROVED_BUNDLE, encoding="utf-8") as f:
        bundle_manifest = json.load(f)
    recorded_checksum = bundle_manifest["catalogue"]["checksum"]["value"]
    assert live_checksum == recorded_checksum == CATALOGUE_CHECKSUM_ON_DISK


def test_catalogue_file_has_zero_cr_bytes() -> None:
    """SIGNAL: the fixture file contains zero \\r bytes -- LF-only, UTF-8, matching the repo's
    .gitattributes discipline (C-21). Would FAIL if a CRLF conversion ever touched this file."""
    raw = Path(CATALOGUE_PATH).read_bytes()
    assert b"\r" not in raw


# ---------------------------------------------------------------------------
# A4 -- X-8 config level: the generation-config guard (NEW, UNWIRED -- R2) raises outside smoke
# mode and passes inside it.
# ---------------------------------------------------------------------------


def _generation_config(parameter_source_status: str) -> GenerationConfig:
    return GenerationConfig(
        config_version="c2-test-fixture-1.0",
        parameter_source_status=parameter_source_status,
        per_template={},
    )


def test_generation_config_guard_raises_outside_smoke_mode_for_test_fixture_only() -> None:
    """SIGNAL: assert_generation_config_permitted raises for a TEST_FIXTURE_ONLY config when
    smoke_mode=False. Would FAIL if the guard stopped rejecting fixture-tagged configs outside
    smoke mode. UNWIRED: nothing calls this guard from a real code path yet (Phase 5)."""
    config = _generation_config("TEST_FIXTURE_ONLY")
    with pytest.raises(GenerationConfigNotPermittedError):
        assert_generation_config_permitted(config, smoke_mode=False)


def test_generation_config_guard_raises_outside_smoke_mode_for_smoke_only() -> None:
    config = _generation_config("SMOKE_ONLY")
    with pytest.raises(GenerationConfigNotPermittedError):
        assert_generation_config_permitted(config, smoke_mode=False)


def test_generation_config_guard_does_not_raise_inside_smoke_mode() -> None:
    """SIGNAL: the SAME TEST_FIXTURE_ONLY config passes when smoke_mode=True is explicitly
    supplied -- proving the guard discriminates on the flag (X-10), not merely always-raising."""
    config = _generation_config("TEST_FIXTURE_ONLY")
    assert_generation_config_permitted(config, smoke_mode=True)  # must not raise


def test_generation_config_guard_does_not_raise_for_a_non_fixture_status() -> None:
    """SIGNAL: a config whose parameter_source_status is outside the disallowed set (e.g. an
    ENGINEERING_ASSUMPTION-tagged config, mirroring B's own vocabulary) is never blocked by this
    guard regardless of smoke_mode -- proving the guard targets the two named tags specifically,
    not every non-approved status."""
    config = _generation_config("ENGINEERING_ASSUMPTION")
    assert_generation_config_permitted(config, smoke_mode=False)  # must not raise
    assert DISALLOWED_OUTSIDE_SMOKE_MODE == frozenset({"TEST_FIXTURE_ONLY", "SMOKE_ONLY"})


# ---------------------------------------------------------------------------
# A5 -- a real provoked checksum mismatch produces a 409 whose body carries a request id, via
# the REAL install_error_handlers. Uses a fresh app.main.create_app() instance (the real
# middleware + the real error handlers, unmodified) with ONE synthetic test-only route added to
# that fresh instance -- never to the app.main:app singleton other code imports.
# ---------------------------------------------------------------------------


def test_bundle_checksum_mismatch_produces_409_with_request_id_via_real_error_handlers() -> None:
    """SIGNAL: a real, provoked RuntimeBundleChecksumMismatchError (bad_checksum_bundle_c.json),
    routed through resolve_c_bundle_and_catalogue's real ConflictError translation and the real
    app.core.errors.install_error_handlers/error_response machinery (not a hand-rolled response),
    produces status_code == 409 AND a body matching the real ErrorResponse contract: schema_version,
    error.code == "CONFLICT", and a non-empty error.request_id. Would FAIL if ConflictError's
    HTTP mapping regressed, or if request_id stopped propagating from the request-observability
    middleware into the error body."""
    from app.main import create_app

    test_app = create_app()  # fresh instance; app.main.app itself is never touched

    @test_app.get("/__test_only_c2_bundle_resolution_409")
    def _test_only_route() -> None:
        resolve_c_bundle_and_catalogue(
            bundle_path=BAD_CHECKSUM_BUNDLE,
            schema_path=SCHEMA_PATH,
            catalogue_path=CATALOGUE_PATH,
            require_approved=False,
        )

    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get(
        "/__test_only_c2_bundle_resolution_409", headers={"X-Request-ID": "c2-test-409-request-id"}
    )

    assert response.status_code == 409
    body = response.json()
    assert body["schema_version"] == ERROR_SCHEMA_VERSION
    assert body["error"]["code"] == "CONFLICT"
    assert body["error"]["request_id"]
    assert isinstance(body["error"]["request_id"], str)


def test_resolve_c_bundle_and_catalogue_raises_conflict_error_directly() -> None:
    """SIGNAL: at the function level (no HTTP involved), resolve_c_bundle_and_catalogue itself
    raises app.core.errors.ConflictError for the same provoked checksum mismatch -- isolates the
    exception-translation behaviour from the HTTP-layer test above."""
    with pytest.raises(ConflictError):
        resolve_c_bundle_and_catalogue(
            bundle_path=BAD_CHECKSUM_BUNDLE,
            schema_path=SCHEMA_PATH,
            catalogue_path=CATALOGUE_PATH,
            require_approved=False,
        )


def test_resolve_c_bundle_and_catalogue_succeeds_on_the_valid_unapproved_bundle() -> None:
    """SIGNAL: the positive path -- resolve_c_bundle_and_catalogue returns a real bundle +
    catalogue + checksum for the valid (if unapproved) fixture, proving the 409 tests above are
    exercising a real failure mode and not a function that always raises."""
    bundle, catalogue, checksum = resolve_c_bundle_and_catalogue(
        bundle_path=VALID_UNAPPROVED_BUNDLE,
        schema_path=SCHEMA_PATH,
        catalogue_path=CATALOGUE_PATH,
        require_approved=False,
    )
    assert bundle.bundle_version == "c2-test-fixture-1.0"
    assert len(catalogue.templates) == 30
    assert checksum == CATALOGUE_CHECKSUM_ON_DISK


# ---------------------------------------------------------------------------
# A8 (partial) -- the new migration creates exactly the one authorized table. The
# EXPECTED_TABLES/BE2_BASE_TABLES/set(Base.metadata.tables) checks themselves live in
# test_be2_architecture_guards.py and are not duplicated here.
# ---------------------------------------------------------------------------


def test_c2_migration_creates_only_the_runtime_bundle_table() -> None:
    migration = Path(
        "migrations/versions/20260816_0001_c2_runtime_bundle_record.py"
    ).read_text(encoding="utf-8")
    created = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', migration))
    assert created == {"c_runtime_bundle_records"}
    lowered = migration.lower()
    assert "create_trigger" not in lowered
    assert "create trigger" not in lowered
    assert "bulk_insert" not in lowered
    assert "component_c_generator" not in lowered
    assert "yass" not in lowered


# ---------------------------------------------------------------------------
# R0-d (Component_C_9b_9c_And_Generator_Plan_v1.0.md) -- couple each C runtime-bundle fixture's
# recorded generator checksum to the sha256 of the wheel its own source_path names. Before this
# test, that coupling was enforced only at RUNTIME, by
# app.infrastructure.runtime_bundle_c.loader.CRuntimeBundleLoader raising
# RuntimeBundleChecksumMismatchError during an in-image run -- which is exactly how the
# validators batch discovered it had missed updating the C-side fixtures after a wheel rebuild
# (buildLog1.md's "A cascade the plan missed surfaced here" paragraph, VALIDATORS BATCH entry).
# Nothing previously asserted this at test-collection time, ahead of a real load.
# ---------------------------------------------------------------------------

_FIXTURES_EXPECTED_TO_MATCH_THE_WHEEL = (
    VALID_UNAPPROVED_BUNDLE,
    MISSING_FIELD_BUNDLE,
    ALL_USABLE_BUNDLE,
)


@pytest.mark.parametrize("fixture_path", _FIXTURES_EXPECTED_TO_MATCH_THE_WHEEL)
def test_fixture_generator_checksum_matches_wheel_on_disk(fixture_path: str) -> None:
    """SIGNAL: this fixture's generator.checksum.value equals the live-computed sha256 of the
    wheel file named at generator.source_path -- read from the fixture and the wheel on disk,
    never the manifest, so this is an independent cross-check rather than the same comparison the
    manifest's own T5-host test already makes. Would FAIL if a fixture's recorded checksum went
    stale after a wheel rebuild (this plan's G2 or 9b-0) without every fixture being updated in
    lockstep -- exactly the gap the validators batch found missing for the C-side fixtures.
    bad_checksum_bundle_c.json is deliberately excluded from this parametrization; see
    test_bad_checksum_fixture_is_deliberately_wrong_not_stale below for why."""
    with open(fixture_path, encoding="utf-8") as f:
        bundle = json.load(f)
    generator = bundle["generator"]
    wheel_path = Path(generator["source_path"])
    assert wheel_path.is_file(), f"{fixture_path}: wheel not found at {wheel_path}"
    actual_sha256 = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    assert generator["checksum"]["algorithm"] == "sha256"
    assert generator["checksum"]["value"] == actual_sha256, (
        fixture_path,
        "recorded",
        generator["checksum"]["value"],
        "actual",
        actual_sha256,
    )


def test_bad_checksum_fixture_is_deliberately_wrong_not_stale() -> None:
    """SIGNAL: bad_checksum_bundle_c.json's generator.checksum.value is (a) the deliberate
    all-'f' constant this fixture was built with and (b) NOT equal to the real wheel's sha256.
    This is the one fixture R0-d must NOT assert matches the wheel -- it exists so
    CRuntimeBundleLoader has a real mismatch to reject (see
    test_bundle_checksum_mismatch_produces_409_with_request_id_via_real_error_handlers and
    test_resolve_c_bundle_and_catalogue_raises_conflict_error_directly above, both of which
    depend on this fixture staying wrong). Asserting it here, rather than simply omitting it from
    the parametrized test above, means a future editor who runs a blanket 'sync all fixture
    checksums to the wheel' pass gets a red test instead of silently deleting the negative
    control."""
    with open(BAD_CHECKSUM_BUNDLE, encoding="utf-8") as f:
        bundle = json.load(f)
    generator = bundle["generator"]
    wheel_path = Path(generator["source_path"])
    assert wheel_path.is_file()
    actual_sha256 = hashlib.sha256(wheel_path.read_bytes()).hexdigest()

    recorded = generator["checksum"]["value"]
    assert len(recorded) == 64 and set(recorded) == {"f"}, (
        "bad_checksum_bundle_c.json's checksum must stay the deliberate all-f value",
        recorded,
    )
    assert recorded != actual_sha256, "bad_checksum_bundle_c.json's checksum must stay wrong"
