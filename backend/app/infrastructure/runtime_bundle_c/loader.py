"""``CRuntimeBundleLoader`` -- schema validation, checksum verification, and the approval gate
for Component C's minimal runtime bundle (Phase 2).

DEVIATION FROM THE ORIGINAL PLAN, RECORDED HERE: the plan was to reuse
``app.infrastructure.runtime_bundle.loader.RuntimeBundleLoader`` unmodified. Verified this does
not work: ``RuntimeBundleLoader.load_and_validate``'s body unconditionally reads B-only manifest
keys (``manifest["sequencing_configuration"]``, ``manifest["bkt_configuration"]``, ...) that a
schema-valid C-shaped bundle does not have -- a real ``KeyError``, independent of and after
``jsonschema.validate`` itself already passed. ``RuntimeBundleLoader`` is not B's *adapter*, but
it is shared, already-tested infrastructure the work order lists changing as out of scope, so it
is not modified, not imported, and not subclassed here. This file mirrors its STRUCTURE (same
``jsonschema`` validation approach, the same per-artifact SHA-256 checksum verification, the
same ``require_approved`` gate raising the same, reused domain error types from
``app.domain.runtime_bundle.errors``) but extracts only Component C's own, smaller field set.
The three private helpers below (``_sha256_of``/``_verify_checksum``/``_checksum``) are
duplicated from ``runtime_bundle/loader.py`` because they are module-private there (not
exported) and are themselves generic byte-hashing/comparison utilities with no B-specific logic.

Fail-closed by construction, same as B's: every branch either returns a fully validated,
approved ``CRuntimeBundle`` or raises one of ``app.domain.runtime_bundle.errors``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional

import jsonschema

from app.domain.runtime_bundle.errors import (
    RuntimeBundleChecksumMismatchError,
    RuntimeBundleNotApprovedError,
    RuntimeBundleNotFoundError,
    RuntimeBundleValidationError,
)
from app.domain.runtime_bundle.types import Checksum, Compatibility, SourceArtifact, VersionedArtifact
from app.domain.runtime_bundle_c.types import (
    CRuntimeBundle,
    EvidenceWindowConfigurationArtifact,
    SafetyConfigurationArtifact,
    SelectionConfigurationArtifact,
)


def _read_json(path: str, *, not_found_message: str) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        raise RuntimeBundleNotFoundError(not_found_message)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeBundleValidationError(f"{path} is not valid JSON: {exc}") from exc


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_checksum(path: Path, checksum: Mapping[str, str], *, label: str) -> None:
    # Note (v3.0 §12.3, mirrored): no try/except is needed around _sha256_of here because the
    # only caller (below) always pre-checks path.exists() first, exactly as B's own equivalent
    # does. A dedicated missing-artifact test still exists as a positive control (X-10), not
    # because this is a defect.
    if not path.exists():
        raise RuntimeBundleChecksumMismatchError(
            f"{label}: referenced artifact file does not exist: {path}"
        )
    if checksum.get("algorithm") != "sha256":
        raise RuntimeBundleValidationError(f"{label}: unsupported checksum algorithm {checksum.get('algorithm')!r}")
    actual = _sha256_of(path)
    expected = checksum.get("value")
    if actual != expected:
        raise RuntimeBundleChecksumMismatchError(
            f"{label}: checksum mismatch for {path} (expected {expected}, got {actual})"
        )


def _checksum(raw: Mapping[str, Any]) -> Checksum:
    return Checksum(algorithm=raw["algorithm"], value=raw["value"])


def _versioned_artifact(raw: Mapping[str, Any]) -> VersionedArtifact:
    return VersionedArtifact(
        version=raw["version"], checksum=_checksum(raw["checksum"]), approval_status=raw["approval_status"]
    )


def _selection_configuration(raw: Optional[Mapping[str, Any]]) -> Optional[SelectionConfigurationArtifact]:
    """Phase 4b: absent (``None``) on any bundle that has not been republished with this block --
    additive-only (owner condition 2). Never substitutes a placeholder; the caller of this
    loader, not this function, decides whether an absent block is fatal for what it's about to
    do (owner condition 1: "halt, not default" belongs at the consumer of W, not here).

    Phase 6b (schema_version 1.2, BREAKING): each of the five real parameter fields is now a
    ``{source, status, value}`` object, not a flat scalar. This function reads ``value`` for the
    flat scalar fields below (unchanged consumer shape) and separately collects every field's
    ``status``/``source`` into ``field_statuses``/``field_sources`` -- the per-field usability
    gate's own input (``bundle_resolution.py``)."""
    if raw is None:
        return None
    window_raw = raw["familiarization_window_by_grade"]
    field_statuses = {name: raw[name]["status"] for name in SelectionConfigurationArtifact.FIELD_NAMES}
    field_sources = {name: raw[name]["source"] for name in SelectionConfigurationArtifact.FIELD_NAMES}
    return SelectionConfigurationArtifact(
        version=raw["version"],
        checksum=_checksum(raw["checksum"]),
        config_version=raw["config_version"],
        parameter_source_status=raw["parameter_source_status"],
        familiarization_window_by_grade={
            int(grade): window for grade, window in window_raw["value"].items()
        },
        familiarization_difficulty_level=raw["familiarization_difficulty_level"]["value"],
        fallback_difficulty_level=raw["fallback_difficulty_level"]["value"],
        familiarization_session_difficulty_cap=raw["familiarization_session_difficulty_cap"]["value"],
        fallback_difficulty_cap=raw["fallback_difficulty_cap"]["value"],
        field_statuses=field_statuses,
        field_sources=field_sources,
    )


