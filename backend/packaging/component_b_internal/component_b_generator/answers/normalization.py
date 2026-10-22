"""Answer normalization — canonical single source of truth.

The authoritative normalizer lives in :mod:`component_b_generator.answers.rules`
(:func:`normalize_answer` / :func:`answers_equivalent`). This module re-exports it so callers
have a stable ``answers.normalization`` import path without introducing a second, divergent
normalizer.
"""

from __future__ import annotations

from .rules import answers_equivalent, normalize_answer

__all__ = ["normalize_answer", "answers_equivalent"]
