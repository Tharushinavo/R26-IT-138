"""Cross-checks a loaded ``RuntimeBundle`` against the catalogue actually in hand (BE3.4).

``RuntimeBundleLoader.load_and_validate`` (BE3b) proves the manifest is internally
well-formed and every artifact it points at matches its own declared checksum. It does not
know about any particular ``Catalogue`` object the caller went on to load. This module closes
that gap: given the bundle and the catalogue an adapter call actually loaded, it fails closed
the moment the two disagree, rather than silently proceeding on a runtime bundle whose
declared catalogue no longer matches reality (a stale pin, a swapped file, a partial load).
"""

from __future__ import annotations

from app.domain.live_engine.types import Catalogue

from .errors import RuntimeBundleValidationError
from .types import RuntimeBundle


def assert_catalogue_matches_bundle(bundle: RuntimeBundle, catalogue: Catalogue, catalogue_checksum: str) -> None:
    """Raise ``RuntimeBundleValidationError`` if ``catalogue`` is not the exact artifact the
    bundle declares. Never returns a "readiness" verdict other than pass/raise — there is no
    partial-match or best-effort fallback path."""
    if catalogue_checksum != bundle.catalogue.checksum.value:
        raise RuntimeBundleValidationError(
            f"catalogue checksum mismatch: bundle {bundle.bundle_version!r} declares "
            f"{bundle.catalogue.checksum.value!r}, loaded catalogue checksum is {catalogue_checksum!r}"
        )
    if catalogue.catalogue_version != bundle.catalogue.version:
        raise RuntimeBundleValidationError(
            f"catalogue version mismatch: bundle {bundle.bundle_version!r} declares "
            f"{bundle.catalogue.version!r}, loaded catalogue version is {catalogue.catalogue_version!r}"
        )
    if len(catalogue.templates) != bundle.compatibility.required_catalogue_template_count:
        raise RuntimeBundleValidationError(
            f"catalogue template count mismatch: bundle {bundle.bundle_version!r} requires "
            f"{bundle.compatibility.required_catalogue_template_count}, loaded catalogue has "
            f"{len(catalogue.templates)}"
        )
    if set(catalogue.skills) != set(bundle.compatibility.skills):
        raise RuntimeBundleValidationError(
            f"catalogue skills mismatch: bundle {bundle.bundle_version!r} declares "
            f"{bundle.compatibility.skills!r}, loaded catalogue skills are {catalogue.skills!r}"
        )
