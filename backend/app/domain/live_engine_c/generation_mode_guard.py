"""Component C Phase 2: the X-8 generation-config smoke-mode guard.

NEW AND UNWIRED (R2, explicit): built and unit-tested this batch; it is NOT on any call path.
Nothing in this codebase invokes real task/instance generation yet --
``component_c_generator.generation.build_task_instance`` is Phase 5 orchestration, which this
batch does not build. Wiring this guard into that real call path is Phase 5's job. This module
does not enforce anything today; it only makes the enforcement possible once a caller exists.

WHY THIS EXISTS. ``component_c_generator.generation_config.CGenerationConfig.parameter_source_status``
is a plain, unconstrained ``str`` at the package level -- verified by reading the package source:
its only validator (``_non_empty``) checks the string is non-blank, nothing more. The package
itself never refuses to let a ``TEST_FIXTURE_ONLY``/``SMOKE_ONLY``-tagged config be used for real
generation; that enforcement is backend-owned, per X-8
("TEST_FIXTURE_ONLY parameters rejected outside smoke mode, and the rejection asserted to
fire"). This is a DIFFERENT mechanism from the bundle-level approval gate
(``CRuntimeBundleLoader.load_and_validate``'s ``require_approved``): that one governs whether a
whole *bundle* may activate; this one governs whether a specific *generation config* may be used
outside smoke/test contexts, independent of which bundle it arrived attached to.
"""

from __future__ import annotations

from app.domain.live_engine_c.types import GenerationConfig

DISALLOWED_OUTSIDE_SMOKE_MODE = frozenset({"TEST_FIXTURE_ONLY", "SMOKE_ONLY"})


class GenerationConfigNotPermittedError(ValueError):
    """Raised when a TEST_FIXTURE_ONLY/SMOKE_ONLY-tagged generation config is used outside
    smoke mode."""


def assert_generation_config_permitted(config: GenerationConfig, *, smoke_mode: bool) -> None:
    """Fails closed: raises unless either the config's ``parameter_source_status`` is outside
    the disallowed set, or the caller has explicitly opted into ``smoke_mode=True``."""
    if not smoke_mode and config.parameter_source_status in DISALLOWED_OUTSIDE_SMOKE_MODE:
        raise GenerationConfigNotPermittedError(
            f"generation config parameter_source_status={config.parameter_source_status!r} "
            "is not permitted outside smoke_mode=True"
        )
