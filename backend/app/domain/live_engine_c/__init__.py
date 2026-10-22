"""Domain-owned ports and types for the Component C live-engine adapter (Phase 1 batch 1b).

Nothing under ``app.domain`` imports the vendored ``component_c_generator`` package, any of its
Pydantic models, or ``models.contracts`` (the frozen B<->C boundary contract Component C
consumes but must not re-declare — Component_C_Master_Build_Plan_v3.0 §5). Only backend-owned
dataclasses and ``Protocol`` interfaces live here; the concrete binding to the package lives in
``app.infrastructure.live_engine_c``.
"""
