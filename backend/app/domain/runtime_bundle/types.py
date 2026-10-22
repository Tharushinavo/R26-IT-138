"""Backend domain mirror of ``runtime-bundle.schema.json`` (frozen, BE0).

Plain, immutable dataclasses built from a schema-validated manifest dict. Field names follow
the schema's own property names so the mapping in the infrastructure loader stays a direct,
auditable transcription rather than a reinterpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class Checksum:
    algorithm: str
    value: str


@dataclass(frozen=True)
class SourceArtifact:
    source_identifier: str
    source_path: str
    checksum: Checksum
    interface_version: str


@dataclass(frozen=True)
class VersionedArtifact:
    version: str
    checksum: Checksum
    approval_status: str


@dataclass(frozen=True)
class SequencingConfiguration:
    version: str
    checksum: Checksum
    approval_status: str
    weights: Mapping[str, float]


@dataclass(frozen=True)
class ColdStartPolicy:
    status: str
    version: str
    checksum: Checksum


@dataclass(frozen=True)
class Compatibility:
    backend_api_major: int
    generator_interface_version: str
    python_specifier: str
    database_schema_minimum: str
    supported_grades: tuple[int, ...]
    skills: tuple[str, ...]
    required_catalogue_template_count: int


@dataclass(frozen=True)
class RuntimeBundle:
    schema_version: str
    bundle_version: str
    publication_state: str
    backend_code_version: str
    database_schema_revision: str
    generator: SourceArtifact
    catalogue: VersionedArtifact
    bkt_configuration: VersionedArtifact
    certification_configuration: VersionedArtifact
    guess_guard_configuration: VersionedArtifact
    sequencing_configuration: SequencingConfiguration
    safe_progress_policy: VersionedArtifact
    attempt_policy: VersionedArtifact
    timeout_policy: VersionedArtifact
    completion_policy: VersionedArtifact
    cold_start_policy: ColdStartPolicy
    approval_status: str
    activation_date: Optional[str]
    compatibility: Compatibility
