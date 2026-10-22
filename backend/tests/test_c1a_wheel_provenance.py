"""Phase 1 batch 1a acceptance tests for prabathi-component-c-live-engine (T1-T9).

Packaging + provenance only -- no app/, no adapter, no architecture-guard change (that is Batch
1b, a separate, later work order). See backend/provenance/component-c-live-engine-manifest.json
for the full provenance record and Component_C_Master_Build_Plan_v3.0.md Section 11 Phase 1.

ENVIRONMENT SPLIT (read before editing; this is the REWORKED split -- three tests were recovered
into the container in the rework pass, see backend/buildLog1.md). `backend/.dockerignore` excludes
`packaging/` and `provenance/` from the application Docker image wholesale, with narrow carve-outs
only for the two wheel files and two small JSON/schema files B already needed (see
.dockerignore's BE3b/BE3c comments and this batch's own carve-out for the C wheel). The Dockerfile
never COPYs `backend/packaging/component_c_internal/`, either `component-*-live-engine-
manifest.json` file, `requirements.in`, `Dockerfile`, or `.dockerignore` itself into the running
container -- by design, a production image should not ship its own build provenance and generator
source tree. `docker compose run --rm api pytest` therefore has no way to see those files; only a
full Dev checkout does (host, or a container with the repo mounted rather than just COPYd).

HOST-CHECKOUT-ONLY (skip with an explicit, file-existence-driven reason in-container; same
collected count in every environment):
  - T1 (65 cases): SOURCE_MANIFEST.txt self-consistency -- needs packaging/.
  - T4-manifest (1 case): C-manifest-vs-B-manifest git_commit_sha1 equality -- needs both
    provenance/*.json files.
  - T5-host (4 cases): requirements.in / Dockerfile / .dockerignore filename presence, and the
    manifest's wheel_sha256 -- none of these four files are COPYd into the image.
  - T7-host (1 case): the trimmed file's SOURCE TEXT assertions (PACKAGING NOTE present, no
    `from .session import` statement, no `def advance_session(`) -- needs packaging/.

ALWAYS RUN, including inside `docker compose run --rm api pytest` (the wheel file itself has its
own .dockerignore carve-out + Dockerfile COPY line, same pattern B already uses; requirements.lock
IS COPYd -- Dockerfile line 18; and the wheel is installed via requirements.lock, so the installed
package and its distribution metadata are both present):
  - T2, T3 (4 cases): wheel-content checks against the .whl archive directly.
  - T4-live (1 case, RECOVERED this rework): the INSTALLED C distribution's METADATA
    Requires-Dist pin for upadya-component-b-live-engine equals the INSTALLED B distribution's
    actual version -- real pin coupling verified in the image, distinct from T4-manifest's
    file-level check (both are wanted; they assert different things).
  - T5-lock (1 case, RECOVERED this rework): requirements.lock's --hash=sha256: for this wheel
    equals sha256sum of the actual .whl on disk.
  - T6 (17 cases): per-module ModuleNotFoundError + importability corroboration, against the
    installed package.
  - T7-live (1 case, RECOVERED this rework): the trimmed file's NAMESPACE assertions against the
    installed package.
  - T8, T9 (2 cases): positive controls that the trim did not silently break what it kept.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import zipfile
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PACKAGING_ROOT = BACKEND_ROOT / "packaging" / "component_c_internal"
SOURCE_MANIFEST_PATH = PACKAGING_ROOT / "SOURCE_MANIFEST.txt"
C_MANIFEST_PATH = BACKEND_ROOT / "provenance" / "component-c-live-engine-manifest.json"
B_MANIFEST_PATH = BACKEND_ROOT / "provenance" / "component-b-live-engine-manifest.json"
REQUIREMENTS_IN_PATH = BACKEND_ROOT / "requirements.in"
REQUIREMENTS_LOCK_PATH = BACKEND_ROOT / "requirements.lock"
DOCKERFILE_PATH = BACKEND_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = BACKEND_ROOT / ".dockerignore"
WHEEL_FILENAME = "prabathi_component_c_live_engine-0.1.0+c3.09267ab-py3-none-any.whl"
WHEEL_PATH = BACKEND_ROOT / "provenance" / "wheels" / WHEEL_FILENAME
C_DISTRIBUTION_NAME = "prabathi-component-c-live-engine"
B_DISTRIBUTION_NAME = "upadya-component-b-live-engine"
# VALIDATORS BATCH: bf4 -> bf5 (validators/ added at the same 09267ab pin; C rebuilt/re-versioned
# c1 -> c2 in lockstep because C's pyproject.toml declares this exact B version as a dependency).
B_PINNED_VERSION = "0.1.0+bf5.09267ab"

_HOST_CHECKOUT_AVAILABLE = PACKAGING_ROOT.is_dir() and C_MANIFEST_PATH.is_file()
_HOST_CHECKOUT_SKIP_REASON = (
    "backend/packaging/component_c_internal and backend/provenance/component-*-live-engine-"
    "manifest.json are excluded from the application Docker image by .dockerignore (development/"
    "provenance artefacts, not runtime dependencies) and are not COPYd by the Dockerfile beyond "
    "the wheel file itself and requirements.lock; this test reads repo source directly and only "
    "runs against a full Dev checkout, not inside `docker compose run --rm api pytest`."
)


def _require_installed_component_c_generator():
    """Local (not module-level) importorskip: only the tests that actually need the installed
    package call this, so host-checkout file-reading tests (T1, T4-manifest, T5-host, T7-host)
    stay independent of whether this particular Python environment happens to have the wheel
    pip-installed."""
    return pytest.importorskip(
        "component_c_generator",
        reason="prabathi-component-c-live-engine is not installed; see backend/requirements.in",
    )


# The 15 never-ship modules (Component_C_Master_Build_Plan_v3.0 Section 6.1). Full dotted paths,
# matching the manifest's excluded_by_omission.modules list exactly. C-22/DEC-1's addition of
# component_c_generator.c_to_3.emit to this list is HISTORICAL as of 9b-0
# (Component_C_9b_9c_And_Generator_Plan_v1.0.md): DEC-1's blocker (the only shipped file importing
# top-level `validators`, which no wheel then provided) is resolved now that B's wheel ships
# validators/, and c_to_3/emit.py is shipped as of this rebuild -- it moved to VERBATIM_65 below
# and its case in test_never_ship_module_is_not_importable_by_full_dotted_path moved to join the
# positive control in test_behaviour_and_c_to_3_packages_remain_importable.
NEVER_SHIP_MODULES = (
    "component_c_generator.behaviour.action_provider",
    "component_c_generator.behaviour.attempt_loop",
    "component_c_generator.behaviour.decisions",
    "component_c_generator.behaviour.latency",
    "component_c_generator.behaviour.outcome_model",
    "component_c_generator.behaviour.seeds",
    "component_c_generator.pipeline.session",
    "component_c_generator.pipeline.pilot",
    "component_c_generator.pipeline.pilot_cohort",
    "component_c_generator.audits",
    "component_c_generator.audits.c_to_3_audit",
    "component_c_generator.audits.coverage",
    "component_c_generator.audits.determinism",
    "component_c_generator.audits.leakage",
    "component_c_generator.audits.population_neutrality",
)

# The 65 verbatim-shipped files, hardcoded here (not derived from SOURCE_MANIFEST.txt at
# collection time) so parametrize collects the same 65 cases in every environment -- including
# inside the container, where they SKIP rather than silently vanish from the collected count.
# Includes component_c_generator/c_to_3/emit.py as of 9b-0 (was VERBATIM_64, 64 entries, before
# this batch resolved DEC-1's blocker -- see NEVER_SHIP_MODULES's comment above).
VERBATIM_65 = (
    "component_c_generator/__init__.py",
    "component_c_generator/adaptation.py",
    "component_c_generator/aggregation/__init__.py",
    "component_c_generator/aggregation/config.py",
    "component_c_generator/aggregation/derive.py",
    "component_c_generator/aggregation/models.py",
    "component_c_generator/behaviour/__init__.py",
    "component_c_generator/behaviour/summary.py",
    "component_c_generator/c_to_3/__init__.py",
    "component_c_generator/c_to_3/adapter.py",
    "component_c_generator/c_to_3/emit.py",
    "component_c_generator/c_to_3/inputs.py",
    "component_c_generator/catalogue/__init__.py",
    "component_c_generator/catalogue/loaded_models.py",
    "component_c_generator/catalogue/loader.py",
    "component_c_generator/catalogue/models.py",
    "component_c_generator/composites/__init__.py",
    "component_c_generator/composites/config.py",
    "component_c_generator/composites/engagement_frustration.py",
    "component_c_generator/composites/learner_state.py",
    "component_c_generator/config.py",
    "component_c_generator/eligibility.py",
    "component_c_generator/evaluation.py",
    "component_c_generator/gameplay_config.py",
    "component_c_generator/generation.py",
    "component_c_generator/generation_config.py",
    "component_c_generator/ids.py",
    "component_c_generator/models/__init__.py",
    "component_c_generator/models/adaptation.py",
    "component_c_generator/models/enums.py",
    "component_c_generator/models/gameplay.py",
    "component_c_generator/models/learner_state.py",
    "component_c_generator/models/seed.py",
    "component_c_generator/models/session.py",
    "component_c_generator/models/task_instance.py",
    "component_c_generator/pipeline/__init__.py",
    "component_c_generator/pipeline/config.py",
    "component_c_generator/pipeline/evidence.py",
    "component_c_generator/policy/__init__.py",
    "component_c_generator/policy/config.py",
    "component_c_generator/policy/rule_based.py",
    "component_c_generator/rewards.py",
    "component_c_generator/safety/__init__.py",
    "component_c_generator/safety/config.py",
    "component_c_generator/safety/controller.py",
    "component_c_generator/scaffolds/__init__.py",
    "component_c_generator/scaffolds/config.py",
    "component_c_generator/scaffolds/ladder.py",
    "component_c_generator/scaffolds/recovery.py",
    "component_c_generator/seeds.py",
    "component_c_generator/selection/__init__.py",
    "component_c_generator/selection/config.py",
    "component_c_generator/selection/phase.py",
    "component_c_generator/selection/selector.py",
    "component_c_generator/tasks/__init__.py",
    "component_c_generator/tasks/base.py",
    "component_c_generator/tasks/build_and_trade.py",
    "component_c_generator/tasks/count_and_collect.py",
    "component_c_generator/tasks/equal_groups_arrays.py",
    "component_c_generator/tasks/join_and_bridge.py",
    "component_c_generator/tasks/match_compare_locate.py",
    "component_c_generator/tasks/number_path.py",
    "component_c_generator/tasks/registry.py",
    "component_c_generator/tasks/share_fairly.py",
    "component_c_generator/tasks/take_away_and_compare.py",
)
assert len(VERBATIM_65) == 65

# COR-2's original five Phase 1 batch 1a pin-DECLARATION locations (requirements.in,
# requirements.lock, Dockerfile, .dockerignore, this manifest), minus requirements.lock (moved to
# its own always-runs test, test_requirements_lock_hash_matches_wheel_on_disk, since
# requirements.lock IS COPYd into the image -- Dockerfile line 18 -- so gating it behind the
# host-checkout skip would hide a real, in-container-checkable signal). The remaining four are
# still genuinely absent in-container. NOTE (R0-b, Component_C_9b_9c_And_Generator_Plan_v1.0.md):
# these five were never the whole count -- the manifest's own cor_2_five_pin_locations block was
# corrected to 9, adding the four tests/fixtures/runtime_bundle_c/*.json locations, which are
# covered by a separate test (test_fixture_generator_checksum_matches_wheel_on_disk and
# test_bad_checksum_fixture_is_deliberately_wrong_not_stale in
# test_c2_catalogue_and_runtime_bundle.py), not this file. This list stays five entries
# deliberately: it is the file-declaration subset, not the full pin-location count.
HOST_ONLY_PIN_LOCATIONS = (
    ("requirements.in", "filename"),
    ("Dockerfile", "filename"),
    (".dockerignore", "filename"),
    ("provenance/component-c-live-engine-manifest.json", "hash"),
)


def _source_manifest_entries() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in SOURCE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel_path, digest = line.split("\t")
        entries[rel_path] = digest
    return entries


# ---------------------------------------------------------------------------
# T1 -- SOURCE_MANIFEST.txt self-consistency (A1). HOST-CHECKOUT ONLY.
# ---------------------------------------------------------------------------
# SIGNAL: each packaged file's on-disk bytes hash to exactly the value SOURCE_MANIFEST.txt
# recorded for it at build time. This is repeatable drift detection, not a re-derivation of the
# pin comparison itself -- the pin-vs-packaged comparison (`git show <sha>:<path>` bytes, read in
# binary, vs packaged bytes, per file) was performed once during this batch's build step and its
# PASSED result is recorded in component-c-live-engine-manifest.json's
# verification.verbatim_byte_identity_check field, because neither this test file's own runtime
# environment nor the containerized suite (docker compose run --rm api pytest, whose image has no
# .git directory at all -- see .dockerignore line 1) can execute `git show` against Yass. If a
# future edit changes a packaged file's bytes without updating SOURCE_MANIFEST.txt to match, this
# test goes red; it does not merely check the file exists.
@pytest.mark.parametrize("rel_path", VERBATIM_65)
def test_verbatim_file_matches_source_manifest_sha256(rel_path: str) -> None:
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    entries = _source_manifest_entries()
    packaged_file = PACKAGING_ROOT / rel_path
    assert packaged_file.is_file(), f"{rel_path} listed in SOURCE_MANIFEST.txt but missing on disk"
    actual = hashlib.sha256(packaged_file.read_bytes()).hexdigest()
    assert actual == entries[rel_path], (rel_path, actual, entries[rel_path])


# ---------------------------------------------------------------------------
# R0-c (Component_C_9b_9c_And_Generator_Plan_v1.0.md) -- SOURCE_MANIFEST.txt's algorithm
# recomputed live and compared against component-c-live-engine-manifest.json's recorded
# package_source_manifest.sha256/file_count. COMPUTED, not asserted -- reuses B's own
# implementation directly (tests/test_validators_batch.py:84-112,
# test_b_source_manifest_recomputed_matches_recorded_hash_and_count), same algorithm, same shape.
# Before this test, only B had one; nothing would go red if C's package_source_manifest fields
# went stale, and both upcoming wheel rebuilds (this plan's G2 and 9b-0) change C's file
# inventory. HOST-CHECKOUT ONLY, same split as T1 above.
# ---------------------------------------------------------------------------
def test_c_source_manifest_recomputed_matches_recorded_hash_and_count() -> None:
    """SIGNAL: re-running the manifest's own documented algorithm (SHA-256 of UTF-8 lines
    '<package-relative-posix-path>\\t<lowercase-sha256-of-file-bytes-as-shipped>\\n', one line per
    *.py file under packaging/component_c_internal excluding build/ and *.egg-info/, sorted by
    path) against the real files on disk produces the exact sha256 and file_count
    component-c-live-engine-manifest.json's package_source_manifest records, and that
    SOURCE_MANIFEST.txt on disk equals the recomputed content exactly. Would FAIL if a file were
    added/removed/edited under packaging/component_c_internal without regenerating
    SOURCE_MANIFEST.txt, or if the manifest's recorded hash/count went stale -- the exact gap a
    wheel rebuild that changes C's file inventory (9b-0's emit.py addition, or G2's re-pin) would
    otherwise open silently."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)

    lines: list[tuple[str, str]] = []
    for path in PACKAGING_ROOT.rglob("*.py"):
        if "build" in path.relative_to(PACKAGING_ROOT).parts:
            continue
        if any(part.endswith(".egg-info") for part in path.relative_to(PACKAGING_ROOT).parts):
            continue
        rel = path.relative_to(PACKAGING_ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append((rel, digest))
    lines.sort(key=lambda pair: pair[0])
    content = "".join(f"{path}\t{digest}\n" for path, digest in lines)
    computed_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    manifest = json.loads(C_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert computed_sha256 == manifest["package_source_manifest"]["sha256"]
    assert len(lines) == manifest["package_source_manifest"]["file_count"]
    assert SOURCE_MANIFEST_PATH.read_text(encoding="utf-8") == content


# ---------------------------------------------------------------------------
# T2 -- never-ship absence, read from the BUILT WHEEL (A2). Runs in-container: the .whl file
# itself has its own .dockerignore carve-out and Dockerfile COPY line (same pattern B already
# uses for its own wheel), so it is present at WHEEL_PATH in every environment this batch runs in.
# ---------------------------------------------------------------------------
def test_never_ship_modules_absent_from_built_wheel() -> None:
    """SIGNAL: none of the 15 never-ship modules appears as a file inside the built .whl's zip
    archive -- read from the wheel's actual contents, not the source tree, so a packaging mistake
    that shipped a never-ship file would be caught even if the source tree itself looked correct.
    Would FAIL if any never-ship module's .py or package __init__.py were present in the archive."""
    assert WHEEL_PATH.is_file(), f"wheel not found at {WHEEL_PATH}"
    with zipfile.ZipFile(WHEEL_PATH) as archive:
        names = archive.namelist()
    for module in NEVER_SHIP_MODULES:
        as_path_prefix = module.replace(".", "/")
        hits = [
            n for n in names
            if n == f"{as_path_prefix}.py" or n == f"{as_path_prefix}/__init__.py"
        ]
        assert not hits, (module, hits)


def test_trimmed_session_state_present_and_never_ship_session_module_absent() -> None:
    """SIGNAL: pipeline/session_state.py (trimmed, still shipped) IS present in the wheel, while
    pipeline/session.py (never-ship) is NOT -- proves T2's check discriminates at the file level,
    not merely by directory, since both live under the same pipeline/ package. Would FAIL if
    either file were on the wrong side of that line."""
    with zipfile.ZipFile(WHEEL_PATH) as archive:
        names = archive.namelist()
    assert "component_c_generator/pipeline/session_state.py" in names
    assert "component_c_generator/pipeline/session.py" not in names


# ---------------------------------------------------------------------------
# T3 -- top_level.txt from the built wheel (A3, A4). Runs in-container (same WHEEL_PATH as T2).
# ---------------------------------------------------------------------------
def test_wheel_top_level_txt_is_exactly_component_c_generator() -> None:
    """SIGNAL: the wheel's own dist-info/top_level.txt metadata declares exactly one top-level
    package, component_c_generator -- asserted against the built artefact's actual metadata, not
    the pyproject.toml declaration that produced it. Would FAIL if a second top-level package
    (e.g. validators/) were ever vendored."""
    with zipfile.ZipFile(WHEEL_PATH) as archive:
        top_level_entries = [n for n in archive.namelist() if n.endswith("top_level.txt")]
        assert len(top_level_entries) == 1
        content = archive.read(top_level_entries[0]).decode("utf-8")
    assert content.strip().splitlines() == ["component_c_generator"]


def test_wheel_has_no_root_level_models_or_validators_package() -> None:
    """SIGNAL: no root-level models/ or validators/ directory exists in the wheel's file listing
    (G8, DEC-1). component_c_generator/models/ is a private subpackage and is correctly present;
    this test only inspects entries OUTSIDE component_c_generator/ and outside the dist-info
    directory, so it cannot be fooled by that legitimate subpackage sharing the name "models".
    Would FAIL if a root-level models/ or validators/ entry appeared."""
    with zipfile.ZipFile(WHEEL_PATH) as archive:
        names = archive.namelist()
    root_level_entries = [
        n for n in names
        if not n.startswith("component_c_generator/") and "dist-info" not in n
    ]
    assert root_level_entries == [], root_level_entries


# ---------------------------------------------------------------------------
# T4-manifest -- pin coupling via provenance files (A5). HOST-CHECKOUT ONLY -- needs both
# manifest JSONs, neither COPYd into the application image.
# ---------------------------------------------------------------------------
def test_c_manifest_git_commit_sha1_matches_b_manifest() -> None:
    """SIGNAL: component-c-live-engine-manifest.json's pinned_source.git_commit_sha1 equals
    component-b-live-engine-manifest.json's -- the two wheels are pin-coupled by field equality,
    not merely by both happening to reference the same commit in prose. Would FAIL if either
    manifest's pin moved without the other. Distinct from test_installed_c_distribution_requires_
    dist_pins_the_installed_b_version below, which checks the same coupling fact through the
    INSTALLED packages' own metadata rather than through the provenance documents."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    c_manifest = json.loads(C_MANIFEST_PATH.read_text(encoding="utf-8"))
    b_manifest = json.loads(B_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert (
        c_manifest["pinned_source"]["git_commit_sha1"]
        == b_manifest["pinned_source"]["git_commit_sha1"]
        == "09267abfe83829168b8b4817eb4c59d10f54e311"
    )


# ---------------------------------------------------------------------------
# T4-live -- pin coupling via INSTALLED distribution metadata (A5, RECOVERED this rework).
# ALWAYS RUNS: importlib.metadata reads the installed dist-info, present in-container because
# requirements.lock installs both wheels.
# ---------------------------------------------------------------------------
def test_installed_c_distribution_requires_dist_pins_the_installed_b_version() -> None:
    """SIGNAL: the INSTALLED prabathi-component-c-live-engine distribution's METADATA
    Requires-Dist line for upadya-component-b-live-engine names a version that equals the
    INSTALLED upadya-component-b-live-engine distribution's actual version -- real pin coupling,
    verified against what pip actually installed in this image, not against a document describing
    what was intended. Would FAIL if the two wheels' pins ever diverged (e.g. one bumped without
    the other) in a way that still let both install successfully (--no-deps means pip never
    cross-checks this itself -- G7)."""
    _require_installed_component_c_generator()
    requires = importlib.metadata.requires(C_DISTRIBUTION_NAME) or []
    b_requirement = next(
        (r for r in requires if r.startswith(B_DISTRIBUTION_NAME)), None
    )
    assert b_requirement is not None, requires
    pinned_version = b_requirement.split("==", 1)[1].strip()
    installed_b_version = importlib.metadata.version(B_DISTRIBUTION_NAME)
    assert pinned_version == installed_b_version == B_PINNED_VERSION


# ---------------------------------------------------------------------------
# T5-host -- pin-location integrity for the four genuinely-absent-in-container locations (A6).
# HOST-CHECKOUT ONLY.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("location_name,kind", HOST_ONLY_PIN_LOCATIONS)
def test_pin_location_references_the_real_wheel(location_name: str, kind: str) -> None:
    """SIGNAL, by kind:
    - "hash" (the manifest): the location's recorded sha256 equals sha256sum of the actual built
      wheel on disk. Would FAIL if the manifest's wheel_sha256 field went stale after a rebuild.
    - "filename" (requirements.in, Dockerfile, .dockerignore): the location contains the wheel's
      exact filename (this repo's requirements.in convention never records a hash for a local
      wheel path -- confirmed from B's own requirements.in line 11 -- so a hash assertion there
      would be asserting something that was never true, not tightening the check). Would FAIL if
      the wheel were renamed/re-versioned without updating these three references.
    """
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    assert WHEEL_PATH.is_file()
    real_sha256 = hashlib.sha256(WHEEL_PATH.read_bytes()).hexdigest()

    if location_name == "requirements.in":
        text = REQUIREMENTS_IN_PATH.read_text(encoding="utf-8")
    elif location_name == "Dockerfile":
        text = DOCKERFILE_PATH.read_text(encoding="utf-8")
    elif location_name == ".dockerignore":
        text = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
    elif location_name == "provenance/component-c-live-engine-manifest.json":
        text = C_MANIFEST_PATH.read_text(encoding="utf-8")
    else:  # pragma: no cover - exhaustive over HOST_ONLY_PIN_LOCATIONS
        raise AssertionError(location_name)

    assert WHEEL_FILENAME in text, (location_name, "wheel filename not referenced")

    if kind == "hash":
        manifest = json.loads(text)
        assert manifest["package"]["wheel_sha256"] == real_sha256, (location_name, real_sha256)
    elif kind == "filename":
        # Filename-only locations never carry a dedicated hash entry for a locally-pathed wheel
        # in this repo's convention -- the WHEEL_FILENAME-presence assertion above is the whole
        # signal for this kind. No further assertion is made here; adding one that can never fail
        # would be exactly the vacuous pattern D6 prohibits.
        pass
    else:  # pragma: no cover - exhaustive over HOST_ONLY_PIN_LOCATIONS
        raise AssertionError(kind)


# ---------------------------------------------------------------------------
# T5-lock -- requirements.lock's hash (A6, RECOVERED this rework). ALWAYS RUNS: requirements.lock
# IS COPYd into the image (Dockerfile line 18) and the wheel is present via its own carve-out.
# ---------------------------------------------------------------------------
def test_requirements_lock_hash_matches_wheel_on_disk() -> None:
    """SIGNAL: requirements.lock's recorded --hash=sha256: for this wheel equals sha256sum of the
    actual .whl file on disk. Would FAIL if requirements.lock's hash went stale after a rebuild --
    which would otherwise only surface indirectly, as `pip install --require-hashes` refusing the
    wheel at image-build time; this test asserts the same fact directly and earlier."""
    assert WHEEL_PATH.is_file()
    real_sha256 = hashlib.sha256(WHEEL_PATH.read_bytes()).hexdigest()
    text = REQUIREMENTS_LOCK_PATH.read_text(encoding="utf-8")
    assert WHEEL_FILENAME in text, "wheel filename not referenced in requirements.lock"
    assert f"--hash=sha256:{real_sha256}" in text, (real_sha256, "hash not found in requirements.lock")


# ---------------------------------------------------------------------------
# T6 -- per-module ModuleNotFoundError by full dotted path (A2 backstop, D6 guard). Runs
# in-container: the package is installed there via requirements.lock.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_name", NEVER_SHIP_MODULES)
def test_never_ship_module_is_not_importable_by_full_dotted_path(module_name: str) -> None:
    """SIGNAL: importlib.import_module(<full dotted path>) raises ModuleNotFoundError for each of
    the 15 never-ship modules. The importorskip guard prevents the vacuous pass that would occur
    if the wheel were not installed at all (every assertion below would then trivially "pass" for
    the wrong reason); this per-test assertion prevents the narrower vacuous pass of testing
    package-root absence when the true risk is a specific SUBMODULE. In particular
    component_c_generator.behaviour and component_c_generator.c_to_3 ARE legitimately importable
    (behaviour/__init__.py, behaviour/summary.py, c_to_3/__init__.py, c_to_3/adapter.py,
    c_to_3/emit.py, c_to_3/inputs.py all ship) -- if behaviour/latency.py were ever later added to
    the wheel, THIS specific parametrized case (not a package-level check) would start succeeding
    at import and this test would go red, exactly the failure mode the guard exists to catch.
    component_c_generator.c_to_3.emit was itself exactly this prediction come true: it WAS a
    parametrized case here (Phase 1 batch 1a through the VALIDATORS BATCH), and 9b-0
    (Component_C_9b_9c_And_Generator_Plan_v1.0.md) is the batch where it started succeeding at
    import -- DEC-1's blocker resolved, B's wheel now shipping validators/. Rather than leave that
    case here to go red, it was MOVED to join the positive control in
    test_behaviour_and_c_to_3_packages_remain_importable below, which already proves c_to_3.adapter
    and c_to_3.inputs DO import; c_to_3.emit now joins them there instead of being asserted absent
    here."""
    _require_installed_component_c_generator()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_behaviour_and_c_to_3_packages_remain_importable() -> None:
    """SIGNAL: the never-ship-adjacent package behaviour/ (which legitimately ships partial
    contents, behaviour/summary.py) and c_to_3/ (which now ships in full -- __init__.py, adapter.py,
    emit.py, inputs.py, as of 9b-0) DO import successfully -- proving T6's per-module
    ModuleNotFoundError assertions are testing specific submodule absence, not accidentally relying
    on the whole package being unreachable. component_c_generator.c_to_3.emit's case moved here
    from test_never_ship_module_is_not_importable_by_full_dotted_path in 9b-0
    (Component_C_9b_9c_And_Generator_Plan_v1.0.md): DEC-1's blocker is resolved (B's wheel now
    ships validators/, emit.py's only missing import) and emit.py is shipped as of this rebuild, so
    it belongs among the imports proven to succeed, not the ones proven to fail. Would FAIL if a
    never-ship-adjacent __init__.py were ever accidentally omitted, or if c_to_3/emit.py regressed
    to being omitted again without this test being moved back."""
    _require_installed_component_c_generator()
    importlib.import_module("component_c_generator.behaviour")
    importlib.import_module("component_c_generator.behaviour.summary")
    importlib.import_module("component_c_generator.c_to_3")
    importlib.import_module("component_c_generator.c_to_3.adapter")
    importlib.import_module("component_c_generator.c_to_3.emit")
    importlib.import_module("component_c_generator.c_to_3.inputs")


def test_wheel_itself_provides_no_top_level_models_or_validators_import() -> None:
    """SIGNAL (UPDATED, VALIDATORS BATCH): `models` and `validators` are both importable in this
    shared environment -- but from upadya-component-b-live-engine, a separate declared
    dependency, never from prabathi-component-c-live-engine itself. Before this batch,
    `validators` was unreachable entirely (B excluded it too); it is now shipped in B's wheel at
    0.1.0+bf5.09267ab specifically so Component C's adapter can call validate_payload (v3.0
    Section 5) -- the OLD assertion that `validators` must "stay unreachable regardless of what
    installs it" was true only because nothing shipped it yet, not because of any rule this
    package enforces itself; that premise changed by deliberate, ruled decision, not drift. What
    this test still enforces, unweakened: `component_c_generator.models` (the private
    subpackage) works, and this test asserts nothing about whether prabathi-component-c-live-
    engine itself vendors a root-level models/ or validators/ -- that remains proven directly
    from the .whl archive by test_wheel_has_no_root_level_models_or_validators_package above,
    completely untouched by this batch. Would FAIL if either `models` or `validators` became
    unimportable in this environment (i.e. if B stopped providing them), or if
    component_c_generator.models stopped working."""
    _require_installed_component_c_generator()
    import component_c_generator  # noqa: F401 -- sanity: package itself imports fine
    from component_c_generator.models import enums as _  # noqa: F401 -- the private subpackage works

    import models  # noqa: F401 -- provided by B's wheel, a separate dependency
    import validators  # noqa: F401 -- provided by B's wheel as of the VALIDATORS BATCH (was absent before)


# ---------------------------------------------------------------------------
# T7-host -- trimmed-file SOURCE TEXT integrity (A7). HOST-CHECKOUT ONLY -- source lives under
# packaging/, excluded from the application image.
# ---------------------------------------------------------------------------
def test_trimmed_session_state_source_text_reflects_the_final_trim() -> None:
    """SIGNAL: the PACKAGING NOTE is present; no line, once stripped, is an actual
    `from .session import ...` statement (line-anchored, not a whole-file substring check -- the
    PACKAGING NOTE itself quotes that import in backticked prose to document its removal, which
    would trip a naive substring check); and `def advance_session(` does not appear anywhere in
    the source (it was removed as a whole function in this rework, not merely stripped of its
    import). Would FAIL if the trim regressed to leaving advance_session's definition in place."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    source_path = PACKAGING_ROOT / "component_c_generator" / "pipeline" / "session_state.py"
    source_text = source_path.read_text(encoding="utf-8")

    assert "class CLearnerSessionState(BaseModel):" in source_text
    assert "def is_eligible_combined_handoff(" in source_text
    assert "def decide_next_session_phase(" in source_text
    assert not any(
        line.strip().startswith("from .session import") for line in source_text.splitlines()
    ), "an actual `from .session import ...` statement is still present, not just mentioned in prose"
    assert "def advance_session(" not in source_text
    assert "PACKAGING NOTE" in source_text


