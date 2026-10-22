"""Component C Phase 4b: the application-service layer behind the three (now four, with
completion, B4-a) HTTP session-lifecycle endpoints. Wires ``app.application.live_engine_c.
session_lifecycle``'s functions to a real caller for the first time.

BUNDLE RESOLUTION: mirrors ``app.application.opportunity_selection``'s own precedent EXACTLY
(``opportunity_selection.py:100-107``, its own comment: "ENGINEERING-ONLY TEST-provenance DRAFT
bridge, not a governed bundle-artifact resolution mechanism") -- BUILDER JUDGMENT — UNRATIFIED:
no work order text authorizes this specific mechanism, but it is the established, already-shipped
pattern for exactly this situation (no DB-backed "current approved C bundle" resolver exists yet;
Phase 2 built only file-path-based loading). Using anything else here would be inventing a new
resolution mechanism unilaterally, which is a bigger, unauthorized decision than reusing B's own
precedent verbatim.

MASTERY SOURCE + IDENTITY (R-5, Phase 4b continuation, supervisor ruling, correcting the earlier
reading of R1): the FIXTURE producer (``app.application.live_engine_c.mastery_fixture``) supplies
ALL FOUR things for every combined-mode session -- the seven mastery VALUES and the three B
identity fields (``mastery_source_student_id`` etc.) -- never accepted from the client request
body. Accepting the identity fields from an HTTP client (the earlier Phase 4b shape) let an
untrusted caller assert B provenance it never produced -- strictly worse than what R1 was written
to prevent (C manufacturing B's own provenance). R1's "caller-supplied, never derived" meant the
SERVER-SIDE producer standing in for B, not the HTTP client. No shared B/C session-mapping
infrastructure exists in this codebase yet (the cold-start assessment's own
``SharedInterventionSessionMapping`` is unbuilt) -- BUILDER JUDGMENT — UNRATIFIED: using the
fixture producer for identity too, rather than inventing a mapping mechanism, mirrors the same
reasoning already applied to the mastery values themselves.
"""

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.bundle_resolution import (
    resolve_c_bundle_and_catalogue,
    resolve_evidence_window_config,
    resolve_safety_config,
    resolve_selection_config,
)
from app.application.live_engine_c.q_policy import load_q_policy
from app.application.live_engine_c.mastery_fixture import (
    fixture_b_mastery_payload_for_phase_4,
    fixture_b_provenance_for_phase_4,
)
from app.application.live_engine_c.session_lifecycle import (
    abandon_session,
    complete_session,
    create_session,
    get_active_session,
)
from app.core.errors import ConflictError, MasteryPayloadRejectedError, ResourceNotFoundError
from app.domain.c_session import CActiveSessionResponse, CSessionCommandResponse, CSessionFields
from app.domain.live_engine_c.errors import LiveEngineCError, MasteryPayloadContractValidationError
from app.domain.live_engine_c.types import AttendanceStatus, Grade, SessionMode
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CSessionRecord
from app.infrastructure.repositories import (
    AppUserRepository,
    CRuntimeBundleRecordRepository,
)

# CONNECT Step 3: repointed to the owner-approved bundle (APPROVAL-2026-08-26-seven-families.md;
# see backend/buildLog2.md). Was the ENGINEERING-ONLY TEST-provenance DRAFT bridge, mirroring
# opportunity_selection.py's own _ENGINEERING_TEST_BUNDLES -- that fixture stays in place;
# existing tests depend on it.
_BUNDLE_PATH = "provenance/c-runtime-bundle-approved-1.0.json"

# CONNECT Step 4: renamed from _NOT_LIVE_PARAMETER_SOURCE_STATUS, which became actively false the
# moment the gate opened -- a false name is worse than a churned one. Generation, Policy, Scaffold,
# and Aggregation are still CODE-GATED, not bundle-data (Z1 -- the bundle schema carries no blocks
# for any of the four; see Component_C_Frontend/ESCALATIONS.md's entry on the four-way split for
# why that stays true even though Policy now has real reviewed numbers). This is the one literal
# string the real HTTP route can ever supply to the session-start code gate; never a call to any
# default_*_config() factory (S8-a's guard). Value changed under
# APPROVAL-2026-08-26-seven-families.md (Families 4/5/6/7, "APPROVED WITH CONDITION") -- production
# keeps smoke_mode=False and now passes on real, approved statuses, never by turning smoke mode on.
_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS = "APPROVED_FOR_PROVISIONAL_IMPLEMENTATION"

