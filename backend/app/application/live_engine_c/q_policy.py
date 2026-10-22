"""LIVE-01: the FROZEN, trained Q-learning difficulty policy (RL notebooks NB02/NB04) as a live proposer.

Q PROPOSES, SAFETY DISPOSES. This module only turns an observation into a proposed action; the pinned
hard-safety controller still decides what is applied (``LiveEngineCAdapter.decide_with_proposed_action``).
It imports nothing from ``component_c_generator`` (that stays the adapter's job) and does no learning: the
tables are read-only artifacts under ``provenance/c_policy/``, hash-checked against ``MANIFEST.json``.

FAIL CLOSED. A missing file, a missing manifest entry or a sha256 mismatch raises
``QPolicyArtifactError`` -- never a silent fallback to the rule policy. The error is a
``LiveEngineCError`` so the session-start path refuses the session (``ConflictError``) up front.

The bucket rules below are byte-for-byte the ones in ``component_c_rl/rl_core/agent.py``; the golden vectors
(``provenance/c_policy/golden_vectors.json``) pin the equivalence.

Simulation-only provenance: literature-informed synthetic data, not clinical evidence; not approved for
use with children beyond the live pilot scope recorded in
``provenance/component-c-q-policy-approval.json``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

from app.domain.live_engine_c.errors import LiveEngineCError

ACTIONS = ("decrease_difficulty", "hold", "increase_difficulty")      # also the tie-break order
UNKNOWN_MASTERY_BUCKET = 3
_FIRST_TRY_EDGES = (0.4, 0.7)
_STRAIN_EDGES = (0.3, 0.6)
_MASTERY_EDGES = (0.33, 0.66)
DEFAULT_FIRST_TRY = 0.5      # same default as rl_core.env when no attempt has been recorded yet

# backend/provenance/c_policy  (this file: backend/app/application/live_engine_c/q_policy.py)
C_POLICY_DIR = Path(__file__).resolve().parents[3] / "provenance" / "c_policy"
_ARTIFACT_NAME = {"c_only": "q_c_only", "combined": "q_main"}


class QPolicyArtifactError(LiveEngineCError):
    """The Q table is missing, unreadable, or its sha256 does not match MANIFEST.json."""


def _bucket(x: float, lo: float, hi: float) -> int:
    return 0 if x < lo else (1 if x < hi else 2)


def state_of(difficulty: int, first_try: float, strain: float, mastery: Optional[float]) -> tuple[int, int, int, int]:
    """(difficulty 1-5, first-try bucket, strain bucket, mastery bucket; 3 = unknown for ``mastery is None``)."""
    return (
        int(difficulty),
        _bucket(first_try, *_FIRST_TRY_EDGES),
        _bucket(strain, *_STRAIN_EDGES),
        UNKNOWN_MASTERY_BUCKET if mastery is None else _bucket(mastery, *_MASTERY_EDGES),
    )


def state_key(state: Sequence[int]) -> str:
    return ",".join(str(int(x)) for x in state)


@dataclass(frozen=True)
class QPolicy:
    session_mode: str
    policy_version: str
    parameter_source_status: str
    artifact_file: str
    artifact_sha256: str
    min_tasks: int
    q: Mapping[str, tuple[float, float, float]]

    def q_values(self, state: Sequence[int]) -> tuple[float, float, float]:
        return self.q.get(state_key(state), (0.0, 0.0, 0.0))

    def propose(self, state: Sequence[int], allowed: Sequence[str], tasks_done: int) -> tuple[str, dict]:
        """"hold" while ``tasks_done < min_tasks`` (as in training); otherwise greedy over ``allowed`` with ties
        broken in the order decrease, hold, increase. Returns ``(action, rl_state)``; ``rl_state`` is the
        JSON-safe record persisted with the decision."""
        allowed_set = [a for a in ACTIONS if a in set(allowed)]
        if not allowed_set:
            raise ValueError("propose requires at least one allowed action")
        qv = self.q_values(state)
        if tasks_done < self.min_tasks:
            action = "hold"
        else:
            action = max(allowed_set, key=lambda a: (qv[ACTIONS.index(a)], -ACTIONS.index(a)))
        return action, {
            "state": state_key(state),
            "q_values": [float(x) for x in qv],
            "allowed": allowed_set,
            "artifact_file": self.artifact_file,
            "artifact_sha256": self.artifact_sha256,
        }


_CACHE: dict[tuple[str, str], QPolicy] = {}


def clear_cache() -> None:
    _CACHE.clear()


def load_q_policy(session_mode: str, *, directory: Optional[Path] = None) -> QPolicy:
    """Loads (and caches after the first success) the table for ``session_mode`` ("c_only" or "combined"),
    verifying its sha256 against ``MANIFEST.json``. Raises ``QPolicyArtifactError`` on any problem."""
    base = Path(directory) if directory is not None else C_POLICY_DIR
    cache_key = (session_mode, str(base))
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    name = _ARTIFACT_NAME.get(session_mode)
    if name is None:
        raise QPolicyArtifactError(f"no Q policy for session_mode {session_mode!r}")
    try:
        manifest = json.loads((base / "MANIFEST.json").read_bytes())
        entry = manifest["artifacts"][name]
        raw = (base / entry["file"]).read_bytes()
    except (OSError, ValueError, KeyError) as exc:
        raise QPolicyArtifactError(f"Q policy artifact {name!r} unavailable: {type(exc).__name__}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != entry.get("sha256"):
        raise QPolicyArtifactError(f"Q policy artifact {name!r} sha256 mismatch (file does not match MANIFEST.json)")
    try:
        art = json.loads(raw)
        if art["session_mode"] != session_mode or art["actions"] != list(ACTIONS):
            raise ValueError("artifact does not match the requested session mode / action order")
        q = {k: tuple(float(x) for x in v) for k, v in art["q"].items()}
        if any(len(v) != 3 for v in q.values()):
            raise ValueError("Q rows must have 3 values")
        policy = QPolicy(
            session_mode=session_mode,
            policy_version=str(art["policy_version"]),
            parameter_source_status=str(entry["parameter_source_status"]),
            artifact_file=entry["file"],
            artifact_sha256=digest,
            min_tasks=int(art["min_tasks"]),
            q=q,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise QPolicyArtifactError(f"Q policy artifact {name!r} malformed: {type(exc).__name__}") from exc
    _CACHE[cache_key] = policy
    return policy
