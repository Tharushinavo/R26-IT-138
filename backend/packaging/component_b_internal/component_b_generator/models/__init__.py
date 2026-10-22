"""Typed internal models for the reviewed live-safe closure.

PACKAGING NOTE (upadya-component-b-live-engine): intentionally minimal — unlike the pinned
Yass source's ``component_b_generator/models/__init__.py``, this file re-exports nothing.
Every module in this package imports the specific submodule it needs (for example
``from ..models.catalogue import ItemTemplate``), so no caller relies on package-level
re-exports. Avoiding eager re-exports here means this package never has to import the
pinned source's excluded hidden-truth/synthetic-behaviour model classes (see
``component_b_generator/models/behaviour.py`` in this package for the reviewed subset that
is actually used).
"""

from __future__ import annotations
