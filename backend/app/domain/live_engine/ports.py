"""Domain ports over the reviewed live-safe Component B capabilities (BE3.1).

One small ``Protocol`` per reuse-map capability. Every method signature uses only backend
domain types (``app.domain.live_engine.types``) — never the vendored package's Pydantic models.
The concrete implementation lives in ``app.infrastructure.live_engine.adapter``.
"""

from __future__ import annotations

from typing import Mapping, Optional, Protocol, Sequence

from .types import (
    ActivationDecision,
    BktConfig,
    Catalogue,
    Grade,
    GuessGuardStatus,
    HintReference,
    OpportunityResponse,
    ScoredCandidate,
    SelectionResult,
    SequencingCandidate,
    SequencingFeatures,
    SessionAggregate,
    SessionIdentity,
    SkillMasteryUpdate,
    TaskConstructionRequest,
    TaskInstance,
)


class CataloguePort(Protocol):
    """Catalogue loading and validation (SPEC §6.1/§7)."""

    def load(self, catalogue_path: str) -> Catalogue:
        """Load + validate the governed catalogue. Fails closed (raises
        ``CatalogueUnavailableError``) on any defect; never returns a partial catalogue."""
        ...

    def checksum(self, catalogue_path: str) -> str:
        """Stable SHA-256 hex digest of the catalogue file bytes."""
        ...


class ActivationPort(Protocol):
    """Activation and grade eligibility (hard gate)."""

    def decide_activation(
        self,
        catalogue: Catalogue,
        item_template_id: str,
        supported_template_ids: tuple[str, ...],
        grade: Grade,
    ) -> ActivationDecision: ...


class SequencingPort(Protocol):
    """Sequencing features and the frozen weighted-sum score (0.50/0.30/0.20)."""

    def compute_features(
        self,
        candidate: SequencingCandidate,
        mastery: Mapping[str, float],
        catalogue: Catalogue,
        history: Mapping[str, Optional[int]],
        bkt_config: BktConfig,
    ) -> SequencingFeatures: ...

    def score_candidate(self, features: SequencingFeatures) -> float: ...

    def rank_candidates(self, scored: Sequence[ScoredCandidate]) -> tuple[ScoredCandidate, ...]: ...

    def select_target(self, scored: Sequence[ScoredCandidate]) -> SelectionResult: ...


class TaskConstructionPort(Protocol):
    """Deterministic single-instance task construction."""

    def build_task_instance(
        self,
        request: TaskConstructionRequest,
        catalogue: Catalogue,
        catalogue_checksum: str,
    ) -> TaskInstance: ...


class AnswerPort(Protocol):
    """Answer normalization and equivalence."""

    def normalize_answer(self, value: object) -> str: ...

    def answers_equivalent(self, a: object, b: object) -> bool: ...

    def correct_answer_raw(self, item_template_id: str, operands: Mapping[str, object]) -> object: ...

    def allowed_equivalent_answers(
        self, item_template_id: str, operands: Mapping[str, object]
    ) -> tuple[str, ...]: ...


class DistractorPort(Protocol):
    """Distractor construction."""

    def generate_distractors(
        self,
        item_template_id: str,
        operands: Mapping[str, object],
        correct_raw: object,
        required: Optional[int] = None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...

    def required_distractor_count(self, item_template_id: str) -> int: ...


class HintPort(Protocol):
    """Exact catalogue hint lookup (fail-closed, no generated fallback)."""

    def get_hint(
        self,
        catalogue: Catalogue,
        catalogue_checksum: str,
        item_template_id: str,
        hint_level: int,
    ) -> HintReference: ...


class BktPort(Protocol):
    """BKT prediction, posterior, and update (FROZEN formulas, no forgetting term)."""

    def predict(self, p_l: float, p_g: float, p_s: float) -> float: ...

    def posterior(self, p_l: float, correct: bool, p_g: float, p_s: float) -> float: ...

    def update(self, p_l: float, correct: bool, p_g: float, p_s: float, p_t: float) -> float: ...


class GuessGuardPort(Protocol):
    """Response-time plausibility check (does not itself decide certification)."""

    def plausibility_floor(
        self, rt_history: Sequence[Optional[float]], q: float, n_min: int
    ) -> Optional[float]: ...

    def evaluate(
        self,
        p_l: float,
        median_item_response_time_sec: float,
        rt_history: Sequence[Optional[float]],
        theta_b: float,
        q: float,
        n_min: int,
    ) -> GuessGuardStatus: ...

    def triggered_count(self, statuses: Sequence[GuessGuardStatus]) -> int: ...


class CertificationPort(Protocol):
    """Estimated -> certified mastery decision (not sticky)."""

    def certify_skill(self, p_l: float, guard_status: GuessGuardStatus, theta_b: float) -> bool: ...


class AggregationPort(Protocol):
    """Fold one session's opportunity/skill-update rows into aggregates."""

    def aggregate_session(
        self,
        session_identity: SessionIdentity,
        opportunities: Sequence[OpportunityResponse],
        skill_mastery_updates: Sequence[SkillMasteryUpdate],
        guard_statuses: Optional[Mapping[str, GuessGuardStatus]] = None,
        theta_b: Optional[float] = None,
    ) -> SessionAggregate: ...