# ---------------------------------------------------------------------------
# T7-live -- trimmed-file NAMESPACE integrity (A7, RECOVERED this rework). ALWAYS RUNS: the
# installed package is present in-container via requirements.lock.
# ---------------------------------------------------------------------------
def test_trimmed_session_state_installed_namespace_reflects_the_final_trim() -> None:
    """SIGNAL: against the INSTALLED module (not the source tree), the four live-required symbols
    are present and the four removed/never-ship-adjacent names are absent as bound module
    attributes. Would FAIL if the wheel ever shipped a stale build where advance_session or
    _DRIVER_OWNED_SESSION_KWARGS were still bound, or where a live-required symbol went missing."""
    _require_installed_component_c_generator()
    module = importlib.import_module("component_c_generator.pipeline.session_state")

    for present_name in (
        "CLearnerSessionState",
        "initial_learner_session_state",
        "is_eligible_combined_handoff",
        "decide_next_session_phase",
        "SessionStateInputError",
        "PIPELINE_SESSION_STATE_VERSION",
    ):
        assert hasattr(module, present_name), f"{present_name} must be bound after the trim"

    for absent_name in (
        "advance_session",
        "run_c_session",
        "RunCSessionResult",
        "_DRIVER_OWNED_SESSION_KWARGS",
    ):
        assert not hasattr(module, absent_name), (
            f"{absent_name} must NOT be a bound name in this module's namespace after the trim"
        )


