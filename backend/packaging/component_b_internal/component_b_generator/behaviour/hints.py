"""Phase B2B.3.1 — deterministic catalogue hint exposure + provenance (SPEC correction 3).

Pure catalogue lookup only: L1/L2/L3 hint text is authored directly in the item catalogue
(``item_sets[*].hint_level_1/2/3``, parsed additively onto :class:`ItemTemplate` by
``catalogue.loader``). ``get_catalogue_hint`` does nothing but read that already-loaded,
already-validated field and wrap it with checksum provenance. There is no LLM call, no
network/API request, and no free-text generation path anywhere in this module — a missing or
blank catalogue hint fails closed (``HintContentError``) rather than falling back to any
generated content.

Reconstruction key: ``(item_template_id, hint_level, catalogue_version, catalogue_checksum)``
(SPEC correction 3 — the free-text ``catalogue_version`` alone is not guaranteed unique, so the
SHA-256 ``catalogue_checksum`` from ``catalogue.loader.catalogue_file_checksum`` is required).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..models.behaviour import HINT_LEVELS
from ..models.catalogue import LoadedCatalogue

B2B_HINT_LOOKUP_VERSION = "b2b3-1.0.0"

_HINT_FIELD_BY_LEVEL = {1: "hint_level_1", 2: "hint_level_2", 3: "hint_level_3"}


class HintContentError(ValueError):
    """Raised (fail-closed) for an unknown template, an out-of-range level, or missing/blank
    catalogue hint content. This is the only outcome for a hint that cannot be produced — there
    is no generated-content fallback."""


class CatalogueHintReference(BaseModel):
    """Deterministic, reconstructable reference to one catalogue-authored hint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_template_id: str
    hint_level: int = Field(ge=1, le=3)
    content: str
    content_id: str
    catalogue_version: str
    catalogue_checksum: str


def get_catalogue_hint(
    catalogue: LoadedCatalogue,
    catalogue_checksum: str,
    item_template_id: str,
    hint_level: int,
) -> CatalogueHintReference:
    """Deterministic catalogue-only hint lookup for one ``(item_template_id, hint_level)``.

    No LLM, no network/API call, no generated text: this function only reads the field already
    parsed onto the caller-supplied ``catalogue`` and reports it back with provenance. Fails
    closed (``HintContentError``) rather than inventing content.
    """
    if hint_level not in HINT_LEVELS:
        raise HintContentError(f"hint_level must be one of {HINT_LEVELS}, got {hint_level!r}")

    template = catalogue.by_id(item_template_id)
    if template is None:
        raise HintContentError(f"unknown item_template_id: {item_template_id!r}")

    field_name = _HINT_FIELD_BY_LEVEL[hint_level]
    content = getattr(template, field_name, None)
    if content is None or not str(content).strip():
        raise HintContentError(
            f"missing/empty {field_name} for template {item_template_id!r} "
            "— fail-closed, no generated fallback"
        )

    return CatalogueHintReference(
        item_template_id=item_template_id,
        hint_level=hint_level,
        content=str(content),
        content_id=f"{item_template_id}::hint_l{hint_level}",
        catalogue_version=catalogue.catalogue_version,
        catalogue_checksum=catalogue_checksum,
    )
