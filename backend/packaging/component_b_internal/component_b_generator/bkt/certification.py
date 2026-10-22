"""Estimated -> certified mastery decision (Phase B3.4).

Resolved human decision (SPEC §A.5): certification is **withheld** on thin timing evidence. A
skill is certified only when the BKT mastery estimate exceeds the global threshold ``theta_B``
AND the Guess-Guard has run (at least ``n_min`` valid timing observations, SPEC §B3.3) and
cleared (``NOT_TRIGGERED``). Both ``TRIGGERED`` and ``INSUFFICIENT_EVIDENCE`` block certification.

Certification is **not sticky**: this module has no persisted "once-certified" flag. It is a pure
function of the current mastery estimate and current guard status, recomputed on every
evaluation, so a skill that was certified at one evaluation is silently de-certified the moment
either input no longer satisfies the rule.

``certified_<skill>`` is a B->3 field only (enforced in B5's per-edge allow-list); this module
does not touch adapters/contracts and adds no B->C path.
"""

from __future__ import annotations

from .guess_guard import GuessGuardStatus


def certify_skill(p_l: float, guard_status: GuessGuardStatus, theta_B: float) -> bool:
    """Pure certification decision (SPEC §A.5, FROZEN/resolved rule).

    ``certified = (p_l > theta_B) AND (guard_status == GuessGuardStatus.NOT_TRIGGERED)``.

    ``theta_B`` is always supplied by the caller (``config.theta_B``) -- never hard-coded here.
    Both ``TRIGGERED`` and ``INSUFFICIENT_EVIDENCE`` yield ``False``: a guard that has not run
    enough valid-timing observations to clear never certifies (no single-lucky certification),
    and a guard that has run and flagged implausibly-fast responses never certifies either.

    Not sticky: call this again with a later ``p_l`` / ``guard_status`` and a previously-``True``
    result becomes ``False`` the moment either input no longer satisfies the rule -- there is no
    persisted state here for a caller to accidentally treat as "once certified, always certified".
    """
    return p_l > theta_B and guard_status == GuessGuardStatus.NOT_TRIGGERED
