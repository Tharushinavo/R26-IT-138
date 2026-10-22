"""VALIDATORS BATCH acceptance tests (T1, T2, T4, T5, T7, T8). T3 is inline in
tests/test_c1a_wheel_provenance.py (B_PINNED_VERSION/WHEEL_FILENAME updated in place). T6 is
inline in tests/test_be2_architecture_guards.py (extends the existing import-boundary guard
mechanism).

Ships validators/__init__.py and validators/contract_validators.py in B's live-engine wheel at
the SAME pin (09267abfe83829168b8b4817eb4c59d10f54e311), so Component C's adapter can call the
frozen contract gate v3.0 Section 5 requires (validate_payload(payload, "b_to_c")). B re-versioned
0.1.0+bf4.09267ab -> 0.1.0+bf5.09267ab; C, which declares B's exact version as a dependency,
rebuilt/re-versioned 0.1.0+c1.09267ab -> 0.1.0+c2.09267ab in lockstep. Neither wheel's Yass pin
moved.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
B_PACKAGING_ROOT = BACKEND_ROOT / "packaging" / "component_b_internal"
B_SOURCE_MANIFEST_PATH = B_PACKAGING_ROOT / "SOURCE_MANIFEST.txt"
B_MANIFEST_PATH = BACKEND_ROOT / "provenance" / "component-b-live-engine-manifest.json"
YASS_ROOT = (
    BACKEND_ROOT.parents[2] / "Yass" if len(BACKEND_ROOT.parents) > 2 else BACKEND_ROOT / "__no_yass__"
)
PINNED_COMMIT = "09267abfe83829168b8b4817eb4c59d10f54e311"
VALIDATORS_FILES = ("validators/__init__.py", "validators/contract_validators.py")

_HOST_CHECKOUT_AVAILABLE = B_PACKAGING_ROOT.is_dir() and B_MANIFEST_PATH.is_file()
_HOST_CHECKOUT_SKIP_REASON = (
    "backend/packaging/component_b_internal and backend/provenance/component-b-live-engine-"
    "manifest.json are excluded from the application Docker image by .dockerignore (development/"
    "provenance artefacts, not runtime dependencies) and are not COPYd by the Dockerfile beyond "
    "the wheel file itself and requirements.lock -- same environment split "
    "tests/test_c1a_wheel_provenance.py's own T1/T4-manifest/T5-host/T7-host already document."
)
_YASS_CHECKOUT_AVAILABLE = YASS_ROOT.is_dir()
_YASS_SKIP_REASON = (
    "The sibling Yass checkout is not present at the expected path; the pin-vs-packaged byte "
    "comparison via `git show <sha>:<path>` can only run against a real Yass checkout. Mirrors "
    "test_c1a_wheel_provenance.py's own precedent: this comparison was performed once during the "
    "batch's build step and its PASSED result is recorded in "
    "component-b-live-engine-manifest.json's verification.validators_widened_closure_check field, "
    "because the containerized suite has no .git directory and no Yass checkout at all."
)


def _git_show_bytes(rel_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(YASS_ROOT), "show", f"{PINNED_COMMIT}:Implementation_v1.0/{rel_path}"],
        capture_output=True,
        check=True,
    )
    return result.stdout


# ---------------------------------------------------------------------------
# T1 -- byte-identity of the two new validators files against the pinned commit, read in BINARY
# via `git show`, never the Yass working tree (G5: the working tree sits on
# component-b-ns07-delta-in-prompt at 69cb112, one commit behind origin/main, and is NOT the pin).
# HOST-CHECKOUT + YASS-CHECKOUT ONLY.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rel_path", VALIDATORS_FILES)
def test_validators_files_byte_identical_to_pinned_commit(rel_path: str) -> None:
    """SIGNAL: the packaged file's bytes equal `git show <full-40-char-sha>:Implementation_v1.0/
    <path>`'s bytes exactly, compared as bytes (not text, not a hash-only comparison) -- would
    FAIL if either file were trimmed, edited, or accidentally copied from the Yass working tree
    (which is NOT the pin) instead of the pinned commit's blob."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    if not _YASS_CHECKOUT_AVAILABLE:
        pytest.skip(_YASS_SKIP_REASON)
    packaged_file = B_PACKAGING_ROOT / rel_path
    assert packaged_file.is_file(), f"{rel_path} missing from B's packaging tree"
    assert packaged_file.read_bytes() == _git_show_bytes(rel_path)


# ---------------------------------------------------------------------------
# T2 -- B's SOURCE_MANIFEST.txt recomputed live and compared to the manifest's recorded values.
# COMPUTED, not asserted. HOST-CHECKOUT ONLY.
# ---------------------------------------------------------------------------
def test_b_source_manifest_recomputed_matches_recorded_hash_and_count() -> None:
    """SIGNAL: re-running the manifest's own documented algorithm (SHA-256 of UTF-8 lines
    '<path>\\t<sha256-of-bytes>\\n', one line per *.py file under packaging/component_b_internal
    excluding build/ and *.egg-info/, sorted by path) against the real files on disk produces
    the exact sha256 and file_count component-b-live-engine-manifest.json's package_source_
    manifest records. Would FAIL if a file were added/removed/edited without regenerating
    SOURCE_MANIFEST.txt, or if the manifest's recorded hash/count went stale."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    import hashlib

    lines: list[tuple[str, str]] = []
    for path in B_PACKAGING_ROOT.rglob("*.py"):
        if "build" in path.relative_to(B_PACKAGING_ROOT).parts:
            continue
        if any(part.endswith(".egg-info") for part in path.relative_to(B_PACKAGING_ROOT).parts):
            continue
        rel = path.relative_to(B_PACKAGING_ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append((rel, digest))
    lines.sort(key=lambda pair: pair[0])
    content = "".join(f"{path}\t{digest}\n" for path, digest in lines)
    computed_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    manifest = json.loads(B_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert computed_sha256 == manifest["package_source_manifest"]["sha256"]
    assert len(lines) == manifest["package_source_manifest"]["file_count"]
    assert B_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8") == content


# ---------------------------------------------------------------------------
# T4 -- OWNER-REQUIRED: this batch opens the gap (C's wheel bytes change only because C's
# pyproject declares B's wheel at an exact version), so this batch closes it. ALWAYS RUNS
# in-container: requirements.lock and the C wheel's installed metadata are both present there.
# ---------------------------------------------------------------------------
def test_c_declared_b_version_matches_b_version_pinned_in_requirements_lock() -> None:
    """SIGNAL: C's declared B-wheel dependency version (read from the INSTALLED C distribution's
    Requires-Dist metadata) equals the B wheel version actually pinned in requirements.lock (read
    from the wheel filename requirements.lock installs). Would FAIL if C's pyproject.toml
    dependency pin were bumped without requirements.lock's B wheel line being bumped to match, or
    vice versa -- a divergence `pip install --no-deps` would never itself notice, since --no-deps
    means pip never cross-checks a declared dependency's version against what actually gets
    installed."""
    import importlib.metadata
    import re

    pytest.importorskip(
        "component_c_generator",
        reason="prabathi-component-c-live-engine is not installed; see backend/requirements.in",
    )
    requires = importlib.metadata.requires("prabathi-component-c-live-engine") or []
    b_requirement = next(
        (r for r in requires if r.startswith("upadya-component-b-live-engine")), None
    )
    assert b_requirement is not None, requires
    c_declared_b_version = b_requirement.split("==", 1)[1].strip()

    lock_text = (BACKEND_ROOT / "requirements.lock").read_text(encoding="utf-8")
    match = re.search(
        r"upadya_component_b_live_engine-(0\.1\.0\+[a-z0-9.]+)-py3-none-any\.whl", lock_text
    )
    assert match is not None, "no B wheel line found in requirements.lock"
    lock_pinned_b_version = match.group(1)

    assert c_declared_b_version == lock_pinned_b_version


# ---------------------------------------------------------------------------
# T5 -- "validators" appears in no dependency file, mirroring
# test_dependency_files_exclude_research_generator's exact style. Cheap insurance against a
# future install shadowing the real, popular PyPI "validators" distribution. ALWAYS RUNS.
# ---------------------------------------------------------------------------
def test_dependency_files_never_declare_a_bare_validators_requirement() -> None:
    """SIGNAL: none of requirements.in/requirements.lock/requirements.txt declares a bare
    `validators` (or `validators==`) PyPI dependency line -- this project's own validators/ comes
    exclusively from inside the vendored B wheel, never from a top-level pip install. Would FAIL
    if a future, unrelated dependency addition (the real PyPI `validators` package, a name
    collision) were added as a normal requirement line."""
    dependency_files = [
        path
        for name in ("requirements.in", "requirements.lock", "requirements.txt")
        if (path := BACKEND_ROOT / name).exists()
    ]
    assert dependency_files
    for path in dependency_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            package_token = stripped.split("==")[0].split("[")[0].strip().lower()
            assert package_token != "validators", (path, line)


# ---------------------------------------------------------------------------
# T7 -- the manifest move: excluded_by_omission entry GONE, the two files PRESENT in the verbatim
# list, and the recorded reason text PRESENT. A test that only checked the line was removed would
# pass on a silent delete -- this checks all three together. HOST-CHECKOUT ONLY.
# ---------------------------------------------------------------------------
def test_b_manifest_validators_move_is_recorded_not_silently_deleted() -> None:
    """SIGNAL: three facts checked together, none sufficient alone. Would FAIL (as intended) if
    validators were removed from excluded_by_omission without being added to the verbatim list
    (files present) or without a recorded reason (silent delete, exactly what the owner's ruling
    forbids)."""
    if not _HOST_CHECKOUT_AVAILABLE:
        pytest.skip(_HOST_CHECKOUT_SKIP_REASON)
    manifest = json.loads(B_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert not any(
        "validators" in module for module in manifest["excluded_by_omission"]["modules"]
    )
    verbatim_files = manifest["verbatim_files_byte_identical_to_pinned_commit"]["files"]
    assert "validators/__init__.py" in verbatim_files
    assert "validators/contract_validators.py" in verbatim_files
    assert manifest["verbatim_files_byte_identical_to_pinned_commit"]["count"] == len(
        verbatim_files
    )

    move_record = manifest["validators_widened_closure"]
    assert "reason" in move_record and move_record["reason"].strip()
    assert "gate" in move_record
    assert move_record["gate"] == (
        "Authorised by the project owner, who states the Component B owner was notified of this "
        "change and agreed. Owner-relayed; no written sign-off record is cited."
    )
    forbidden_upgrades = ("signed off", "sign-off record is cited\".", "approved by", "approver")
    lowered_gate = move_record["gate"].lower()
    assert "no written sign-off record is cited" in lowered_gate
    assert "signed off" not in lowered_gate


# ---------------------------------------------------------------------------
# T8 -- a provocation test: invalid input reaching the real adapter conversion raises the
# BACKEND-OWNED error (X-3), never the package's own ContractValidationError. ALWAYS RUNS.
# ---------------------------------------------------------------------------
def test_mastery_payload_invalid_input_raises_backend_owned_error_not_package_type() -> None:
    """SIGNAL: calling the real, converted _to_pkg_mastery_payload with a student_id that fails
    B's own frozen ^STU-[0-9]{4}$ pattern raises MasteryPayloadContractValidationError (a
    backend-owned app.domain.live_engine_c.errors type), never
    validators.contract_validators.ContractValidationError itself crossing the X-3 boundary.
    This is a REAL failure path through the actual conversion (Q5/S11), not a synthetic call to
    validate_payload in isolation -- the seven mastery fields and schema_version/component_source
    this function always emits never touch B_TO_C_PROHIBITED_FIELDS, so the only invalid-input
    path reachable through this function today is a contract-level (pydantic) rejection, exactly
    what this test provokes."""
    pytest.importorskip(
        "component_c_generator",
        reason="prabathi-component-c-live-engine is not installed; see backend/requirements.in",
    )
    from validators.contract_validators import ContractValidationError as PkgContractValidationError

    from app.domain.live_engine_c.errors import MasteryPayloadContractValidationError
    from app.infrastructure.live_engine_c.adapter import _to_pkg_mastery_payload

    with pytest.raises(MasteryPayloadContractValidationError) as excinfo:
        _to_pkg_mastery_payload(
            {
                "counting": 0.5, "number_sense": 0.5, "place_value": 0.5, "addition": 0.5,
                "subtraction": 0.5, "multiplication": 0.5, "division": 0.5,
            },
            mastery_source_student_id="NOT-A-VALID-ID",
            mastery_source_intervention_session_id="STU-0001-I-001",
            mastery_source_intervention_session_number=1,
        )
    assert not isinstance(excinfo.value, PkgContractValidationError)
