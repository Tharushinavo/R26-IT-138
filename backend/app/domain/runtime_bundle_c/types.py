"""Backend domain mirror of ``provenance/c-runtime-bundle.schema.json`` (Phase 2).

Reuses ``Checksum``/``SourceArtifact``/``VersionedArtifact``/``Compatibility`` from
``app.domain.runtime_bundle.types`` (Component B's own domain module) directly -- those four
dataclasses carry no B-specific field or meaning; they are unchanged, structurally shared
shapes. Only the top-level aggregate is new: unlike
``app.domain.runtime_bundle.types.RuntimeBundle``, ``CRuntimeBundle`` carries none of B's config
blocks (``bkt_configuration``, ``certification_configuration``, ``guess_guard_configuration``,
``sequencing_configuration``, ``safe_progress_policy``, ``attempt_policy``, ``timeout_policy``,
``completion_policy``, ``cold_start_policy``) -- none of those are Component C concepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from app.domain.runtime_bundle.types import Checksum, Compatibility, SourceArtifact, VersionedArtifact


@dataclass(frozen=True)
class SelectionConfigurationArtifact:
    """Phase 4b, schema_version 1.1, AMENDED Phase 6b (schema_version 1.2, BREAKING -- see the
    schema's own top-level description). Mirrors ``provenance/c-runtime-bundle.schema.json``'s
    ``selectionConfiguration`` $def exactly. ``config_version``/``parameter_source_status`` are
    carried as their own independent fields, never derived from ``version`` (unchanged reasoning
    from 1.1). Every numeric/config value here is whatever the bundle manifest records -- never a
    default supplied by this type; a bundle without this block produces no instance of it at all
    (``Optional`` on ``CRuntimeBundle`` below), never a placeholder instance.

    PHASE 6b: the flat, block-level ``approval_status`` field is GONE, replaced by
    ``field_statuses``/``field_sources`` -- one entry per real parameter field (the five keys
    named in ``FIELD_NAMES`` below), read directly off each field's own ``{source, status,
    value}`` object in the manifest. The five *value* fields below stay flat scalars (unchanged
    shape, unchanged consumers -- ``resolve_selection_config`` still reads them exactly as
    before); only the STATUS bookkeeping moved from one block-level field to five per-field
    entries."""

    FIELD_NAMES = (
        "familiarization_window_by_grade",
        "familiarization_difficulty_level",
        "fallback_difficulty_level",
        "familiarization_session_difficulty_cap",
        "fallback_difficulty_cap",
    )

    version: str
    checksum: Checksum
    config_version: str
    parameter_source_status: str
    familiarization_window_by_grade: Mapping[int, int]
    familiarization_difficulty_level: int
    fallback_difficulty_level: int
    familiarization_session_difficulty_cap: int
    fallback_difficulty_cap: int
    field_statuses: Mapping[str, str]
    field_sources: Mapping[str, str]


@dataclass(frozen=True)
class SafetyConfigurationArtifact:
    """Phase 6b, schema_version 1.2, NEW. Mirrors ``provenance/c-runtime-bundle.schema.json``'s
    ``safetyConfiguration`` $def exactly -- per-field {source, status, value} from the start
    (S3/W2: this family is provably mixed, unlike selection_configuration which only became
    mixed on correction). Same shape as ``SelectionConfigurationArtifact``: flat scalar value
    fields plus ``field_statuses``/``field_sources`` maps, one entry per of the nine
    ``FIELD_NAMES`` below."""

    FIELD_NAMES = (
        "consecutive_error_trigger",
        "strain_trigger",
        "increase_block_window",
        "prior_overloaded_disengaged_cap",
        "safe_termination_error_threshold",
        "strain_bucket_low_max",
        "strain_bucket_moderate_max",
        "strain_bucket_high_max",
    )

    version: str
    checksum: Checksum
    config_version: str
    parameter_source_status: str
    consecutive_error_trigger: int
    strain_trigger: float
    increase_block_window: int
    prior_overloaded_disengaged_cap: int
    safe_termination_error_threshold: int
    strain_bucket_low_max: float
    strain_bucket_moderate_max: float
    strain_bucket_high_max: float
    field_statuses: Mapping[str, str]
    field_sources: Mapping[str, str]


@dataclass(frozen=True)
class EvidenceWindowConfigurationArtifact:
    """SEVENTH-FAMILY GATE batch. Mirrors ``provenance/c-runtime-bundle.schema.json``'s
    ``evidenceWindowConfiguration`` $def exactly -- per-field {source, status, value} from the
    start (same discipline ``SafetyConfigurationArtifact`` used, S3/W2's own reasoning, not
    reopened here: a single-field family still gets a per-field status map rather than a
    block-level one, since SUPERVISOR RULING 2/4 require per-field {source, status, value} and
    treat schema-optional/gate-required as separate layers regardless of field count). Same
    shape as ``SelectionConfigurationArtifact``/``SafetyConfigurationArtifact``: flat scalar
    value field(s) plus ``field_statuses``/``field_sources`` maps, one entry per of the single
    ``FIELD_NAMES`` entry below."""

    FIELD_NAMES = ("recent_window_task_count",)

    version: str
    checksum: Checksum
    config_version: str
    parameter_source_status: str
    recent_window_task_count: int
    field_statuses: Mapping[str, str]
    field_sources: Mapping[str, str]


@dataclass(frozen=True)
class CRuntimeBundle:
    schema_version: str
    bundle_version: str
    publication_state: str
    backend_code_version: str
    database_schema_revision: str
    generator: SourceArtifact
    catalogue: VersionedArtifact
    approval_status: str
    activation_date: Optional[str]
    compatibility: Compatibility
    selection_configuration: Optional[SelectionConfigurationArtifact]
    safety_configuration: Optional[SafetyConfigurationArtifact]
    evidence_window_configuration: Optional[EvidenceWindowConfigurationArtifact]
