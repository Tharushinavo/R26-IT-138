"""``LiveEngineAdapter`` — binds every ``app.domain.live_engine`` port to the vendored,
reviewed live-safe subset of the Component B generator (``component_b_generator``, packaged as
``upadya-component-b-live-engine``; see ``backend/provenance/component-b-live-engine-reuse-map.json``).

No formula is copied or rewritten here: every method below calls straight through to the
package's own pure functions. This module's job is exactly the three things BE3.2 asks for:

1. map backend domain types <-> the package's Pydantic/dataclass types;
2. call the existing package functions;
3. translate package exceptions into the stable ``app.domain.live_engine.errors`` hierarchy.

Only this module (and ``app.infrastructure.runtime_bundle``, for schema/checksum validation of
the *manifest*, not the engine) may import ``component_b_generator``. See
``tests/test_be3_live_engine_boundary.py`` for the import-boundary guard that enforces this and
keeps the 13 explicitly prohibited research/synthetic modules unreachable from ``app/``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Mapping, Optional, Sequence

from component_b_generator.answers.registry import (
    allowed_equivalent_answers as _pkg_allowed_equivalent_answers,
    correct_answer_raw as _pkg_correct_answer_raw,
)
from component_b_generator.answers.rules import (
    AnswerRuleError as _PkgAnswerRuleError,
    answers_equivalent as _pkg_answers_equivalent,
    normalize_answer as _pkg_normalize_answer,
)
from component_b_generator.answers.structured import (
    StructuredParseError as _PkgStructuredParseError,
    structured_forms_equivalent as _pkg_structured_forms_equivalent,
)
from component_b_generator.bkt.certification import certify_skill as _pkg_certify_skill
from component_b_generator.bkt.config import BBKTConfig as _PkgBBKTConfig, SkillBKTParams as _PkgSkillBKTParams
from component_b_generator.bkt.guess_guard import (
    GuessGuardStatus as _PkgGuessGuardStatus,
    evaluate_guess_guard as _pkg_evaluate_guess_guard,
    guess_guard_triggered_count as _pkg_guess_guard_triggered_count,
    plausibility_floor as _pkg_plausibility_floor,
)
from component_b_generator.bkt.state import BBKTSkillState as _PkgBBKTSkillState
from component_b_generator.bkt.update import (
    bkt_posterior as _pkg_bkt_posterior,
    bkt_predict as _pkg_bkt_predict,
    bkt_update as _pkg_bkt_update,
)
from component_b_generator.behaviour.hints import (
    HintContentError as _PkgHintContentError,
    get_catalogue_hint as _pkg_get_catalogue_hint,
)
from component_b_generator.catalogue.loader import (
    CatalogueValidationError as _PkgCatalogueValidationError,
    catalogue_file_checksum as _pkg_catalogue_file_checksum,
    load_catalogue as _pkg_load_catalogue,
)
from component_b_generator.aggregation.session import (
    SessionIdentity as _PkgSessionIdentity,
    aggregate_session as _pkg_aggregate_session,
)
from component_b_generator.distractors.registry import (
    generate_distractors as _pkg_generate_distractors,
    required_distractor_count as _pkg_required_distractor_count,
)
from component_b_generator.generation.activation import decide_activation as _pkg_decide_activation
from component_b_generator.generation.errors import (
    DistractorGenerationError as _PkgDistractorGenerationError,
    TaskInstanceValidationError as _PkgTaskInstanceValidationError,
    UnsupportedTemplateError as _PkgUnsupportedTemplateError,
)
from component_b_generator.generation.task_instances import build_task_instance as _pkg_build_task_instance
from component_b_generator.models.behaviour import BOpportunityResponseSummary as _PkgOpportunityResponseSummary
from component_b_generator.models.opportunity import (
    GeneratedItemOpportunity as _PkgGeneratedItemOpportunity,
    SkillMasteryUpdate as _PkgSkillMasteryUpdate,
)
from component_b_generator.samplers.registry import supported_template_ids as _pkg_supported_template_ids
from component_b_generator.seeds import SeedManager as _PkgSeedManager
from component_b_generator.sequencing.config import BSequencingConfig as _PkgBSequencingConfig
from component_b_generator.sequencing.features import compute_features as _pkg_compute_features
from component_b_generator.sequencing.models import SequencingCandidate as _PkgSequencingCandidate
from component_b_generator.sequencing.score import (
    ScoredCandidate as _PkgScoredCandidate,
    SequencingFeatures as _PkgSequencingFeatures,
    rank_candidates as _pkg_rank_candidates,
    score_candidate as _pkg_score_candidate,
    select_target as _pkg_select_target,
)

from app.domain.live_engine.errors import (
    AnswerRuleUnavailableError,
    CatalogueUnavailableError,
    DistractorConstructionError,
    HintUnavailableError,
    LiveEngineError,
    TaskConstructionError,
    TemplateNotActiveError,
    UnknownTemplateError,
)
from app.domain.live_engine.types import (
    ActivationDecision,
    BktConfig,
    Catalogue,
    GuessGuardStatus,
    HintReference,
    ItemTemplate,
    OpportunityResponse,
    ScoredCandidate,
    SelectionReason,
    SelectionResult,
    SequencingCandidate,
    SequencingFeatures,
    SessionAggregate,
    SessionAggregateStats,
    SessionIdentity,
    SkillMasteryUpdate,
    SkillSessionRollup,
    TaskConstructionRequest,
    TaskInstance,
)

# Pinned, non-configurable sequencing weights (BEplan §"sequencing uses the frozen weighted
# score": 0.50/0.30/0.20). Never sourced from caller input — the package's own config model
# rejects any other value, and this adapter never gives it the chance to try.
_SEQUENCING_CONFIG_VERSION = "be3b-adapter-pinned-1.0"
_SEQUENCING_PARAMETER_SOURCE_STATUS = "ENGINEERING_ASSUMPTION"

# Provenance-only fields required by the package's ``BOpportunityResponseSummary`` model that
# carry no aggregation math and are not part of the reviewed domain type (BE3b keeps the
# aggregation port's input shape backend-owned; see reuse map "session aggregation" entry).
_DERIVATION_VERSION = "be3b-adapter-1.0"
_SOURCE_EVENT_SCHEMA_VERSION = "be3b-adapter-1.0"


def _map_template(template) -> ItemTemplate:
    return ItemTemplate(
        item_template_id=template.item_template_id,
        skill_id=template.skill_id,
        curriculum_node_id=template.curriculum_node_id,
        difficulty_level=template.difficulty_level,
        task_type=template.task_type,
        representation_type=template.representation_type,
        evidence_status=template.evidence_status,
        eligible_grades=tuple(template.eligible_grades),
        grade_gate_status=template.grade_gate_status,
        prerequisite_nodes=tuple(template.prerequisite_nodes),
    )


def _map_catalogue(catalogue) -> Catalogue:
    return Catalogue(
        catalogue_version=catalogue.catalogue_version,
        catalogue_status=catalogue.catalogue_status,
        source_path=catalogue.source_path,
        skills=tuple(catalogue.skills),
        templates=tuple(_map_template(t) for t in catalogue.templates),
    )


@lru_cache(maxsize=8)
def _load_package_catalogue_cached(source_path: str):
    """The parse itself, memoised per governed path. See ``_load_package_catalogue``."""
    return _pkg_load_catalogue(source_path)


def _load_package_catalogue(source_path: str):
    """Re-load the package's own ``LoadedCatalogue`` from the same governed path.

    Every port method that needs package-native catalogue objects (activation, sequencing
    features, task construction, hints) re-derives them from ``source_path`` rather than
    reconstructing a package Pydantic model by hand from the trimmed domain ``Catalogue`` — so
    the object handed to the reviewed package functions is always the real, fully-validated
    loader output, never a hand-rolled approximation of it.

    PARSED ONCE PER PATH, not once per call. That intent above is about *what* the package
    receives -- genuine loader output rather than a hand-rolled approximation -- and memoising
    preserves it exactly: the cached object IS `_pkg_load_catalogue`'s own fully-validated
    output. What it stops is re-deriving it dozens of times inside a single request. Because
    "every port method" re-derives, one adaptive selection called this 50 times (36
    `decide_activation` + 14 `compute_features`), and each call was a full `yaml.safe_load` of
    the packaged catalogue: ~79ms apiece, ~1.1s of pure CPU per question asked, which was the
    single largest cost in `POST .../complete` and larger than all of its 18 database round
    trips combined.

    Safe to share because the catalogue is immutable at runtime -- it ships inside the vendored
    wheel and is read-only in the image -- and because the package functions handed the object
    are the reviewed pure ones (`select_candidate` is documented as a pure, side-effect-free
    core). Nothing mutates what it is given. `lru_cache` does not cache exceptions, so an
    unreadable or invalid catalogue still raises on every attempt exactly as before.
    """
    try:
        return _load_package_catalogue_cached(source_path)
    except _PkgCatalogueValidationError as exc:
        raise CatalogueUnavailableError(str(exc)) from exc


def _to_pkg_bkt_config(config: BktConfig) -> _PkgBBKTConfig:
    return _PkgBBKTConfig(
        skill_params={
            skill: _PkgSkillBKTParams(p_l0=p.p_l0, p_t=p.p_t, p_g=p.p_g, p_s=p.p_s)
            for skill, p in config.skill_params.items()
        },
        theta_B=config.theta_b,
        floor_quantile=config.floor_quantile,
        floor_min_obs=config.floor_min_obs,
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
    )


def _to_pkg_sequencing_candidate(candidate: SequencingCandidate) -> _PkgSequencingCandidate:
    return _PkgSequencingCandidate(
        skill_id=candidate.skill_id,
        item_template_id=candidate.item_template_id,
        difficulty_band=candidate.difficulty_band,
    )


def _to_domain_sequencing_candidate(candidate) -> SequencingCandidate:
    return SequencingCandidate(
        skill_id=candidate.skill_id,
        item_template_id=candidate.item_template_id,
        difficulty_band=candidate.difficulty_band,
    )


def _to_pkg_features(features: SequencingFeatures) -> _PkgSequencingFeatures:
    return _PkgSequencingFeatures(
        mastery_gap=features.mastery_gap,
        prerequisite_readiness=features.prerequisite_readiness,
        spacing_due=features.spacing_due,
    )


def _to_domain_features(features) -> SequencingFeatures:
    return SequencingFeatures(
        mastery_gap=features.mastery_gap,
        prerequisite_readiness=features.prerequisite_readiness,
        spacing_due=features.spacing_due,
    )


def _guess_guard_to_pkg(status: GuessGuardStatus) -> _PkgGuessGuardStatus:
    return _PkgGuessGuardStatus(status.value)


def _guess_guard_to_domain(status) -> GuessGuardStatus:
    return GuessGuardStatus(status.value)


class LiveEngineAdapter:
    """Concrete adapter implementing every ``app.domain.live_engine`` port.

    Stateless: every method is a pure function of its arguments (plus, for catalogue-dependent
    calls, a re-read of the governed catalogue file at ``Catalogue.source_path``). No mutable
    instance state is held between calls.
    """

    # ---- CataloguePort -------------------------------------------------------------

    def load(self, catalogue_path: str) -> Catalogue:
        return _map_catalogue(_load_package_catalogue(catalogue_path))

    def checksum(self, catalogue_path: str) -> str:
        try:
            return _pkg_catalogue_file_checksum(catalogue_path)
        except _PkgCatalogueValidationError as exc:
            raise CatalogueUnavailableError(str(exc)) from exc

    # ---- ActivationPort -------------------------------------------------------------

    def decide_activation(
        self,
        catalogue: Catalogue,
        item_template_id: str,
        supported_template_ids: tuple[str, ...],
        grade: int,
    ) -> ActivationDecision:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        template = pkg_catalogue.by_id(item_template_id)
        if template is None:
            raise UnknownTemplateError(f"unknown item_template_id: {item_template_id!r}")
        decision = _pkg_decide_activation(
            template, supported_template_ids, grade, pkg_catalogue.catalogue_status
        )
        return ActivationDecision(
            item_template_id=decision.item_template_id,
            recognized=decision.recognized,
            implementation_supported=decision.implementation_supported,
            grade_eligible=decision.grade_eligible,
            curriculum_active=decision.curriculum_active,
            catalogue_status_ok=decision.catalogue_status_ok,
            calibration_restricted=decision.calibration_restricted,
            active=decision.active,
            reason=decision.reason,
        )

    def supported_template_ids(self) -> tuple[str, ...]:
        return _pkg_supported_template_ids()

    # ---- SequencingPort -------------------------------------------------------------

    def compute_features(
        self,
        candidate: SequencingCandidate,
        mastery: Mapping[str, float],
        catalogue: Catalogue,
        history: Mapping[str, Optional[int]],
        bkt_config: BktConfig,
    ) -> SequencingFeatures:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        pkg_mastery = {
            skill_id: _PkgBBKTSkillState(student_id="_", skill_id=skill_id, p_l=p_l, observation_count=0)
            for skill_id, p_l in mastery.items()
        }
        features = _pkg_compute_features(
            _to_pkg_sequencing_candidate(candidate),
            pkg_mastery,
            pkg_catalogue,
            history,
            _to_pkg_bkt_config(bkt_config),
        )
        return _to_domain_features(features)

    def score_candidate(self, features: SequencingFeatures) -> float:
        config = _PkgBSequencingConfig(
            w_mastery_gap=0.50,
            w_prereq=0.30,
            w_spacing=0.20,
            config_version=_SEQUENCING_CONFIG_VERSION,
            parameter_source_status=_SEQUENCING_PARAMETER_SOURCE_STATUS,
        )
        return _pkg_score_candidate(_to_pkg_features(features), config)

    def rank_candidates(self, scored: Sequence[ScoredCandidate]) -> tuple[ScoredCandidate, ...]:
        pkg_scored = [
            _PkgScoredCandidate(
                candidate=_to_pkg_sequencing_candidate(s.candidate),
                features=_to_pkg_features(s.features),
                score=s.score,
            )
            for s in scored
        ]
        ranked = _pkg_rank_candidates(pkg_scored)
        return tuple(
            ScoredCandidate(
                candidate=_to_domain_sequencing_candidate(r.candidate),
                features=_to_domain_features(r.features),
                score=r.score,
            )
            for r in ranked
        )

    def select_target(self, scored: Sequence[ScoredCandidate]) -> SelectionResult:
        pkg_scored = [
            _PkgScoredCandidate(
                candidate=_to_pkg_sequencing_candidate(s.candidate),
                features=_to_pkg_features(s.features),
                score=s.score,
            )
            for s in scored
        ]
        result = _pkg_select_target(pkg_scored)
        reason = result.selection_reason
        return SelectionResult(
            candidate=_to_domain_sequencing_candidate(result.candidate),
            selection_reason=SelectionReason(
                winning_item_template_id=reason.winning_item_template_id,
                winning_skill_id=reason.winning_skill_id,
                score=reason.score,
                mastery_gap=reason.mastery_gap,
                prerequisite_readiness=reason.prerequisite_readiness,
                spacing_due=reason.spacing_due,
                tie_broken=reason.tie_broken,
                tie_break_basis=reason.tie_break_basis,
            ),
        )

    # ---- TaskConstructionPort -------------------------------------------------------------

    def build_task_instance(
        self,
        request: TaskConstructionRequest,
        catalogue: Catalogue,
        catalogue_checksum: str,
    ) -> TaskInstance:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        template = pkg_catalogue.by_id(request.item_template_id)
        if template is None:
            raise UnknownTemplateError(f"unknown item_template_id: {request.item_template_id!r}")

        seed_manager = _PkgSeedManager(request.global_seed)
        seed_lineage = seed_manager.item_opportunity(
            request.student_id,
            request.scheduled_session_number,
            request.b_session_index,
            request.item_index,
        )
        opportunity = _PkgGeneratedItemOpportunity(
            item_opportunity_id=request.item_opportunity_id,
            student_id=request.student_id,
            grade=request.grade,
            scheduled_session_number=request.scheduled_session_number,
            b_session_index=request.b_session_index,
            item_index=request.item_index,
            event_order=request.event_order,
            item_template_id=request.item_template_id,
            skill_id=request.skill_id,
            curriculum_node_id=request.curriculum_node_id,
            selection_reason_internal=request.selection_reason_internal,
            seed_lineage=seed_lineage,
        )
        try:
            instance = _pkg_build_task_instance(
                opportunity,
                template,
                pkg_catalogue.catalogue_version,
                pkg_catalogue.catalogue_status,
                catalogue_checksum,
            )
        except _PkgUnsupportedTemplateError as exc:
            raise TemplateNotActiveError(str(exc)) from exc
        except _PkgTaskInstanceValidationError as exc:
            raise TaskConstructionError(str(exc)) from exc

        return TaskInstance(
            item_instance_id=instance.item_instance_id,
            item_opportunity_id=instance.item_opportunity_id,
            item_template_id=instance.item_template_id,
            skill_id=instance.skill_id,
            grade=instance.grade,
            difficulty_level=instance.difficulty_level,
            representation_type=instance.representation_type,
            response_format=instance.response_format,
            generated_operands=dict(instance.generated_operands),
            prompt=dict(instance.prompt),
            correct_answer=instance.correct_answer,
            allowed_equivalent_answers=tuple(instance.allowed_equivalent_answers),
            distractor_candidates=tuple(instance.distractor_candidates),
            distractor_rule_ids=tuple(instance.distractor_rule_ids),
            generation_seed=instance.generation_seed,
            catalogue_version=instance.catalogue_version,
            catalogue_checksum=instance.catalogue_checksum,
            applied_guard_ids=tuple(instance.applied_guard_ids),
        )

    # ---- AnswerPort -------------------------------------------------------------

    def normalize_answer(self, value: object) -> str:
        return _pkg_normalize_answer(value)

    def answers_equivalent(self, a: object, b: object) -> bool:
        return _pkg_answers_equivalent(a, b)

    def structured_forms_equivalent(self, a: object, b: object) -> bool:
        """Tolerant place-value comparison, routed through the reviewed package parser (BE-C2 B).

        Wraps ``component_b_generator.answers.structured.structured_forms_equivalent``, which parses
        both sides with ``parse_place_value_expression`` — hand-written, deterministic, no ``eval``,
        only the two approved grammars — and compares the resulting integers. Nothing is
        reimplemented here; this exists so the call is routed like every other scientific call.

        Returns ``False`` rather than raising when either side is not one of the approved forms: a
        child typing something unparseable is a wrong answer, not a server error. Callers must still
        scope *when* to use this — see ``attempt_submission``; applying it to an arithmetic template
        would start accepting ``10+2`` as an answer to a question whose answer is ``12``, i.e.
        accepting a restatement of the problem.
        """
        if not isinstance(a, str) or not isinstance(b, str):
            return False
        try:
            return _pkg_structured_forms_equivalent(a, b)
        except _PkgStructuredParseError:
            return False

    def correct_answer_raw(self, item_template_id: str, operands: Mapping[str, object]) -> object:
        try:
            return _pkg_correct_answer_raw(item_template_id, dict(operands))
        except KeyError as exc:
            raise AnswerRuleUnavailableError(str(exc)) from exc
        except _PkgAnswerRuleError as exc:
            raise TaskConstructionError(str(exc)) from exc

    def allowed_equivalent_answers(
        self, item_template_id: str, operands: Mapping[str, object]
    ) -> tuple[str, ...]:
        return tuple(_pkg_allowed_equivalent_answers(item_template_id, dict(operands)))

    # ---- DistractorPort -------------------------------------------------------------

    def generate_distractors(
        self,
        item_template_id: str,
        operands: Mapping[str, object],
        correct_raw: object,
        required: Optional[int] = None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        try:
            values, rule_ids = _pkg_generate_distractors(item_template_id, dict(operands), correct_raw, required)
        except KeyError as exc:
            raise AnswerRuleUnavailableError(str(exc)) from exc
        except _PkgDistractorGenerationError as exc:
            raise DistractorConstructionError(str(exc)) from exc
        return tuple(values), tuple(rule_ids)

    def required_distractor_count(self, item_template_id: str) -> int:
        try:
            return _pkg_required_distractor_count(item_template_id)
        except KeyError as exc:
            raise AnswerRuleUnavailableError(str(exc)) from exc

    # ---- HintPort -------------------------------------------------------------

    def get_hint(
        self,
        catalogue: Catalogue,
        catalogue_checksum: str,
        item_template_id: str,
        hint_level: int,
    ) -> HintReference:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        try:
            hint = _pkg_get_catalogue_hint(pkg_catalogue, catalogue_checksum, item_template_id, hint_level)
        except _PkgHintContentError as exc:
            raise HintUnavailableError(str(exc)) from exc
        return HintReference(
            item_template_id=hint.item_template_id,
            hint_level=hint.hint_level,
            content=hint.content,
            content_id=hint.content_id,
            catalogue_version=hint.catalogue_version,
            catalogue_checksum=hint.catalogue_checksum,
        )

    # ---- BktPort -------------------------------------------------------------

    def predict(self, p_l: float, p_g: float, p_s: float) -> float:
        return _pkg_bkt_predict(p_l=p_l, p_g=p_g, p_s=p_s)

    def posterior(self, p_l: float, correct: bool, p_g: float, p_s: float) -> float:
        return _pkg_bkt_posterior(p_l=p_l, correct=correct, p_g=p_g, p_s=p_s)

    def update(self, p_l: float, correct: bool, p_g: float, p_s: float, p_t: float) -> float:
        return _pkg_bkt_update(p_l=p_l, correct=correct, p_g=p_g, p_s=p_s, p_t=p_t)

    # ---- GuessGuardPort -------------------------------------------------------------

    def plausibility_floor(
        self, rt_history: Sequence[Optional[float]], q: float, n_min: int
    ) -> Optional[float]:
        return _pkg_plausibility_floor(rt_history, q, n_min)

    def evaluate(
        self,
        p_l: float,
        median_item_response_time_sec: float,
        rt_history: Sequence[Optional[float]],
        theta_b: float,
        q: float,
        n_min: int,
    ) -> GuessGuardStatus:
        status = _pkg_evaluate_guess_guard(p_l, median_item_response_time_sec, rt_history, theta_b, q, n_min)
        return _guess_guard_to_domain(status)

    def triggered_count(self, statuses: Sequence[GuessGuardStatus]) -> int:
        return _pkg_guess_guard_triggered_count(_guess_guard_to_pkg(s) for s in statuses)

    # ---- CertificationPort -------------------------------------------------------------

    def certify_skill(self, p_l: float, guard_status: GuessGuardStatus, theta_b: float) -> bool:
        return _pkg_certify_skill(p_l, _guess_guard_to_pkg(guard_status), theta_b)

    # ---- AggregationPort -------------------------------------------------------------

    def aggregate_session(
        self,
        session_identity: SessionIdentity,
        opportunities: Sequence[OpportunityResponse],
        skill_mastery_updates: Sequence[SkillMasteryUpdate],
        guard_statuses: Optional[Mapping[str, GuessGuardStatus]] = None,
        theta_b: Optional[float] = None,
    ) -> SessionAggregate:
        pkg_identity = _PkgSessionIdentity(
            student_id=session_identity.student_id,
            b_session_index=session_identity.b_session_index,
            scheduled_session_number=session_identity.scheduled_session_number,
            status=session_identity.status,
        )
        pkg_opportunities = [
            _PkgOpportunityResponseSummary(
                learner_id=o.learner_id,
                session_id=o.session_id,
                scheduled_session_index=o.scheduled_session_index,
                item_opportunity_id=o.item_opportunity_id,
                task_instance_id=o.task_instance_id,
                item_template_id=o.item_template_id,
                skill_id=o.skill_id,
                first_attempt_correct=o.first_attempt_correct,
                first_attempt_error_pattern=o.first_attempt_error_pattern,
                total_attempts=o.total_attempts,
                retry_count=o.total_attempts - 1,
                hint_requested=o.hint_requested,
                hint_count=o.hint_count,
                final_item_completed=o.final_item_completed,
                assisted_completion=o.assisted_completion,
                unassisted_completion=o.unassisted_completion,
                total_response_time_ms=o.total_response_time_ms,
                first_attempt_response_time_ms=o.first_attempt_response_time_ms,
                derivation_version=_DERIVATION_VERSION,
                source_event_schema_version=_SOURCE_EVENT_SCHEMA_VERSION,
            )
            for o in opportunities
        ]
        pkg_updates = [
            _PkgSkillMasteryUpdate(
                student_id=u.student_id,
                skill_id=u.skill_id,
                b_session_index=u.b_session_index,
                mastery_before=u.mastery_before,
                predicted_correct_probability=u.predicted_correct_probability,
                posterior_l=u.posterior_l,
                mastery_after=u.mastery_after,
            )
            for u in skill_mastery_updates
        ]
        pkg_guard_statuses = (
            {skill_id: _guess_guard_to_pkg(status) for skill_id, status in guard_statuses.items()}
            if guard_statuses is not None
            else None
        )
        try:
            result = _pkg_aggregate_session(
                pkg_identity,
                pkg_opportunities,
                pkg_updates,
                guard_statuses=pkg_guard_statuses,
                theta_B=theta_b,
            )
        except ValueError as exc:
            raise LiveEngineError(str(exc)) from exc

        summary = result.summary
        stats = result.stats
        return SessionAggregate(
            session_id=summary.session_id,
            status=summary.status,
            opportunity_ids=tuple(summary.opportunity_ids),
            skill_ids_practiced=tuple(summary.skill_ids_practiced),
            stats=SessionAggregateStats(
                session_id=stats.session_id,
                first_attempt_accuracy=stats.first_attempt_accuracy,
                completion_count=stats.completion_count,
                completion_rate=stats.completion_rate,
                total_retries=stats.total_retries,
                hint_bearing_opportunities=stats.hint_bearing_opportunities,
                response_time_mean_ms=stats.response_time_mean_ms,
                response_time_median_ms=stats.response_time_median_ms,
                response_time_std_ms=stats.response_time_std_ms,
                error_class_distribution=dict(stats.error_class_distribution),
            ),
            skill_rollups=tuple(
                SkillSessionRollup(
                    skill_id=r.skill_id,
                    opportunities=r.opportunities,
                    attempts=r.attempts,
                    first_attempt_correct=r.first_attempt_correct,
                    first_attempt_accuracy=r.first_attempt_accuracy,
                    estimated_mastery=r.estimated_mastery,
                    certified=r.certified,
                )
                for r in result.skill_rollups
            ),
        )
