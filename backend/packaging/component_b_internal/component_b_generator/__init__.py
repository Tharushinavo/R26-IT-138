"""Component B item-level statistical generator — Phase B1.

Implements `Component_B_Generator_v1.0/SPEC.md` incrementally. Phase B1 provides
package structure, typed internal models, read-only config loading, item-catalogue
loading + validation, a deterministic hierarchical seed manager, minimal cohort
initialization, and minimal grade-gated `b_item_opportunities` generation.

SF-039 (binding): `population` / `dd_subtype` are audit-only. No runtime code path
branches on them; no dictionary keyed by TD/MLD/DD selects runtime behaviour. Learner
behaviour is driven by learner-level latent/configuration placeholders whose exact
distributions are ``CALIBRATION_PENDING`` and will be supplied in a later phase.

This package is executable code and lives under ``Implementation_v1.0/``. The folder
``Component_B_Generator_v1.0/`` remains specification-only.
"""

from __future__ import annotations

PHASE = "B1"
CATALOGUE_VERSION = "1.0"
GENERATOR_PACKAGE_VERSION = "0.1.0-phase-b1"

__all__ = ["PHASE", "CATALOGUE_VERSION", "GENERATOR_PACKAGE_VERSION"]
