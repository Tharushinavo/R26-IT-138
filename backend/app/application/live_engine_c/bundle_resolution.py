"""``resolve_c_bundle_and_catalogue`` -- the one function in this batch that maps a fail-closed
runtime-bundle/catalogue failure to the stable, public ``ConflictError`` (409) contract.

Mirrors ``app.application.opportunity_selection``'s own bundle-resolution pattern
(``except (RuntimeBundleError, LiveEngineError) as exc: raise ConflictError() from exc``) for
Component C: ``CRuntimeBundleLoader`` (not B's ``RuntimeBundleLoader`` -- see
``app.infrastructure.runtime_bundle_c.loader`` for why) validates the bundle manifest and its
declared checksums; the adapter then loads and checksums the catalogue artefact itself.

Not a service, not a router, no session logic, no persistence write -- a single pure function
with one job: translate every fail-closed exception this chain can raise into the one stable
error type the public API contract already knows how to render as HTTP 409 with a request id
(``app.core.errors.install_error_handlers``, unmodified, unrelated to this batch).
"""

from __future__ import annotations

import os

from typing import Mapping, Optional

from app.core.errors import ConflictError
from app.domain.live_engine_c.errors import (
    ConfigurationFamilyNotUsableError,
    EvidenceWindowConfigurationMissingError,
    LiveEngineCError,
    SafetyConfigurationMissingError,
    SelectionConfigurationMissingError,
)
from app.domain.live_engine_c.generation_mode_guard import DISALLOWED_OUTSIDE_SMOKE_MODE
from app.domain.live_engine_c.types import (
    Catalogue,
    EvidenceWindowConfig,
    PolicyConfig,
    SafetyConfig,
    SelectionConfig,
)
from app.domain.runtime_bundle.errors import RuntimeBundleError
from app.domain.runtime_bundle_c.types import CRuntimeBundle
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.runtime_bundle_c.loader import CRuntimeBundleLoader

# X1 (owner ruling, Phase 6b): "usable = {APPROVED}, and every other value -- the five named,
# plus any value nobody has considered yet -- is not usable by construction." A WHITELIST, never
# a deny-list matching specific known-bad statuses (X1-a) -- a status string this codebase has
# never seen, including a deliberately nonsense one, refuses by the same "not in the set" check
# as every named-but-unusable status (X1-b, proven by
# tests/test_c6b_policy_and_safety.py::test_x1b_nonsense_status_refuses_by_default).
USABLE_APPROVAL_STATUSES = frozenset({"APPROVED"})


def resolve_c_bundle_and_catalogue(
    *,
    bundle_path: str,
    schema_path: str,
    catalogue_path: str,
    require_approved: bool = True,
    artifact_paths: Optional[Mapping[str, str]] = None,
) -> tuple[CRuntimeBundle, Catalogue, str]:
    """Load + validate the C runtime bundle manifest, then load + checksum the catalogue it
    points at. Fails closed: any ``RuntimeBundleError`` (schema failure, checksum mismatch,
    missing file, unapproved status) or ``LiveEngineCError`` (catalogue load failure) is
    translated into ``ConflictError`` -- never returned as a partial result, never silently
    substituted with a fallback.
    """
    resolved_artifact_paths = dict(artifact_paths or {})
    resolved_artifact_paths.setdefault("catalogue", catalogue_path)
    # PERF-01: these inputs are immutable files. The result of a SUCCESSFUL resolution (schema validation, every artifact
    # checksum, catalogue parse + checksum) is cached per process, keyed by the arguments AND by each file's identity
    # (path, size, mtime) -- so the first call after start-up does the full validation, a file that is missing or changed
    # on disk is re-validated from scratch (and fails closed as before), and a failure is never cached.
    cache_key = (bundle_path, schema_path, catalogue_path, require_approved, tuple(sorted(resolved_artifact_paths.items())))
    fingerprint = _file_fingerprint(bundle_path, schema_path, *resolved_artifact_paths.values())
    cached = _RESOLUTION_CACHE.get(cache_key)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]
    try:
        bundle = CRuntimeBundleLoader().load_and_validate(
            bundle_path,
            schema_path,
            artifact_paths=resolved_artifact_paths,
            require_approved=require_approved,
        )
        adapter = LiveEngineCAdapter()
        catalogue = adapter.load(catalogue_path)
        catalogue_checksum = adapter.checksum(catalogue_path)
    except (RuntimeBundleError, LiveEngineCError) as exc:
        raise ConflictError() from exc
    result = (bundle, catalogue, catalogue_checksum)
    if fingerprint is not None:
        _RESOLUTION_CACHE[cache_key] = (fingerprint, result)
    return result


