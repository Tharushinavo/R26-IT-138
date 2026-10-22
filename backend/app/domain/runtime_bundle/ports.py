"""Runtime-bundle loading and validation port (BE3.1 first port entry)."""

from __future__ import annotations

from typing import Mapping, Optional, Protocol

from .types import RuntimeBundle


class RuntimeBundleLoaderPort(Protocol):
    """Load a runtime-bundle manifest and fail closed on any defect.

    Never returns a partial or best-effort bundle: any missing required field, schema
    mismatch, checksum mismatch, or (when ``require_approved``) unapproved/absent
    ``approval_status`` raises instead of returning.
    """

    def load_and_validate(
        self,
        bundle_path: str,
        schema_path: str,
        *,
        artifact_paths: Optional[Mapping[str, str]] = None,
        require_approved: bool = True,
    ) -> RuntimeBundle: ...
