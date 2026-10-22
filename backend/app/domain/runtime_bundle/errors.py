"""Fail-closed runtime-bundle errors (BEplan §BE0.6/§BE3.1).

Every one of these must make readiness/startup fail. None of them may be caught and silently
replaced with a fallback bundle or a default value — see
``backend/provenance/runtime-bundle.schema.json``'s ``x-runtime-invariants``.
"""

from __future__ import annotations


class RuntimeBundleError(Exception):
    """Base type for every fail-closed runtime-bundle loading/validation failure."""


class RuntimeBundleNotFoundError(RuntimeBundleError):
    """The bundle manifest file (or the referenced schema file) does not exist."""


class RuntimeBundleValidationError(RuntimeBundleError):
    """The manifest is not valid JSON, or fails schema validation (missing required field,
    wrong type, an unrecognized ``additionalProperties``, a violated ``const``/``enum``)."""


class RuntimeBundleChecksumMismatchError(RuntimeBundleError):
    """A declared artifact checksum does not match the referenced file's actual SHA-256."""


class RuntimeBundleNotApprovedError(RuntimeBundleError):
    """The bundle's ``approval_status`` is absent or is not ``APPROVED``.

    Raised whenever the caller asks for an activation-ready bundle (``require_approved=True``,
    the default). BE3b never marks a bundle ``APPROVED`` and never suppresses this error —
    approval is the separate BE4 governance gate.
    """
