"""Typed mathematical task-instance model + activation/manifest records (Phase B2A).

A :class:`GeneratedItemInstance` is the deterministic *mathematical content* instantiated on
top of a completed Phase-B1 ``GeneratedItemOpportunity``: sampled operands / structured
quantity data, a recomputed correct answer, allowed equivalent answers, and mathematical
distractor candidates — with the applied hard guards recorded (SPEC §8; catalogue §8/§12).

Phase B2A is content-only. This record carries **no learner response**: attempt-derived and
mastery fields (``first_attempt_correct``, ``total_attempts``, ``hint_requests_item``,
``response_time``, BKT mastery, certification, guess-guard) are **not** fields here — they
belong to later learner-response / mastery phases. This record also carries no ``population``
and no ``dd_subtype`` (SF-039 — those are audit-only, on the learner identity, never here).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .enums import Grade
from .session import SeedLineage

# item_instance_id: STU-0001-B003-I002-X001  (opportunity id + task-instance suffix)
ITEM_INSTANCE_ID_RE = re.compile(r"^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}-X[0-9]{3}$")

# Response formats permitted by the catalogue (§2.4) — the subset used by Phase-B2A samplers
# plus the full vocabulary for forward compatibility.
ResponseFormat = str

ValidityStatus = Literal["VALID"]

# Learner-response / mastery fields that MUST remain unpopulated in Phase B2A. They are not
# declared on this model at all; this tuple documents the boundary and is asserted in tests.
DEFERRED_RESPONSE_FIELDS: Tuple[str, ...] = (
    "first_attempt_correct",
    "final_item_completed",
    "total_attempts",
    "hint_requests_item",
    "first_attempt_error_class",
    "response_time",
    "submitted_answer",
    "bkt_mastery",
    "mastery_certified",
    "guess_guard_result",
)

# Audit-only labels that must never appear on a generated instance (SF-039).
FORBIDDEN_INSTANCE_FIELDS: Tuple[str, ...] = ("population", "dd_subtype")


class GeneratedItemInstance(BaseModel):
    """One deterministic mathematical task instance (Phase B2A)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- identity / lineage (game-independent) ---
    item_instance_id: str
    item_opportunity_id: str
    learner_id: str
    scheduled_session_index: int
    item_index: int

    # --- catalogue linkage ---
    item_template_id: str
    task_type: str
    skill_id: str
    curriculum_node_id: str  # INTERNAL ONLY — never crosses B->C
    grade: Grade
    difficulty_level: str  # catalogue difficulty metadata (e.g. "L2")
    representation_type: str
    response_format: ResponseFormat

    # --- generated mathematical content ---
    generated_operands: Dict[str, Any]  # structured quantity data (sampled inputs)
    prompt: Dict[str, Any]  # renderable prompt data (stem + representation params)
    correct_answer: str  # canonical, normalized string form (recomputed, never trusted)
    allowed_equivalent_answers: Tuple[str, ...] = ()
    distractor_candidates: Tuple[str, ...] = ()
    distractor_rule_ids: Tuple[str, ...] = ()  # generating rule id per retained candidate

    # --- provenance / determinism ---
    generation_seed: int
    seed_lineage: SeedLineage
    catalogue_version: str
    catalogue_checksum: str

    # --- validity ---
    validity_status: ValidityStatus = "VALID"
    applied_guard_ids: Tuple[str, ...] = ()

    generation_phase: str = "B2A"

    @field_validator("item_instance_id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not ITEM_INSTANCE_ID_RE.match(v):
            raise ValueError(f"item_instance_id must match {ITEM_INSTANCE_ID_RE.pattern}, got {v!r}")
        return v

    @model_validator(mode="after")
    def _answer_option_invariants(self) -> "GeneratedItemInstance":
        # The correct answer may never appear among the distractor candidates, and the full
        # option set (correct + distractors) must be free of duplicates (catalogue §8).
        if self.correct_answer in self.distractor_candidates:
            raise ValueError("distractor_candidates must never contain the correct_answer")
        options = (self.correct_answer,) + tuple(self.distractor_candidates)
        if len(set(options)) != len(options):
            raise ValueError("answer options (correct + distractors) must be unique")
        if len(set(self.distractor_candidates)) != len(self.distractor_candidates):
            raise ValueError("distractor_candidates must be unique")
        return self


class ActivationDecision(BaseModel):
    """Explicit runtime-activation decision for one template (never inferred solely from the
    absence of ``RETIRED``). Records every input that produced ``active``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_template_id: str
    recognized: bool  # a known catalogue template id
    implementation_supported: bool  # a Phase-B2A sampler/answer/distractor strategy exists
    grade_eligible: bool  # eligible for the requested grade (grade gate)
    curriculum_active: bool  # not RETIRED / not DEFERRED
    catalogue_status_ok: bool  # catalogue-level status recognized
    calibration_restricted: bool  # grade gate or values are CALIBRATION_PENDING for this use
    active: bool
    reason: str


class TaskInstanceRunManifest(BaseModel):
    """Phase-B2A reproducibility provenance (extends the B1 manifest's guarantees).

    ``run_timestamp_metadata`` is recorded as **metadata only** and is never used as a random
    seed (determinism derives solely from ``global_seed`` + config + catalogue checksum).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    generation_phase: str
    generator_package_version: str
    global_seed: int
    config_version: str
    config_hash: str
    smoke_mode: bool
    catalogue_version: str
    catalogue_status: str
    catalogue_source_path: str
    catalogue_checksum: str
    sampler_registry_version: str
    code_version: str
    git_commit: Optional[str] = None  # populated when a git checkout is available
    python_version: str
    run_timestamp_metadata: str  # provenance only — NOT a seed
    n_item_opportunities: int
    n_item_instances: int
    implemented_template_ids: Tuple[str, ...]
    unsupported_template_ids: Tuple[str, ...]  # run-scoped: templates skipped in THIS run
    # --- Phase B2A.2 additions (defaults keep any prior construction path valid) ---
    implementation_phase: str = "B2A"
    answer_registry_version: str = ""
    distractor_registry_version: str = ""
    guard_registry_version: str = ""
    catalogue_count: int = 0  # total authoritative templates (derived)
    implemented_count: int = 0  # catalogue-wide implemented count (derived)
    deferred_count: int = 0  # catalogue-wide deferred count (derived)
    deferred_template_ids: Tuple[str, ...] = ()
    coverage_summary: Tuple[Tuple[str, str], ...] = ()  # (template_id, coverage_status) per template
    disclosure: str = "Literature-informed synthetic data — not clinical evidence."
