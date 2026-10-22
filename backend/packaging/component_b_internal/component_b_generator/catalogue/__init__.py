"""Authoritative Component B item-catalogue loading (read-only)."""

from __future__ import annotations

from .loader import (
    DEFAULT_CATALOGUE_PATH,
    SEVEN_SKILLS,
    CatalogueValidationError,
    load_catalogue,
    normalize_grade_scope,
)

__all__ = [
    "load_catalogue",
    "normalize_grade_scope",
    "CatalogueValidationError",
    "DEFAULT_CATALOGUE_PATH",
    "SEVEN_SKILLS",
]
