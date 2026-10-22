"""Stable internal/application errors for the live-engine adapter (BE3.2).

The adapter never lets a package-internal exception type (``CatalogueValidationError``,
``UnsupportedTemplateError``, ``TaskInstanceValidationError``, ``HintContentError``,
``DistractorGenerationError``, ...) cross into ``app.application``/``app.api``. Every failure
from the vendored package is translated into one of these instead.
"""

from __future__ import annotations


class LiveEngineError(Exception):
    """Base type for every stable error raised by the live-engine adapter."""


class CatalogueUnavailableError(LiveEngineError):
    """The governed catalogue could not be loaded or failed a load-time invariant."""


class UnknownTemplateError(LiveEngineError):
    """A referenced ``item_template_id`` does not exist in the loaded catalogue."""


class TemplateNotActiveError(LiveEngineError):
    """A template is not active for the requested grade (unsupported, ineligible, retired,
    deferred, or an unrecognized/calibration-restricted catalogue status)."""


class TaskConstructionError(LiveEngineError):
    """Deterministic task-instance construction failed a hard guard or validation rule."""


class AnswerRuleUnavailableError(LiveEngineError):
    """No correct-answer rule is registered for the requested template."""


class DistractorConstructionError(LiveEngineError):
    """The required number of distinct distractors could not be constructed."""


class HintUnavailableError(LiveEngineError):
    """Governed L1/L2/L3 hint content is missing, blank, or the level/template is unknown.

    Fail-closed: callers must never substitute generated or paraphrased content for this.
    """