# ---------------------------------------------------------------------------
# T8 -- POSITIVE CONTROL: _SEVEN_SKILLS's validator actually fires (X-10). ALWAYS RUNS.
# ---------------------------------------------------------------------------
def test_seven_skills_validator_rejects_unknown_skill_key() -> None:
    """POSITIVE CONTROL: constructs CLearnerSessionState with an unknown key in
    sessions_since_last_practice and asserts it RAISES. This is the whole reason _SEVEN_SKILLS
    was retained in the trim (it is referenced only by this validator, on a kept class) --
    absence of failure elsewhere in the suite is not evidence the validator still fires. Would
    FAIL (silently pass construction) if _SEVEN_SKILLS or the validator that reads it were ever
    accidentally dropped."""
    _require_installed_component_c_generator()
    from pydantic import ValidationError

    module = importlib.import_module("component_c_generator.pipeline.session_state")
    with pytest.raises(ValidationError):
        module.CLearnerSessionState(
            eligible_combined_handoffs_completed=0,
            sessions_since_last_practice={"not_a_real_skill": 1},
            prior_session_end_state=None,
        )


# ---------------------------------------------------------------------------
# T9 -- POSITIVE CONTROL: decide_next_session_phase survived the trim (X-10). ALWAYS RUNS.
# ---------------------------------------------------------------------------
def test_decide_next_session_phase_c_only_path_survives_trim() -> None:
    """POSITIVE CONTROL: calls decide_next_session_phase with session_mode="c_only" and asserts it
    returns exactly "c_only". Uses ONLY the c_only path, which returns before touching
    selection_config at all -- so this needs no CSelectionConfig instance and records no
    threshold or scientific parameter (G1); selection_config=None is passed deliberately to prove
    the c_only branch never dereferences it. Would FAIL if the function were accidentally removed
    by a future edit, or if its c_only branch started consulting selection_config."""
    _require_installed_component_c_generator()
    module = importlib.import_module("component_c_generator.pipeline.session_state")
    state = module.initial_learner_session_state()
    result = module.decide_next_session_phase(
        session_mode="c_only", grade=1, state=state, selection_config=None,
    )
    assert result == "c_only"