_RESOLUTION_CACHE: dict = {}


def clear_resolution_cache() -> None:
    _RESOLUTION_CACHE.clear()


def _file_fingerprint(*paths: str):
    """(path, size, mtime_ns) for every file, or ``None`` if any is missing (then nothing is cached and the loader
    reports the missing file exactly as before)."""
    try:
        stats = [(path, os.stat(path)) for path in paths]
    except OSError:
        return None
    return tuple((path, st.st_size, st.st_mtime_ns) for path, st in stats)


def resolve_selection_config(bundle: CRuntimeBundle) -> SelectionConfig:
    """Phase 4b, owner condition 1: "Fail-closed means halt, not default." Raises
    ``SelectionConfigurationMissingError`` when ``bundle.selection_configuration`` is ``None``
    (a real, expected state for any bundle not yet republished with the block, B1-b/additive-
    only) -- never defaults, never substitutes a placeholder, never partially constructs
    ``SelectionConfig``. When present, this is a direct field-by-field carry: no vocabulary
    coercion (``approval_status`` is not read here at all -- it is the bundle's own governance
    gate value, already enforced by ``resolve_c_bundle_and_catalogue``'s ``require_approved``;
    ``config_version``/``parameter_source_status`` are read from their own, independent manifest
    fields)."""
    artifact = bundle.selection_configuration
    if artifact is None:
        raise SelectionConfigurationMissingError(
            f"runtime bundle {bundle.bundle_version!r} carries no selection_configuration -- "
            "halting rather than proceeding on a default (owner condition 1)"
        )
    return SelectionConfig(
        config_version=artifact.config_version,
        parameter_source_status=artifact.parameter_source_status,
        familiarization_window_by_grade=artifact.familiarization_window_by_grade,
        familiarization_difficulty_level=artifact.familiarization_difficulty_level,
        fallback_difficulty_level=artifact.fallback_difficulty_level,
        familiarization_session_difficulty_cap=artifact.familiarization_session_difficulty_cap,
        fallback_difficulty_cap=artifact.fallback_difficulty_cap,
    )


def resolve_safety_config(bundle: CRuntimeBundle) -> SafetyConfig:
    """Phase 6b, symmetric to ``resolve_selection_config`` one family later: "Fail-closed means
    halt, not default." Raises ``SafetyConfigurationMissingError`` when
    ``bundle.safety_configuration`` is ``None`` -- never defaults, never substitutes a
    placeholder. When present, this is a direct field-by-field carry of the already-resolved
    scalar values; per-field STATUS is checked separately, by ``assert_family_usable`` below,
    called from ``create_session`` (S2-a) -- never here, and never skipped by virtue of this
    function having been reached (this function has no opinion on usability at all)."""
    artifact = bundle.safety_configuration
    if artifact is None:
        raise SafetyConfigurationMissingError(
            f"runtime bundle {bundle.bundle_version!r} carries no safety_configuration -- "
            "halting rather than proceeding on a default (S2-a)"
        )
    return SafetyConfig(
        config_version=artifact.config_version,
        parameter_source_status=artifact.parameter_source_status,
        consecutive_error_trigger=artifact.consecutive_error_trigger,
        strain_trigger=artifact.strain_trigger,
        increase_block_window=artifact.increase_block_window,
        prior_overloaded_disengaged_cap=artifact.prior_overloaded_disengaged_cap,
        safe_termination_error_threshold=artifact.safe_termination_error_threshold,
        strain_bucket_low_max=artifact.strain_bucket_low_max,
        strain_bucket_moderate_max=artifact.strain_bucket_moderate_max,
        strain_bucket_high_max=artifact.strain_bucket_high_max,
    )


