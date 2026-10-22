"""Pure BKT prediction and posterior-update math (Phase B3.1, Parameters §8.1, FROZEN).

Three pure, side-effect-free functions — no orchestration, no state folding, no I/O, no global
RNG, no truth mutation. All three formulas are verbatim from Parameters §8.1 and there is no
forgetting term: mastery only ever advances via the ``P(T)`` transition applied in
``bkt_update``.

**Timeout contract.** A timeout is an observed *incorrect* first attempt (FROZEN §6.10). This
module takes a plain ``correct: bool`` parameter; it has no timeout-specific branch. The caller
(B3.2 orchestrator) is responsible for mapping a timeout to ``correct=False`` before calling
into this module.

**Pre-transition vs. post-transition posterior.** ``bkt_posterior`` returns the Bayesian
posterior ``p(L|obs)`` *before* the ``P(T)`` transition is applied. ``bkt_update`` composes
``bkt_posterior`` and then applies the transition to produce ``p(L)_next``. An incorrect
observation always lowers ``p(L|obs)`` relative to the prior; the subsequent
``+ (1 − p(L|obs))·P(T)`` transition step may raise ``p(L)_next`` back above the prior — so
direction assertions belong on ``bkt_posterior``, never on ``bkt_update``'s return value.
"""

from __future__ import annotations

_EPS = 1e-12


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def bkt_predict(p_l: float, p_g: float, p_s: float) -> float:
    """P(first-attempt correct) = p_l·(1 − P(S)) + (1 − p_l)·P(G) (Parameters §8.1, FROZEN)."""
    value = p_l * (1.0 - p_s) + (1.0 - p_l) * p_g
    return _clamp01(value)


def bkt_posterior(p_l: float, correct: bool, p_g: float, p_s: float) -> float:
    """Bayesian posterior p(L|obs), *before* the P(T) transition (Parameters §8.1, FROZEN).

    correct:   p_l·(1−P(S)) / [ p_l·(1−P(S)) + (1−p_l)·P(G) ]
    incorrect: p_l·P(S)     / [ p_l·P(S)     + (1−p_l)·(1−P(G)) ]

    A timeout is treated as an incorrect first attempt by the caller (``correct=False``); this
    function itself has no timeout branch. Denominators are guarded against division by ~0 for
    boundary priors (p_l == 0 or p_l == 1) even though they are strictly positive whenever
    0 < P(G) < 1 and 0 < P(S) < 1.
    """
    if correct:
        numerator = p_l * (1.0 - p_s)
        denominator = numerator + (1.0 - p_l) * p_g
    else:
        numerator = p_l * p_s
        denominator = numerator + (1.0 - p_l) * (1.0 - p_g)

    if denominator <= _EPS:
        return _clamp01(p_l)

    return _clamp01(numerator / denominator)


def bkt_update(p_l: float, correct: bool, p_g: float, p_s: float, p_t: float) -> float:
    """Next-step mastery p(L)_next (Parameters §8.1, FROZEN; no forgetting term).

    Two explicit stages:
      1. posterior = bkt_posterior(p_l, correct, p_g, p_s)   # pre-P(T)
      2. p(L)_next = posterior + (1 − posterior)·P(T)        # transition (estimator-only P(T))

    Returns an estimate only — never the hidden simulation truth.
    """
    posterior = bkt_posterior(p_l, correct, p_g, p_s)
    next_p_l = posterior + (1.0 - posterior) * p_t
    return _clamp01(next_p_l)
