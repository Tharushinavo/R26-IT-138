"""Component C Phase 5: the application-service layer behind the two task-serving HTTP endpoints
(``POST .../tasks/next``, ``POST .../tasks/{tid}/actions``).

HEADLINE CONSEQUENCE, PHASE 5 THROUGH CONNECT STEP 3 (Phase 5 work order, verbatim instruction,
STATE PLAINLY): PHASE 5 DELIVERED A COMPLETE, TESTED SERVING PATH THAT WAS DELIBERATELY NOT LIVE.
Every real (non-smoke) call to ``next_task`` refused before any task was generated, because
GenerationConfig had no governed values anywhere in this codebase (S1, Phase 5 work order): "The
frozen catalogue supplies no numeric bound and no action-space enumeration for any of the 30
templates and the Parameters do not fix them either; every value is an ENGINEERING_ASSUMPTION
tagged TEST_FIXTURE_ONLY. Governance assigned no values here." That reasoning was correct for as
long as it was true — it stopped being true at CONNECT Step 1, when the owner approved Family 4
(Generation) "with condition" in ``APPROVAL-2026-08-26-seven-families.md``: "Generated task
payloads must remain schema-constrained and must never expose answer-bearing values. Unsupported
payload structures must fail closed." ``app.domain.live_engine_c.generation_mode_guard.
assert_generation_config_permitted`` is the guard that enforces schema-conformance and fail-closed
behaviour; it stays wired in below, unchanged, and still runs on every call — CONNECT Step 4 changes
what config it is checking, never whether the check runs. A green test suite exercising this module
is now evidence the serving mechanism can be reached in production, under the values and status
this docstring names below — not evidence of clinical or pedagogical readiness, which
``APPROVAL-2026-08-26-seven-families.md`` does not claim either.

GENERATIONCONFIG STAYS INJECTION-ONLY, NO DEFAULT ANYWHERE, AND THIS MODULE STILL NEVER READS THE
PACKAGE'S OWN TABLE DIRECTLY (S1, mirrors W1's shape for SelectionConfig — UNCHANGED, in the end,
BY CONNECT STEP 4, though a first attempt at this step crossed it and proved the crossing
unnecessary; recorded here because that is worth knowing, not because it happened). Every function
below that needs a ``GenerationConfig`` still takes it as a required, no-default parameter, and
this module still never calls ``default_generation_config()`` — asserted mechanically, see
``test_be2_architecture_guards.py::test_no_app_code_defaults_or_calls_default_generation_config``.
A separate, independent guard in the same file
(``test_component_c_generator_full_dotted_path_enforcement``) restricts ``component_c_generator``
as an import root to exactly one file, ``app/infrastructure/live_engine_c/adapter.py`` — the first
implementation of ``PRODUCTION_GENERATION_CONFIG`` below imported
``generation_config.DEFAULT_TEMPLATE_GENERATION_PARAMS`` directly here and tripped it, a real
finding, not a false positive: this module has no more business reading that table than any other
non-adapter file does. Correction (supervisor ruling, CONNECT Step 4): the values are obtained
through ``LiveEngineCAdapter.production_generation_params_by_template()`` /
``.production_generation_config_version()``, the same shape ``supported_template_ids()`` already
uses to expose package data to this layer — so the no-direct-read discipline this paragraph states
is not merely restored, it was never actually broken in what shipped. Under
``APPROVAL-2026-08-26-seven-families.md`` Family 4 ("Generated task payloads must remain
schema-constrained and must never expose answer-bearing values. Unsupported payload structures
must fail closed."), the resulting config covers all 30 real catalogue template ids (verified 1:1
against the vendored catalogue, not assumed) and is tagged
``APPROVED_FOR_PROVISIONAL_IMPLEMENTATION``, not a silent promotion to a status that looks more
settled than the approval actually was.

PRODUCTION GENERATION CONFIG (was: PRODUCTION GENERATION-CONFIG PROBE, renamed CONNECT Step 4 —
see that step's own buildLog2.md entry for why keeping "PROBE" on a populated, approved object
would itself have been the misleading-name defect this rename exists to avoid). Prior state,
preserved rather than erased: the real HTTP route (``app.api.routes.c_task``) had no legitimate
source for a populated ``GenerationConfig`` — no bundle mechanism existed (S1 explicitly forbade
building one) and no default call was permitted (above) — so it passed an intentionally EMPTY probe
(``per_template={}``, ``parameter_source_status="TEST_FIXTURE_ONLY"``), unconditionally refused by
the guard regardless of content, its emptiness a second, redundant containment. CONNECT Step 4
replaces that probe with a real, populated config under the Family 4 approval named above; the
guard call itself is untouched — it now passes for a different, disclosed reason (a real,
approved-for-provisional-implementation status) rather than being bypassed.

SEED LINEAGE — BUILDER JUDGMENT — UNRATIFIED, DISCLOSED PROMINENTLY. ``SeedLineage``'s own
docstring (``app/domain/live_engine_c/types.py``) says: "obtaining a real seed value is left to
whichever future phase's work order explicitly authorizes that call" — this work order does not
mention seed lineage construction anywhere. What follows is the minimum, non-derived plumbing
needed to call ``select_task`` at all: ``component_c_session_lineage`` is the session's own
``global_seed`` at the ROOT (``path=()``, ``seed=global_seed`` — the value BEFORE any derivation,
not a derived one); ``task_opportunity_lineage`` uses ``task_index`` (a real, already-known,
non-invented value) as its sole path-distinguishing element so that different tasks within one
session receive different lineages, matching the name's own singular-per-opportunity shape. NO
hash/mixing function is called here — ``derive_child_lineage``/``SeedManager``/``rng_from``/
``SUBSTREAMS`` are called ONLY inside the package's own ``select_task``, never in this module or
the adapter (unchanged from Phase 1b's boundary). These are plain integers/string-pair tuples,
not a B-shaped identifier of any kind — see R-8 below for the field that IS.

R-8 (SUPERVISOR RULING, Phase 5 continuation): the ORIGINAL version of this module derived its own
``STU-####``/``STU-####-C-###`` values from a UUID hash (a SECOND, independent construction site
minting a B-shaped identifier, alongside the mastery fixture's own ``FIXTURE_MASTERY_SOURCE_
STUDENT_ID = "STU-0001"``). That is exactly the defect R-5 exists to prevent: two places computing
what is nominally "the same real child's platform identity" would almost always DISAGREE (a
UUID-hash derivation here, a fixed fictional constant there), for the SAME learner, inside the
SAME call. Collapsed to the single existing source: ``select_task``/``build_task_instance``'s
``student_id``/``c_session_id`` parameters, and ``evaluate``'s reconstructed ``TaskInstance``, now
read ``FIXTURE_MASTERY_SOURCE_STUDENT_ID`` (``mastery_fixture.py``) directly, for EVERY session
mode -- not only combined. This is deliberate, not an oversight: these two package parameters are
format-validated only (``^STU-[0-9]{4}$`` / ``^STU-[0-9]{4}-C-[0-9]{3}$``), never used for lookup,
RNG, or cross-referencing anywhere the installed wheel or this codebase does (confirmed: seed
derivation is the separate ``SeedLineage`` parameter above; nothing stores ``game_task_instance_id``
as its own column). For a ``c_only`` session there is no B mastery involved at all and no
real-B-session claim is being made by reusing this constant -- it is functioning here purely as
the ONE already-reviewed, already-fictional placeholder this codebase uses to satisfy the
package's format requirement, never as an assertion that B is involved. ``_stu_session_id_suffix``
below supplies a fixed session-distinguishing suffix for the same reason -- one constant, one
source, never a second minting site.

SESSIONS_SINCE_LAST_PRACTICE (P4): sourced EXCLUSIVELY through ``session_lifecycle.
_learner_session_state``, the SAME function Phase 4's session-phase decision already uses — never
re-derived here, never touching any B table or B-derived value.

MASTERY SOURCE + IDENTITY: reuses the exact same fixture producer as ``c_session_service.py``
(``fixture_b_mastery_payload_for_phase_4`` / ``fixture_b_provenance_for_phase_4``) for combined-
mode sessions — never from the client, same R-5 reasoning.

RAW EVENTS ONLY, THROUGH PHASE 5 (S6): Phase 5 left this module writing ``CGameplayEventRecord``
rows directly (``game_task_offered`` on ``next_task``, ``answer_evaluated`` on ``submit_action``)
and nothing else — no terminal event, no ``CTaskOpportunitySummaryRecord`` derivation. That was
correct for Phase 5's own scope; it was NOT because derivation belongs to Phase 8 (S6's stated
reason was wrong even though its effect was right — see ``app/domain/live_engine_c/ports.py``'s
``SummaryPort`` docstring, corrected this batch, T2).

TERMINAL EVENT + SUMMARY DERIVATION (T1/T6, Phase 6a work order): ``submit_action`` now writes a
``game_task_completed``/``completed_correct`` terminal event and derives+persists a
``CTaskOpportunitySummaryRecord`` when — and only when — the submitted action evaluates correct.
Owner ruling (T1), quoted verbatim: "One opportunity carries one ``correct_answer_payload`` and
the evaluator returns one verdict against it. I cannot construct a coherent reading in which a
correctly-answered opportunity stays open — a follow-on activity is a new opportunity, not a
continuation of a solved one. And it needs no unsigned parameter: a correct answer on attempt 2 of
a cap of 3 is ``completed_correct``, so the attempt bound never enters. The cap only governs the
incorrect path, which is exactly why your asymmetry is real rather than an oversight." The other
eight terminal reasons are NOT built — see ``app/application/live_engine_c/terminal_event.py``'s
module docstring for the full mapping and T1-5's plain statement of what that leaves unclosed. The
terminal write and the summary derivation themselves live in ``terminal_event.py`` and
``summary_service.py`` respectively (T6-b: this module already carried three concerns).

BATCH 2 -- ``decide_and_persist_adaptation``'s FIRST LIVE CALLER (correcting adaptation_service.py's
own now-stale docstring claim that it is "exercised end-to-end only via direct calls"):
``submit_action``'s ``is_correct`` branch now calls ``build_evidence_for_session`` then
``decide_and_persist_adaptation`` immediately after ``derive_and_persist_summary`` -- see the
in-line comment at that call site for the ordering proof, ``bundle_resolution.
assert_policy_config_matches_session_gate`` for the policy-status seam this batch closes, and this
batch's own ``buildLog1.md`` entry for the full R0 trace of what this does and does not unblock
downstream (session aggregation, C-17 Item B). WIRED, NOT REACHABLE, same as every other path this
module documents above: the six-family session-creation gate (session_lifecycle.create_session)
still refuses every real HTTP request (X2-3) -- nothing about THIS call changes whether a session
can be created in production, only what happens on the correct-answer path of a session that
already exists (today, only a ``smoke_mode=True`` test-constructed one).

BATCH 3 (F-2, the read half): ``submit_action``'s incorrect-answer branch no longer passes the
literal ``safety_forces_recovery=False`` to ``decide_and_persist_scaffold_level`` -- it reads the
most recent prior ``c_policy_decisions`` row for the session and reads that row's own
``safety_forces_recovery`` (batch 3's new column, written by adaptation_service.py's own switch to
``decide_adaptation_with_safety_flags``), falling back to ``False`` explicitly, and for a stated
reason, only when no such row exists yet. See the in-line comment at that call site for the full
three-break register (rewritten this batch, not deleted) and the no-prior-row reasoning, and this
batch's own ``buildLog1.md`` entry for the full R0 trace and verdict on F-2.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.adaptation_service import build_evidence_for_session, decide_and_persist_adaptation
from app.application.live_engine_c.bundle_resolution import (
    assert_policy_config_matches_session_gate,
    assert_q_policy_matches_session_gate,
    resolve_c_bundle_and_catalogue,
    resolve_evidence_window_config,
    resolve_safety_config,
    resolve_selection_config,
)
from app.application.live_engine_c.c_session_service import (
    _APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
    _require_learner_id,
)
from app.application.live_engine_c.mastery_fixture import (
    FIXTURE_MASTERY_BY_SKILL,
    FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
    FIXTURE_MASTERY_SOURCE_STUDENT_ID,
    fixture_b_mastery_payload_for_phase_4,
    fixture_b_provenance_for_phase_4,
)
from app.application.live_engine_c.q_policy import DEFAULT_FIRST_TRY, load_q_policy, state_of as q_state_of
from app.application.live_engine_c.scaffold_service import decide_and_persist_scaffold_level
from app.application.live_engine_c.session_lifecycle import _learner_session_state, _provenance
from app.application.live_engine_c.summary_service import derive_and_persist_summary
from app.application.live_engine_c.telemetry_validation import get_derivable_history_for_session
from app.application.live_engine_c.terminal_event import write_completed_correct_terminal_event
from app.core.errors import ActionPayloadRejectedError, ConflictError, ResourceNotFoundError
from app.domain.c_task import CNextTaskResponse, CSubmitActionResult, CTaskFields
from app.domain.live_engine_c.action_payload_validation import (
    ActionPayloadValidationError,
    validate_action_payload,
)
from app.domain.live_engine_c.errors import LiveEngineCError, UnknownTemplateError
from app.domain.live_engine_c.client_support import selectable_template_ids
from app.domain.live_engine_c.prompt_wording import prompt_text_for
from app.domain.live_engine_c.generation_mode_guard import (
    GenerationConfigNotPermittedError,
    assert_generation_config_permitted,
)
from app.domain.live_engine_c.types import (
    GenerationConfig,
    PolicyConfig,
    PolicyMode,
    ScaffoldConfig,
    ScaffoldLevel,
    SeedLineage,
    TaskInstance,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CGameplayEventRecord, CTaskInstanceRecord, CTaskOpportunityRecord
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CPolicyDecisionRecordRepository,
    CSessionRecordRepository,
    CTaskInstanceRecordRepository,
    CTaskOpportunityRecordRepository,
)

# CONNECT Step 3: repointed to the owner-approved bundle, same as c_session_service.py, same
# disclosure and same provenance record (APPROVAL-2026-08-26-seven-families.md).
_BUNDLE_PATH = "provenance/c-runtime-bundle-approved-1.0.json"
_SCHEMA_PATH = "provenance/c-runtime-bundle.schema.json"
# CONNECT Step 2: repointed to the governed catalogue, vendored verbatim from the sibling Yass/
# tree (APPROVAL-2026-08-26-seven-families.md; see backend/buildLog2.md). Its own status line
# reads PROPOSED FOR APPROVAL, not APPROVED -- vendoring and repointing here does not change
# that. The TEST_FIXTURE_ONLY catalogue below stays in place; existing tests depend on it.
_CATALOGUE_PATH = "provenance/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md"

# CONNECT Step 4: was PRODUCTION_GENERATION_CONFIG_PROBE (deliberately empty, deliberately
# always-refused, per_template={}) -- see the module docstring's own rewritten paragraph for the
# full account, including the corrected routing below. Real, populated GenerationConfig over all
# 30 templates, values obtained through LiveEngineCAdapter -- never a direct import of
# component_c_generator here (test_component_c_generator_full_dotted_path_enforcement restricts
# that import root to app/infrastructure/live_engine_c/adapter.py alone; a first attempt imported
# the package's table directly in this file and correctly tripped that guard). Template-id
# coverage verified 1:1 against the vendored real catalogue's 30 ids -- no missing id either
# direction -- under APPROVAL-2026-08-26-seven-families.md Family 4 ("Generated task payloads must
# remain schema-constrained and must never expose answer-bearing values. Unsupported payload
# structures must fail closed."). assert_generation_config_permitted still runs on every call,
# unchanged -- this config passes it now for a disclosed reason, never by bypassing it.
_adapter_for_production_configs = LiveEngineCAdapter()
PRODUCTION_GENERATION_CONFIG = GenerationConfig(
    config_version=_adapter_for_production_configs.production_generation_config_version(),
    parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
    per_template=_adapter_for_production_configs.production_generation_params_by_template(),
)

# Phase 7, Z1/Z5: Scaffold is injection-only (zero SPEC-stated fields, same classification as
# Generation) but, unlike GenerationConfig, is NOT smoke-gated per task-call -- Z1's own
# inversion reasoning: gating a protective mechanism per-call would mean "refuse to emit a
# scaffold," which fails OPEN, not closed. Its usability is checked once, at SESSION START
# (session_lifecycle.create_session's own five-family gate). This config carries the SAME literal
# numbers component_c_generator.scaffolds.config.default_scaffold_config() would produce
# (hardcoded here, never calling that factory -- S8-a's guard) -- unchanged by CONNECT Step 4,
# because they already matched the real defaults (confirmed by reading scaffolds/config.py
# directly, not assumed). CONNECT Step 4: renamed from PRODUCTION_SCAFFOLD_CONFIG_PROBE (it was
# never empty like Generation's, but "probe" implied deliberately-unusable, which stops being true
# once a real approved status is attached) and parameter_source_status only moves, under
# APPROVAL-2026-08-26-seven-families.md Family 6 ("The backend remains authoritative for
# scaffold_level. The frontend only consumes...").
PRODUCTION_SCAFFOLD_CONFIG = ScaffoldConfig(
    config_version="c4.2-scaffold-1.0.0",
    parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
    level_c1_min_consecutive_incorrect=1,
    level_c2_min_consecutive_incorrect=2,
    level_c3_min_consecutive_incorrect=3,
    level_c4_min_consecutive_incorrect=4,
)

# BATCH 2 -- PRODUCTION POLICY-CONFIG PROBE, SUPERVISOR RULING, PRESERVED VERBATIM BECAUSE IT WAS
# CORRECT UNDER A CLOSED GATE (quoted in full, not summarised): "PolicyConfig has SIX required
# numeric fields, no defaults, so it cannot be constructed empty like the generation probe. A
# probe is therefore unavoidable. It must NOT mirror default_policy_config()'s values the way
# PRODUCTION_SCAFFOLD_CONFIG_PROBE mirrors default_scaffold_config(): values matching the real
# defaults make probe-supplied behaviour indistinguishable from correct behaviour, which for a
# config feeding the safety layer is the worst available failure mode. Carry
# parameter_source_status='TEST_FIXTURE_ONLY' and values chosen to be conspicuously
# non-calibrated." That ruling governed a config with no legitimate source of real values --
# governance had assigned none, so ANY plausible-looking number would have overstated what was
# known, and the ruling's own fix (implausible, edge-pinned values) was the correct response to
# that specific problem.
#
# CONNECT STEP 4 -- THE GATE OPENED, THE PROBLEM THE RULING SOLVED NO LONGER EXISTS: under
# APPROVAL-2026-08-26-seven-families.md Family 5 ("Policy -- APPROVED WITH CONDITION: retry is
# child-initiated and returns to the same task; scaffold escalation remains backend-controlled;
# exact retry limits and final feedback policy can be refined later"), governance has now assigned
# real values -- the same ones the ruling above named and forbade mirroring, because at the time
# they were merely plausible-looking rather than authorized. They are no longer merely
# plausible-looking. Renamed from PRODUCTION_POLICY_CONFIG_PROBE to PRODUCTION_POLICY_CONFIG for
# the same reason as Generation and Scaffold: it is no longer a probe. The real
# default_policy_config() values (component_c_generator.policy.config, still never CALLED from
# app/ -- S8-a's guard still applies, these are hardcoded literals, same discipline
# PRODUCTION_SCAFFOLD_CONFIG already used) are 0.80 / 1.30 / 0.30 / 0.40 / 3 / 0.60. The two
# ordering constraints CPolicyConfig's own model_validator enforces
# (decrease_correctness_threshold < increase_correctness_threshold;
# increase_max_strain < decrease_min_strain, packaging/component_c_internal/component_c_generator/
# policy/config.py:47-53) are checked and hold for these real values (0.40 < 0.80;
# 0.30 < 0.60) -- verified by hand, since the app-level PolicyConfig dataclass below carries no
# validator of its own to enforce this mechanically. ``config_version`` is now
# "c4.1-policy-1.0.0", the real, reviewed version string this config now legitimately is.
# ``parameter_source_status`` is still the SAME imported constant (renamed
# ``_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS``) session_lifecycle's own gate is fed at session
# creation (c_session_service.py) -- not a second, independently-typed literal -- so THE SEAM
# assertion below (``assert_policy_config_matches_session_gate``, called in ``submit_action``)
# still has a real, structural relationship to compare, now carrying the new value on both sides.
#
# tests/test_batch2_adaptation_live_caller.py::test_production_policy_config_probe_does_not_mirror_the_real_defaults
# asserted the OLD state (probe != real defaults, status == TEST_FIXTURE_ONLY) as a tripwire
# against a SILENT promotion. Per supervisor ruling, CONNECT Step 4, it is inverted rather than
# deleted -- see that test's own updated docstring for what it now protects.
PRODUCTION_POLICY_CONFIG = PolicyConfig(
    config_version="c4.1-policy-1.0.0",
    parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
    increase_correctness_threshold=0.80,
    increase_max_avg_attempts=1.30,
    increase_max_strain=0.30,
    decrease_correctness_threshold=0.40,
    decrease_error_run_threshold=3,
    decrease_min_strain=0.60,
)

# SEVENTH-FAMILY GATE batch: PRODUCTION_EVIDENCE_WINDOW_CONFIG_PROBE (batch 2's own disclosed
# open finding, quoted in the module docstring's own prior revision) is REMOVED. EvidenceWindowConfig
# is now a BUNDLE-classified, gated family (session_lifecycle.create_session's own seventh gate
# call, bundle_resolution.resolve_evidence_window_config) -- submit_action below resolves it from
# the SAME already-resolved bundle safety_config/selection_config already use, never a probe.

# BATCH 2 -- v3.0 §7.3: Q-learning stays EXPERIMENTAL_ONLY; "rule_based_baseline" is the only
# policy_mode any real call may use (component_c_generator.policy.rule_based.
# QLearningDisabledError is raised by decide_adaptation for any other value -- see
# app/domain/live_engine_c/errors.py's own QLearningDisabledError docstring). No column anywhere
# stores a per-session/per-instance policy_mode (verified: neither CSessionRecord nor
# CTaskInstanceRecord carries one) -- this is a fixed, never-client-influenced constant, the same
# shape as _SMOKE_MODE in c_session_service.py, not a value read off any record.
PRODUCTION_POLICY_MODE: PolicyMode = "frozen_q_evaluation"
#
# LIVE-01 (supersedes the BATCH 2 paragraph above for the PRODUCTION mode): difficulty is now proposed by the
# FROZEN, trained Q-learning policy (app/application/live_engine_c/q_policy.py, tables under
# provenance/c_policy/, hash-verified at session start) -- Q proposes, the pinned safety layer disposes
# (LiveEngineCAdapter.decide_with_proposed_action). The rule policy no longer decides in production but its
# code path (decide_adaptation_with_safety_flags with "rule_based_baseline") is untouched and tested. No
# per-child learning: frozen only (internal_reward stays NULL). Approval record:
# provenance/component-c-q-policy-approval.json.


# The engine's OWN declared domain for a difficulty level, not a range chosen here: both
# ``SelectionResult.initial_difficulty_level`` and the policy's own observable-evidence model's
# ``current_difficulty_level`` both annotate it ``Ge(1), Le(5)``. That evidence type is referred to
# here by description rather than by its own identifier, following this module's existing
# convention: C-17's guard test asserts the name appears NOWHERE in this file, so spelling it even
# inside a comment trips it. Used only to REJECT an out-of-domain
# carried level (see next_task), never to clamp one into range. Asserted against the installed
# wheel's own annotations by test_c_difficulty_progression, so this cannot drift silently.
_ENGINE_DIFFICULTY_MIN = 1
_ENGINE_DIFFICULTY_MAX = 5

# R-8: the ONE fixed session-distinguishing suffix used with FIXTURE_MASTERY_SOURCE_STUDENT_ID
# to satisfy build_task_instance's ^STU-[0-9]{4}-C-[0-9]{3}$ requirement -- never a second
# per-session derivation, since the underlying student id is already a single fixed constant.
_STU_SESSION_SUFFIX = "001"


def _stu_session_id() -> str:
    return f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-{_STU_SESSION_SUFFIX}"


def _generation_config_checksum(config: GenerationConfig) -> str:
    """No existing column precedent pins down what ``c_gameplay_events.config_checksum`` should
    cover (undocumented since Phase 3a) -- BUILDER JUDGMENT — UNRATIFIED: a deterministic digest
    of the generation config's own identity strings, mirroring ``catalogue_checksum``'s role for
    the catalogue."""
    return hashlib.sha256(f"{config.config_version}:{config.parameter_source_status}".encode()).hexdigest()


# BE-prompt-text batch: c_task.py's own docstring states the full reasoning. ``blanks`` is
# meaningful for exactly these three templates -- gated by explicit membership, not a bare
# ``record.difficulty_vector.get("blanks")``, so a future template that happened to reuse the key
# name for an unrelated meaning could not silently misreport through this field.
_BLANKS_TEMPLATE_IDS = frozenset({"C-NP-01", "C-NP-02", "C-NP-03"})


def _blanks(record: CTaskInstanceRecord) -> Optional[int]:
    """Reads a value the pinned generator already computed and persisted onto this instance's
    ``difficulty_vector`` at generation time (never recomputed from configuration -- see
    c_task.py's docstring for why that distinction is what makes this permitted). ``None`` for
    every template outside the three that carry the ``"blanks"`` key."""
    if record.game_task_template_id not in _BLANKS_TEMPLATE_IDS:
        return None
    return record.difficulty_vector["blanks"]


def _task_fields(record: CTaskInstanceRecord) -> CTaskFields:
    """Allow-list construction (X-4) -- see app/domain/c_task.py's own docstring for the full
    private/public rationale, column by column. ``prompt_text`` lookup can raise
    ``PromptWordingUnavailableError`` (a ``LiveEngineCError``); callers must translate it the same
    way every other ``LiveEngineCError`` in this module is translated, at the call site."""
    return CTaskFields(
        c_task_instance_id=record.c_task_instance_id,
        game_family_id=record.game_family_id,
        game_task_template_id=record.game_task_template_id,
        task_index=record.task_index,
        skill_id=record.skill_id,
        difficulty_level=record.difficulty_level,
        representation_mode=record.representation_mode,
        prompt_payload=record.prompt_payload,
        interactive_assets=record.interactive_assets,
        valid_action_space=record.valid_action_space,
        scaffold_state=record.scaffold_state,
        technical_status=record.technical_status,
        blanks=_blanks(record),
        prompt_text=prompt_text_for(record.game_task_template_id, record.prompt_payload),
    )


def _to_domain_task_instance(
    record: CTaskInstanceRecord, *, student_id: str, c_session_id: str
) -> TaskInstance:
    """Reconstructs the domain ``TaskInstance`` the adapter's ``evaluate`` port expects, from the
    persisted PRIVATE row. ``student_id``/``c_session_id`` are not stored on this table (Phase
    3a's minimal-FK style) and are supplied by the caller, who already has them from the
    authenticated request -- never invented, never re-derived."""
    # The package's own GameTaskInstance model requires game_task_instance_id to match
    # ^STU-####-C-###-T###-X###$ -- built from the already-STU-formatted c_session_id and this
    # record's own task_index, mirroring build_task_instance's own construction
    # (f"{c_session_id}-T{task_index:03d}-X001") rather than the raw private UUID.
    game_task_instance_id = f"{c_session_id}-T{record.task_index:03d}-X001"
    return TaskInstance(
        game_family_id=record.game_family_id,
        game_task_template_id=record.game_task_template_id,
        game_task_instance_id=game_task_instance_id,
        template_version=record.template_version,
        catalogue_version=record.catalogue_version,
        generator_version=record.generator_version,
        seed_lineage=SeedLineage(
            global_seed=record.seed_lineage_global_seed,
            path=tuple(tuple(pair) for pair in record.seed_lineage_path),
            seed=record.seed_lineage_seed,
        ),
        student_id=student_id,
        c_session_id=c_session_id,
        task_index=record.task_index,
        skill_id=record.skill_id,
        curriculum_node_id=record.curriculum_node_id,
        grade_scope=record.grade_scope,
        difficulty_level=record.difficulty_level,
        difficulty_vector=dict(record.difficulty_vector),
        functional_role=record.functional_role,
        representation_mode=record.representation_mode,
        prompt_payload=dict(record.prompt_payload),
        interactive_assets=dict(record.interactive_assets),
        correct_answer_payload=dict(record.correct_answer_payload),
        correctness_function_id=record.correctness_function_id,
        valid_action_space=dict(record.valid_action_space),
        completion_condition=record.completion_condition,
        failure_condition=record.failure_condition,
        scaffold_state=record.scaffold_state,  # type: ignore[arg-type]
        recovery_parent_instance_id=record.recovery_parent_instance_id,
        technical_status=record.technical_status,
    )


class TaskService:
    async def next_task(
        self,
        session: AsyncSession,
        *,
        principal_user_id: str,
        request_id: str,
        c_session_id: UUID,
        generation_config: GenerationConfig,
        smoke_mode: bool,
    ) -> CNextTaskResponse:
        # PERF-01: user -> learner link -> owned session, read AND row-locked, in ONE round trip (was: the user/link
        # lookup, the session read, and a separate SELECT ... FOR UPDATE below). The lock is the same session-row lock;
        # it is now taken before the state check, which only matters for a request that is about to be refused anyway.
        session_record = await CSessionRecordRepository(session).get_owned_for_subject(
            c_session_id, principal_user_id, for_update=True
        )
        if session_record is None:
            raise ResourceNotFoundError()
        student_id = session_record.student_id
        if session_record.state != "active":
            raise ConflictError()

        # CONNECT resume-instead-of-mint batch (owner ruling): lock the SESSION row before the
        # gate checks and the resume-or-mint decision -- the instance row this task might resume
        # (or the one a racing concurrent call might mint) does not exist yet at this point, unlike
        # Step 5's lock target. Closes both the concurrent-first-call race (two calls on a fresh
        # session both finding nothing to resume, both minting the SAME task_index -- verified
        # CTaskOpportunityRecord carries no uniqueness constraint on (c_session_id, task_index),
        # and task_index is the SOLE seed-lineage-distinguishing element per this module's own
        # docstring, so a collision would silently draw the identical template twice) and any race
        # between the resume check below and the mint path.
        # (PERF-01: the session row was locked by the read above.)

        try:
            assert_generation_config_permitted(generation_config, smoke_mode=smoke_mode)
        except GenerationConfigNotPermittedError as exc:
            raise ConflictError() from exc

        adapter = LiveEngineCAdapter()
        try:
            # PERF-01: the catalogue is the one the resolution above already loaded from _CATALOGUE_PATH
            # (it was parsed a second time here with the identical call).
            bundle, catalogue, catalogue_checksum = resolve_c_bundle_and_catalogue(
                bundle_path=_BUNDLE_PATH,
                schema_path=_SCHEMA_PATH,
                catalogue_path=_CATALOGUE_PATH,
                require_approved=False,
            )
            selection_config = resolve_selection_config(bundle)
        except LiveEngineCError as exc:
            raise ConflictError() from exc

        # CONNECT resume-instead-of-mint batch (owner ruling): if this session already has an
        # unterminated instance, return it instead of minting a new one -- an app reopened, a page
        # refreshed, or a retried request must not silently abandon the task the child was already
        # on (ESCALATIONS.md §7 has the full account of what that cost before this batch: no
        # terminal event, no summary, no marker distinguishing "abandoned" from "never reached").
        # DELIBERATELY PLACED AFTER the gate checks above, not before them, even though the
        # generation work below (select_task, the RNG, instance construction) is genuinely
        # unnecessary on this path and returning earlier would be the obvious optimization: a
        # resumed task must never be able to outlive the approval that authorized it. If a
        # parameter family's approval were ever withdrawn between when this task was first offered
        # and when it is resumed, assert_generation_config_permitted / the bundle-and-catalogue
        # resolution above must still refuse -- a resume path that skipped them would be fail-OPEN
        # in a system whose entire discipline is fail-closed, and it would look completely normal
        # while doing it. The cost is one bundle resolution per resume; do not "optimize" this away.
        event_repo = CGameplayEventRecordRepository(session)
        pending_instance = await CTaskInstanceRecordRepository(session).find_most_recent_for_session(c_session_id)
        if pending_instance is not None and not await event_repo.has_terminal_for_instance(
            pending_instance.c_task_instance_id
        ):
            try:
                task_fields = _task_fields(pending_instance)
            except LiveEngineCError as exc:
                raise ConflictError() from exc
            return CNextTaskResponse(**task_fields.model_dump(), request_id=request_id)

        learner_state, _local_state_record = await _learner_session_state(session, student_id)
        # task_index is 1-based: the package's own GameTaskInstance model requires >= 1.
        task_index = await CTaskOpportunityRecordRepository(session).count_for_session(c_session_id) + 1

        mastery_by_skill: Optional[Mapping[str, float]] = None
        mastery_source_student_id: Optional[str] = None
        mastery_source_intervention_session_id: Optional[str] = None
        mastery_source_intervention_session_number: Optional[int] = None
        if session_record.session_mode == "combined":
            mastery_by_skill = fixture_b_mastery_payload_for_phase_4()
            (
                mastery_source_student_id,
                mastery_source_intervention_session_id,
                mastery_source_intervention_session_number,
            ) = fixture_b_provenance_for_phase_4()

        # See module docstring, "SEED LINEAGE" -- root construction only, no derivation.
        session_lineage = SeedLineage(
            global_seed=session_record.global_seed, path=(), seed=session_record.global_seed
        )
        task_opportunity_lineage = SeedLineage(
            global_seed=session_record.global_seed,
            path=(("task_index", str(task_index)),),
            seed=session_record.global_seed,
        )

        try:
            result = adapter.select_task(
                session_mode=session_record.session_mode,
                session_phase=session_record.session_phase,
                grade=session_record.grade,
                catalogue=catalogue,
                # The app cannot draw three of the thirty templates, so the engine is never
                # offered them and selects something else instead -- no retry loop, because a
                # template outside the pool is simply never chosen. See client_support.py for
                # which three, why, and why this is a client-capability constraint rather than a
                # scientific one.
                supported_template_ids=selectable_template_ids(adapter.supported_template_ids()),
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                c_session_id=_stu_session_id(),
                task_index=task_index,
                mastery_payload=mastery_by_skill,
                mastery_source_student_id=mastery_source_student_id,
                mastery_source_intervention_session_id=mastery_source_intervention_session_id,
                mastery_source_intervention_session_number=mastery_source_intervention_session_number,
                sessions_since_last_practice=learner_state.sessions_since_last_practice,
                component_c_session_lineage=session_lineage,
                task_opportunity_lineage=task_opportunity_lineage,
                generation_config=generation_config,
                selection_config=selection_config,
            )
        except LiveEngineCError as exc:
            raise ConflictError() from exc

        # DIFFICULTY PROGRESSION -- closing the loop recorded in buildLog2.md, entry 2026-10-10
        # "Component C difficulty level". Until this batch the adaptation policy decided a
        # ``difficulty_after`` after every answered task, persisted it, and nothing ever read it
        # back: ``select_task`` has no current-difficulty parameter (verified by
        # ``inspect.signature`` against the installed wheel, not read from a doc), so every task
        # was built at ``SelectionResult.initial_difficulty_level`` -- in ``c_only`` always
        # ``fallback_difficulty_level``, i.e. 1. The policy's own evidence then reported
        # "currently 1" forever, because that evidence reads the previous INSTANCE's level, so the
        # decision could never start from anything but 1 either. A closed circle.
        #
        # NO FORMULA LIVES HERE, deliberately. This carries the engine's own already-clamped
        # output and performs no arithmetic of its own: the safety controller has already computed
        # ``difficulty_after = clamp(target, floor, ceiling)`` with the session mode's cap applied
        # (``c_only`` caps at 2). Stepping, flooring or capping in app code would be the
        # orchestration layer implementing adaptive science, which this codebase refuses
        # everywhere else and must refuse here.
        #
        # PRECEDENT, not a new mechanism: ``most_recent_for_session``'s own docstring already
        # establishes that the most recently written decision is what feeds the NEXT task --
        # ``increase_block_remaining`` has been read exactly this way since Phase 6b. This adds a
        # second field to that same established read, it does not invent a pathway.
        #
        # ``difficulty_after`` is the decision made after the PREVIOUS task, which is why the
        # first task of a session (no decision yet) keeps ``select_task``'s own level untouched.
        prior_decision = await CPolicyDecisionRecordRepository(session).most_recent_for_session(c_session_id)
        carried_difficulty_level = (
            prior_decision.difficulty_after if prior_decision is not None else result.initial_difficulty_level
        )

        # VALIDITY, NOT POLICY -- and it REJECTS rather than clamps, deliberately. The engine
        # already bounds its own output (the hard-safety controller step ends in
        # ``difficulty_after = max(floor, min(ceiling, target))``), so a value outside the engine's
        # declared domain means the row is untrustworthy, not that it needs correcting here.
        # Clamping it would silently manufacture a level no policy chose; discarding it falls back
        # to the level the engine just selected, which is a value the engine DID choose.
        #
        # This matters because ``difficulty_level`` carries no database CHECK of its own, while
        # the policy evidence's own ``current_difficulty_level`` is annotated ``Le(5)`` -- so an
        # out-of-domain level persisted here would not fail at the write, it would fail later, on
        # the child's NEXT submission, as a validation error in evidence construction.
        if not _ENGINE_DIFFICULTY_MIN <= carried_difficulty_level <= _ENGINE_DIFFICULTY_MAX:
            carried_difficulty_level = result.initial_difficulty_level

        instance = result.task_instance
        if carried_difficulty_level != instance.difficulty_level:
            # Same template, same skill, same seed lineage ``select_task`` chose -- ONLY the
            # difficulty differs. Rebuilt through the adapter's own governed entry point (the one
            # the recovery path already uses), never by mutating the frozen instance the engine
            # returned.
            try:
                instance = adapter.build_task_instance(
                    catalogue=catalogue,
                    game_task_template_id=result.selected_template_id,
                    seed_lineage=instance.seed_lineage,
                    grade=session_record.grade,
                    difficulty_level=carried_difficulty_level,
                    student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    c_session_id=_stu_session_id(),
                    task_index=task_index,
                    config=generation_config,
                )
            except LiveEngineCError:
                # DEFENSIVE, and expected never to fire: all 30 templates are frozen at all five
                # difficulty levels (the 150-exemplar sweep in buildLog2.md's 2026-09-28 entry).
                # If a template ever cannot be built at the carried level, the child keeps the
                # task the engine already produced rather than being shown an error -- and the
                # rows below then record the level ACTUALLY used, never the one intended, so the
                # audit trail stays honest about what the child met.
                instance = result.task_instance

        opportunity_id = uuid4()
        opportunity = CTaskOpportunityRecord(
            c_task_opportunity_id=opportunity_id,
            c_session_id=c_session_id,
            task_index=task_index,
            selected_skill_id=result.selected_skill_id,
            selected_template_id=result.selected_template_id,
            # The level the child ACTUALLY met, read off the instance rather than from
            # ``select_task``'s own suggestion -- so a defensive fallback above (template not
            # buildable at the carried level) records what was really served, not what was
            # intended. This column is also what reaches ``build_policy_evidence`` as
            # ``current_difficulty_level`` on the next submission, which is how the policy comes
            # to observe a state above 1 at all.
            initial_difficulty_level=instance.difficulty_level,
            mastery_context_mode=result.mastery_context_mode,
            mastery_selected_skill=result.mastery_selected_skill,
            session_phase=result.session_phase,
            terminal_reason=None,
            task_offered_at_utc=datetime.now(UTC),
            **_provenance("c_task_opportunity", opportunity_id, request_id, "c_task.offered"),
        )
        await CTaskOpportunityRecordRepository(session).add(opportunity)

        instance_id = uuid4()
        instance_record = CTaskInstanceRecord(
            c_task_instance_id=instance_id,
            c_task_opportunity_id=opportunity_id,
            game_family_id=instance.game_family_id,
            game_task_template_id=instance.game_task_template_id,
            template_version=instance.template_version,
            catalogue_version=instance.catalogue_version,
            generator_version=instance.generator_version,
            task_index=instance.task_index,
            skill_id=instance.skill_id,
            curriculum_node_id=instance.curriculum_node_id,
            grade_scope=instance.grade_scope,
            difficulty_level=instance.difficulty_level,
            difficulty_vector=dict(instance.difficulty_vector),
            functional_role=instance.functional_role,
            representation_mode=instance.representation_mode,
            prompt_payload=dict(instance.prompt_payload),
            interactive_assets=dict(instance.interactive_assets),
            correct_answer_payload=dict(instance.correct_answer_payload),
            correctness_function_id=instance.correctness_function_id,
            valid_action_space=dict(instance.valid_action_space),
            completion_condition=instance.completion_condition,
            failure_condition=instance.failure_condition,
            scaffold_state=instance.scaffold_state,
            recovery_parent_instance_id=None,
            technical_status=instance.technical_status,
            seed_lineage_global_seed=instance.seed_lineage.global_seed,
            seed_lineage_path=[list(pair) for pair in instance.seed_lineage.path],
            seed_lineage_seed=instance.seed_lineage.seed,
            **_provenance("c_task_instance", instance_id, request_id, "c_task.instance_generated"),
        )
        await CTaskInstanceRecordRepository(session).add(instance_record)

        event_id = uuid4()
        offered_event = CGameplayEventRecord(
            c_gameplay_event_id=event_id,
            c_session_id=c_session_id,
            game_task_instance_id=instance_id,
            task_index=task_index,
            event_type="game_task_offered",
            event_index=1,
            attempt_number=None,
            event_timestamp_relative_ms=0,
            action_payload=None,
            evaluation_payload=None,
            scaffold_code=None,
            technical_flag=False,
            terminal_reason=None,
            seed_lineage_global_seed=instance.seed_lineage.global_seed,
            seed_lineage_path=[list(pair) for pair in instance.seed_lineage.path],
            seed_lineage_seed=instance.seed_lineage.seed,
            generator_version=instance.generator_version,
            config_checksum=_generation_config_checksum(generation_config),
            **_provenance("c_gameplay_event", event_id, request_id, "c_task.offered"),
        )
        await CGameplayEventRecordRepository(session).add(offered_event)

        try:
            task_fields = _task_fields(instance_record)
        except LiveEngineCError as exc:
            raise ConflictError() from exc
        return CNextTaskResponse(**task_fields.model_dump(), request_id=request_id)

    async def submit_action(
        self,
        session: AsyncSession,
        *,
        principal_user_id: str,
        request_id: str,
        c_session_id: UUID,
        c_task_instance_id: UUID,
        action_payload: Mapping[str, Any],
        generation_config: GenerationConfig,
        scaffold_config: ScaffoldConfig,
        submission_spy: Optional[list] = None,
    ) -> CSubmitActionResult:
        # PERF-01: user -> learner link -> owned session in ONE round trip (was two). Unknown user, user without a
        # learner link and a session the learner does not own were already the same ResourceNotFoundError.
        session_record = await CSessionRecordRepository(session).get_owned_for_subject(c_session_id, principal_user_id)
        if session_record is None:
            raise ResourceNotFoundError()
        student_id = session_record.student_id

        instance_repo = CTaskInstanceRecordRepository(session)
        # PERF-01: the instance is read AND row-locked in one round trip (was a read here and a separate
        # lock_for_update further down). It is the same row lock, now taken before the checks below instead of after
        # them: sequential behaviour is identical, a concurrent duplicate simply waits one step earlier.
        instance_record = await instance_repo.get_owned(c_task_instance_id, c_session_id, for_update=True)
        if instance_record is None:
            raise ResourceNotFoundError()

        event_repo = CGameplayEventRecordRepository(session)
        # PERF-01: ONE read of this instance's event stream (was four separate counting queries: terminal check, max
        # index / timestamp, answer_submitted count, started check). Taken under the instance lock above, so it is as
        # consistent as the separate reads were; everything those queries returned is derived from it below.
        stream = list(await event_repo.list_ordered_for_instance(c_task_instance_id))
        # T1-4 (owner ruling): checked BEFORE evaluate() is ever called -- "A network retry or a
        # double-tap on a correct answer is an ordinary event, not an edge case, and Q4 left
        # action submission with no idempotency key -- so this check is the only thing standing
        # between a retry and a duplicated terminal write." A structured 409, never a second
        # scoring.
        if any(e.event_type in event_repo._TERMINAL_EVENT_TYPES for e in stream):
            raise ConflictError(
                details=[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]
            )

        try:
            validate_action_payload(instance_record.valid_action_space, action_payload)
        except ActionPayloadValidationError as exc:
            details = [{"location": list(loc), "type": code} for loc, code in exc.field_errors] or None
            raise ActionPayloadRejectedError(details=details) from exc

        adapter = LiveEngineCAdapter()
        domain_instance = _to_domain_task_instance(
            instance_record,
            student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
            c_session_id=_stu_session_id(),
        )
        try:
            evaluation = adapter.evaluate(domain_instance, action_payload)
        except UnknownTemplateError as exc:
            raise ConflictError() from exc

        if submission_spy is not None:
            submission_spy.append(c_task_instance_id)

        # Phase 6a, LATENT DEFECT SINCE PHASE 5 (found by this batch's own derivation wiring,
        # never visible before -- same shape as R-7's catalogue-status finding): Phase 5 wrote a
        # SINGLE event typed "answer_evaluated" carrying action_payload directly on it. The
        # package's own GameplayEvent model (component_c_generator.models.gameplay) permits
        # action_payload ONLY on ('action_performed', 'answer_submitted') and forbids it on
        # 'answer_evaluated' -- a real, structural violation, invisible through Phase 5 because
        # nothing ever translated a persisted event back into the package's own model until this
        # batch's derive_task_opportunity_summary call did. It also meant no "answer_submitted"
        # event ever existed, so derive_task_opportunity_summary's own total_attempts/retry_count
        # (both counted from answer_submitted events, behaviour/summary.py:43-46) could never
        # have been anything but zero. Fixed here to two events, mirroring the package's real
        # event vocabulary: submitted (action_payload only) then evaluated (evaluation_payload
        # only), same attempt_number, consecutive event_index.
        #
        # CONNECT Step 5: lock the instance row FIRST, in this transaction, before either count
        # below -- the SAME row the c_gameplay_events triggers themselves lock at insert time
        # (CTaskInstanceRecordRepository.lock_for_update's own docstring has the full reasoning).
        # This is what closes the race two concurrent submissions on one instance would otherwise
        # have: without it, both could read the same existing_submitted_count and write the same
        # attempt_number, undercounting retries in exactly the way Family 3's condition ("each
        # retry must receive an incrementing attempt_number") exists to prevent.
        # (PERF-01: the lock was taken with the instance read above, and the stream was read once, above.)
        max_index = max((e.event_index for e in stream), default=0) or 0
        max_timestamp = max((e.event_timestamp_relative_ms for e in stream), default=0) or 0
        # CONNECT Step 5 (Family 3; ESCALATIONS.md §2 closed by this batch): attempt_number was
        # hardcoded to 1 on both events below. Derived here instead, from the count of this
        # instance's own existing answer_submitted events -- the SAME derivation
        # derive_task_opportunity_summary already performs internally (behaviour/summary.py:43-46)
        # -- so the persisted column is honest rather than only derivable downstream. Both events
        # written by this call share the same attempt_number (they are the same attempt) and their
        # event_index values stay consecutive, both already true of the existing max_index+1/+2
        # derivation above -- this adds one more shared value alongside it, not a second scheme.
        attempt_number = sum(1 for e in stream if e.event_type == "answer_submitted") + 1

        # Phase 6a, second LATENT DEFECT SINCE PHASE 5 found by the same exercise: no code path
        # anywhere ever wrote "game_task_started" (next_task writes only "game_task_offered").
        # derive_task_opportunity_summary's own invariant requires task_started before
        # task_completed -- see CGameplayEventRecordRepository.has_started_for_instance's own
        # docstring. Guarded so a wrong-answer retry (still permitted; only a TERMINAL instance
        # is blocked by T1-4) never writes it twice.
        new_events: list = []     # PERF-01: inserted together in ONE statement (was one flush per event)
        if not any(e.event_type == "game_task_started" for e in stream):
            started_event_id = uuid4()
            started_event = CGameplayEventRecord(
                c_gameplay_event_id=started_event_id,
                c_session_id=c_session_id,
                game_task_instance_id=c_task_instance_id,
                task_index=instance_record.task_index,
                event_type="game_task_started",
                event_index=max_index + 1,
                attempt_number=None,
                event_timestamp_relative_ms=max_timestamp + 1,
                action_payload=None,
                evaluation_payload=None,
                scaffold_code=None,
                technical_flag=False,
                terminal_reason=None,
                seed_lineage_global_seed=instance_record.seed_lineage_global_seed,
                seed_lineage_path=instance_record.seed_lineage_path,
                seed_lineage_seed=instance_record.seed_lineage_seed,
                generator_version=instance_record.generator_version,
                config_checksum=_generation_config_checksum(generation_config),
                **_provenance("c_gameplay_event", started_event_id, request_id, "c_task.started"),
            )
            new_events.append(started_event)
            max_index, max_timestamp = max_index + 1, max_timestamp + 1

        submitted_event_id = uuid4()
        submitted_event = CGameplayEventRecord(
            c_gameplay_event_id=submitted_event_id,
            c_session_id=c_session_id,
            game_task_instance_id=c_task_instance_id,
            task_index=instance_record.task_index,
            event_type="answer_submitted",
            event_index=max_index + 1,
            attempt_number=attempt_number,
            event_timestamp_relative_ms=max_timestamp + 1,
            action_payload=dict(action_payload),
            evaluation_payload=None,
            scaffold_code=None,
            technical_flag=False,
            terminal_reason=None,
            seed_lineage_global_seed=instance_record.seed_lineage_global_seed,
            seed_lineage_path=instance_record.seed_lineage_path,
            seed_lineage_seed=instance_record.seed_lineage_seed,
            generator_version=instance_record.generator_version,
            config_checksum=_generation_config_checksum(generation_config),
            **_provenance("c_gameplay_event", submitted_event_id, request_id, "c_task.action_submitted"),
        )
        new_events.append(submitted_event)

        evaluated_event_id = uuid4()
        evaluated_event = CGameplayEventRecord(
            c_gameplay_event_id=evaluated_event_id,
            c_session_id=c_session_id,
            game_task_instance_id=c_task_instance_id,
            task_index=instance_record.task_index,
            event_type="answer_evaluated",
            event_index=max_index + 2,
            attempt_number=attempt_number,
            event_timestamp_relative_ms=max_timestamp + 2,
            action_payload=None,
            # NEVER correctness_function_id, NEVER the correct_answer_payload -- only the
            # boolean verdict (P1-d: evaluator internals must never leak).
            evaluation_payload={"is_correct": evaluation.is_correct},
            scaffold_code=None,
            technical_flag=False,
            terminal_reason=None,
            seed_lineage_global_seed=instance_record.seed_lineage_global_seed,
            seed_lineage_path=instance_record.seed_lineage_path,
            seed_lineage_seed=instance_record.seed_lineage_seed,
            generator_version=instance_record.generator_version,
            config_checksum=_generation_config_checksum(generation_config),
            **_provenance("c_gameplay_event", evaluated_event_id, request_id, "c_task.action_evaluated"),
        )
        new_events.append(evaluated_event)

        # T1 (owner ruling): completed_correct is the ONLY terminal reason built this batch. See
        # terminal_event.py's module docstring for the full nine-reason mapping and T1-5's
        # statement of what remains unclosed.
        scaffold_level: ScaffoldLevel = "C0"
        if evaluation.is_correct:
            # PERF-01: the terminal event is queued (not flushed) and goes in the SAME INSERT as the answer events; the
            # stream state it needs (not terminal -- checked above under the lock; max index / timestamp after the
            # queued answer events) is already known, so it does not re-query. The unique-terminal-index backstop
            # (T1-3) is translated below around that one flush, as terminal_event.py translated it around its own.
            terminal_event = await write_completed_correct_terminal_event(
                session,
                c_session_id=c_session_id,
                c_task_instance_id=c_task_instance_id,
                task_index=instance_record.task_index,
                seed_lineage_global_seed=instance_record.seed_lineage_global_seed,
                seed_lineage_path=instance_record.seed_lineage_path,
                seed_lineage_seed=instance_record.seed_lineage_seed,
                generator_version=instance_record.generator_version,
                config_checksum=_generation_config_checksum(generation_config),
                request_id=request_id,
                known_max_index=max_index + 2,
                known_max_timestamp=max_timestamp + 2,
                known_not_terminal=True,
                defer_flush=True,
            )
            new_events.append(terminal_event)
        session.add_all(new_events)
        try:
            await session.flush()
        except IntegrityError as exc:
            if evaluation.is_correct and "uq_c_gameplay_events_at_most_one_terminal_per_instance" in str(exc.orig):
                raise ConflictError(
                    details=[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]
                ) from exc
            raise
        full_stream = sorted([*stream, *new_events], key=lambda e: e.event_index)
        if evaluation.is_correct:
            await derive_and_persist_summary(
                session,
                adapter=adapter,
                c_session_id=c_session_id,
                c_task_instance_id=c_task_instance_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                stu_session_id=_stu_session_id(),
                game_task_instance_id=domain_instance.game_task_instance_id,
                request_id=request_id,
                records=full_stream,
            )

            # BATCH 2: decide_and_persist_adaptation's first live caller under app/ (v3.0 §11
            # Phase 6 scope, "build_policy_evidence -> decide_adaptation per completed task;
            # persist AdaptationDecision to c_policy_decisions" -- unwired since Phase 6b, direct
            # test-side calls only until now).
            #
            # ORDERING IS LOAD-BEARING, VERIFIED BY DIRECT READ (not asserted): the pinned
            # build_policy_evidence (packaging/component_c_internal/component_c_generator/
            # pipeline/evidence.py:92-93) raises ValueError("build_policy_evidence requires at
            # least one summary (the just-finished task)") on an empty history.
            # build_evidence_for_session (adaptation_service.py:157) reads that history via
            # telemetry_validation.get_derivable_history_for_session -- every persisted
            # CTaskOpportunitySummaryRecord for this session, in order -- so the just-finished
            # task's own summary MUST already be a persisted row before build_evidence_for_session
            # is called below. derive_and_persist_summary above is what persists it. This is why
            # the call below is placed AFTER derive_and_persist_summary, never before or
            # interleaved with it -- reordering these two calls would turn the session's very
            # first correct answer into an unhandled ValueError.
            try:
                bundle, _adaptation_catalogue_manifest, _adaptation_catalogue_checksum = (
                    resolve_c_bundle_and_catalogue(
                        bundle_path=_BUNDLE_PATH,
                        schema_path=_SCHEMA_PATH,
                        catalogue_path=_CATALOGUE_PATH,
                        require_approved=False,
                    )
                )
                # safety_config/selection_config: resolved via the SAME real path
                # c_session_service.py already uses (resolve_safety_config/resolve_selection_config
                # over the resolved bundle) -- reused here, never a second resolution mechanism,
                # never a probe (both families are BUNDLE-DATA families, gated by per-field status
                # at session creation, X4; that gate already passed or this session would not
                # exist).
                adaptation_safety_config = resolve_safety_config(bundle)
                adaptation_selection_config = resolve_selection_config(bundle)
                # SEVENTH-FAMILY GATE batch: EvidenceWindowConfig resolved the SAME real path --
                # never PRODUCTION_EVIDENCE_WINDOW_CONFIG_PROBE (removed), never a second
                # resolution mechanism. This family is BUNDLE-DATA too (gated by per-field status
                # at session creation, session_lifecycle.create_session's own seventh
                # assert_family_usable call); that gate already passed or this session would not
                # exist.
                adaptation_evidence_window_config = resolve_evidence_window_config(bundle)

                # THE SEAM: see PRODUCTION_POLICY_CONFIG's own comment (renamed CONNECT Step 4)
                # and bundle_resolution.assert_policy_config_matches_session_gate's docstring for
                # the full reasoning. Ties the PolicyConfig object actually reaching
                # decide_and_persist_adaptation below to the SAME parameter_source_status this
                # session was gated on at creation (session_lifecycle.create_session's own
                # assert_code_gated_family_usable(family_name="policy_config", ...) call) --
                # structurally, not by coincidence of two literals matching today.
                assert_policy_config_matches_session_gate(
                    PRODUCTION_POLICY_CONFIG,
                    session_gated_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                )
            except LiveEngineCError as exc:
                raise ConflictError() from exc

            # NO PER-CALL GATE HERE (Z1's own inversion reasoning, session_lifecycle.py's Phase 7
            # docstring, applied identically to adaptation as it already is to scaffold emission):
            # the pinned decide_adaptation composition runs its own hard-safety controller step
            # unconditionally, INSIDE itself (component_c_generator/adaptation.py:46, verified by
            # test_s8c_decide_adaptation_always_applies_safety_structurally -- see that test's own
            # name for the exact package-level call this refers to, deliberately not spelled out
            # by its own identifier here so this in-line comment does not itself trip
            # test_c17_3_initial_difficulty_path_does_not_consume_prior_session_end_state's
            # whole-module absence check in test_c5_task_serve_and_evaluate.py). Refusing THIS call
            # per-task would mean "skip the safety decision for this task," which fails OPEN, not
            # closed. Policy's own usability is established ONCE, at session creation
            # (assert_code_gated_family_usable(family_name="policy_config", ...), already asserted
            # above against the SAME status this session was gated on) -- by the time submit_action
            # runs, a session already exists, meaning that gate already passed.
            #
            # prior_session_end_state: read through the SAME real mechanism next_task's own
            # session-phase decision already uses (_learner_session_state), never hardcoded --
            # mirroring Z6-a's own "derive from real data, not a literal" precedent for
            # is_recovery_context. Its value is None for every session today (C-17 Item B: the
            # producer, session aggregation, refuses unconditionally -- see this batch's own R0
            # trace in buildLog1.md) -- that is a fact about the DATA, not a shortcut taken HERE.
            learner_state, _adaptation_local_state_record = await _learner_session_state(session, student_id)
            adaptation_seed_lineage = SeedLineage(
                global_seed=instance_record.seed_lineage_global_seed,
                path=tuple(tuple(pair) for pair in instance_record.seed_lineage_path),
                seed=instance_record.seed_lineage_seed,
            )
            # PERF-01: the session's derivable history is read ONCE and shared by the evidence builder and the Q
            # observation below (it used to be read twice, three queries each time).
            session_history = await get_derivable_history_for_session(session, c_session_id=c_session_id)
            evidence = await build_evidence_for_session(
                session,
                adapter=adapter,
                c_session_id=c_session_id,
                c_task_instance_id=c_task_instance_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=_stu_session_id(),
                session_mode=session_record.session_mode,
                session_phase=session_record.session_phase,
                current_difficulty_level=instance_record.difficulty_level,
                prior_session_end_state=learner_state.prior_session_end_state,
                evidence_window_config=adaptation_evidence_window_config,
                history_records=session_history,
            )
            # LIVE-01: the frozen Q policy PROPOSES; the pinned safety layer DISPOSES (inside
            # decide_with_proposed_action). The observation is built from persisted data only, with the same
            # definitions the policy was trained on (rl_core.env.DifficultyEnv.obs): first-try = mean
            # first_attempt_correct over the last 5 summaries of THIS session (0.5 if none), strain = the
            # evidence's rolling strain, mastery = the selected skill's mastery for combined sessions (the
            # fixture, mastery_fixture.py) and None for c_only, tasks_done = the number of summaries.
            try:
                q_policy = load_q_policy(session_record.session_mode)
                assert_q_policy_matches_session_gate(
                    q_policy.parameter_source_status,
                    session_gated_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                )
            except LiveEngineCError as exc:
                raise ConflictError() from exc
            q_history = session_history
            q_recent = [r.first_attempt_correct for r in q_history[-5:] if r.first_attempt_correct is not None]
            q_observation = {
                "difficulty": instance_record.difficulty_level,
                "first_try": (sum(1.0 for x in q_recent if x) / len(q_recent)) if q_recent else DEFAULT_FIRST_TRY,
                "strain": evidence.rolling_strain_score,
                "mastery": (
                    FIXTURE_MASTERY_BY_SKILL[instance_record.skill_id]
                    if session_record.session_mode == "combined"
                    else None
                ),
                "tasks_done": len(q_history),
            }
            q_allowed = adapter.preview_allowed_actions(
                evidence=evidence,
                current_difficulty_level=instance_record.difficulty_level,
                safety_config=adaptation_safety_config,
                selection_config=adaptation_selection_config,
            )
            q_action, q_rl_state = q_policy.propose(
                q_state_of(
                    q_observation["difficulty"], q_observation["first_try"], q_observation["strain"], q_observation["mastery"]
                ),
                q_allowed,
                q_observation["tasks_done"],
            )
            await decide_and_persist_adaptation(
                session,
                adapter=adapter,
                c_session_id=c_session_id,
                c_task_opportunity_id=instance_record.c_task_opportunity_id,
                policy_mode=PRODUCTION_POLICY_MODE,
                evidence=evidence,
                current_difficulty_level=instance_record.difficulty_level,
                seed_lineage=adaptation_seed_lineage,
                policy_config=PRODUCTION_POLICY_CONFIG,
                safety_config=adaptation_safety_config,
                selection_config=adaptation_selection_config,
                request_id=request_id,
                proposed_action=q_action,
                policy_version=f"{q_policy.policy_version}+{adapter.safety_controller_version()}",
                rl_state=q_rl_state,
            )
        else:
            # Phase 7, Z5: the ORDINARY escalation path -- decided from the real, just-persisted
            # event stream (never a caller-asserted count).
            #
            # REGISTER RECONCILIATION, BATCH 3 (REWRITES the prior register note above rather than
            # deleting it -- breaks (1) and (2) are now CLOSED, not merely described; see this
            # batch's own R0 trace in buildLog1.md for the full verdict):
            #   (1) CLOSED by batch 1. safety.controller's hard-safety step DOES compute
            #       activate_recovery_flag on its SafetyDecision (controller.py) -- component_c_
            #       generator's own pinned adaptation.decide_adaptation drops it when composing
            #       AdaptationDecision (frozen=True, extra="forbid" -- closed from both directions,
            #       never just at the constructor). LiveEngineCAdapter.decide_adaptation_with_
            #       safety_flags (adapter.py) reconstructs it by calling the pinned proposal step
            #       and the pinned hard-safety step (named deliberately not spelled out by its own
            #       identifier here -- see this module's own C-17 test, which scans this module's
            #       whole source text for that exact identifier's absence, elsewhere unchanged by
            #       this batch) a second time, on an identically-translated evidence object --
            #       proven by test_adaptation_safety_flags_reconstruction.py's own parity test.
            #       THIS IS A WORKAROUND, NOT THE REAL FIX: it works only because
            #       decide_adaptation happens to compose those two calls in that exact order today
            #       -- an unpublished implementation detail of a pinned function, never a published
            #       contract. The real fix -- the owner-authorized AdaptationDecision interface
            #       change adding activate_recovery_flag/request_safe_termination as real fields --
            #       is still PENDING upstream (a wheel re-pin this codebase cannot itself perform).
            #       Batch 1's reconstruction is what supplies the flag until that lands.
            #   (2) CLOSED by batch 2. adaptation_service.decide_and_persist_adaptation now has a
            #       real caller under app/ -- this module's own is_correct branch, above -- so a
            #       session that exists (still only smoke_mode=True/direct-call, X2-3 unchanged)
            #       produces a real, persisted CPolicyDecisionRecord on its correct-answer path.
            #   (3) CLOSED by batch 3 (this batch). The column exists
            #       (c_policy_decisions.safety_forces_recovery, migration 20260816_0006, mirrors
            #       c_scaffold_events' own sibling column exactly); batch 3 switched (1)'s adapter
            #       call so decide_and_persist_adaptation persists the real, reconstructed
            #       activate_recovery_flag into it (never a literal); and the read below replaces
            #       the literal `False` this note used to sit next to with a real read-back of the
            #       most recent prior c_policy_decisions row for THIS session.
            # NO-PRIOR-ROW CASE, DECIDED EXPLICITLY, NOT COLLAPSED: on the first incorrect answer
            # of a session where no task has yet completed correctly, there is no c_policy_decisions
            # row at all -- a state distinct from "a prior decision computed False," which this
            # code does not conflate. ScaffoldDecisionContext.safety_forces_recovery is a bare
            # bool (no third state to represent "unknown"), and no safety computation has run yet
            # for this session to have forced anything -- so the no-prior-row case reads as False,
            # the same value as an explicit prior False, but for a different, plainly-stated
            # reason: absence of a safety intervention, not evidence of one that didn't fire.
            # F-2 is CLOSED AT THE MECHANISM LEVEL by this batch (a real signal now travels
            # producer -> persistence -> read-back -> scaffold decision end to end, proven by this
            # batch's own negative control) but NOT AT THE PRODUCTION LEVEL: X2-3 is unchanged, so
            # no live session can ever generate that signal today.
            prior_decision = await CPolicyDecisionRecordRepository(session).most_recent_for_session(c_session_id)
            safety_forces_recovery = (
                prior_decision.safety_forces_recovery if prior_decision is not None else False
            )
            scaffold_level = await decide_and_persist_scaffold_level(
                session,
                adapter=adapter,
                c_session_id=c_session_id,
                c_task_opportunity_id=instance_record.c_task_opportunity_id,
                c_task_instance_id=c_task_instance_id,
                scaffold_config=scaffold_config,
                safety_forces_recovery=safety_forces_recovery,
                request_id=request_id,
                events=full_stream,
            )

        return CSubmitActionResult(
            c_task_instance_id=c_task_instance_id,
            response_matched=evaluation.is_correct,
            scaffold_level=scaffold_level,
            request_id=request_id,
        )
