"""Domain-owned ports and types for the Component B live-engine adapter (BE3).

Nothing under ``app.domain`` imports the vendored ``component_b_generator`` package or any of
its Pydantic models. Only backend-owned dataclasses and ``Protocol`` interfaces live here; the
concrete binding to the package lives in ``app.infrastructure.live_engine``.
"""
