"""BE4b: adaptive next-question selection (BEplan §9 BE4.2).

Every scientific step goes through ``app.infrastructure.live_engine.adapter.LiveEngineAdapter``
— this module copies or reimplements no formula. It only orchestrates: resolve the session's
pinned TEST bundle, load/initialize the learner's seven skill states, build the eligible
candidate set through the adapter's activation gate, score/rank/select through the adapter's
frozen-weight sequencing port, build the task through the adapter's construction port, persist
through BE4a's ``OpportunityPersistenceService`` (reused, not duplicated), and return only BE4a's
safe presentation DTO.

Engineering-only bundle bridge (documented limitation): the DB-level ``RuntimeBundleRecord`` a
session is pinned to (BE2/BE4a) carries no file path to the actual runtime-bundle manifest this
batch needs to *read* (catalogue path, TEST BKT fixture). No governed bundle-artifact resolution
mechanism exists yet, and this batch may not touch ``provenance/``. Until that lands,
``_ENGINEERING_TEST_BUNDLES`` maps the one known BE3b TEST-provenance DRAFT fixture
(``tests/fixtures/runtime_bundle/valid_unapproved_bundle.json`` +
``tests/fixtures/runtime_bundle/test_catalogue.md``, reused — not duplicated) by
``bundle_version``; any other ``bundle_version`` fails closed as "no eligible bundle". This
bridge must not survive into a governed production selection path.

The BKT config used for ``compute_features`` is likewise a fixed, population-neutral,
TEST_FIXTURE_ONLY set of parameters (mirroring ``tests/test_be3b_live_engine_adapter.py``'s own
``_bkt_config()`` fixture), never the population-conditioned research table in
``provenance/component-b-scientific-parameter-authorization.json`` — that table is keyed by
``population`` (TD/MLD/DD), which is architecturally prohibited anywhere near live BKT (see
``tests/test_be2_architecture_guards.py`` ``PROHIBITED_COLUMN_TERMS`` and
``tests/test_be3_live_engine_boundary.py``).

``scheduled_session_number`` and ``b_session_index`` (SeedManager lineage coordinates) are fixed
engineering placeholders (``1``); no curriculum-scheduling system exists yet in this codebase.
``global_seed`` is derived deterministically from the session's own ``session_id`` (a stable,
server-generated UUID pinned once at session creation) via SHA-256, rather than adding a new
``b_sessions`` column — this keeps BE2's already-committed session schema untouched while still
giving every opportunity in a session a fixed, reproducible seed root.
"""

from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from typing import TYPE_CHECKING, Mapping
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.opportunity_persistence import OpportunityPersistenceService
from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError
from app.domain.b_opportunity import (
    OpportunityPresentationFields,
    OpportunityPresentationResponse,
    opportunity_presentation_fields,
    project_task_instance_to_presentation,
)
from app.domain.live_engine.errors import LiveEngineError
from app.domain.live_engine.locales import DEFAULT_LOCALE, Locale
from app.domain.live_engine.types import (
    BktConfig,
    Catalogue,
    ScoredCandidate,
    SelectionResult,
    SequencingCandidate,
    SkillBktParams,
    TaskConstructionRequest,
    TaskInstance,
)
from app.domain.principal import AuthenticatedPrincipal
from app.domain.runtime_bundle.errors import RuntimeBundleError
from app.domain.runtime_bundle.readiness import assert_catalogue_matches_bundle
from app.infrastructure.persistence_models import AppUser, LearnerSkillStateRecord
from app.infrastructure.repositories import (
    AppUserRepository,
    ItemOpportunityRepository,
    LearnerRepository,
    LearnerSkillStateRepository,
    RuntimeBundleRecordRepository,
    SessionRecordRepository,
    TaskInstanceRepository,
)
from app.infrastructure.runtime_bundle.loader import RuntimeBundleLoader
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


if TYPE_CHECKING:
    # Deferred: importing app.infrastructure.live_engine.adapter pulls in
    # component_b_generator transitively. Keeping that import lazy (see
    # OpportunitySelectionService.select_next_opportunity) means app.main / every other route
    # stays importable — and every other test collectible — on a host without the vendored
    # wheel installed (e.g. this repo's own Python 3.11-only wheel on a 3.10/3.13/3.14 host).
    # Only actually calling this route requires the package; that is the same "adapter is the
    # only importer" boundary BE3 already established, just kept lazy at the call site too.
    from app.infrastructure.live_engine.adapter import LiveEngineAdapter


