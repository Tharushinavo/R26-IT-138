"""``RuntimeBundleLoader`` — schema validation, checksum verification, and the approval gate.

Fail-closed by construction: every branch either returns a fully validated, approved
``RuntimeBundle`` or raises one of ``app.domain.runtime_bundle.errors``. There is no code path
that returns a partial bundle, a default value, or a silently-substituted fallback.
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
from app.domain.runtime_bundle.types import (
    Checksum,
    ColdStartPolicy,
    Compatibility,
    RuntimeBundle,
    SequencingConfiguration,
    SourceArtifact,
    VersionedArtifact,
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


class RuntimeBundleLoader:
    """Concrete ``RuntimeBundleLoaderPort`` implementation."""

    def load_and_validate(
        self,
        bundle_path: str,
        schema_path: str,
        *,
        artifact_paths: Optional[Mapping[str, str]] = None,
        require_approved: bool = True,
    ) -> RuntimeBundle:
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

        sequencing_raw = manifest["sequencing_configuration"]
        sequencing_configuration = SequencingConfiguration(
            version=sequencing_raw["version"],
            checksum=_checksum(sequencing_raw["checksum"]),
            approval_status=sequencing_raw["approval_status"],
            weights=dict(sequencing_raw["weights"]),
        )

        cold_start_raw = manifest["cold_start_policy"]
        cold_start_policy = ColdStartPolicy(
            status=cold_start_raw["status"],
            version=cold_start_raw["version"],
            checksum=_checksum(cold_start_raw["checksum"]),
        )

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
                f"{approval_status!r}, not 'APPROVED' — refusing to activate"
            )

        return RuntimeBundle(
            schema_version=manifest["schema_version"],
            bundle_version=manifest["bundle_version"],
            publication_state=manifest["publication_state"],
            backend_code_version=manifest["backend_code_version"],
            database_schema_revision=manifest["database_schema_revision"],
            generator=generator,
            catalogue=_versioned_artifact(manifest["catalogue"]),
            bkt_configuration=_versioned_artifact(manifest["bkt_configuration"]),
            certification_configuration=_versioned_artifact(manifest["certification_configuration"]),
            guess_guard_configuration=_versioned_artifact(manifest["guess_guard_configuration"]),
            sequencing_configuration=sequencing_configuration,
            safe_progress_policy=_versioned_artifact(manifest["safe_progress_policy"]),
            attempt_policy=_versioned_artifact(manifest["attempt_policy"]),
            timeout_policy=_versioned_artifact(manifest["timeout_policy"]),
            completion_policy=_versioned_artifact(manifest["completion_policy"]),
            cold_start_policy=cold_start_policy,
            approval_status=approval_status,
            activation_date=manifest["activation_date"],
            compatibility=compatibility,
        )