def _safety_configuration(raw: Optional[Mapping[str, Any]]) -> Optional[SafetyConfigurationArtifact]:
    """Phase 6b, NEW: symmetric to ``_selection_configuration`` above, per-field from the start
    (S3/W2 -- this family is provably mixed, so it never had a block-level status to migrate
    away from)."""
    if raw is None:
        return None
    field_statuses = {name: raw[name]["status"] for name in SafetyConfigurationArtifact.FIELD_NAMES}
    field_sources = {name: raw[name]["source"] for name in SafetyConfigurationArtifact.FIELD_NAMES}
    return SafetyConfigurationArtifact(
        version=raw["version"],
        checksum=_checksum(raw["checksum"]),
        config_version=raw["config_version"],
        parameter_source_status=raw["parameter_source_status"],
        consecutive_error_trigger=raw["consecutive_error_trigger"]["value"],
        strain_trigger=raw["strain_trigger"]["value"],
        increase_block_window=raw["increase_block_window"]["value"],
        prior_overloaded_disengaged_cap=raw["prior_overloaded_disengaged_cap"]["value"],
        safe_termination_error_threshold=raw["safe_termination_error_threshold"]["value"],
        strain_bucket_low_max=raw["strain_bucket_low_max"]["value"],
        strain_bucket_moderate_max=raw["strain_bucket_moderate_max"]["value"],
        strain_bucket_high_max=raw["strain_bucket_high_max"]["value"],
        field_statuses=field_statuses,
        field_sources=field_sources,
    )


def _evidence_window_configuration(
    raw: Optional[Mapping[str, Any]],
) -> Optional[EvidenceWindowConfigurationArtifact]:
    """SEVENTH-FAMILY GATE batch: symmetric to ``_safety_configuration`` above, per-field from
    the start (SUPERVISOR RULING 2/4: additive block, per-field {source, status, value}, no
    const anywhere on a PROPOSED_UNSIGNED/CALIBRATION_PENDING field)."""
    if raw is None:
        return None
    field_statuses = {
        name: raw[name]["status"] for name in EvidenceWindowConfigurationArtifact.FIELD_NAMES
    }
    field_sources = {
        name: raw[name]["source"] for name in EvidenceWindowConfigurationArtifact.FIELD_NAMES
    }
    return EvidenceWindowConfigurationArtifact(
        version=raw["version"],
        checksum=_checksum(raw["checksum"]),
        config_version=raw["config_version"],
        parameter_source_status=raw["parameter_source_status"],
        recent_window_task_count=raw["recent_window_task_count"]["value"],
        field_statuses=field_statuses,
        field_sources=field_sources,
    )