# The real HTTP route never lets a client set smoke_mode -- same shape as task_service.py's
# PRODUCTION_GENERATION_CONFIG_PROBE/hardcoded smoke_mode=False. A MODULE-LEVEL constant (not an
# inline literal) so it can be monkeypatched the same way _BUNDLE_PATH already is, file-locally,
# for Phase 4b's own pre-existing HTTP-level tests (test_c4b_routes_and_bundle_config.py) --
# mirroring the ratified pattern from Phase 6b's own final step (all_usable_for_tests_bundle_c.json
# + its autouse fixture): this batch's uniform five-family gate (Z2) closes off the LAST path
# those pre-existing tests used to reach a real 201, since smoke_mode=False now also blocks
# Generation/Policy/Scaffold even when the bundle itself is all-usable.
_SMOKE_MODE = False
_SCHEMA_PATH = "provenance/c-runtime-bundle.schema.json"
# CONNECT Step 2: repointed to the governed catalogue, vendored verbatim from the sibling Yass/
# tree (APPROVAL-2026-08-26-seven-families.md; see backend/buildLog2.md). Its own status line
# reads PROPOSED FOR APPROVAL, not APPROVED -- vendoring and repointing here does not change
# that. The TEST_FIXTURE_ONLY catalogue below stays in place; existing tests depend on it.
_CATALOGUE_PATH = "provenance/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md"


def _fields(record: CSessionRecord) -> CSessionFields:
    # R-1: mastery_context_mode is deliberately absent -- derivable client-side from session_mode
    # (see app/domain/c_session.py's docstring).
    return CSessionFields(
        c_session_id=record.c_session_id,
        state=record.state,
        session_mode=record.session_mode,
        session_phase=record.session_phase,
        grade=record.grade,
        started_at_utc=record.started_at_utc,
        row_version=record.row_version,
    )


async def _require_learner_id(session: AsyncSession, principal_user_id: str) -> UUID:
    """The learner behind a principal, in one round trip.

    DELIBERATELY NO `profile_type` CHECK, unlike Component B's equivalents. This function never had
    one: it rejects an unknown subject and a subject with no learner link, and nothing else. The
    join below changes the number of round trips and nothing about that -- adding the
    LEARNER/ForbiddenError branch here would be an authorization change wearing a performance
    change's clothes, which is not what this edit is.
    """
    found = await AppUserRepository(session).find_with_learner_link_by_subject(principal_user_id)
    if found is None:
        raise ResourceNotFoundError()
    _user, link = found
    if link is None:
        raise ResourceNotFoundError()
    return link.learner_id


