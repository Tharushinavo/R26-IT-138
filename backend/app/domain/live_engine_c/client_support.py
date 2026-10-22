"""Templates the app cannot draw, and therefore must never be asked to (2026-09-28).

THE PROBLEM. Three of Component C's thirty templates have no renderable surface in the app. When
the engine selects one, the child gets "This one isn't ready" with a support code -- a dead end in
the middle of a game, for a task that was never going to work. The owner's instruction is that the
backend should not serve these at all: reject them at selection and pick something else.

THIS IS A CLIENT-CAPABILITY CONSTRAINT, NOT A SCIENTIFIC ONE. Nothing here says these tasks are
pedagogically wrong, too hard, or badly designed. It says the app has no screen for them. That
distinction matters for how this is read later: the exclusions are provisional in principle (ship a
surface and the entry goes away) even where the refusal behind them is permanent in practice, and
they narrow the pool the adaptive selector chooses from, which is a real effect on what a child
meets. Serving a guaranteed dead end is worse, but it is not nothing, and it belongs in the record
rather than in a silent filter.

WHY EACH ONE. The app's refusals are structural, decided by its own pure resolvers, and two of the
three exist to protect the answer rather than for want of effort:

  * ``C-SF-02`` -- the child must form equal groups, but the template declares no bin-count payload
    key: the NUMBER OF GROUPS *is* the answer. No fixed-slot scene can show the bins without
    showing the answer. Refusal ruled PERMANENT on 2026-08-26.
  * ``C-TC-02`` -- "how many more or how many fewer" resolves against ``value-report``, which
    refuses it rather than mount a partial scene.
  * ``C-CC-04`` -- before/after conservation resolves against ``option-select``, which refuses it
    for the same reason.

KEEPING THIS HONEST. The list is the app's behaviour written down, not a second opinion about it.
``frontend/src/api/__tests__/c-unrenderable-templates.test.ts`` runs every frozen exemplar through
the app's real resolvers and asserts the unrenderable set is EXACTLY these three, so shipping a
surface fails that test and points here; ``tests/test_c_client_support.py`` asserts every id here
is a real template and that the remaining pool is large enough to select from. Neither side can
drift quietly.
"""

from __future__ import annotations

from typing import Mapping


#: Template id -> why the app cannot draw it. The mapping carries the reason so this is a record
#: rather than a bare denylist; only the keys are used at selection time.
CLIENT_UNRENDERABLE_TEMPLATE_IDS: Mapping[str, str] = {
    "C-CC-04": "option-select refuses the before/after conservation scene",
    "C-SF-02": "bin count is the answer; no fixed-slot scene can show it without leaking it (permanent, 2026-08-26)",
    "C-TC-02": "value-report refuses the how-many-more/fewer scene",
}

#: Below this, an exclusion has gone wrong -- a typo in an id, or a wheel that changed its template
#: set -- and the selector would be choosing from a pool too small to adapt over. Deliberately a
#: floor to trip on, not a target: the real pool is 27 of 30 today.
MINIMUM_SELECTABLE_TEMPLATES = 20


def selectable_template_ids(supported: tuple[str, ...]) -> tuple[str, ...]:
    """``supported`` minus the templates the app cannot draw, order preserved.

    Order is preserved because the engine's own selection is seeded and deterministic; re-ordering
    the pool would change which task a given seed produces, which is not this function's business.
    """
    return tuple(template_id for template_id in supported if template_id not in CLIENT_UNRENDERABLE_TEMPLATE_IDS)
