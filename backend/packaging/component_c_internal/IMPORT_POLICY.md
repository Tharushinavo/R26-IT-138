# Component C research-generator and live-engine policy

## Full research generator classification

The complete Yass `component_c_generator` tree at the pinned commit (including `pipeline.pilot`,
`pipeline.pilot_cohort`, `pipeline.session`, `audits/*`, and the synthetic-behaviour modules under
`behaviour/`) is research/reproduction source only. It must not be installed in an Upadya
application image, imported by the application, or treated as an application runtime dependency.

## Architecture boundary

1. Yass owns synthetic dataset generation, offline pilots, and research audits.
2. Upadya owns real learners, real sessions, server-side telemetry validation, persistence, policy
   and safety state, scaffolds, and rewards.
3. Upadya may reuse only existing deterministic live-safe scientific functions through a reviewed
   adapter; mathematical formulas must not be copied or rewritten.
4. Upadya must never import or execute synthetic/offline/pilot/audit modules.
5. The full research-generator tree is not vendored by this package beyond its reviewed live-safe
   subset.

## Never-ship modules (16, per Component_C_Master_Build_Plan_v3.0 §6.1, plus C-22/DEC-1)

Explicitly excluded from `prabathi-component-c-live-engine` by omission — unreachable by
construction, not merely unimported:

```
component_c_generator.behaviour.action_provider
component_c_generator.behaviour.attempt_loop
component_c_generator.behaviour.decisions
component_c_generator.behaviour.latency
component_c_generator.behaviour.outcome_model
component_c_generator.behaviour.seeds
component_c_generator.pipeline.session
component_c_generator.pipeline.pilot
component_c_generator.pipeline.pilot_cohort
component_c_generator.audits            (and all audits/* submodules)
component_c_generator.audits.c_to_3_audit
component_c_generator.audits.coverage
component_c_generator.audits.determinism
component_c_generator.audits.leakage
component_c_generator.audits.population_neutrality
component_c_generator.c_to_3.emit        (C-22 / DEC-1 -- see below)
```

`component_c_generator.pipeline.session_state` ships **trimmed**: it retains only
`CLearnerSessionState` and `is_eligible_combined_handoff` for use, and no longer binds
`run_c_session` in its namespace (see the in-file PACKAGING NOTE and
`backend/provenance/component-c-live-engine-manifest.json`).

## C-22 / DEC-1 — `c_to_3/emit.py` is omitted; `validators/` is not vendored

At the pin, `c_to_3/emit.py` is the only shipped-list file that imports a top-level package
neither this wheel nor `upadya-component-b-live-engine` provides: `validators.contract_validators`
(`validate_payload`, `validate_payload_against_mapping`). `validators/` is genuinely shared, not
C-specific — its `PayloadKind` literal includes `"b_to_c"` and `"b_to_3"` alongside `"c_to_3"`, so
it validates B's payloads too. Vendoring it into this wheel would make Component C the owner of a
package that also governs Component B's contracts, creating a circular/duplicated-ownership
problem the moment B ships its own `adapters/*` closure. The owner resolved this by omitting
`c_to_3/emit.py` from Phase 1 rather than vendoring `validators/`. Consequence: this wheel does not
provide `NoRealCSessionError` or `emit_c_to_3`; `Component_C_Master_Build_Plan_v3.0` §11 Phase 9
names `emit_c_to_3`/`NoRealCSessionError` in its acceptance criteria, so a Phase 9 rebuild and
re-pin of this wheel (or an extraction of a third, shared wheel owning `models/` + `validators/` +
`schemas/`) is **scheduled**, not merely possible. `c_to_3/__init__.py`, `c_to_3/adapter.py`, and
`c_to_3/inputs.py` ship unmodified; none of the three imports `validators`.

`component_b_generator`'s own manifest (`backend/provenance/component-b-live-engine-manifest.json`,
`excluded_by_omission.modules`) separately lists `"validators (and validators/*)"` as excluded from
B's wheel. That exclusion was scoped to B's own reviewed capability closure at BE3/BF-4 and predates
this decision. C's omission of `c_to_3/emit.py` (and, with it, the only C-side need for
`validators/`) is an independent decision reached for the ownership reason above — a later reader
should not read either omission as drift from the other.

## Vendoring boundary

- This package vendors **no `models/`**. `models/contracts.py` is byte-identical in
  `upadya-component-b-live-engine`, which is this package's sole `models` provider (a declared
  `pyproject.toml` dependency, pinned at the same commit).
- This package vendors **no `validators/`** (C-22 / DEC-1 above).
- `top_level.txt` for this wheel is `component_c_generator` only.

## Vendor-prefix split — deliberate

`upadya-component-b-live-engine` keeps the `upadya-` prefix; this package uses `prabathi-`
(Component_C_Master_Build_Plan_v3.0 §12.1 item 5 — attributes C's engine to C's owner, Prabathi /
Alwis L.P.M., IT22117878). The two coupled wheels carrying different vendor prefixes is deliberate,
not drift.

## Future integration

Component C's Phase 1 batch 1b adds one reviewed import boundary,
`app/infrastructure/live_engine_c/adapter.py`, enforced by a full-dotted-path AST architecture
guard extension and a per-module `ModuleNotFoundError` test suite — mirrored from
`backend/tests/test_be3_live_engine_boundary.py` and `backend/tests/test_be2_architecture_guards.py`.
Batch 1a (this package) wires no application code and is imported by nothing under `app/`.
