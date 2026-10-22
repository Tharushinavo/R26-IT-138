"""Deterministic weighted-sum selection score + canonical tie-break (Phase B4.3, B-022).

``score_candidate`` computes the FROZEN weighted sum from ``BSequencingConfig`` (never a
hard-coded weight); ``select_target``/``rank_candidates`` pick and order candidates with a fully
canonical, seedless tie-break. No item-within-skill selection or task-instance wiring here
(B4.4); ``difficulty_band`` is never a term in the score (sequencing/ordering-only, a within-skill
concern for B4.4).
"""

from __future__ import annotations

from typing import NamedTuple, Sequence, Tuple

from pydantic import BaseModel, ConfigDict

from models.contracts import SKILLS

from .config import BSequencingConfig
from .features import SequencingFeatures
from .models import SequencingCandidate

_SKILL_ORDER = {skill: idx for idx, skill in enumerate(SKILLS)}


def score_candidate(features: SequencingFeatures, config: BSequencingConfig) -> float:
    """FROZEN weighted-sum selection score (B-022):
    ``score = w_mastery_gap*mastery_gap + w_prereq*prerequisite_readiness + w_spacing*spacing_due``.

    Weights are always read from ``config`` (which itself only accepts the pinned
    0.50/0.30/0.20 set, B4.0) -- never hard-coded here. Since every feature is in ``[0,1]`` and
    the weights sum to 1.0, the result is always in ``[0,1]``. ``difficulty_band`` is not a term
    in this sum -- it plays no role in candidate scoring.
    """
    return (
        config.w_mastery_gap * features.mastery_gap
        + config.w_prereq * features.prerequisite_readiness
        + config.w_spacing * features.spacing_due
    )


class ScoredCandidate(NamedTuple):
    """A candidate paired with its computed score and the features that produced it."""

    candidate: SequencingCandidate
    features: SequencingFeatures
    score: float


def _canonical_key(scored: ScoredCandidate) -> Tuple[float, int, str]:
    # Descending score first (negated for ascending sort), then canonical tie-break: skill
    # order, then lexicographic item_template_id.
    skill_rank = _SKILL_ORDER.get(scored.candidate.skill_id, len(_SKILL_ORDER))
    return (-scored.score, skill_rank, scored.candidate.item_template_id)


def rank_candidates(scored_candidates: Sequence[ScoredCandidate]) -> Tuple[ScoredCandidate, ...]:
    """Deterministic descending-score order with the canonical tie-break (skill order, then
    lexicographic ``item_template_id``). Pure; no seed, no RNG; stable and reproducible
    regardless of input ordering."""
    return tuple(sorted(scored_candidates, key=_canonical_key))


class SelectionReason(BaseModel):
    """Transparent, deterministic rationale for one selection (B-internal; B->3 export is a
    later slice, B5). Records the winning score, its three feature components, and whether a
    tie was broken (and on what canonical basis)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    winning_item_template_id: str
    winning_skill_id: str
    score: float
    mastery_gap: float
    prerequisite_readiness: float
    spacing_due: float
    tie_broken: bool
    tie_break_basis: str


class SelectionResult(NamedTuple):
    candidate: SequencingCandidate
    selection_reason: SelectionReason


def select_target(scored_candidates: Sequence[ScoredCandidate]) -> SelectionResult:
    """Select the highest-scoring candidate with the canonical, fully-deterministic tie-break.
    No randomness, no seed. Raises ``ValueError`` on an empty candidate set (fail-closed rather
    than fabricating a selection)."""
    if not scored_candidates:
        raise ValueError("select_target requires at least one scored candidate")

    ranked = rank_candidates(scored_candidates)
    winner = ranked[0]
    tied = [s for s in ranked if s.score == winner.score]
    tie_broken = len(tied) > 1

    reason = SelectionReason(
        winning_item_template_id=winner.candidate.item_template_id,
        winning_skill_id=winner.candidate.skill_id,
        score=winner.score,
        mastery_gap=winner.features.mastery_gap,
        prerequisite_readiness=winner.features.prerequisite_readiness,
        spacing_due=winner.features.spacing_due,
        tie_broken=tie_broken,
        tie_break_basis="skill order, then lexicographic item_template_id" if tie_broken else "unique highest score",
    )
    return SelectionResult(candidate=winner.candidate, selection_reason=reason)