class CSessionService:
    async def create(
        self,
        session: AsyncSession,
        *,
        principal_user_id: str,
        request_id: str,
        grade: Grade,
        session_mode: SessionMode,
    ) -> CSessionCommandResponse:
        student_id = await _require_learner_id(session, principal_user_id)
        adapter = LiveEngineCAdapter()
        try:
            bundle, _catalogue, catalogue_checksum = resolve_c_bundle_and_catalogue(
                bundle_path=_BUNDLE_PATH,
                schema_path=_SCHEMA_PATH,
                catalogue_path=_CATALOGUE_PATH,
                require_approved=False,
            )
            selection_config = resolve_selection_config(bundle)
            # Phase 6b, S2-a: resolved (and its absence raised) here, the SAME point
            # selection_config already was -- both families fail closed before create_session is
            # ever called, and create_session's own gate (X4) checks their per-field statuses
            # again, structurally, not merely because this caller happened to run first.
            safety_config = resolve_safety_config(bundle)
            # SEVENTH-FAMILY GATE batch: same fail-closed-before-create_session shape, one family
            # later. Resolved (and its absence raised) here even though, like safety_config, the
            # returned object is not itself threaded into create_session below -- only its
            # per-field field_statuses map is (X4's own gate re-checks them structurally).
            evidence_window_config = resolve_evidence_window_config(bundle)
            # LIVE-01: the frozen Q table is loaded and hash-verified HERE, before any session row exists, so a
            # missing or tampered artifact refuses the session up front (fail closed, no rule fallback).
            q_policy = load_q_policy(session_mode)
        except LiveEngineCError as exc:
            raise ConflictError() from exc

        # The manifest's own bundle_version must already be a REGISTERED c_runtime_bundle_records
        # row -- resolve_c_bundle_and_catalogue reads a FILE (the manifest), it never touches the
        # database; the FK column on c_sessions requires a real row. A manifest referencing an
        # unregistered bundle_version fails closed here, not with an invented FK target.
        bundle_record = await CRuntimeBundleRecordRepository(session).find_by_version(bundle.bundle_version)
        if bundle_record is None:
            raise ConflictError()

        # R-5: mastery VALUES and B IDENTITY both come from the same server-side fixture producer
        # for every combined-mode session -- never from the client (see this module's own
        # docstring and mastery_fixture.py's).
        if session_mode == "combined":
            mastery_by_skill = fixture_b_mastery_payload_for_phase_4()
            (
                mastery_source_student_id,
                mastery_source_intervention_session_id,
                mastery_source_intervention_session_number,
            ) = fixture_b_provenance_for_phase_4()
        else:
            mastery_by_skill = None
            mastery_source_student_id = None
            mastery_source_intervention_session_id = None
            mastery_source_intervention_session_number = None
        try:
            record = await create_session(
                session,
                adapter,
                student_id=student_id,
                grade=grade,
                session_mode=session_mode,
                catalogue_version=bundle.catalogue.version,
                catalogue_checksum=catalogue_checksum,
                c_runtime_bundle_record_id=bundle_record.c_runtime_bundle_record_id,
                # A real random seed for this session's own RNG lineage -- NOT "seed derivation"
                # (component_c_generator.seeds.derive_child_lineage etc., still explicitly out
                # of scope per the adapter's own module docstring); just initializing the
                # NOT NULL column with a real value rather than an invented fixed literal.
                global_seed=secrets.randbits(63),
                selection_config=selection_config,
                selection_config_field_statuses=bundle.selection_configuration.field_statuses,
                safety_config_field_statuses=bundle.safety_configuration.field_statuses,
                evidence_window_config_field_statuses=bundle.evidence_window_configuration.field_statuses,
                generation_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                policy_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                scaffold_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                aggregation_parameter_source_status=_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS,
                q_policy_parameter_source_status=q_policy.parameter_source_status,
                smoke_mode=_SMOKE_MODE,
                request_id=request_id,
                mastery_by_skill=mastery_by_skill,
                mastery_source_student_id=mastery_source_student_id,
                mastery_source_intervention_session_id=mastery_source_intervention_session_id,
                mastery_source_intervention_session_number=mastery_source_intervention_session_number,
            )
        except MasteryPayloadContractValidationError as exc:
            # B2-c: structured (loc, type) pairs only -- NEVER the blanket ConflictError, which
            # would silently drop the field_errors this batch's Q2 fix exists to expose safely.
            details = [{"location": list(loc), "type": code} for loc, code in exc.field_errors] or None
            raise MasteryPayloadRejectedError(details=details) from exc
        except LiveEngineCError as exc:
            # Every other LiveEngineCError (SF043OrderingError, SelectionConfigurationMissingError
            # if it somehow reaches here, etc.) -- the blanket pattern, mirroring
            # resolve_c_bundle_and_catalogue's own precedent exactly. None of these carry a
            # structured, safe-to-expose field_errors payload the way the mastery-contract case
            # does.
            raise ConflictError() from exc
        return CSessionCommandResponse(**_fields(record).model_dump(), request_id=request_id)

    async def get_active(
        self, session: AsyncSession, *, principal_user_id: str, request_id: str
    ) -> CActiveSessionResponse:
        student_id = await _require_learner_id(session, principal_user_id)
        record = await get_active_session(session, student_id)
        return CActiveSessionResponse(
            session=_fields(record) if record is not None else None, request_id=request_id
        )

    async def abandon(
        self, session: AsyncSession, *, principal_user_id: str, c_session_id: UUID, request_id: str
    ) -> CSessionCommandResponse:
        student_id = await _require_learner_id(session, principal_user_id)
        record = await abandon_session(session, c_session_id, student_id)
        return CSessionCommandResponse(**_fields(record).model_dump(), request_id=request_id)

    async def complete(
        self,
        session: AsyncSession,
        *,
        principal_user_id: str,
        c_session_id: UUID,
        request_id: str,
        attendance_status: AttendanceStatus,
    ) -> CSessionCommandResponse:
        student_id = await _require_learner_id(session, principal_user_id)
        adapter = LiveEngineCAdapter()
        record = await complete_session(
            session, adapter, c_session_id, student_id, attendance_status=attendance_status,
        )
        return CSessionCommandResponse(**_fields(record).model_dump(), request_id=request_id)
