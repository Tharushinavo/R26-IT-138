# Component B research-wheel and live-engine policy

## Full wheel classification

The existing `upadya-component-b-generator` wheel is classified:

`BE0_RESEARCH_REPRODUCIBILITY_ARTIFACT_ONLY`

It preserves the complete Yass research generator for offline reproduction. It must not be
installed in an Upadya application image, imported by the application, or treated as an application
runtime dependency. Its inclusion of synthetic learner generation, simulated responses/latency,
cohort construction, pipeline, pilot, and audit code is intentional only for research reproduction.

## Architecture boundary

1. Yass owns synthetic dataset generation and offline research experiments.
2. Upadya owns real learners, real attempts, server timing, persistence, BKT state, hints,
   sequencing, and progress.
3. Upadya may reuse only existing deterministic live-safe scientific functions through a reviewed
   adapter; mathematical formulas must not be copied or rewritten.
4. Upadya must never import or execute synthetic/offline modules.
5. The full research-generator wheel is not an application runtime dependency.

Explicitly prohibited in the application are `cohort/*`, hidden learner truth, synthetic learner
traits, `behaviour.first_attempt`, `behaviour.latency`, `behaviour.attempt_loop`, `pipeline.py`,
`pilot.py`, synthetic audits, dataset-generation entry points, experiment runners, simulated
answers, and simulated timing.

## Future BE3 integration

The preferred BE3 approach is a new minimal package named `upadya-component-b-live-engine`. It may
contain only the reviewed live-safe dependency closure and required shared models/validators. It is
not built in BE0 or BE1. The exact source-level inventory is recorded in
`backend/provenance/component-b-live-engine-reuse-map.json`.

Infrastructure-only BE1 imports no Component B engine code. BE3 must add architecture tests that
fail on prohibited imports before any application adapter is accepted.
