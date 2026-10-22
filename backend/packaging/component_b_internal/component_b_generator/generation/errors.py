"""Phase-B2A generation errors."""

from __future__ import annotations


class UnsupportedTemplateError(ValueError):
    """Raised when a task instance is requested for a template that has no implemented
    Phase-B2A sampler/answer/distractor strategy. Phase B2A never fabricates placeholder
    mathematical content for an unsupported template."""


class TaskInstanceValidationError(ValueError):
    """Raised when a generated (or supplied) task instance violates a hard mathematical or
    catalogue-constraint guard (SPEC §8; catalogue §8/§12)."""


class DistractorGenerationError(ValueError):
    """Raised when the required number of distinct, valid, correct-excluded distractor
    candidates cannot be generated for a template (Phase B2A.2 distractor-count policy).
    Phase B2A.2 never silently returns fewer distractors than required."""