def resolve_evidence_window_config(bundle: CRuntimeBundle) -> EvidenceWindowConfig:
    """SEVENTH-FAMILY GATE batch, mirroring ``resolve_safety_config`` exactly, one family later.
    Raises ``EvidenceWindowConfigurationMissingError`` when
    ``bundle.evidence_window_configuration`` is ``None`` -- never defaults, never substitutes a
    placeholder. When present, this is a direct field-by-field carry of the already-resolved
    scalar value; per-field STATUS is checked separately, by ``assert_family_usable`` below,
    called from ``create_session`` -- never here, and never skipped by virtue of this function
    having been reached (this function has no opinion on usability at all, same discipline as
    ``resolve_safety_config``/``resolve_selection_config``)."""
    artifact = bundle.evidence_window_configuration
    if artifact is None:
        raise EvidenceWindowConfigurationMissingError(
            f"runtime bundle {bundle.bundle_version!r} carries no evidence_window_configuration "
            "-- halting rather than proceeding on a default"
        )
    return EvidenceWindowConfig(
        config_version=artifact.config_version,
        parameter_source_status=artifact.parameter_source_status,
        recent_window_task_count=artifact.recent_window_task_count,
    )


def assert_family_usable(*, family_name: str, field_statuses: Mapping[str, str]) -> None:
    """X4 -- THE ONE STRUCTURAL GATE MECHANISM, shared by BOTH families (selection and safety),
    called twice from ``session_lifecycle.create_session`` itself, before any ``CSessionRecord``
    is constructed -- never as caller-side ordering that merely happens to run first (S7's own
    finding: incidental ordering is not a gate, it holds only until someone reorders a call).

    X1/W2: usable = {APPROVED} only (``USABLE_APPROVAL_STATUSES``, a whitelist). ANY field whose
    status is not in that set makes the WHOLE family unusable -- W2's trap named exactly:
    "mark enough fields as something-other-than-pending and the block reads as usable... Per-field
    status is for accuracy of the record, never for partial enablement." Raises
    ``ConfigurationFamilyNotUsableError`` naming the family and every unusable field (never the
    value any field held)."""
    unusable = tuple(
        name for name, status in field_statuses.items() if status not in USABLE_APPROVAL_STATUSES
    )
    if unusable:
        raise ConfigurationFamilyNotUsableError(family_name, unusable)


def assert_code_gated_family_usable(*, family_name: str, parameter_source_status: str, smoke_mode: bool) -> None:
    """Phase 7, Z2: the SAME session-start gate `assert_family_usable` implements for the two
    BUNDLE-DATA families (selection, safety), extended to the THREE CODE-GATED families
    (generation, policy, scaffold) -- Z1's own classification: these families have zero
    SPEC-stated fields, so there is no per-field bundle status for them to carry at all; the only
    thing determining usability is whether the caller has explicitly opted into ``smoke_mode``,
    exactly mirroring ``generation_mode_guard.assert_generation_config_permitted``'s own,
    already-built (Phase 2) mechanism -- generalized here, not reinvented, and reusing that
    module's own ``DISALLOWED_OUTSIDE_SMOKE_MODE`` set rather than a second copy of it.

    USABILITY SEMANTICS (Z2-d-2a, stated and derived BEFORE Case 0 was attempted, from what each
    family actually requires -- not loosened afterward to make a test pass): a code-gated
    family's config is usable if and only if ``smoke_mode=True``, OR its
    ``parameter_source_status`` is somehow outside ``{"TEST_FIXTURE_ONLY", "SMOKE_ONLY"}`` --
    which today it never is, for any of the three families, anywhere in this codebase (no
    governed value has ever been constructed for Generation, Policy, or Scaffold). Raises the
    SAME ``ConfigurationFamilyNotUsableError`` the bundle-data families raise -- ONE mechanism,
    one error type, across all five families -- naming ``parameter_source_status`` as the one
    unusable field (never the value it held)."""
    if not smoke_mode and parameter_source_status in DISALLOWED_OUTSIDE_SMOKE_MODE:
        raise ConfigurationFamilyNotUsableError(family_name, ("parameter_source_status",))