SCHEMA_REVISION = "20260727_0002"
RUNTIME_BUNDLE_SCHEMA_PATH = "provenance/runtime-bundle.schema.json"
PRESENTATION_TOKEN_TTL = timedelta(minutes=10)
DEFAULT_TIMEOUT = timedelta(minutes=5)

# See module docstring: ENGINEERING-ONLY TEST-provenance DRAFT bridge, not a governed
# bundle-artifact resolution mechanism.
_ENGINEERING_TEST_BUNDLES: Mapping[str, tuple[str, str]] = {
    "be3b-test-fixture-1.0": (
        "tests/fixtures/runtime_bundle/valid_unapproved_bundle.json",
        "tests/fixtures/runtime_bundle/test_catalogue.md",
    ),
}

_SEVEN_SKILLS = (
    "counting",
    "number_sense",
    "place_value",
    "addition",
    "subtraction",
    "multiplication",
    "division",
)

# TEST_FIXTURE_ONLY, population-neutral — see module docstring for why this is never sourced
# from provenance/component-b-scientific-parameter-authorization.json's population-conditioned
# table. Mirrors tests/test_be3b_live_engine_adapter.py::_bkt_config() exactly.
_ENGINEERING_BKT_CONFIG = BktConfig(
    skill_params={skill: SkillBktParams(p_l0=0.2, p_t=0.15, p_g=0.2, p_s=0.1) for skill in _SEVEN_SKILLS},
    theta_b=0.8,
    floor_quantile=0.1,
    floor_min_obs=5,
    config_version="be4b-engineering-fixture-1.0",
    parameter_source_status="TEST_FIXTURE_ONLY",
)

# Fixed engineering placeholders — see module docstring. Not scientific parameters; pure
# bookkeeping coordinates required by the adapter's SeedManager lineage signature.
_SCHEDULED_SESSION_NUMBER = 1
_B_SESSION_INDEX = 1
_SELECTION_REASON_INTERNAL = "be4b-adaptive-selection"


def _difficulty_band(difficulty_level: str) -> int:
    match = re.fullmatch(r"L(\d+)", difficulty_level)
    if not match:
        raise ConflictError()
    return int(match.group(1))