class CRuntimeBundleLoader:
    """Concrete loader for Component C's minimal runtime bundle."""

    def load_and_validate(
        self,
        bundle_path: str,
        schema_path: str,
        *,
        artifact_paths: Optional[Mapping[str, str]] = None,
        require_approved: bool = True,
    ) -> CRuntimeBundle:
        schema = _read_json(schema_path, not_found_message=f"runtime-bundle schema not found: {schema_path}")
        manifest = _read_json(bundle_path, not_found_message=f"runtime-bundle manifest not found: {bundle_path}")

        try:
            jsonschema.validate(instance=manifest, schema=schema)
        except jsonschema.ValidationError as exc:
            raise RuntimeBundleValidationError(
                f"runtime-bundle manifest failed schema validation at {list(exc.absolute_path)}: {exc.message}"
            ) from exc
        except jsonschema.SchemaError as exc:
            raise RuntimeBundleValidationError(f"runtime-bundle schema itself is invalid: {exc.message}") from exc

        generator_raw = manifest["generator"]
        generator = SourceArtifact(
            source_identifier=generator_raw["source_identifier"],
            source_path=generator_raw["source_path"],
            checksum=_checksum(generator_raw["checksum"]),
            interface_version=generator_raw["interface_version"],
        )
        _verify_checksum(Path(generator.source_path), generator_raw["checksum"], label="generator")

        artifact_paths = artifact_paths or {}
        for field_name, checked_path in artifact_paths.items():
            raw_field = manifest.get(field_name)
            if raw_field is None or "checksum" not in raw_field:
                raise RuntimeBundleValidationError(
                    f"artifact_paths supplied a path for {field_name!r}, which has no checksum in the manifest"
                )
            _verify_checksum(Path(checked_path), raw_field["checksum"], label=field_name)

        compatibility_raw = manifest["compatibility"]
        compatibility = Compatibility(
            backend_api_major=compatibility_raw["backend_api_major"],
            generator_interface_version=compatibility_raw["generator_interface_version"],
            python_specifier=compatibility_raw["python_specifier"],
            database_schema_minimum=compatibility_raw["database_schema_minimum"],
            supported_grades=tuple(compatibility_raw["supported_grades"]),
            skills=tuple(compatibility_raw["skills"]),
            required_catalogue_template_count=compatibility_raw["required_catalogue_template_count"],
        )

        approval_status = manifest["approval_status"]
        if require_approved and approval_status != "APPROVED":
            raise RuntimeBundleNotApprovedError(
                f"runtime bundle {manifest.get('bundle_version')!r} has approval_status "
                f"{approval_status!r}, not 'APPROVED' -- refusing to activate"
            )

        return CRuntimeBundle(
            schema_version=manifest["schema_version"],
            bundle_version=manifest["bundle_version"],
            publication_state=manifest["publication_state"],
            backend_code_version=manifest["backend_code_version"],
            database_schema_revision=manifest["database_schema_revision"],
            generator=generator,
            catalogue=_versioned_artifact(manifest["catalogue"]),
            approval_status=approval_status,
            activation_date=manifest["activation_date"],
            compatibility=compatibility,
            selection_configuration=_selection_configuration(manifest.get("selection_configuration")),
            safety_configuration=_safety_configuration(manifest.get("safety_configuration")),
            evidence_window_configuration=_evidence_window_configuration(
                manifest.get("evidence_window_configuration")
            ),
        )