def assert_policy_config_matches_session_gate(
    policy_config: PolicyConfig, *, session_gated_parameter_source_status: str
) -> None:
    """THE SEAM (Batch 2, ``adaptation_service.decide_and_persist_adaptation``'s first live
    caller under ``app/``, ``task_service.submit_action``): ``assert_code_gated_family_usable``
    above gates ``policy_config`` at SESSION CREATION by a SEPARATE STRING argument
    (``session_lifecycle.create_session``'s own ``policy_parameter_source_status`` parameter,
    sourced today from ``c_session_service._APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS``, renamed
    CONNECT Step 4 from ``_NOT_LIVE_PARAMETER_SOURCE_STATUS`` -- the ONLY value any real session in
    this codebase is ever gated on) -- that string is never read off a ``PolicyConfig`` object,
    because none exists yet at session-creation time. The ``PolicyConfig`` object
    ``decide_and_persist_adaptation`` actually runs against is built LATER, per task, at
    ``submit_action``. These are two different values, from two different call sites, that CONNECT
    Step 4 keeps carrying the identical literal (now ``"APPROVED_FOR_PROVISIONAL_IMPLEMENTATION"``,
    was ``"TEST_FIXTURE_ONLY"``) -- but nothing before this function made that STRUCTURAL. A future
    change resolving a governed ``PolicyConfig`` for the session-start gate while ``submit_action``
    still passed a config with a different status would produce
    a governed-looking session silently running adaptation on invented thresholds, with the gate
    itself reporting success -- because the gate never looked at the object doing the work.

    This is the RUNTIME half of closing that gap: called at the one point in ``submit_action``
    where a real ``PolicyConfig`` object exists, immediately before it is handed to
    ``decide_and_persist_adaptation``, comparing its OWN ``parameter_source_status`` against the
    value that gated this session's creation. An import-time / object-identity coincidence (both
    call sites merely referencing the same constant) would prove only that the two started equal,
    not that they stay tied together after either call site is edited independently -- this
    assertion re-checks the relationship on every call. Raises the same
    ``ConfigurationFamilyNotUsableError`` every other family-usability failure raises (X1/Z2's own
    one-mechanism, one-error-type discipline), naming ``policy_config`` and
    ``parameter_source_status`` -- never the values themselves."""
    if policy_config.parameter_source_status != session_gated_parameter_source_status:
        raise ConfigurationFamilyNotUsableError("policy_config", ("parameter_source_status",))


def assert_q_policy_matches_session_gate(
    q_policy_parameter_source_status: str, *, session_gated_parameter_source_status: str
) -> None:
    """LIVE-01 seam, the Q-policy twin of ``assert_policy_config_matches_session_gate``: the status of the Q
    artifact actually loaded at ``submit_action`` must equal the status the session was gated on at creation
    (``q_policy_config`` family, ``session_lifecycle.create_session``). Raises the same
    ``ConfigurationFamilyNotUsableError`` as the other gates."""
    if q_policy_parameter_source_status != session_gated_parameter_source_status:
        raise ConfigurationFamilyNotUsableError("q_policy_config", ("parameter_source_status",))