def _derive_global_seed(session_id: UUID) -> int:
    digest = hashlib.sha256(str(session_id).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def student_number(learner_id: UUID) -> int:
    """Deterministic 4-digit derivation from ``learner_id`` — see ``package_item_opportunity_id``
    and ``package_student_id`` for the two package-format identifiers built from it."""
    return int(hashlib.sha256(str(learner_id).encode()).hexdigest(), 16) % 10_000


def package_item_opportunity_id(learner_id: UUID, b_session_index: int, opportunity_index: int) -> str:
    """The vendored package's ``GeneratedItemOpportunity.item_opportunity_id`` validator
    requires the exact format ``^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$`` (internal-only, opaque —
    it carries no learner PII and never leaves the backend). ``learner_id`` is our real UUID
    identity; the 4-digit student number here is a deterministic derivation from it purely to
    satisfy this format, not a second identity. Real global uniqueness of the opportunity is
    enforced separately, at the DB level, by ``ItemOpportunityRecord``'s UUID primary key."""
    return f"STU-{student_number(learner_id):04d}-B{b_session_index:03d}-I{opportunity_index:03d}"


def package_student_id(learner_id: UUID) -> str:
    """BE4e (BEplan §9 BE4.6): the vendored package's ``aggregate_session`` builds
    ``session_id`` as ``f"{student_id}-B-{b_session_index:03d}"`` and validates it against
    ``^STU-[0-9]{4}-B-[0-9]{3}$`` (see ``component_b_generator.aggregation.session``). Reuses the
    same opaque, PII-free derivation as ``package_item_opportunity_id`` rather than inventing a
    second student-identifier scheme."""
    return f"STU-{student_number(learner_id):04d}"


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "actor_user_id": user_id,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_B_OPPORTUNITY_SELECTION_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


def select_candidate(
    *,
    adapter: LiveEngineAdapter,
    catalogue: Catalogue,
    bkt_config: BktConfig,
    grade: int,
    mastery: Mapping[str, float],
    sessions_since_practice: Mapping[str, int] | None = None,
) -> SelectionResult:
    """Pure, side-effect-free core: candidate build -> hard gates -> features -> score -> select.

    No database access, no opportunity/seed identity — selecting a target skill/template does
    not depend on which physical opportunity row it will end up attached to. Called once by the
    persisting service below, and called twice directly by the determinism test with identical
    arguments to prove byte-identical output.

    ``sessions_since_practice`` is supplied by the caller (which has the database session) precisely
    so this function can stay pure — see the history note below.
    """
    supported_template_ids = adapter.supported_template_ids()
    # BE-P2 defect fix — spacing_due was inert.
    #
    # This line used to be `history = {skill: None for skill in catalogue.skills}`: a fresh all-None
    # mapping rebuilt on EVERY selection, never populated from practice history. Since
    # `sequencing.features.compute_features` maps a `None` entry to `spacing_due = 1.0`, every
    # candidate scored a constant 1.0 on spacing forever — so the approved formula's 20% spacing
    # weight added the same 0.20 to every candidate and could never differentiate anything. A skill
    # practised five times running was exactly as "due" as one never practised.
    #
    # Only the WIRING changed. `SPACING_DUE_SATURATION_SESSIONS`, the 0.50/0.30/0.20 weights,
    # mastery_gap's formula and every BKT parameter are untouched — they were never the defect.
    # A caller that supplies nothing still gets the previous behaviour, which keeps the pure
    # determinism test callable without a database.
    history: dict[str, int | None] = {skill: None for skill in catalogue.skills}
    for skill_id, gap in (sessions_since_practice or {}).items():
        if skill_id in history:
            history[skill_id] = gap

    scored: list[ScoredCandidate] = []
    for template in catalogue.templates:
        decision = adapter.decide_activation(catalogue, template.item_template_id, supported_template_ids, grade)
        if not decision.active:
            continue
        candidate = SequencingCandidate(
            skill_id=template.skill_id,
            item_template_id=template.item_template_id,
            difficulty_band=_difficulty_band(template.difficulty_level),
        )
        features = adapter.compute_features(candidate, mastery, catalogue, history, bkt_config)
        score = adapter.score_candidate(features)
        scored.append(ScoredCandidate(candidate=candidate, features=features, score=score))

    if not scored:
        raise ConflictError()

    return adapter.select_target(scored)


def build_task(
    *,
    adapter: LiveEngineAdapter,
    catalogue: Catalogue,
    catalogue_checksum: str,
    selection: SelectionResult,
    student_id: str,
    grade: int,
    item_opportunity_id: str,
    opportunity_index: int,
    global_seed: int,
) -> TaskInstance:
    """Pure, side-effect-free core: the deterministic construction step, given an already-
    selected candidate and the real (already-persisted) opportunity identity."""
    winning_template = catalogue.by_id(selection.candidate.item_template_id)
    if winning_template is None:
        raise ConflictError()

    request = TaskConstructionRequest(
        item_opportunity_id=item_opportunity_id,
        student_id=student_id,
        grade=grade,
        scheduled_session_number=_SCHEDULED_SESSION_NUMBER,
        b_session_index=_B_SESSION_INDEX,
        item_index=opportunity_index,
        event_order=opportunity_index,
        item_template_id=selection.candidate.item_template_id,
        skill_id=selection.candidate.skill_id,
        curriculum_node_id=winning_template.curriculum_node_id,
        selection_reason_internal=_SELECTION_REASON_INTERNAL,
        global_seed=global_seed,
    )
    return adapter.build_task_instance(request, catalogue, catalogue_checksum)


async def resolve_bundle_and_catalogue(
    adapter: LiveEngineAdapter, bundle_record
) -> tuple[Catalogue, str]:
    """Shared engineering-bridge bundle/catalogue resolution (see module docstring) — reused by
    BE4b's standalone selection endpoint and BE4e's next-or-complete transition (BEplan §9 BE4.2
    + BE4.6) rather than duplicated. Fails closed (``ConflictError``) on any unknown bundle
    version or mismatched/invalid catalogue."""
    fixture = _ENGINEERING_TEST_BUNDLES.get(bundle_record.bundle_version)
    if fixture is None:
        raise ConflictError()
    manifest_path, catalogue_path = fixture
    try:
        bundle = RuntimeBundleLoader().load_and_validate(
            manifest_path,
            RUNTIME_BUNDLE_SCHEMA_PATH,
            artifact_paths={"catalogue": catalogue_path},
            require_approved=False,
        )
        catalogue = adapter.load(catalogue_path)
        catalogue_checksum = adapter.checksum(catalogue_path)
        assert_catalogue_matches_bundle(bundle, catalogue, catalogue_checksum)
    except (RuntimeBundleError, LiveEngineError) as exc:
        raise ConflictError() from exc
    return catalogue, catalogue_checksum


async def load_or_init_skill_states(
    session: AsyncSession,
    learner_id: UUID,
    bkt_config: BktConfig,
    user_id: UUID,
    request_id: str,
) -> dict[str, float]:
    """Module-level so BE4e's next-or-complete transition can reuse it without reaching into a
    private ``OpportunitySelectionService`` method (BEplan §9 BE4.6)."""
    repository = LearnerSkillStateRepository(session)
    existing = {row.skill_id: row for row in await repository.list_for_learner(learner_id)}
    mastery: dict[str, float] = {}
    for skill_id in _SEVEN_SKILLS:
        row = existing.get(skill_id)
        if row is not None:
            mastery[skill_id] = row.p_l
            continue
        p_l0 = bkt_config.skill_params[skill_id].p_l0
        record_id = uuid4()
        record = LearnerSkillStateRecord(
            learner_skill_state_id=record_id,
            learner_id=learner_id,
            skill_id=skill_id,
            p_l=p_l0,
            observation_count=0,
            **provenance(user_id, request_id, "b_learner_skill_state.initialized", "b_learner_skill_state", record_id),
        )
        session.add(record)
        mastery[skill_id] = p_l0
    await session.flush()
    return mastery


async def open_adaptive_opportunity(
    *,
    locale: Locale = DEFAULT_LOCALE,
    session: AsyncSession,
    adapter: LiveEngineAdapter,
    catalogue: Catalogue,
    catalogue_checksum: str,
    grade: int,
    mastery: Mapping[str, float],
    session_id: UUID,
    learner_id: UUID,
    runtime_bundle_record_id: UUID,
    opportunity_index: int,
    user_id: UUID,
    request_id: str,
) -> "OpportunityPresentationFields":
    """Shared select -> build -> persist -> issue-token core (BEplan §9 BE4.2), reused by BE4b's
    standalone selection endpoint and BE4e's next-or-complete transition (BEplan §9 BE4.6). No
    persistence logic of its own beyond what BE4a's ``OpportunityPersistenceService`` already
    provides."""
    opportunity_service = OpportunityPersistenceService(session)

    # BE-P2: real practice history, so spacing_due can actually vary between candidates. Both call
    # sites (BE4b's selection endpoint and BE4e's next-or-complete transition) reach this one place,
    # so neither can drift from the other.
    sessions_since_practice = await ItemOpportunityRepository(session).sessions_since_practice(learner_id)

    try:
        selection_result = select_candidate(
            adapter=adapter,
            catalogue=catalogue,
            bkt_config=_ENGINEERING_BKT_CONFIG,
            grade=grade,
            mastery=mastery,
            sessions_since_practice=sessions_since_practice,
        )
    except LiveEngineError as exc:
        raise ConflictError() from exc

    selection_reason = selection_result.selection_reason
    # One open opportunity per active session is enforced at the DB level (BE4a partial unique
    # index) inside open_opportunity; callers of this function must have already established
    # that no OPEN opportunity exists for this session (BE4b: brand-new session; BE4e: the prior
    # opportunity was just closed in the same transaction).
    opportunity = await opportunity_service.open_opportunity(
        session_id=session_id,
        learner_id=learner_id,
        skill_id=selection_result.candidate.skill_id,
        item_template_id=selection_result.candidate.item_template_id,
        opportunity_index=opportunity_index,
        selection_provenance={
            "winning_item_template_id": selection_reason.winning_item_template_id,
            "winning_skill_id": selection_reason.winning_skill_id,
            "score": selection_reason.score,
            "mastery_gap": selection_reason.mastery_gap,
            "prerequisite_readiness": selection_reason.prerequisite_readiness,
            "spacing_due": selection_reason.spacing_due,
            "tie_broken": selection_reason.tie_broken,
            "tie_break_basis": selection_reason.tie_break_basis,
        },
        timeout=DEFAULT_TIMEOUT,
        provenance=provenance(user_id, request_id, "b_opportunity.opened", "b_item_opportunity", session_id),
    )

    try:
        task_instance = build_task(
            adapter=adapter,
            catalogue=catalogue,
            catalogue_checksum=catalogue_checksum,
            selection=selection_result,
            student_id=str(learner_id),
            grade=grade,
            item_opportunity_id=package_item_opportunity_id(learner_id, _B_SESSION_INDEX, opportunity_index),
            opportunity_index=opportunity_index,
            global_seed=_derive_global_seed(session_id),
        )
    except LiveEngineError as exc:
        raise ConflictError() from exc

    task_instance_record = await opportunity_service.create_task_instance(
        item_opportunity_id=opportunity.item_opportunity_id,
        item_template_id=task_instance.item_template_id,
        skill_id=task_instance.skill_id,
        grade=task_instance.grade,
        difficulty_level=task_instance.difficulty_level,
        representation_type=task_instance.representation_type,
        response_format=task_instance.response_format,
        prompt=task_instance.prompt,
        correct_answer=task_instance.correct_answer,
        allowed_equivalent_answers=task_instance.allowed_equivalent_answers,
        distractor_candidates=task_instance.distractor_candidates,
        distractor_rule_ids=task_instance.distractor_rule_ids,
        generated_operands=task_instance.generated_operands,
        generation_seed=task_instance.generation_seed,
        applied_guard_ids=task_instance.applied_guard_ids,
        catalogue_version=task_instance.catalogue_version,
        catalogue_checksum=task_instance.catalogue_checksum,
        provenance=provenance(user_id, request_id, "b_task_instance.created", "b_task_instance", opportunity.item_opportunity_id),
    )

    raw_token, _token_record = await opportunity_service.issue_presentation_token(
        session_id=session_id,
        item_opportunity_id=opportunity.item_opportunity_id,
        learner_id=learner_id,
        runtime_bundle_record_id=runtime_bundle_record_id,
        ttl=PRESENTATION_TOKEN_TTL,
        provenance=provenance(user_id, request_id, "b_presentation_token.issued", "b_presentation_token", opportunity.item_opportunity_id),
    )

    presented = project_task_instance_to_presentation(
        task_instance_record,
        presentation_token=raw_token,
        server_timeout_deadline_utc=opportunity.timeout_deadline_utc,
        locale=locale,
    )
    return opportunity_presentation_fields(presented)


async def reissue_presentation_for_open_opportunity(
    *,
    locale: Locale = DEFAULT_LOCALE,
    session: AsyncSession,
    session_id: UUID,
    learner_id: UUID,
    runtime_bundle_record_id: UUID,
    open_opportunity,
    user_id: UUID,
    request_id: str,
) -> "OpportunityPresentationFields":
    """BE4e recovery (BEplan §9 BE4.6 step 6): app restart, a stale/expired presentation token,
    or a retried network call must be able to re-fetch the session's already-OPEN opportunity
    without creating a duplicate — the BE4a partial unique index only prevents a *second* OPEN
    opportunity, it does not itself provide a safe re-fetch path. Issues a fresh presentation
    token bound to the same opportunity (the old token, if any, is left to expire naturally;
    ``PresentationTokenRecord`` has no uniqueness constraint tying it to one token per
    opportunity, so re-issuing is additive, not destructive)."""
    opportunity_service = OpportunityPersistenceService(session)
    task_instance_record = await TaskInstanceRepository(session).find_by_opportunity(open_opportunity.item_opportunity_id)
    if task_instance_record is None:
        raise ConflictError()
    raw_token, _token_record = await opportunity_service.issue_presentation_token(
        session_id=session_id,
        item_opportunity_id=open_opportunity.item_opportunity_id,
        learner_id=learner_id,
        runtime_bundle_record_id=runtime_bundle_record_id,
        ttl=PRESENTATION_TOKEN_TTL,
        provenance=provenance(user_id, request_id, "b_presentation_token.reissued", "b_presentation_token", open_opportunity.item_opportunity_id),
    )
    presented = project_task_instance_to_presentation(
        task_instance_record,
        presentation_token=raw_token,
        server_timeout_deadline_utc=open_opportunity.timeout_deadline_utc,
        locale=locale,
    )
    return opportunity_presentation_fields(presented)


class OpportunitySelectionService:
    """BE4b application service: the ``POST /api/v1/b/sessions/{session_id}/opportunities``
    use case. Reuses BE4a's ``OpportunityPersistenceService`` for every persistence step; adds
    no persistence logic of its own beyond the seven-skill-state read/initialize."""

    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def _require_learner(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> tuple[AppUser, UUID]:
        found = await AppUserRepository(session).find_with_learner_link_by_subject(principal.user_id)
        if found is None:
            raise ResourceNotFoundError()
        user, link = found
        if user.profile_type != "LEARNER":
            raise ForbiddenError()
        if link is None:
            raise ResourceNotFoundError()
        return user, link.learner_id

    async def select_next_opportunity(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        request_id: str,
        locale: Locale = DEFAULT_LOCALE,
    ) -> OpportunityPresentationResponse:
        async with self._uow_factory() as uow:
            user, learner_id = await self._require_learner(uow.session, principal)

            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"b_opportunity.select:{learner_id}"},
            )

            session_row = await SessionRecordRepository(uow.session).get_owned(session_id, learner_id)
            if session_row is None:
                raise ResourceNotFoundError()
            if session_row.state != "active":
                raise ConflictError()

            # BE4e recovery (BEplan §9 BE4.6 step 6): app restart, a retried network call, or a
            # stale presentation token must be able to re-fetch the session's already-OPEN
            # opportunity rather than fail with the BE4a one-open-per-session conflict — see
            # reissue_presentation_for_open_opportunity.
            existing_open = await ItemOpportunityRepository(uow.session).find_open_for_session(session_id)
            if existing_open is not None:
                fields = await reissue_presentation_for_open_opportunity(
                    locale=locale,
                    session=uow.session,
                    session_id=session_id,
                    learner_id=learner_id,
                    runtime_bundle_record_id=session_row.runtime_bundle_record_id,
                    open_opportunity=existing_open,
                    user_id=user.user_id,
                    request_id=request_id,
                )
                response = OpportunityPresentationResponse(**fields.model_dump(), request_id=request_id)
                await uow.commit()
                return response

            learner_row = await LearnerRepository(uow.session).get_by_id(learner_id)
            if learner_row is None or learner_row.grade is None:
                raise ConflictError()
            grade = learner_row.grade

            bundle_record = await RuntimeBundleRecordRepository(uow.session).get_by_id(session_row.runtime_bundle_record_id)
            if bundle_record is None:
                raise ConflictError()

            from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

            adapter = LiveEngineAdapter()
            catalogue, catalogue_checksum = await resolve_bundle_and_catalogue(adapter, bundle_record)

            mastery = await load_or_init_skill_states(
                uow.session, learner_id, _ENGINEERING_BKT_CONFIG, user.user_id, request_id
            )

            existing_count = await ItemOpportunityRepository(uow.session).count_for_session(session_id)
            opportunity_index = existing_count + 1

            fields = await open_adaptive_opportunity(
                locale=locale,
                session=uow.session,
                adapter=adapter,
                catalogue=catalogue,
                catalogue_checksum=catalogue_checksum,
                grade=grade,
                mastery=mastery,
                session_id=session_id,
                learner_id=learner_id,
                runtime_bundle_record_id=session_row.runtime_bundle_record_id,
                opportunity_index=opportunity_index,
                user_id=user.user_id,
                request_id=request_id,
            )
            response = OpportunityPresentationResponse(**fields.model_dump(), request_id=request_id)
            await uow.commit()
            return response
