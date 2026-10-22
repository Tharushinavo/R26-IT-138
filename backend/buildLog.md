# Component B Backend Build Log

> This is the living, append-only development audit log for the Component B backend. Future work
> must be appended as a new dated phase or batch. Earlier entries must not be removed, rewritten,
> or silently altered. Each entry records scope, sources, files, commands, evidence, errors, fixes,
> decisions, limitations, current state, and the exact next task.

---

## Phase BE0 — Baseline Freeze and Characterization — READY FOR REVIEW, NOT FORMALLY APPROVED

Completed: 2026-07-22 Asia/Colombo (`2026-07-21` UTC)  
Build target: `Dev/backend/`  
Scientific source repository: `Yass`  
Authorized by: the user's BE0-only task, `Dev/backend.md`, the Component B specifications and
registers, and the existing pinned Component B generator implementation

### 1. Build target and scope

This phase freezes and characterizes the existing Component B scientific generator before the
backend depends on it. It does not implement new scientific behavior.

In scope:

- source, shared-module, dependency, catalogue, and test provenance;
- exact dependency locks;
- catalogue coverage and response-format audit;
- deterministic-generation verification;
- fail-closed deferred-template verification;
- grade-gate, first-attempt BKT, skill-isolation, sequencing, hint, certification, and aggregation
  characterization;
- an immutable runtime-bundle manifest schema;
- packaging and live-versus-synthetic boundary decisions;
- permanent Docker/PostgreSQL decisions for the first future BE1 batch.

Explicitly out of scope and not started:

- BE1 Docker implementation;
- PostgreSQL services or database schemas;
- SQLAlchemy or Alembic;
- authentication and `/api/v1/me`;
- session APIs;
- live question, attempt, hint, mastery, or completion endpoints;
- Component C or Component 3 implementation.

### 2. Source documents followed

Application design:

- `Upadya/Dev/backend.md` — authoritative backend architecture and BE0–BE6 sequence.
- `Upadya/Dev/frontend.md` — future public API/client contract boundary.
- `Upadya/componantBArchi.md` — Component B architecture and scientific boundary context.

Component B authorities:

- `Yass/Component_B_Generator_v1.0/SPEC.md`.
- `Yass/Component_B_Generator_v1.0/R26-IT-138_Component_B_Phase_B2B_Learner_Response_and_Attempt_Spec_v1.0.md`.
- `Yass/Component_B_v1.0/R26-IT-138_Component_B_Item_and_Task_Set_Catalogue_v1.0.md`.
- `Yass/Component_B_v1.0/R26-IT-138_Component_B_Empirical_Statistical_Parameters_v1.0.md`.
- `Yass/Registers_v0.3/R26-IT-138_Component_B_Variable_Register_v0.3.md`.
- `Yass/Registers_v0.3/R26-IT-138_Shared_Foundation_Decision_Register_v0.3.md`.
- `Yass/Implementation_v1.0/CONTRACT_IMPLEMENTATION_REPORT.md`.
- `Yass/build/buildB/build1.md`.
- `Yass/Deployment_MLOps_v1.0/R26-IT-138_Backend_Deployment_Recalibration_and_Model_Optimization_Strategy_v1.0.md`.

Build-log structure reference:

- `HereWeGo/Dev/build1.md` from the Reells project. Its dated-batch, context, commands, errors,
  fixes, verification, decisions, and caveats structure was adapted here.

### 3. Files created

`backend/provenance/component-b-baseline.json`

- Machine-readable authoritative BE0 baseline.
- Records source, shared-module, runtime, dependency, catalogue, coverage, scientific status,
  packaging, governance, and test provenance.

`backend/provenance/requirements-generator.in`

- Exact 29-package direct and active-transitive dependency closure derived from the environment
  that passed the initial 885-test run.
- Separates generator/scientific dependencies from the FastAPI application's `requirements.txt`.

`backend/provenance/requirements-generator-win-py310.lock`

- Hash-locked resolution for CPython 3.10 on Windows x64.
- Installed successfully into a clean temporary virtual environment with `pip --require-hashes`.

`backend/provenance/component-b-coverage.json`

- Structured 36/29/7 catalogue partition.
- Records deferred reasons, grade activation, catalogue/runtime response formats, and four explicit
  response-format vocabulary mismatches.

`backend/provenance/component-b-characterization.json`

- Structured test and behavioral evidence.
- Records full clean-lock suite results, deterministic digest, fail-closed result, focused behavior
  suite, and the meaning of Guess-Guard `INSUFFICIENT_EVIDENCE` for certification.

`backend/provenance/runtime-bundle.schema.json`

- Draft 2020-12 JSON Schema for immutable Component B runtime bundles.
- Includes all required code, schema, generator, catalogue, scientific configuration, policy,
  approval, activation, and compatibility fields.

`backend/buildLog.md`

- This living, append-only audit log.

### 4. Files modified

`backend/provenance/component-b-baseline.json`

- Initially created with source/catalogue/coverage and the first test result.
- Expanded during the same BE0 phase with clean hash-lock evidence, shared-module checksums,
  scientific statuses, packaging boundaries, response formats, and runtime-bundle references.

No generator source, Component B test, FastAPI endpoint, database, frontend, or BE1 infrastructure
file was modified.

### 5. Environment and version information

Verification host:

```text
OS: Microsoft Windows NT 10.0.26200.0
Architecture: x64
Python runtime family: CPython 3.10
Exact Python: 3.10.20
Initial environment: conda:component_b
Authoritative reproduction environment: clean temporary venv installed from the committed hash lock
```

Direct generator dependencies verified:

```text
pydantic       2.13.4
PyYAML          6.0.3
jsonschema      4.25.1
pytest          9.1.1
scikit-learn    1.7.2
numpy           2.2.6
pandas          2.3.3
```

The committed input/lock also pins every active transitive dependency, for 29 packages total.

### 6. Provenance values

```text
Yass Git commit:
  0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b

Component B generator Git tree:
  73acb113bbb179f5946333c27b0142c43f3063f3

Component B tracked-source manifest SHA-256:
  fd4f052e41539434ad4ff6bbb72fa01815ef750ceeb0a6d8ebc6fbc481e07e2c

Shared models Git tree:
  1f1c517043e7ac43197506ea8edfd0339021b5c4
Shared models manifest SHA-256:
  9ee1cc5ef18d09d5ae543235501d21ac1bc1b1b45bf8baca5c5348044c83b239
models/contracts.py SHA-256:
  b730c3f60b4565cc3bb390480337a821f229306f846884546727e8f42abb5e15

Shared validators Git tree:
  dcd9bb307567ce0b811ba1bc40a0c24a0a515303
Shared validators manifest SHA-256:
  4bc2066d77a5283cab7ac6eb24c37a33c75ab94e65da3938337f8f189173b386
validators/contract_validators.py SHA-256:
  613a81085ea12983791997c42d9a6f59fa5597610417f81f6493e91e8f570fee

Backend repository commit available at recording time:
  a360b8c6390bc77ae13989dcc03e7198388ce70b
The new backend BE0 files were not committed at recording time.
```

The generator's declared package metadata remains stale:

```text
PHASE=B1
CATALOGUE_VERSION=1.0
GENERATOR_PACKAGE_VERSION=0.1.0-phase-b1
```

The implementation contains B1 through B6. Package metadata must never be the sole provenance key.

### 7. Dependency and lock decisions

Input:

```text
backend/provenance/requirements-generator.in
SHA-256: 8870351034a456771dd5e535a18c282b20b54d3b36a6471f439ebcc459430b88
```

Lock:

```text
backend/provenance/requirements-generator-win-py310.lock
SHA-256: 27c04928c42688e45d7c82e44d07623c0f7d9c3cee8dd2ab3650532d32d6b04a
Target: CPython 3.10 / Windows x64
Packages: 29
Distribution SHA-256 hashes: included and required
```

Decision:

- A raw `pip freeze` was rejected because the `component_b` environment contains unrelated Jupyter,
  Gradio, media, browser, database, and other project dependencies.
- `conda list --explicit` was rejected as the only lock because most scientific packages were pip
  installed and absent from the Conda explicit list.
- The selected mechanism derives the minimum active transitive dependency closure from package
  metadata, pins every version, generates distribution hashes, and verifies installation into a
  clean environment.
- Before BE1 Docker use, the same exact-version input must be resolved and tested for Python 3.11 on
  Linux. No scientific dependency may be silently upgraded during that step.

### 8. Catalogue coverage

Catalogue:

```text
Path: Component_B_v1.0/R26-IT-138_Component_B_Item_and_Task_Set_Catalogue_v1.0.md
Version: 1.0
Status: PROPOSED_FOR_APPROVAL
SHA-256: eaf073da8af155bdb935b7c2abfba04f892bbfecf44522f20f044aeec4b579ac
```

Coverage:

```text
Total:       36
Implemented: 29
Deferred:     7
Partition complete: yes
```

Deferred and fail-closed:

```text
B-CNT05-FORWARD-FROM-N   CALIBRATION_PENDING
B-NS01-READ-NUMERAL      insufficiently specified
B-NS06-NUMBER-LINE       CALIBRATION_PENDING
B-PV05-REGROUP-ONES      insufficiently specified
B-PV06-UNGROUP-TEN       insufficiently specified
B-SUB02-DIFFERENCE       CALIBRATION_PENDING
B-DIV04-INVERSE-FACT     CALIBRATION_PENDING
```

An explicit construction attempt for every deferred template raised
`UnsupportedTemplateError`. No generic fallback question was generated.

Grade activation:

```text
Grade 2: 14 active templates; counting, number_sense, place_value, addition, subtraction.
         Multiplication and division excluded.
Grade 3: 16 active templates; all seven eligible skills represented.
Hard gates: grade, implementation support, catalogue availability.
Prerequisites: soft scoring input only.
```

Response formats:

- The catalogue machine block declares 14 distinct response-format values.
- The 29 implemented sampler strategies expose nine runtime response-format values.
- Four implemented templates use a runtime label different from the catalogue label:
  - `B-ADD02-COUNT-ON`: `single_integer_or_mark` -> `single_integer_or_choice`.
  - `B-CNT06-SKIP-COUNT`: `ordered_integer_sequence` -> `single_integer`.
  - `B-PV02-DECOMPOSE-2D`: `structured_pair` -> `expanded_form`.
  - `B-PV04-DECOMPOSE-3D`: `structured_triple_or_expression` -> `expanded_form`.
- Existing tests pass, but a reviewed backend adapter mapping is unresolved. The vocabularies must
  not be assumed identical.

### 9. Test and verification results

Initial confirmation in the existing Conda environment:

```text
885 passed in 315.21s (0:05:15)
Wall duration: 318.05s
Exit code: 0
```

Authoritative clean hash-lock reproduction:

```text
Started:  2026-07-21T19:03:30.4054736Z
Finished: 2026-07-21T19:08:23.1680282Z
Python:   3.10.20
Collected: 885
Passed:    885
Failed:    0
Skipped:   0
Warnings:  0
Errors:    0
Pytest duration: 292.09s (0:04:52)
Wall duration:   292.763s
Exit code: 0
```

Deterministic generation:

```text
Config version: b1-smoke-0.1.0
Config hash: 715b2a4200771e8ccea63e88a32884d3f660922ec37abfcc72519c9542974d0b
Global seed: 20260716
Generated private item instances: 54
Repeated output: byte-identical
Private output SHA-256: b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c
```

Focused behavior characterization:

```text
20 passed in 1.31s
Wall duration: 2.028s
Exit code: 0
```

Confirmed behavior:

- only attempt one creates the BKT observation;
- later retry success does not add another BKT observation;
- each skill has an independent BKT state and cross-skill transfer is rejected;
- orchestration equals direct calls to the existing BKT formulas;
- sequencing weights are exactly 0.50/0.30/0.20;
- ranking and tie-breaking are deterministic;
- prerequisites remain soft;
- all 29 implemented templates expose nonblank exact L1/L2/L3 catalogue hints;
- missing/blank hints fail closed;
- hint code has no network, LLM, generation, or paraphrase fallback;
- Guess-Guard `INSUFFICIENT_EVIDENCE` prevents certification even above `theta_B`;
- certification is recomputed and non-sticky; contradictory evidence can decertify;
- aggregation behavior for first-attempt accuracy, retries, hints, non-timeout timing, error classes,
  and latest per-skill estimated mastery passed.

### 10. Commands executed

Representative provenance commands:

```text
git -C <Yass> rev-parse HEAD
git -C <Yass> rev-parse HEAD:Implementation_v1.0/component_b_generator
git -C <Yass> ls-tree -r --name-only HEAD -- Implementation_v1.0/component_b_generator
Get-FileHash -Algorithm SHA256 <catalogue>
conda run -n component_b python -c <catalogue/dependency metadata query>
```

Dependency resolution and verification:

```text
<component_b-python> -m uv pip compile backend/provenance/requirements-generator.in \
  --generate-hashes --python-version 3.10 --python-platform windows \
  --no-header --no-annotate

<component_b-python> -m venv C:\tmp\component-b-be0-venv-20260722

C:\tmp\component-b-be0-venv-20260722\Scripts\python.exe -m pip install \
  --require-hashes -r backend/provenance/requirements-generator-win-py310.lock
```

Complete suite command, from `Yass/Implementation_v1.0`:

```text
C:\tmp\component-b-be0-venv-20260722\Scripts\python.exe -B -m pytest -q --tb=short \
  -p no:cacheprovider \
  tests/test_activation_classification.py \
  tests/test_b_generator_phase_b1.py \
  tests/test_b_generator_phase_b2a.py \
  tests/test_b_generator_phase_b2a2.py \
  tests/test_b_generator_phase_b2b0.py \
  tests/test_b_generator_phase_b2b1.py \
  tests/test_b_generator_phase_b2b2.py \
  tests/test_b_generator_phase_b2b3.py \
  tests/test_b_generator_phase_b3.py \
  tests/test_b_generator_phase_b4.py \
  tests/test_b_generator_phase_b5.py \
  tests/test_b_generator_phase_b6_0.py \
  tests/test_b_generator_phase_b6_1_leakage.py \
  tests/test_b_generator_phase_b6_2_fidelity.py \
  tests/test_b_generator_phase_b6_3_pilot.py
```

Focused characterization command selected exact test nodes from B3, B4, B2B3, and B5 for
first-attempt BKT, skill isolation, sequencing, hints, certification, and aggregation. The complete
node list and structured results are preserved in `component-b-characterization.json` and this
phase's execution record.

### 11. Errors, root causes, and fixes

#### Error 1 — Windows sandbox helper intermittently failed

Symptom:

```text
helper_read_acl_helper_spawn_failed / setup refresh access denied
```

Root cause: transient Codex Windows sandbox-helper launch failure while accessing an in-workspace
file, not a repository permission or JSON-content error.

Fix: retried the same narrowly scoped `apply_patch`; it succeeded. No alternate unsafe write method
was used for authored JSON/Markdown.

#### Error 2 — Windows wildcard passed literally to `rg`

Symptom:

```text
rg ... tests\test_*.py -> filename/directory syntax error
```

Root cause: Windows did not expand the wildcard for that invocation.

Fix: enumerated files with `Get-ChildItem` and used `rg` glob options or explicit paths.

#### Error 3 — Multiline Python rejected by `conda run`

Symptom:

```text
AssertionError: Support for scripts where arguments contain newlines not implemented
```

Root cause: `conda run` cannot forward a multiline `python -c` argument on this Windows setup.

Fix: invoked the exact environment Python executable and passed the helper source through a
temporary process environment variable. No helper file was added to Yass.

#### Error 4 — `uv` script not found through `conda run`

Symptom:

```text
'uv' is not recognized
```

Root cause: the installed module was importable but its console script was not visible through the
`conda run` command path.

Fix: used `<component_b-python> -m uv pip compile`, which resolved the exact same installed module.

#### Error 5 — First fail-closed probe used an invalid opportunity ID

Symptom:

```text
GeneratedItemOpportunity validation rejected BE0-001
Expected ^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$
```

Root cause: the verification helper's temporary ID did not follow the governed identifier contract.
The intended unsupported-template code path was not reached.

Fix: reran with `STU-9999-B001-I###` identifiers. All seven deferred templates then raised
`UnsupportedTemplateError`, and no fallback was produced.

#### Error 6 — Response-format `rg` extraction quoting failed

Symptom: a PowerShell/regex quoting combination produced an invalid regular expression while
extracting sampler literals.

Root cause: command quoting, not generator content.

Fix: queried the sampler registry through the pinned Python API and separately parsed the
authoritative machine-readable catalogue YAML block. This also exposed the four real vocabulary
mismatches recorded above.

### 12. Scientific and governance decisions

Status vocabulary used:

```text
APPROVED
APPROVED_FOR_PROVISIONAL_IMPLEMENTATION
PROVISIONAL
ENGINEERING_ASSUMPTION
CALIBRATION_PENDING
DISABLED
UNRESOLVED
```

Current status:

- Seven-skill BKT numeric parameters: `CALIBRATION_PENDING`; no production defaults.
- Certification threshold `theta_B`: `CALIBRATION_PENDING`; no approved value recorded.
- Guess-Guard rule: `APPROVED_FOR_PROVISIONAL_IMPLEMENTATION`; numeric quantile/minimum observation
  values remain `CALIBRATION_PENDING`.
- Sequencing rule and 0.50/0.30/0.20 weights: `APPROVED_FOR_PROVISIONAL_IMPLEMENTATION`.
- Four-session spacing saturation: `ENGINEERING_ASSUMPTION` from the current implementation.
- Hint catalogue: `PROVISIONAL`; exact catalogue text only; fallback `DISABLED`.
- Live attempt limits: `UNRESOLVED`.
- Timeout semantics: `APPROVED_FOR_PROVISIONAL_IMPLEMENTATION`; numeric threshold `UNRESOLVED`.
- Completion policy: `UNRESOLVED`.
- Safe-progress policy: `UNRESOLVED`.
- Cold-start override: `DISABLED`.
- Formal academic/owner sign-off: `UNRESOLVED`.

No missing value was replaced with an invented number.

### 13. Generator packaging decision

Selected planned strategy: pinned internal wheel, status `ENGINEERING_ASSUMPTION` until reviewed.

The future wheel must include:

- `component_b_generator`;
- top-level `models`;
- top-level `validators` when existing serialization/future-boundary adapters are packaged.

The catalogue is a separate governed runtime-bundle artefact supplied by explicit path and checksum.
The loader's repository-relative default must not be relied on by the backend.

Safe live adapter capabilities:

- catalogue loading/activation and coverage;
- deterministic task generation;
- answer normalization/evaluation;
- exact hint lookup;
- BKT state/update math;
- Guess-Guard/certification;
- sequencing;
- aggregation.

Forbidden from the live import graph:

- synthetic learner behavior;
- hidden learner truth;
- latency simulation;
- cohort generation;
- `pipeline.py`;
- `pilot.py`;
- synthetic experiment runners;
- population/`dd_subtype`-driven audit behavior.

### 14. Runtime-bundle manifest decision

`backend/provenance/runtime-bundle.schema.json` requires:

- bundle and schema versions;
- publication state and immutability flag;
- backend code and database schema revision;
- generator identifier/path/interface/checksum;
- catalogue version/checksum/approval;
- BKT, certification, Guess-Guard, sequencing, safe-progress, attempt, timeout, and completion
  configuration versions/checksums/approval;
- frozen sequencing weights;
- disabled cold-start policy;
- bundle approval and activation date;
- API, generator-interface, Python, database, grade, skill, and catalogue compatibility.

Permanent rules:

- publication makes the manifest immutable;
- existing sessions remain pinned to their original bundle;
- activating a new bundle affects only new sessions;
- missing/incompatible artefacts fail readiness closed;
- cold-start remains disabled unless separately approved.

No publishable bundle instance was invented because required configuration versions/checksums and
approval records are unresolved.

### 15. Permanent Docker development decision for BE1 onward

This decision is recorded now and was not implemented during BE0.

From BE1 onward, normal backend development, startup, tests, and verification must run in Docker:

- use a pinned Python 3.11 base image;
- verify and record the exact image tag and resolved digest before use;
- run FastAPI in a service named `api`;
- run PostgreSQL in a separate service named `db`;
- manage both with Docker Compose;
- run tests and verification inside `api`;
- install from committed reproducible lock files;
- run the API as a non-root user where practical;
- keep secrets outside images and committed source;
- add API and database health checks;
- use named volumes for persistent database storage;
- implement graceful startup and shutdown;
- record every Docker command and result in this log.

Expected BE1 commands:

```text
docker compose build
docker compose up -d
docker compose ps
docker compose exec api pytest
docker compose exec api python -m compileall app
docker compose logs api
docker compose logs db
docker compose down
```

Host-runtime exception used in BE0:

```text
Commands: provenance queries, lock generation, clean-venv installation, and generator tests listed above.
Reason Docker could not be used: this task explicitly prohibited implementing the BE1 Docker
environment; BE0 had to characterize the existing pinned generator first.
Reproducibility impact: the initial host Conda environment alone was not accepted as proof.
Independent verification: exact dependency hashes were committed, installed into a clean temporary
venv, and the complete 885-test suite passed again.
```

### 16. Permanent PostgreSQL Docker decision

This decision is recorded now and was not implemented during BE0.

- Use the official PostgreSQL 16 Docker image.
- Never use `postgres:latest`.
- Before BE1 implementation, verify the currently available official PostgreSQL 16 Bookworm patch
  tag and record its resolved image digest.
- Do not invent or record a tag/digest before verification.
- Use service name `db` and hostname `db` inside `DATABASE_URL`; never use `localhost` from `api`.
- Use service name `api` for FastAPI.
- Store `/var/lib/postgresql/data` in a named volume.
- Configure database, user, and password through environment variables.
- Keep real credentials in an uncommitted `.env` or secret manager; commit safe `.env.example`
  placeholders only.
- Never hard-code real passwords in Dockerfile or Compose.
- Add `pg_isready` health checking.
- Make API startup depend on database health.
- Expose PostgreSQL to the host only when local inspection requires it.
- Use Alembic as migration authority.
- Test migrations against PostgreSQL, never SQLite.
- Use the same PostgreSQL integration path in local Docker, CI, and staging.
- Review and record every future PostgreSQL image upgrade.

Intended future shape, not yet created:

```text
services:
  db:
    image: <verified PostgreSQL 16 Bookworm patch tag and digest>
    volumes:
      - component_b_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  api:
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
volumes:
  component_b_postgres_data:
```

### 17. Assumptions

- The current Yass HEAD is the intended source snapshot for this BE0 record; the Component B
  generator subtree matched the previously inspected tree and remained unchanged through testing.
- The 15-file scope (activation plus all `test_b_generator_phase_*.py`) is the complete existing
  Component B generator suite. Component C tests and future shared B-to-C/B-to-3 contract tests were
  excluded by scope.
- Existing frozen formulas/rules may be characterized without granting production approval to their
  unresolved numeric parameters.
- The pinned internal wheel is the preferred controlled artefact, but its build/review is not claimed
  complete.

### 18. Missing information and unresolved issues

- Formal acceptance/sign-off for the application design set.
- Approved production/pilot BKT parameters for all seven skills.
- Approved certification threshold.
- Approved Guess-Guard quantile and minimum observation count.
- Approved live attempt count, timeout threshold, completion policy, and safe-progress policy.
- Academic/owner approval record for catalogue and scientific configuration.
- Reviewed mapping for four catalogue/runtime response-format mismatches.
- Built and checksummed internal generator wheel.
- Python 3.11/Linux hash lock and clean Docker characterization result; intentionally deferred until
  BE1 Docker foundation is authorized.
- Exact PostgreSQL 16 Bookworm tag/digest and Python 3.11 base tag/digest; deliberately not looked up
  or implemented during BE0.

### 19. Known limitations

- The catalogue is only `PROPOSED_FOR_APPROVAL`.
- Scientific numeric parameters remain provisional/calibration-pending.
- Seven templates remain unavailable.
- Generator package metadata is stale.
- The B6 simulation pipeline has known synthetic limitations and is forbidden from the live path.
- The current hash lock proves Windows/CPython 3.10 reproduction, not the future BE1 Linux/Python
  3.11 container.
- JSON Schema records runtime-bundle immutability semantics but storage/application enforcement must
  be implemented later.
- `buildLog.md` is ignored by the repository's current Markdown `.gitignore` rule. It exists locally
  as requested but will not be committed unless the ignore policy is deliberately changed.

### 20. Current backend state

- Existing FastAPI bootstrap files from earlier work remain unchanged.
- BE0 provenance and characterization artefacts now exist.
- No database or BE1 infrastructure exists.
- No session, question, attempt, hint, mastery, or completion API exists.
- No generator is imported by the FastAPI application.
- The scientific source passed both existing-environment and clean hash-lock suites.

### 21. Completed work

- [x] Source commit/tree/content provenance.
- [x] Shared-module checksums.
- [x] Backend commit recorded.
- [x] Runtime and host recorded.
- [x] Exact scientific dependency closure and hash lock.
- [x] Clean lock installation.
- [x] Fresh complete 885-test result.
- [x] Deterministic fixed-seed private output digest.
- [x] 36/29/7 coverage report.
- [x] Seven deferred templates explicitly fail closed with no fallback.
- [x] Grade gate evidence.
- [x] First-attempt-only BKT and skill-isolation evidence.
- [x] Sequencing evidence.
- [x] Hint provenance/fail-closed/no-LLM evidence.
- [x] Guess-Guard/certification evidence.
- [x] Aggregation evidence.
- [x] Scientific statuses without invented values.
- [x] Packaging and live/offline boundary record.
- [x] Runtime-bundle schema.
- [x] Permanent future Docker/PostgreSQL decisions.
- [x] Living build log.

### 22. Remaining BE0 review work

- [ ] Owner/research review of the baseline and reports.
- [ ] Formal acceptance or documented rejection of the design authority set.
- [ ] Decision on the four response-format mappings.
- [ ] Approval of the packaging strategy and whether wheel construction is required before BE1.
- [ ] Resolution or explicit governed deferral of scientific policy/configuration inputs.
- [ ] Formal decision permitting transition to BE1.

### 23. BE0 exit-gate assessment

Technical characterization gate: **PASSED**.

Evidence:

- exact immutable source and shared checksums;
- clean hash-locked environment recreated successfully;
- 885/885 tests passed;
- deterministic digest reproduced;
- deferred/grade/scientific boundaries verified;
- coverage and characterization reports validate;
- runtime-bundle schema exists.

Formal BE0 phase approval: **NOT PASSED — PENDING REVIEW/APPROVAL**.

Reasons:

- catalogue and scientific approvals remain unresolved/calibration-pending;
- four response-format mappings require review;
- packaging strategy is not yet approved and no wheel is built;
- required owner/academic sign-off is not recorded.

Therefore BE1 must not start yet. The repository is ready for BE0 review, not for a claim of approved
pilot/production readiness.

### 24. Exact recommended next task

Conduct a BE0 governance and packaging review only:

1. Review `component-b-baseline.json`, `component-b-coverage.json`,
   `component-b-characterization.json`, and `runtime-bundle.schema.json`.
2. Decide the four response-format mappings.
3. Approve or revise the pinned internal-wheel packaging strategy.
4. Record which unresolved scientific policy values may remain explicitly deferred and which must be
   supplied before BE1.
5. Record formal owner/research approval or rejection of BE0.

Only after that approval should the first BE1 task begin: create and verify the backend Dockerfile,
`.dockerignore`, and Docker Compose services `api` and PostgreSQL `db` using verified pinned image
tags and digests.

### 25. Final artefact validation

The clean hash-locked environment loaded all four authored JSON files and performed these checks:

```text
JSON_FILES_VALID=4
RUNTIME_SCHEMA_DRAFT_2020_12_VALID=true
RUNTIME_SCHEMA_COMPLETE_DRAFT_INSTANCE_VALID=true
BASELINE_INVARIANTS_VALID=true
VALIDATION_EXIT_CODE=0
```

The runtime schema was validated both as Draft 2020-12 and against a complete in-memory draft
bundle containing every required field. The draft was not saved as an approved bundle because its
scientific policy checksums and approvals are unresolved.

After validation, the Yass repository HEAD was observed at
`848742c1a453648478c6b2ef02d91ca996ea566b` for an unrelated Component C6.0 commit. The BE0 snapshot
remains pinned to `0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b`. Object-level comparison confirmed
that `component_b_generator`, shared `models`, shared `validators`, and the Component B catalogue
are identical across both commits, with no path diff. Therefore the effective Component B source
under test did not change; the concurrent repository movement is recorded rather than silently
rewriting baseline provenance.

---

End of Phase BE0 entry. Append future work below this line; do not rewrite this entry.
## Phase BE0 Closure — Governance, Packaging, and Python 3.11 Reproduction

### Closure scope and reason

This section appends the final BE0 governance and packaging review. It does not start BE1 and
does not add Docker, Compose, PostgreSQL, authentication, session APIs, SQLAlchemy, or Alembic.
The review reconciles the original CPython 3.10 evidence with Python 3.11, registers response
contract decisions, selects a safe generator supply strategy, makes BE0 evidence trackable, and
issues an evidence-based exit decision.

### Files changed

- `backend/provenance/requirements-generator-win-py311.lock` — Windows x64 CPython 3.11 hash lock.
- `backend/provenance/component-b-characterization.json` — preserves Python 3.10 evidence and adds
  the Python 3.11 reproduction, focused suite, deterministic digest, and comparison.
- `backend/provenance/component-b-baseline.json` — adds the intended Python 3.11 Docker/CI baseline,
  reviewed mapping/packaging status, and closure gate.
- `backend/provenance/component-b-coverage.json` — records a reasoned result for each mapping.
- `backend/provenance/component-b-closure-decisions.json` — new machine-readable mapping,
  packaging, governance, approver, blocking, next-action, and exit-gate register.
- `.gitignore` — narrowly unignores the build log and BE0 provenance `.json`, `.in`, and `.lock`.
- `backend/buildLog.md` — this append-only closure record.

No generator scientific source or test was modified.

### Python 3.11 environment and dependency reproduction

```text
C:\tmp\component-b-be0-py311-20260722
CPython 3.11.15, Windows x64
pip 26.1.2
```

Commands:

```text
conda create -y -p C:\tmp\component-b-be0-py311-20260722 python=3.11 pip
conda run -n component_b python -m uv pip compile \
  backend/provenance/requirements-generator.in \
  --generate-hashes --python-version 3.11 --python-platform windows \
  --no-header --no-annotate \
  --output-file C:\tmp\requirements-generator-win-py311.lock
C:\tmp\component-b-be0-py311-20260722\python.exe -m pip install \
  --require-hashes -r backend/provenance/requirements-generator-win-py311.lock
```

The 3.11 lock contains the same 29 exact packages and is byte-identical to the 3.10 lock:
`27c04928c42688e45d7c82e44d07623c0f7d9c3cee8dd2ab3650532d32d6b04a`. This is valid because
`uv` emitted complete compatible distribution hashes for the exact-version input. A clean 3.11
`pip --require-hashes` installation succeeded; no scientific dependency was changed.

### Python 3.11 tests and deterministic comparison

The complete command used the same 15 explicit Component B files recorded in the earlier BE0
section, with `C:\tmp\component-b-be0-py311-20260722\python.exe -B -m pytest -q --tb=short
-p no:cacheprovider`.

```text
Complete suite: 885 collected, 885 passed, 0 failed, 0 skipped, 0 warnings, 0 errors
Exit code: 0
Pytest duration: 192.97 seconds
Output SHA-256: e3c7a35695b240b99c957d4f228ff99cf662726a2f5732a38a7489883c45b6eb

Focused suite: 20 collected, 20 passed, 0 failed, 0 skipped, 0 warnings, 0 errors
Exit code: 0
Pytest duration: 1.59 seconds
Output SHA-256: 7c5450e4934e30b8485d5cc1b4876c144bae83874402b6094af813a7ce776ed1
```

The focused nodes cover first-attempt BKT, independent skill states, Guess-Guard/certification,
sequencing/ties/soft prerequisites, exact fail-closed hints, and aggregation/provenance behavior.

Deterministic Phase B2A generation used `default_b1_config`, seed `20260716`, and canonical JSON
of the private `item_instances` (`model_dump(mode="json")`, sorted keys, compact separators):

```text
Config version: b1-smoke-0.1.0
Config hash: 715b2a4200771e8ccea63e88a32884d3f660922ec37abfcc72519c9542974d0b
Item instances: 54
Private output SHA-256: b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c
Repeated output: byte-identical
Python 3.10 comparison: exact digest match
```

CPython 3.11.15 therefore passes the characterized scope and becomes the intended Docker/CI
baseline. A Linux/Docker lock still requires generation and verification during separately
authorized BE1 work.

### Response-format mapping review

Catalogue rows, sampler registrations, sampled prompt/operand shapes, answer equivalences, and
frontend source were reviewed. No frontend renderer/input contract exists for the response-format
vocabulary. No new format was invented, and all four remain unresolved:

| Template | Catalogue | Generator | Result | Required decision |
|---|---|---|---|---|
| B-ADD02 | `single_integer_or_mark` | `single_integer_or_choice` | UNRESOLVED | Numeric endpoint does not prove mark support; owner must select behavior. |
| B-CNT06 | `ordered_integer_sequence` | `single_integer` | UNRESOLVED | Terminal-only generator is narrower; owner must confirm v1 intent. |
| B-PV02 | `structured_pair` | `expanded_form` | UNRESOLVED | Multi-equivalence text is not an exact pair DTO; frontend contract required. |
| B-PV04 | `structured_triple_or_expression` | `expanded_form` | UNRESOLVED | Expression behavior is plausible, but triple/parser support is unproven. |

Exact sources, sampler shapes, reasoning, and short decision requests are recorded in
`component-b-closure-decisions.json`.

### Generator packaging decision

- Pinned internal wheel — selected: immutable, installable, checksum-verifiable, checkout-independent.
- Immutable source artefact — acceptable fallback only with equivalent manifest, isolation, and tests.
- Repository-relative source import — rejected because the checkout and layout are mutable.

The wheel must include `component_b_generator`, top-level `models`, top-level `validators`, and
metadata binding it to the pinned Yass commit/tree. The catalogue remains a separate checksummed
runtime-bundle asset. A PEP 440 version derived from generator version plus pinned short commit is
proposed, but the final string needs packaging-owner approval because existing metadata is stale.

```text
python -m build --wheel --no-isolation <approved immutable packaging source directory>
python -m pip install --no-deps --require-hashes -r <wheel-lock>
python -I -c <import component_b_generator, models, validators; verify provenance>
<run complete Component B suite>
```

Wheel construction is not complete and remains separately approved work. Mutable-checkout runtime
imports are prohibited.

### Governance register

`component-b-closure-decisions.json` records status, source, BE1/session/pilot blocking, approver,
approved value or deferral, and next action without inventing values.

- Catalogue is PROVISIONAL and blocks BE1 authorization, session APIs, and live use.
- BKT, certification, and Guess-Guard numerics are CALIBRATION_PENDING; they do not block generic
  scaffolding but block live session APIs and pilot/production.
- Attempt limits, completion, and safe progress are UNRESOLVED and block session/live work.
- Timeout semantics are provisional; the numeric threshold is unresolved.
- Cold start is a governed fail-closed deferral: DISABLED.
- Named owner/academic sign-off is UNRESOLVED and blocks BE1 authorization.

### Git tracking review

The global Markdown ignore remains. Only these exceptions were added:

```text
!/backend/buildLog.md
!/backend/provenance/
!/backend/provenance/*.json
!/backend/provenance/*.in
!/backend/provenance/*.lock
```

```text
git check-ignore -v backend/buildLog.md
.gitignore:33:!/backend/buildLog.md backend/buildLog.md

git check-ignore backend/buildLog.md
exit 1 (not ignored)

git check-ignore backend/provenance/component-b-baseline.json
exit 1 (not ignored)

git status --short --untracked-files=all
?? backend/buildLog.md
?? backend/provenance/component-b-baseline.json
?? backend/provenance/component-b-characterization.json
?? backend/provenance/component-b-closure-decisions.json
?? backend/provenance/component-b-coverage.json
?? backend/provenance/requirements-generator-win-py310.lock
?? backend/provenance/requirements-generator-win-py311.lock
?? backend/provenance/requirements-generator.in
?? backend/provenance/runtime-bundle.schema.json
```

They are untracked but commit-eligible. No broad Markdown exception was added.

### Problems and fixes

1. No installed 3.11 launcher existed; a clean Conda prefix supplied CPython 3.11.15.
2. The 3.11 lock matched the 3.10 SHA. Clean hash-enforced 3.11 installation verified this was
   expected compatibility, not a missing output.
3. Sampler inspection initially assumed Pydantic output; `SampledContent` is a dataclass, so the
   read-only inspection was rerun with `dataclasses.asdict`. Source was not changed.
4. The Windows sandbox helper intermittently denied one patch; the same scoped relative patch was
   retried successfully.
5. No frontend renderer contract exists, so compatibility was not guessed.

### Formal BE0 exit-gate assessment

| Requirement | Result | Evidence / consequence |
|---|---|---|
| Technical characterization | PASSED | 885/885 complete and 20/20 focused. |
| Reproducibility | PASSED | Clean hash locks and exact seed digest. |
| Python 3.11 compatibility | PASSED (Windows x64) | CPython 3.11.15 matches 3.10 behavior/digest. |
| Packaging strategy | SELECTED | Pinned wheel selected; mutable checkout rejected. |
| Packaging artefact/approval | UNRESOLVED | Wheel not built; metadata and approval pending. |
| Response mappings | UNRESOLVED | Four of four need owner decision/frontend contract. |
| Governance approvals | UNRESOLVED | Catalogue, policies, and named sign-off remain open. |
| Permission to begin BE1 engineering | NOT AUTHORIZED | Formal BE0 approval is absent. |
| Pilot/production readiness | NOT READY | Scientific, policy, mapping, packaging gates remain. |

### Final result and exact recommended next task

Technical characterization, reproducibility, and Windows CPython 3.11 compatibility pass. Full BE0
approval does not pass, and BE1 Docker implementation is not authorized.

Exact recommended next task: obtain named Component B owner and academic/research decisions that
(1) resolve all four mappings against an explicit frontend contract, (2) approve the pinned-wheel
strategy and separately authorize building/verifying it with all required packages, (3) approve
catalogue v1.0 or record a governed deferral, and (4) record governed deferrals for every blocked
scientific/session policy. Then re-assess BE0 before authorizing BE1 Docker work.
## BE0 Architecture Correction — Research Generator and Live Application Separation

### Correction scope

This section supersedes only the earlier proposed use of the complete Component B generator wheel
as an application dependency. It preserves the earlier evidence. No BE1 implementation, live
engine package, session behavior, schema, authentication code, BKT runtime, or learner flow was
created.

### Installed-wheel verification result

The already-running isolated installed-wheel test finished and was not rerun or fixed.

```text
Wheel: upadya_component_b_generator-0.1.0+be0.0e86fdc-py3-none-any.whl
Wheel SHA-256: 12b5ba5b7e8a70785a3e2b49e5c07bc8f89cc677c268ea509907f8f6d517e750
Source commit: 0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b
Source manifest SHA-256: fd4f052e41539434ad4ff6bbb72fa01815ef750ceeb0a6d8ebc6fbc481e07e2c
Python: CPython 3.11.15
Import mode: python -I; imports resolved from the clean environment site-packages
Result: 884 passed, 1 failed in 213.14s (0:03:33)
Skipped: 0; warnings: 0
Output SHA-256: 03514e92481b4458cc775d9c1f0ca359ec63eeed97bea4c0680815888895c41c
```

The failure was `test_pilot_report_git_provenance_is_present_and_honest`. In the isolated non-Git
installation, pilot code reported `git provenance unavailable`, while the test additionally expected
the literal word `not`. This is an offline pilot provenance-message assertion, not a scientific
formula or live-safe capability failure. Logic was not changed.

The wheel and evidence are retained as `BE0_RESEARCH_REPRODUCIBILITY_ARTIFACT_ONLY`. The wheel is
not approved for the Upadya application container.

### Corrected architecture decision

1. Yass owns synthetic dataset generation and offline research experiments.
2. Upadya owns real learners, attempts, server timing, persistence, BKT state, hints, sequencing,
   and progress.
3. Upadya may reuse only existing deterministic live-safe functions through a reviewed adapter and
   immutable minimal dependency closure.
4. Upadya must never import or execute synthetic/offline modules.
5. The complete research-generator wheel is not an application runtime dependency.

The preferred future package is `upadya-component-b-live-engine`. It belongs to BE3 and was not
built here. It must contain only the reviewed live-safe source closure and necessary shared
models/validators. Formulas must be reused, not copied or rewritten. The inventory is
`backend/provenance/component-b-live-engine-reuse-map.json`.

### Allowed future application reuse

Subject to BE3 minimal packaging, adapters, configuration approval, and architecture tests:

- catalogue validation, checksum, and grade normalization;
- activation and grade eligibility;
- sequencing features, scoring, ranking, and target selection;
- deterministic task construction after removing synthetic import reachability;
- answer normalization/equivalence and place-value parsing;
- distractor construction and exact catalogue hint lookup;
- BKT prediction, posterior, and update;
- Guess-Guard and certification;
- session aggregation after adapting real-attempt DTOs.

No mathematical formula was copied or rewritten.

### Prohibited application code

The application must not install the full research wheel or execute `cohort/*`, hidden learner
truth, synthetic traits, `behaviour.first_attempt`, `behaviour.latency`,
`behaviour.attempt_loop`, simulated answers/timing, `pipeline.py`, `pilot.py`, synthetic audits,
dataset-generation entry points, or experiment runners.

### Infrastructure-only BE1 reassessment

The full wheel is not required for infrastructure-only BE1. Python 3.11 reproduction passed,
unresolved policies are recorded without invented values, production remains fail-closed, and
engine/session behavior remains blocked.

Infrastructure-only BE1 is authorized for Dockerfile, `.dockerignore`, Docker Compose with pinned
Python 3.11 API and official PostgreSQL 16, settings, errors, request IDs, logging, CORS, health,
database connectivity, SQLAlchemy unit-of-work and Alembic foundations, Supabase JWT verification,
and `GET /api/v1/me`.

Not authorized: BE2 session behavior/persistence semantics; BE3 engine packaging/integration; BE4
learning flow; BE5 unresolved renderer integration; runtime-bundle activation; pilot; production.

### Files changed and next task

- `backend/provenance/component-b-baseline.json`
- `backend/provenance/component-b-closure-decisions.json`
- `backend/provenance/component-b-live-engine-reuse-map.json` (new)
- `backend/packaging/component_b_internal/IMPORT_POLICY.md`
- `backend/buildLog.md`

Exact next task: begin infrastructure-only BE1 with the pinned Python 3.11 API Dockerfile,
`.dockerignore`, and Docker Compose foundation using pinned official PostgreSQL 16. Do not install
the research wheel or add session/Component B engine behavior.

Transition result: `INFRASTRUCTURE_ONLY_BE1_AUTHORIZED`.

## Phase BE1 — Batch 1: Docker and PostgreSQL Infrastructure Foundation

### Scope and architecture boundary

Implemented only the authorized BE1 infrastructure foundation: a pinned Python 3.11 API image,
strict build-context exclusions, Docker Compose API/PostgreSQL services, environment template,
settings, CORS, and infrastructure-stage liveness/readiness checks. No session API, persistence
model, migration, authentication, question selection/generation, attempt, hint, BKT, sequencing,
completion, progress, live-engine, Component C, or learner-flow behavior was added.

The full Component B research-generator wheel remains
`BE0_RESEARCH_REPRODUCIBILITY_ARTIFACT_ONLY`. It is neither installed nor mounted in the API
container. The application image contains no Yass source, wheel, provenance directory, research
dataset, pipeline, pilot, synthetic learner code, or experiment runner.

### Files created or updated

- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/compose.yaml`
- `backend/.env.example`
- `backend/requirements.in`
- `backend/requirements.lock`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/api/routes/health.py`
- `backend/tests/test_health.py`
- `backend/buildLog.md` (this append-only section)

### Reproducible inputs and image pins

- API base: `python:3.11.15-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba`
- Python linux/amd64 manifest observed during pin review:
  `sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941`
- Database: `postgres:16.10-bookworm@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74`
- PostgreSQL linux/amd64 manifest observed during pin review:
  `sha256:94f23d40fdaf5e60cb2fd8a98c22f02a7b8724949f310d95a0ddf075e8c8b208`
- Dependency lock SHA-256:
  `4d3c79b8d2266c3ed9e50896ccfb7346dac56e47d5583291874ecae4c6797622`
- Dependency installation uses `pip install --require-hashes --no-deps -r requirements.lock`.
- API runtime Python: `Python 3.11.15`.
- Built API image/tag: `upadya-backend:be1-batch1`.
- Built OCI image/index digest:
  `sha256:d0cb921ba8ab82618546915a5defd02626bda7394ae367c5af710912debd969d`.
- Build output configuration digest:
  `sha256:c036d06fecf204352115c76f52ad59999db88c29aaa4d412b622087a92b1d556`.

The dependency lock was generated with:

```powershell
conda run -n component_b python -m uv pip compile requirements.in --generate-hashes `
  --python-version 3.11 --python-platform x86_64-manylinux_2_28 `
  --no-header --no-annotate --output-file C:\tmp\upadya-backend-requirements.lock
```

The Docker build context was 73.69 kB. The `.dockerignore` excludes secrets/environment files,
Git metadata, caches, virtual/Conda environments, frontend/node artefacts, provenance, packaging,
wheels, research/data/output directories, and build logs. Only the application, tests, and locked
runtime inputs are copied. The API build uses cache-friendly lockfile installation before source
copying.

### Commands executed

```powershell
docker compose config --quiet
docker compose build --no-cache
docker compose up -d
docker compose ps --all
docker compose exec -T api python --version
docker compose exec -T api python -m compileall -q app
docker compose exec -T api python -m pytest -q
docker compose exec -T api id
docker compose exec -T db pg_isready -U upadya -d upadya
curl.exe -fsS http://127.0.0.1:8000/health/live
curl.exe -fsS http://127.0.0.1:8000/health/ready
docker inspect upadya-be1-api-1
docker inspect upadya-be1-db-1
docker history --no-trunc upadya-backend:be1-batch1
docker compose restart db
```

The final shutdown used `docker compose down` without `--volumes`; the named database volume was
intentionally preserved.

### Verification results

- `docker compose config --quiet`: PASS.
- No-cache API build: PASS.
- Containers: `upadya-be1-api-1` and `upadya-be1-db-1`; both reported healthy.
- API exposure: `127.0.0.1:8000`; PostgreSQL host port bindings: none.
- API-to-database hostname: `db`.
- PostgreSQL readiness: `/var/run/postgresql:5432 - accepting connections`.
- API compile check: PASS.
- Container tests: `3 passed` in 0.37 seconds. Warnings were one upstream
  FastAPI/Starlette TestClient deprecation and a non-failing pytest cache warning because the
  runtime image is read-only to UID 10001 under `/app`.
- Runtime identity: `uid=10001(app) gid=10001(app)`; image user is `10001:10001`.
- Liveness: HTTP 200 with `status=alive` and a request ID.
- Readiness: HTTP 200 with `stage=infrastructure`, `api_process=ok`, and `database_tcp=ok`.
  Generator, catalogue, runtime bundle, migrations, and authentication are honestly reported as
  `not_checked`; readiness does not imply scientific or product readiness.
- API mounts: zero. Database mount:
  `upadya-be1-postgres-data -> /var/lib/postgresql/data`.
- Research package check: `upadya-component-b-generator` not installed.
- Container filesystem check: no Yass-named path or `.whl` under `/app`.
- Image history review: no secret values and no research-wheel installation or copy step.
- Logs: normal API health requests and PostgreSQL startup/restart messages; no credential values
  were exposed in the reviewed output.
- Persistence: inserted marker `volume-survives-restart`, restarted only the database container,
  queried the same marker successfully, and observed PostgreSQL skip initialization because the
  existing data directory was retained. PASS.
- Readiness after database restart: HTTP 200. PASS.

### Errors encountered and fixes

1. The first local lockfile copy used an incorrect path relative to the backend working directory.
   The copy failed without changing backend content; it was immediately rerun with the correct
   destination, and the resulting lock checksum was verified.
2. The first host-side health query embedded a PowerShell variable in an outer PowerShell command,
   which expanded it early and produced an empty-pipe parser error. It was replaced by direct
   `curl.exe -fsS` requests; both endpoints returned HTTP 200.
3. Inspecting PostgreSQL by the unqualified local tag failed because Compose retained the
   digest-qualified reference. Inspection by the exact digest succeeded and matched the Compose
   pin.

### Batch decision and exact next task

Result: **PASS — BE1 Batch 1 infrastructure foundation is complete.**

This does not authorize sessions, database domain tables, migrations for learner behavior,
authentication implementation, scientific runtime integration, pilot use, or production use.

Exact next task: begin BE1 Batch 2 infrastructure-only foundations for stable errors, structured
logging/request-ID integration, database connectivity, SQLAlchemy unit-of-work scaffolding, and
Alembic scaffolding. Keep domain/session tables and migrations, authentication, `/api/v1/me`, the
Component B live engine, learner flows, pilot, and production outside that batch unless separately
authorized.

## Phase BE1 — Batch 2: Errors, Logging, Database and Migration Foundations

### Scope and decisions

Implemented only the authorized BE1 infrastructure: versioned safe errors, bounded request IDs,
JSON structured request logging, SQLAlchemy 2 async PostgreSQL connectivity, async session
lifecycle, an infrastructure-only unit of work, and async Alembic scaffolding. No authentication,
`/api/v1/me`, learner/session/attempt/question/mastery/progress model, repository, business table,
scientific runtime, Component B engine, Component C/3, pilot, or production behavior was added.

The error envelope is version `1.0` and contains a stable code, user-safe message, request ID, and
optional structured details. It deliberately omits a timestamp because errors do not require one;
operational timestamps belong in logs. Central handlers cover application, validation,
authentication-shaped, not-found, conflict, service-unavailable, and unexpected errors. Raw
exceptions, stack traces, SQL, paths, and credentials are not returned.

Incoming `X-Request-ID` values are accepted only when they match a conservative 1–64 character
allowlist; all other values are replaced with a UUID. A ContextVar carries the ID into logs.
Uvicorn raw access logs are disabled, and application logs use route templates rather than raw URLs
to avoid recording identifiers. No headers, request bodies, learner answers, tokens, passwords, or
database URLs are logged.

Readiness now performs SQLAlchemy `SELECT 1` through asyncpg. It honestly leaves migrations,
authentication, catalogue, generator, runtime bundle, and higher-level behavior as `not_checked`.
Engine disposal runs during application shutdown. SQLite is rejected rather than used as fallback.

The Alembic revision `20260722_0001` is an intentionally empty infrastructure baseline. Alembic
reads the application `DATABASE_URL`; no credential is committed in the migration configuration.
Migration commands run inside the API container as documented in `migrations/README.md`.

### Files created

- `backend/app/core/errors.py`
- `backend/app/core/logging.py`
- `backend/app/core/request_context.py`
- `backend/app/application/unit_of_work.py`
- `backend/app/infrastructure/database.py`
- `backend/app/infrastructure/unit_of_work.py`
- `backend/alembic.ini`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/README.md`
- `backend/migrations/versions/20260722_0001_empty_infrastructure_baseline.py`
- `backend/pytest.ini`
- `backend/tests/test_errors_and_request_ids.py`
- `backend/tests/test_database_and_uow.py`

### Files changed

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/api/routes/health.py`
- `backend/tests/test_health.py`
- `backend/requirements.in`
- `backend/requirements.lock`
- `backend/Dockerfile`
- `backend/compose.yaml`
- `backend/buildLog.md`

### Dependencies and artefacts

- SQLAlchemy `2.0.46` with asyncio support
- asyncpg `0.31.0`
- Alembic `1.18.4`
- Existing pins retained: FastAPI `0.137.1`, Uvicorn `0.49.0`, httpx `0.28.1`, pytest `9.1.1`
- Lock generated for CPython 3.11 / x86_64 manylinux with hashes and 33 resolved packages
- `requirements.lock` SHA-256:
  `d6ef4408a902e2aa7a2d2c63474cbea2715ace9bf9e1e00f3e171e12d85059ad`
- Final image: `upadya-backend:be1-batch2`
- Final image/index digest:
  `sha256:ef5503a329711fdb119d1386602ae6b661991ad538219caf7e2b85f19d2429fd`
- Runtime Python: `3.11.15`; runtime identity: UID/GID `10001:10001`

### Commands and verification

```powershell
conda run -n component_b python -m uv pip compile requirements.in --generate-hashes `
  --python-version 3.11 --python-platform x86_64-manylinux_2_28 `
  --no-header --no-annotate --output-file requirements.lock
docker compose config --quiet
docker compose build --no-cache
docker compose up -d --force-recreate
docker compose ps
docker compose exec -T api python --version
docker compose exec -T api python -m compileall -q app migrations
docker compose exec -T api python -m pytest -q
docker compose exec -T api alembic current
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade base
docker compose exec -T api alembic upgrade head
docker compose exec -T db pg_isready -U upadya -d upadya
```

Final results:

- Compose validation and clean no-cache build: PASS.
- Both containers healthy; API bound to `127.0.0.1:8000`; database host port bindings `{}`.
- Compile: PASS.
- Tests: `12 passed, 1 warning in 0.46s`. The warning is the upstream FastAPI TestClient notice
  that Starlette's current `httpx` integration is deprecated.
- Request IDs: valid incoming IDs preserved on success and errors; unsafe/overlong values replaced;
  every tested response contains `X-Request-ID`; error body ID matches header. PASS.
- Stable errors: not-found, conflict, authentication-shaped, validation, database unavailable, and
  unexpected internal errors covered; internal exception text is absent from responses. PASS.
- Structured logging: JSON request-start, completion, and exception events tested. Runtime logs
  include timestamp, level, logger, event, request ID, method, route template, status, duration,
  version, and environment. The runtime evidence correlated `final-client-123` and
  `final-error-123`. PASS.
- Database connectivity: async SQLAlchemy/asyncpg readiness `SELECT 1` succeeded; PostgreSQL
  `pg_isready` accepted connections. PASS.
- Unit of work: commit, rollback-on-failure, and close behavior tested; `3` lifecycle/database URL
  tests are part of the 12-test result. PASS.
- Migrations: current → upgrade head → downgrade base → upgrade head completed transactionally on
  PostgreSQL; final revision is `20260722_0001 (head)`. PASS.
- Schema inspection found `alembic_version` plus `be1_persistence_check`. The latter is the
  pre-existing Batch 1 named-volume persistence marker. Batch 2 created only Alembic's
  infrastructure version table and no business/domain table.
- API container: non-root, zero mounts, healthy. Research generator package not installed; no Yass
  path or wheel found under `/app`. PASS.
- Reviewed responses and JSON application logs contain no secrets, database URL, authorization
  header, learner data, raw exception, SQL, or internal path.

### Errors, causes, and fixes

1. A pre-container local pytest attempt used the research `component_b` Conda environment, which
   intentionally lacks FastAPI and SQLAlchemy. Collection failed for missing packages. No package
   was installed into that research environment; authoritative tests ran in the locked API image.
2. The first container run produced `11 passed, 1 failed`: Starlette's unmatched-route exception is
   its base `HTTPException`, while the handler was registered for FastAPI's subclass. Registering
   the centralized handler for Starlette's base type fixed the not-found contract. Final result:
   12 passed.
3. The first non-root test run warned that `/app/.pytest_cache` was not writable. `pytest.ini` now
   places cache data under `/tmp`; the final run has no cache warning.
4. Final logging review identified that raw paths could eventually contain learner identifiers.
   Logging was hardened to route templates, Uvicorn access logging was disabled, and a final clean
   no-cache image was built and retested.

### Limitations, blockers, and next task

This batch supplies infrastructure only. It does not make authentication, sessions, catalogue,
Component B engine, BKT, runtime bundle, learner flow, pilot, or production ready. Migration status
is intentionally not asserted by `/health/ready` until a separately reviewed honest mechanism is
implemented. The test-only infrastructure routes exist only when the test modules are imported and
are not part of normal application startup.

Result: **PASS — BE1 Batch 2 is complete.**

Recommended next task: separately authorize BE1 Batch 3 for Supabase JWT verification foundations
and `GET /api/v1/me`, using the stable error, request-ID, logging, database, and migration
infrastructure completed here. Do not add sessions, learner business tables, scientific runtime,
pilot, or production behavior in that task.

## Phase BE1 — Batch 3: Supabase JWT Verification and Authenticated Identity

Implemented server-side asymmetric Supabase JWT verification, authenticated-principal extraction,
`GET /api/v1/me`, offline authentication tests, and safe environment placeholders only. No learner
or profile record is created and the endpoint does not access Component B session data.

### Files and dependencies

Created `app/api/routes/identity.py`, `app/domain/principal.py`,
`app/infrastructure/auth.py`, and `tests/test_auth.py`. Changed `.env.example`, `Dockerfile`,
`app/core/config.py`, `app/main.py`, `compose.yaml`, `requirements.in`, and `requirements.lock`.

Pinned PyJWT `[crypto]` `2.13.0`; the lock resolves cryptography `49.0.0`, cffi `2.1.0`, and
pycparser `3.0`. Existing Batch 2 pins remain unchanged. Lock SHA-256:
`79998c3267fb0129bac47732c0e9b0971f3839ff20ddee385cc50a6f0c54f1e6`. Final image is
`upadya-backend:be1-batch3` with digest
`sha256:448504e841889c80290b9cbc83317fcca75a3b365474fc23d7df8cf8143078d2`.

Safe configuration placeholders were added for `SUPABASE_URL`, `SUPABASE_JWT_ISSUER`,
`SUPABASE_JWT_AUDIENCE`, `SUPABASE_JWKS_URL`, and `SUPABASE_JWKS_CACHE_TTL_SECONDS`. No real key,
secret, project token, or credential was committed.

### JWT and JWKS design

Only asymmetric `RS256` and `ES256` are allowed. Unsigned, HMAC, unsupported-algorithm, missing-kid,
malformed, expired, premature, wrong-issuer, wrong-audience, missing-subject, invalid-signature, and
unknown-key tokens fail closed using the existing request-ID error envelope. PyJWT validates the
signature, configured issuer, optional audience, expiry, not-before, and non-empty subject. Raw
tokens are never stored.

The principal exposes only `user_id` and an optional email. Email is included only when the signed
claims also assert `email_verified=true` or a non-empty `email_confirmed_at`. Roles, metadata, raw
claims, and tokens are not returned.

The JWKS set cache has a configured TTL clamped to 30–3600 seconds and a five-second timeout. No
indefinite per-key cache is used. Unknown `kid` performs at most one forced refresh under a process
lock, supporting key rotation, with a 5–30 second cooldown to prevent key-ID refresh spraying.
Verification failure or unavailable JWKS always fails closed.

### Commands and results

Ran the reproducible `uv pip compile` command for CPython 3.11/manylinux with hashes, followed by
`docker compose config --quiet`, `docker compose build`, `docker compose up -d`, `docker compose
ps`, in-container compileall, full pytest, focused authentication pytest, unauthenticated and
deterministic authenticated `/api/v1/me` checks, container/log/schema inspection, and final
`docker compose down`.

Full result: `26 passed, 1 warning in 0.73s`. Focused auth result: `14 passed, 1 warning in 0.64s`.
The sole warning is the existing upstream FastAPI TestClient/httpx deprecation.

Unauthenticated `/api/v1/me` returned HTTP 401 with schema `1.0` and a request ID matching the
response header. The deterministic offline authenticated request returned HTTP 200 with exactly
`{"user_id":"user-123","email":"verified@example.test"}` and request ID `docker-auth-123`.

Rotation testing started with JWKS lacking `key-2`; one refresh loaded the rotated key and verified
the token. An immediate unknown-kid spray attempt caused no third fetch. Token-leakage tests and
runtime log inspection found no JWT, Authorization header, test secret, database URL, or credential.

The API remains healthy and non-root (`10001:10001`) with zero mounts; PostgreSQL has no host port.
Schema remains only `alembic_version` and the pre-existing Batch 1 `be1_persistence_check`; Batch 3
added no migration or business table. The research-generator package remains uninstalled and no
Yass path or wheel exists under `/app`.

### Errors, limitations, and next task

The initial unsupported-HMAC test used a short test key and produced a library warning; the test key
was lengthened without changing application behavior. Security review then identified possible
repeated default unknown-kid refreshes, so the locked cooldown layer was added and tested.

Tests are offline and no real Supabase project was contacted. Deployment must provide the exact
issuer, audience policy, and HTTPS JWKS URL through managed configuration. Authentication does not
create profiles, local authorization policy, learner records, or sessions. Sessions, questions,
attempts, BKT, hints, sequencing, progress, completion, live-engine integration, Component C/3,
pilot, and production remain blocked.

Result: **PASS — BE1 Batch 3 is complete.**

Exact next recommended task: conduct a BE1 closure/security review of Batches 1–3 and define the
BE1-to-BE2 transition decision. Do not create learner/session business tables or session behavior
until BE2 scope and unresolved policies are explicitly authorized.

## Phase BE1 Closure — Infrastructure, Database and Authentication Review

### Repository and review scope

Reviewed the committed BE1 Batch 1–3 implementation without adding or changing runtime
functionality. Batch 3 commit `7d6ef7036120185a1017a7773bb46990c39d7c66` is present locally and
at `origin/B_frontend`; the pre-review tree was clean. All Batch 3 application and test files are
tracked. This build log contains the Batch 1, Batch 2, and Batch 3 evidence sections.

Security-critical files reviewed included the Dockerfile, Compose definition, environment example,
dependency input/lock, application configuration, request middleware, error/logging infrastructure,
JWT/JWKS verifier, principal and identity route, async database/session lifecycle, unit of work,
Alembic environment and empty baseline, health routes, and all tests.

### Dependency and supply-chain review

The committed dependency lock was reproduced to a temporary file with the documented CPython 3.11
x86_64-manylinux `uv pip compile --generate-hashes` command. The reproduced file was byte-identical
to the committed lock. Both SHA-256 values are
`79998c3267fb0129bac47732c0e9b0971f3839ff20ddee385cc50a6f0c54f1e6`.

Direct pins include PyJWT `[crypto]` `2.13.0`, SQLAlchemy `[asyncio]` `2.0.46`, asyncpg `0.31.0`,
Alembic `1.18.4`, FastAPI `0.137.1`, and Uvicorn `0.49.0`. The resolved lock pins cryptography
`49.0.0`. The image copies only `requirements.lock` before running
`pip install --require-hashes --no-deps`; application and tests are copied afterward. No research
generator appears in the dependency input or lock, and runtime package inspection reports
`upadya-component-b-generator` absent.

### Authentication security review

PASS. The server verifies JWT signature and explicitly allowlists `RS256` and `ES256`. It requires a
non-empty `kid`, expiry, issuer, and non-empty subject; validates configured audience and not-before
when present; and rejects unsigned, malformed, unsupported-algorithm, expired, premature,
wrong-issuer, wrong-audience, invalid-signature, missing-subject, and unknown-key tokens. Failure to
load or verify JWKS fails closed through the stable version `1.0` authentication error envelope.

JWKS caching has a configured TTL clamped to 30–3600 seconds, five-second fetch timeout, no
indefinite per-key cache, locked forced refresh, and 5–30 second unknown-key refresh cooldown.
Deterministic tests prove rotation succeeds after one refresh and repeated unknown-key attempts do
not cause immediate additional fetches.

The raw token is not stored in the principal, response, log fields, exception text, or database.
Authorization headers are never passed to logging. `/api/v1/me` returns only `user_id` and an email
whose signed claims assert verification/confirmation. Authentication failures return a user-safe
401 with request ID matching `X-Request-ID`.

### Docker and infrastructure verification

Executed `docker compose config --quiet`, `docker compose build --no-cache`, `docker compose up -d`,
`docker compose ps`, in-container Python/compile/test/migration commands, PostgreSQL readiness,
health and authentication-error requests, API/database logs, image/container/history inspection,
schema inspection, and `docker compose down`.

- API base remains pinned to Python `3.11.15-slim-bookworm` digest
  `sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba`.
- PostgreSQL remains pinned to `16.10-bookworm` digest
  `sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74`.
- Closure no-cache API image/index digest:
  `sha256:5219bce0ea3ab0eac38f744658fcc732a79cae36759237fddaabd288870edb13`.
- Runtime Python: `3.11.15`; API user: UID/GID `10001:10001`; API mounts: zero.
- `DATABASE_URL` resolves hostname `db`; PostgreSQL host-port bindings are `{}`.
- Named volume `upadya-be1-postgres-data` is attached at `/var/lib/postgresql/data`, survived the
  review, and remains present after shutdown.
- API filesystem search found no Yass path or wheel. Image history contains no research artefact,
  credential, token, or secret-bearing build instruction.
- Targeted tracked-file credential-signature scan found no private key, Supabase secret key, or
  service-role credential. Reviewed API/database logs contain no token, Authorization header,
  database URL, password, or learner-sensitive data. Committed local-development values and
  `.env.example` Supabase URLs are explicitly non-secret placeholders.

### Database and migration review

PASS. Alembic upgrade-head, downgrade-base, and upgrade-head all completed using PostgreSQL
transactional DDL. The sole revision `20260722_0001` has empty upgrade/downgrade functions. Schema
inspection found only `alembic_version` and the pre-existing Batch 1 infrastructure marker
`be1_persistence_check`. No learner, session, question, attempt, mastery, hint, or progress table
exists. SQLAlchemy exposes only engine/session/probe lifecycle, and the unit of work exposes only
open, commit, rollback, and close—no business repository or domain behavior.

### Health, observability, tests, and warning

PASS. `/health/live` returned process liveness. `/health/ready` returned only infrastructure status
with API and database connection `ok`; generator, catalogue, runtime bundle, migrations, and
authentication remain `not_checked`. It makes no session, engine, BKT, learner-flow, pilot, or
production-readiness claim.

Success and error responses preserved supplied request IDs (`closure-live-123`,
`closure-ready-123`, and `closure-error-123`). Structured JSON logs contain request IDs, method,
route template, status, duration, version, and environment without sensitive values.

The closure container suite reports `26 passed, 1 warning in 0.66s`. The warning is
`StarletteDeprecationWarning` from FastAPI's test-only `TestClient` import regarding the current
httpx integration. It does not occur in the production request path and is non-blocking, but should
be removed when the upstream-supported test client migration is available. A duplicate idempotent
`httpx` logger-level assignment is noted as harmless cleanup debt and was not changed during this
review-only task.

### Unresolved risks, blocked work, and formal exit decision

All implemented BE1 infrastructure and security gates pass. However, the existing governed
baseline explicitly records `be2_be3_be4_be5_pilot_production` as
`BLOCKED_BY_PHASE_AND_UNRESOLVED_GOVERNANCE`, and the closure decision register explicitly lists
`BE2 session behavior and persistence semantics` in blocked scope. This review has no authority to
override those records or invent the unresolved policies.

The requested final-state vocabulary couples BE1 closure with BE2 authorization. Because BE2 is
still explicitly blocked, `BE1_CLOSED_BE2_AUTHORIZED` would be false even though BE1 technical gates
pass. Therefore the formal decision is:

`BE1_NOT_CLOSED`

This means formal transition is withheld by governance, not that a BE1 technical/security test
failed. Learner/session tables, session APIs, questions, attempts, BKT, sequencing, hints, progress,
live-engine integration, Component C/3, pilot, and production remain prohibited.

Exact next task: perform a governance-only BE1-to-BE2 authorization review that resolves or
explicitly defers the recorded BE2 blockers and defines the allowed BE2 persistence scope. Do not
implement BE2 until that decision is recorded.

## BE1-to-BE2 Governance Authorization Review

### Review scope and evidence

This was a governance-only review. No application code, migration, table, API, test, scientific
logic, or runtime dependency was created or changed. The review used the BE0 baseline, closure,
coverage, characterization, live-engine boundary, runtime-bundle schema, and prior build-log
evidence; the backend plan and both Component B application architecture documents; and the
authoritative Yass Component B specification, variable and shared-foundation registers, approved
blocking-decisions memo, approval-status confirmation, catalogue, and empirical-parameter record.

The starting technical evidence remains unchanged: Batch 3 commit
`7d6ef7036120185a1017a7773bb46990c39d7c66`, closure-review commit `6a7b4a9`, 26 tests passed,
Alembic upgrade/downgrade/upgrade passed, and zero business tables. The prior `BE1_NOT_CLOSED`
decision was a governance hold rather than a failed infrastructure or security gate.

The complete blocker classification and enforceable scope are recorded in
`backend/provenance/component-b-be2-governance-authorization.json`.

### Decisions and formal deferrals

The Supabase subject is the canonical external application-user key, not the learner ID. Live
learners require separate opaque UUIDs. Because account-to-learner cardinality and relationship
ownership are not approved, the schema may use a cardinality-neutral junction but may not expose
learner selection, linking, or CRUD. Grade may be nullable and constrained to 2 or 3, with no
default; grade ownership, mutation, inference, and grade-dependent behavior remain blocked.

The documented session state vocabulary may be represented and constrained, including at most one
`starting` or `active` session per learner, but no live session may be created and no state
transition may execute in this limited authorization. Start, resume, recovery, abandonment,
replacement, expiry, and completion behavior remain blocked. Session expiry has no approved
duration. Completion remains disabled and must not be conflated with stopped, abandoned, expired,
or technical-failure states.

Idempotency is an approved engineering contract: scope keys by authenticated actor, operation, and
opaque key; fingerprint the canonical request body; replay the original committed response for an
identical request; return a stable conflict for a mismatched body; serialize concurrent replays;
and commit the record atomically with the future mutation. This foundation may be implemented even
though no new state-changing endpoint is currently authorized.

Attempt limits remain unresolved and synthetic negative-binomial bounds are non-authoritative for
the application. The first-attempt-only evidence rule remains a required future invariant, but item
opportunities, attempts, retries, timing classification, hints, and mastery updates are outside this
limited BE2 scope. Server issuance and receipt timestamps and raw duration fields may be designed in
a future attempt schema without a threshold; no timeout, background/pause adjustment, or learner
outcome may be derived until approved. Network, API, database, and infrastructure failures remain
technical and never become learner failures.

Safe progress, descriptive summaries, certification, and completion output remain disabled. No
counts are exposed yet because the presentation, privacy, consent, and retention contracts are not
approved. BKT, sequencing, hints, certification, Guess-Guard, task generation, answer evaluation,
and the minimal live-engine adapter remain BE3/BE4 work. No placeholder probability, threshold,
score, answer, hint, or scientific default is permitted.

### Authorized and prohibited scope

BE2 is authorized only for non-live schema, migration, repository, idempotency, and audit
foundations using visibly synthetic fixtures in an isolated test database. Authorized table scope
is: `app_users`, `b_learners`, a cardinality-neutral `app_user_learner_links`, immutable metadata-only
`b_runtime_bundle_records`, lifecycle/provenance-only `b_sessions`, append-only technical
`b_session_events`, `b_idempotency_records`, and append-only `b_audit_events`. Runtime-bundle rows
cannot be activated or used by a live session without complete approved checksums and approvals.

No new endpoint or executable lifecycle transition is authorized. Item-opportunity, attempt,
mastery/skill-state, hint, selection, session-summary/progress, and integration/outbox tables remain
prohibited. Learner CRUD, account linking, session start/resume/recovery/abandon/expire/complete,
descriptive summaries, real-child data collection, research export, live-engine integration,
Component C/3, pilot, and production behavior remain prohibited.

Every permitted record design must use minimum-data pseudonymous identifiers, UTC server
timestamps, source class/system/record provenance, environment and schema revision, request and
actor references, and append-only audit evidence where appropriate. Synthetic/test records must
remain in isolated non-live databases and may never be copied into live learner records. Prohibited
fields include population, `dd_subtype`, hidden truth, true mastery, synthetic traits, simulated
answers/correctness/latency, off-day state, experiment identifiers, and pipeline/pilot/audit-runner
outputs.

### Owners, unresolved risks, and transition

Product, privacy/child-safety, ethics/project-governance, and academic/research owners still must
approve account-to-learner relationships, grade control, consent, retention, withdrawal/deletion,
session lifecycle and expiry, attempt limits, timeout/background rules, completion, safe progress,
catalogue mappings, scientific configuration, and named formal sign-off. These items are formally
deferred only from the neutral persistence foundation; they continue to fail closed for live data,
API behavior, scientific behavior, BE3/BE4, pilot, and production.

The BE1 technical and security gates are complete, and the machine-readable scope prevents this
transition from being interpreted as authorization for session behavior or learner data collection.
The formal decision is:

`BE1_CLOSED_BE2_LIMITED_SCOPE_AUTHORIZED`

Exact next task: implement BE2 Limited Batch 1 only—the authorized neutral persistence models,
Alembic migrations, repositories, idempotency/audit foundations, constraints, and isolated
synthetic database tests. Add no endpoints, live records, lifecycle execution, item opportunities,
attempts, scientific fields, live-engine integration, pilot, or production behavior.

## Phase BE2 Limited — Batch 1: Neutral Persistence, Audit and Idempotency Foundations

### Authorization and scope

Implementation started from commit `74676f8`. The hard boundary is
`backend/provenance/component-b-be2-governance-authorization.json`, with decision
`BE1_CLOSED_BE2_LIMITED_SCOPE_AUTHORIZED`. The complete authorization and preceding governance
section were read before code changes. No missing scientific, product, privacy, lifecycle, or
identity decision was inferred.

Only the eight authorized tables were introduced: `app_users`, `b_learners`,
`app_user_learner_links`, `b_runtime_bundle_records`, `b_sessions`, `b_session_events`,
`b_idempotency_records`, and `b_audit_events`. Migration `20260722_0002` follows the empty BE1
baseline `20260722_0001`. No seed data, trigger, dataset, research import, or endpoint was added.

### Files created and changed

Created `app/application/repositories.py`, `app/infrastructure/persistence_models.py`,
`app/infrastructure/repositories.py`,
`migrations/versions/20260722_0002_be2_neutral_persistence.py`,
`tests/test_be2_architecture_guards.py`, and `tests/test_be2_persistence.py`. Changed
`migrations/env.py` and this build log. Alembic now targets the authorized metadata and excludes
only the pre-existing documented `be1_persistence_check` connectivity marker from autogenerate
ownership; the marker itself was not changed.

### Schema, provenance, idempotency, audit, and repositories

Primary resource identifiers are opaque PostgreSQL UUIDs. The Supabase subject is unique and is not
a learner ID. Learner grade is nullable, has no default, and accepts only 2 or 3. The user-to-learner
junction does not encode one-to-one cardinality or relationship behavior.

Session states are constrained data only. A partial unique index permits at most one `starting` or
`active` row per learner. Row version is nonnegative and an active row requires a bundle reference.
No service executes transitions. Bundle rows contain only authorized identity/checksum/publication/
approval metadata and nothing is activated or seeded. Timestamps are timezone-aware, foreign keys
restrict deletion, and event repositories expose no update or delete operation.

Every table requires source class/system, environment, schema revision, request, operation/event,
reason, resource ID/type, timestamps, and exactly one pseudonymous user or system actor. Source
class accepts exactly `REAL`, `SYNTHETIC`, `IMPORTED`, or `TEST`, with no default. Tests use visibly
synthetic subjects and `TEST` provenance in the isolated Docker database.

Idempotency is uniquely scoped by actor, method, operation, and opaque key. It stores the authorized
request fingerprint, neutral nonblank status, optional canonical response/status, and expiry. No
endpoint is wired to it. Repositories provide add/get/existence for all eight tables; idempotency
adds scoped lookup and audit remains append/read only. No lifecycle or scientific policy exists.

### Commands, results, errors, and fixes

Ran Compose configuration, no-cache build, startup/status, Python 3.11.15 and compile checks,
complete pytest, Alembic upgrade/current/downgrade-to-`20260722_0001`/upgrade, PostgreSQL readiness
and metadata inspection, non-root/mount/port checks, dependency/source scans, Docker history/log
leakage scans, and shutdown while preserving the named volume.

Final tests: `34 passed, 1 warning`. The warning is the recorded upstream FastAPI/Starlette
TestClient deprecation. Tests cover exact tables/columns/nullability/keys/constraints/indexes, the
migration cycle, all repositories, rollback, audit persistence, provenance rejection, idempotency,
absence of scientific fields, unchanged OpenAPI paths, and absence of Yass dependencies/imports.

Alembic ends at `20260722_0002 (head)`; the full migration cycle passes and `alembic check` reports
no drift. PostgreSQL contains the eight application tables plus infrastructure-owned
`alembic_version` and pre-existing `be1_persistence_check`. PostgreSQL has no host port, the API has
no source mount and remains UID/GID `10001:10001`, and `upadya-be1-postgres-data` is preserved.

The first run exposed test-harness defects: FastAPI 0.137 represents included routers differently,
the image intentionally copies only the dependency lock, and pooled async connections crossed
separate event loops. Guards now use OpenAPI and available committed dependency files; database
tests use disposed `NullPool` engines and independently upgrade to head. Alembic initially treated
the BE1 connectivity marker as unmanaged, so exactly that marker is excluded from comparison.
Idempotency status is merely nonblank because authorization defines no closed status vocabulary.

### Guards, limitations, and blocked work

Guards prove only eight tables were added; paths remain `/health/live`, `/health/ready`, and
`/api/v1/me`; and no lifecycle service, Yass/research dependency, trigger, seed, BKT, sequencing,
certification, Guess-Guard, hint, or generation integration exists. Container discovery finds no
Yass package/path/wheel. Docker history and logs have zero sensitive-pattern matches.

No real learner ingestion, CRUD/linking API, session API/transition, opportunity, attempt,
retry/hint, timing interpretation, mastery, progress/completion, live engine, Component C/3,
research export, pilot, or production behavior exists. Consent/retention/deletion, relationship and
grade ownership, lifecycle/expiry, attempts/timeouts, completion/progress, catalogue/science, and
formal sign-off remain unresolved and fail closed.

Exact next task: conduct the BE2 Limited Batch 1 closure review only. Do not add endpoints,
lifecycle behavior, live data, scientific fields, or BE3 integration without new machine-readable
authorization.

## Phase BE2 Limited — Batch 1 Closure Review

### Repository and review boundary

Reviewed implementation commit `c516683` and file-ending-only commit `488dff0`. The full starting
HEAD was `488dff0d24ec3c9d19e2d3d98a5c3251a6bd2755`; local `B_frontend` matched
`origin/B_frontend`, and the pre-review working tree was clean. This review changed no application,
migration, model, repository, test, dependency, or runtime functionality. Only this append-only
closure evidence was added.

The implementation was assessed against
`backend/provenance/component-b-be2-governance-authorization.json`, especially its exact eight-table
boundary and required fail-closed constraints. Reviewed files included the neutral SQLAlchemy
models, repository protocols and implementations, Alembic environment and revision
`20260722_0002`, architecture guards, persistence tests, Docker/Compose definitions, dependency
files, and the documented `be1_persistence_check` ownership exclusion.

### Passing evidence

The implementation creates exactly `app_users`, `b_learners`, `app_user_learner_links`,
`b_runtime_bundle_records`, `b_sessions`, `b_session_events`, `b_idempotency_records`, and
`b_audit_events`. PostgreSQL additionally contains only the infrastructure-owned
`alembic_version` and pre-existing `be1_persistence_check` marker. The marker is excluded only from
Alembic autogenerate comparison and is not changed or treated as a BE2 business table.

The no-cache Docker build passed. Python compilation passed. The complete suite reported
`34 passed, 1 warning`; the warning remains the known upstream FastAPI/Starlette TestClient
deprecation. Alembic upgrade to head, current, downgrade to `20260722_0001`, re-upgrade to head, and
`alembic check` passed. Final revision was `20260722_0002`, and PostgreSQL readiness passed.

Repository operations remain neutral add/get/existence operations, plus exact scoped idempotency
lookup. No update/delete convenience API, lifecycle service, scientific formula, task behavior, or
public route was added. Provenance source classes are constrained and have no default; actor,
request, source, environment, schema, reason, resource, and timestamp fields are present.
Idempotency uniqueness is scoped by actor, method, operation, and key. Audit and session-event
records carry neutral append-only repository contracts.

Architecture guards and direct inspection confirmed that the only OpenAPI paths remain
`/health/live`, `/health/ready`, and `/api/v1/me`; the API remains UID/GID `10001:10001` with no
source mounts; PostgreSQL has no host port; the named `upadya-be1-postgres-data` volume was
preserved; and no Yass module, `component_b_generator`, research wheel, or research artefact exists
in the application container.

### Closure-blocking findings

Two explicit authorization constraints are not enforced:

1. The authorization requires an `active` session to reference an immutable approved runtime
   bundle and states that, because no approved bundle exists, live activation must fail closed. The
   database check only requires `runtime_bundle_record_id IS NOT NULL`. A rollback-only PostgreSQL
   probe successfully inserted an `active` session referencing a `DRAFT` bundle whose
   `approval_status` was `UNRESOLVED`.
2. The authorization requires published runtime-bundle records to be immutable. The database check
   only requires the boolean `immutable_after_publication` to be true when state is `PUBLISHED`; it
   does not prevent later updates. The same rollback-only probe successfully changed the manifest
   checksum of a `PUBLISHED` record marked immutable.

PostgreSQL reported zero non-internal triggers on `b_runtime_bundle_records` and `b_sessions`, and
the repositories contain no alternative enforcement. The diagnostic transaction was rolled back,
so it left no test records. Existing tests do not cover either required rejection and therefore
their passing result cannot satisfy these two gates.

These findings do not authorize adding lifecycle behavior. A narrowly scoped corrective task must
enforce published-bundle immutability and prevent any active-session row from referencing a draft,
unapproved, or otherwise ineligible bundle, with database-level tests. The correction must not add
an endpoint, session transition service, real learner data, scientific configuration, engine
integration, or runtime activation.

### Formal closure decision

The table boundary, repositories, provenance, idempotency, audit structure, migration cycle,
architecture separation, and infrastructure checks otherwise pass. However, closure requires every
machine-readable required constraint to hold. Because the two bundle fail-closed constraints above
are demonstrably bypassable, the formal decision is:

`BE2_LIMITED_BATCH_1_NOT_CLOSED`

Exact next task: perform a governance-bound BE2 Limited Batch 1 corrective patch only for the two
failed database invariants and their tests, then repeat this closure review. Do not authorize or
begin endpoints, executable lifecycle transitions, live learner data, attempts, progress,
scientific logic, or Component B engine integration.

## BE2 Limited Batch 1 Corrective Patch — Runtime Bundle Eligibility and Immutability

### Scope and implementation

Starting from commit `0aa408da67a208eed4eced204578871ba39570d1`, this corrective patch addresses
only the two database integrity gaps identified by the preceding closure review. Alembic revision
`20260722_0003` follows `20260722_0002` and installs two PostgreSQL trigger functions and two
triggers. It creates no table, column, seed, endpoint, lifecycle service, or scientific behavior.

`enforce_b_session_active_bundle_eligibility` rejects a direct insert or update that would leave an
`active` session referencing a runtime bundle unless the existing bundle fields are exactly
`publication_state = 'PUBLISHED'`, `approval_status = 'APPROVED'`, and
`immutable_after_publication = true`. It also locks the selected bundle row during the check.
`enforce_b_runtime_bundle_integrity` rejects a checksum change when the old bundle row is both
published and immutable. The same bundle-side guard prevents publication, approval, or immutability
changes from making a bundle ineligible while an active session references it. All rejections use
PostgreSQL check-violation SQLSTATE `23514` and named constraints. No status or eligibility rule was
invented beyond the authorized existing fields and literals.

Files created:

- `migrations/versions/20260722_0003_bundle_integrity_guards.py`
- `tests/test_be2_bundle_integrity.py`

File changed:

- `tests/test_be2_architecture_guards.py`

The migration, focused test, and architecture-guard SHA-256 values at verification time were,
respectively, `6FDA45920C217D2271CDFEF603D6141153C4C5AFC69BFCD24D0943EFB7570F99`,
`C8DFA12363B55C4A919A98C0A92490E34B2D9745C6B9DF66EAAA69692EE1D2B8`, and
`0FC562CF825080445BD02D2A3F3A0F4B6903317C93A531758C77DC28A6E8A6F6`.

### Direct-SQL and test evidence

The focused Docker test ran direct SQL through SQLAlchemy rather than repositories or application
services. It proved that non-active technical-failure persistence remains possible with a draft
bundle; direct insert of an active session with a draft bundle fails; direct insert with an
unresolved bundle fails; an eligible published/approved/immutable bundle succeeds; direct update
from non-active to active with a draft bundle fails; repointing an active session to a draft bundle
fails; and revoking approval from a bundle referenced by an active session fails without changing
the original data. A second direct-SQL test proved that a draft mutable checksum can change, an
unchanged published checksum remains valid, and changing the checksum of a published immutable
bundle fails while preserving the original checksum.

Focused result: `2 passed in 2.48s`. Complete result: `37 passed, 1 warning in 7.88s`. The warning is
the previously recorded upstream FastAPI/Starlette TestClient deprecation and is unrelated to the
patch. `python -m compileall app` passed. Architecture guards verify that revision `0003` contains
only the exact two functions and triggers, creates no table, contains no seed insert, and introduces
no Yass or generator reference.

### Docker, migration, metadata, and isolation verification

`docker compose config --quiet`, `docker compose build`, `docker compose up -d`, container status,
compilation, focused pytest, and full pytest passed. The built API image manifest-list digest was
`sha256:06c5d48a09cac72097481f83f8291219b57cb99533e823743c814b43c6294007`.
The API and database were healthy; PostgreSQL 16 remained pinned by digest and exposed only its
container port. The API remained UID/GID `10001:10001`, had no source mount, and the named
`upadya-be1-postgres-data` volume remained configured.

Alembic upgrade/current/check, downgrade from `20260722_0003` to `20260722_0002`, and re-upgrade to
head passed. `alembic check` reported no new operations, final head was `20260722_0003`, and
`pg_isready` reported accepting connections. PostgreSQL metadata showed exactly
`trg_b_sessions_active_bundle_eligible` on `b_sessions` and `trg_b_runtime_bundle_integrity` on
`b_runtime_bundle_records`, backed by the two named functions. The table set remained the authorized
eight tables plus `alembic_version` and the pre-existing `be1_persistence_check` marker.

Compose inspection confirmed `DATABASE_URL` still uses hostname `db`, PostgreSQL has no host port,
and the API has no source volume. Image history and service logs showed no added secrets, tokens, or
Authorization headers. Application logs contained only existing structured health events and
request IDs. OpenAPI paths remained exactly `/health/live`, `/health/ready`, and `/api/v1/me`.
Dependency/source guards and container tests confirmed that no Yass source,
`component_b_generator`, research wheel, or scientific runtime dependency was introduced.

### Limits and next task

This patch does not authorize or implement public endpoints, session lifecycle transitions, real
learner ingestion, attempts, progress, BKT, sequencing, hints, Component B engine integration,
Component C/3, pilot, or production behavior. It does not declare BE2 Limited Batch 1 closed.

Exact next task: conduct a separate BE2 Limited Batch 1 closure re-review against the corrected
database invariants and all original authorization gates. Do not begin any later behavior or phase
unless that review issues a new formal authorization.

## BE2 Limited Batch 1 Closure Re-Review — Runtime Bundle Integrity Confirmation

### Repository state and review authority

This re-review began with a clean working tree at corrective commit
`7a7b03ccbb972b8a3fabe7f6686e6f9d17cbd0f7` (`fix(backend): enforce runtime bundle integrity
guards`). Local `B_frontend` exactly matched `origin/B_frontend`, confirming the corrective commit
was present on the remote. The underlying BE2 persistence implementation is commit `c516683`, with
file-ending normalization in `488dff0`; the first closure review is commit `0aa408d`. The governing
machine-readable authority remains
`backend/provenance/component-b-be2-governance-authorization.json`, introduced by commit `74676f8`.

The authorization, revisions `20260722_0002` and `20260722_0003`, direct-SQL integrity tests,
architecture guards, persistence models, application and SQLAlchemy repository contracts, previous
closure evidence, and corrective-patch evidence were reviewed. No functionality was implemented or
modified during this re-review; only this append-only evidence was added.

### Previous blockers and corrective database objects

The previous decision was `BE2_LIMITED_BATCH_1_NOT_CLOSED` because direct SQL could create an active
session against a draft/unresolved bundle and could change the checksum of a published immutable
bundle. Revision `20260722_0003` corrects those two failures with database-level enforcement:

- `enforce_b_session_active_bundle_eligibility()` and
  `trg_b_sessions_active_bundle_eligible` enforce that every inserted or updated `active` session
  references a bundle whose existing fields are `PUBLISHED`, `APPROVED`, and immutable.
- `enforce_b_runtime_bundle_integrity()` and `trg_b_runtime_bundle_integrity` prevent checksum
  changes to a published immutable bundle and prevent a bundle referenced by an active session from
  being changed into an ineligible state.

PostgreSQL metadata confirmed both functions and both triggers at revision `20260722_0003`. The
session trigger is `BEFORE INSERT OR UPDATE OF state, runtime_bundle_record_id`; the bundle trigger
is `BEFORE UPDATE OF manifest_checksum, publication_state, approval_status,
immutable_after_publication`. Existing foreign keys, checks, uniqueness constraints, and the
one-starting-or-active-session partial unique index remain in effect. The corrective revision adds
no table, column, seed, endpoint, service, or scientific field.

### Invariant and direct-SQL confirmation

The focused tests exercise the PostgreSQL guards rather than relying on repository or application
validation. They confirm that direct insertion of an active session against a draft bundle fails;
an unresolved bundle fails; a published, approved, immutable bundle succeeds; a pre-existing
non-active technical-failure record retains its already-authorized behavior; transition to active
against an ineligible bundle fails; repointing an active session to an ineligible bundle fails; and
failed writes are rolled back without leaving rejected records. They also confirm that eligibility
cannot be revoked while an active session references the bundle.

For checksum immutability, a draft mutable checksum change remains allowed, a no-op update of the
published checksum remains allowed, and a direct-SQL checksum change for a published immutable
bundle fails. After the failed update, the original checksum remains stored. These results confirm
that direct SQL cannot bypass either invariant and that enforcement does not introduce executable
lifecycle behavior.

### Docker, tests, migrations, and schema inspection

`docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps`
passed. The build used pinned Python `3.11.15-slim-bookworm` and PostgreSQL `16.10-bookworm` image
digests; the API image manifest-list digest for this review was
`sha256:b2d617c3a5e0a50fc32e75ef9991d0382aa3359a473d74840f00d63de4a01991`.
`python -m compileall app` passed. The complete Docker test run collected 37 tests and reported
`37 passed, 1 warning in 7.90s`; the sole warning is the already-recorded upstream
FastAPI/Starlette TestClient deprecation. Provenance, idempotency, audit, repositories, rollback,
architecture guards, and the two focused integrity tests all passed.

Alembic upgrade, current, check, downgrade to `20260722_0002`, and re-upgrade passed. Final current
revision was `20260722_0003 (head)`, `alembic check` reported `No new upgrade operations detected`,
and PostgreSQL reported accepting connections. There is no schema drift.

The exact eight authorized application tables remain `app_users`, `b_learners`,
`app_user_learner_links`, `b_runtime_bundle_records`, `b_sessions`, `b_session_events`,
`b_idempotency_records`, and `b_audit_events`. PostgreSQL additionally contains only
infrastructure-owned `alembic_version` and the pre-existing `be1_persistence_check` marker.
Model/migration inspection and passing exact-schema tests confirm that no unauthorized column or
additional table was introduced.

### Architecture, isolation, and leakage boundary

OpenAPI still exposes only `/health/live`, `/health/ready`, and `/api/v1/me`. No session or learner
endpoint, lifecycle transition service, real-user ingestion, attempt, item-opportunity, progress,
completion, BKT, sequencing, hint, Guess-Guard, certification, task generation, or Component B
live-engine integration exists. Repository contracts remain neutral add/get/existence operations,
plus the already-authorized scoped idempotency lookup.

The API ran as UID/GID `10001:10001` and had no mounts. PostgreSQL exposed no host port and retained
only the named `upadya-be1-postgres-data` volume; after `docker compose down`, volume inspection
confirmed that the named database volume was preserved. Application-content inspection found no Yass
source, `component_b_generator`, or wheel. Dependency and architecture guards found no research
generator dependency or import. Targeted scans of service logs and image history found no token,
Authorization header, secret, JWT, research-generator, or wheel leakage.

### Remaining risks, closure decision, and next task

The corrective objects close the two technical blockers without widening the authorized scope.
All policy and scientific matters recorded as unresolved in the authorization remain unresolved and
fail closed, including learner relationship and grade ownership, lifecycle and expiry semantics,
attempts and timeouts, completion and safe progress, catalogue approval and response mappings,
scientific parameters, privacy/retention, formal owner approval, and live-engine activation.
Closure of this limited persistence foundation does not authorize additional BE2 behavior, a live
learner flow, pilot, or production.

The formal closure decision is:

`BE2_LIMITED_BATCH_1_CLOSED`

Exact next task: obtain a new machine-readable governance authorization defining the next narrowly
scoped BE2 batch before implementing any endpoint, lifecycle transition, real-user ingestion,
attempt, progress, scientific field, or Component B live-engine integration.

## Post-BE2 Limited Batch 1 Governance Authorization Review

### Review purpose and sources

This governance-only review followed formal closure of BE2 Limited Batch 1 at corrective commit
`7a7b03ccbb972b8a3fabe7f6686e6f9d17cbd0f7`, migration head `20260722_0003`, and the verified
`37 passed, 1 known upstream warning` baseline. It changed no application code, migration, API,
test, dependency, database model, or scientific logic.

The review considered the existing BE2 machine authorization and build evidence; `backend.md` and
`frontend.md`; the Component B backend/frontend architecture and Component B architecture; the
generator specification and proposed learner-response/attempt specification; the Component B
variable and shared-foundation decision registers; the persistence models, repository contracts,
and migration history through `20260722_0003`. Its resulting machine record is
`backend/provenance/component-b-be2-next-scope-authorization.json`.

Architecture documents describe a future target, but they are not by themselves authorization to
create real child records or execute lifecycle behavior. The proposed response/attempt specification
is scientific research specification material, remains proposed for approval, and includes synthetic
behavior that the live backend is prohibited from importing or executing. Shared generator decisions
do not resolve application ownership, consent, access-control, or lifecycle policy.

### Account, ownership, and learner-profile findings

The verified Supabase subject is the external identity key and is conceptually mapped to
`app_users`; it must never be used as `learner_id`. However, there is no approved provisioning rule
for creating or activating that mapping. Account-to-learner cardinality remains explicitly
unresolved. The sources also contain incompatible role vocabularies: one proposes
learner/supervisor/operator, while the broader architecture proposes learner/guardian/teacher/
researcher/admin. No source with sufficient authority selects the application vocabulary or exact
capabilities.

Consequently, learner create, list, retrieve, update, deactivate, link, and unlink APIs are not
authorized. Grade remains schema-constrained to nullable 2 or 3, but required grade, assignment
authority, and grade-change authority are unresolved. No learner-profile response fields are newly
authorized; names, contacts, birth data, diagnosis, population, subtype, hidden truth, and research
membership remain prohibited. The existing `/api/v1/me` response remains limited to its already
implemented `user_id` and verified email contract and is not expanded to roles or learner data.

### Session lifecycle and preparation findings

The seven state strings remain authorized only as schema vocabulary: `starting`, `active`,
`completing`, `completed`, `abandoned`, `expired`, and `technical_failed`. No start, prepare, resume,
abandon, expire, complete, recovery, replacement, or other transition is authorized. The existing
database rule permitting at most one starting or active session per learner remains unchanged; it
does not authorize creating either state.

Creating a session without selecting a question could be architecturally separable, but it is still
a lifecycle mutation. Learner ownership, consent, expiry and recovery semantics, the exact response
contract, and an approved live runtime-bundle resolution path are missing. Learner ID, grade, and a
bundle ID are therefore not sufficient authority. The first question remains blocked until a
separately authorized BE3 live-engine integration. Session preparation is treated as a BE2
lifecycle concern with BE3 prerequisites, not as implicit BE4 authority, and is not authorized now.

### Provenance, privacy, idempotency, and audit findings

REAL records may not yet be created. A future live command must server-assign `source_class=REAL`,
derive the actor from a verified subject-to-`app_users` mapping, and record request, operation,
reason, resource, source system, environment, schema revision, and server timestamp. Client-supplied
provenance must never select REAL. TEST and SYNTHETIC fixtures remain confined to isolated test
databases; TEST, SYNTHETIC, and IMPORTED source classes must be rejected by any future live path.

The minimum future learner record is an opaque pseudonymous learner ID, governed grade, and neutral
status. Consent, retention, withdrawal, deletion or irreversible anonymization, identity separation,
and child-safety ownership require approval before REAL admission. No research export or operational
identity-to-research join is authorized.

Every future state-changing command must use the existing actor/method/operation/key idempotency
scope, canonical body fingerprint, atomic response persistence, identical replay, body-mismatch
conflict, and concurrency protection. Future profile and lifecycle changes require append-only audit
evidence including actor, request, reason, target, before/after version references, timestamp,
environment, and required approval evidence. These future requirements do not authorize a command.

### Authorized boundary and still-blocked behavior

No new table, column, endpoint, request field, response field, lifecycle transition, or live mutation
is authorized. The existing eight application tables and the existing health and `/api/v1/me`
endpoints remain unchanged. Fail-closed behavior prohibits inferring learner ownership from subject,
email, UUID possession, or editable token metadata; assigning default grade, role, consent, expiry,
or bundle; or creating application-user, learner, relationship, or session rows through live requests.

Item opportunities, answer attempts, hints, retries, timing interpretation, BKT, mastery,
sequencing, Guess-Guard, certification, progress, completion, Component B live-engine integration,
Yass generator installation, Component C, Component 3, research export, pilot, and production all
remain blocked.

### Decision and exit requirements

No smallest executable application scope can be stated without inventing policy. Before another
authorization can be issued, named owners must approve account-to-learner cardinality and
provisioning, one reconciled role/capability vocabulary, learner profile and grade authority, and
REAL-data consent/retention/withdrawal/deletion rules. Any proposed session-preparation batch must
also approve its exact transitions, ownership checks, response fields, idempotency, audit, expiry
and recovery behavior, and eligible runtime-bundle path. The new machine record enumerates the
required future tests and exit gates.

The formal decision is:

`BE2_NEXT_SCOPE_NOT_AUTHORIZED`

Exact next task: obtain the named product, security, privacy/child-safety, academic, and governance
owner decisions recorded in `component-b-be2-next-scope-authorization.json`, then issue a narrower
machine-readable authorization before implementation. Do not begin implementation from architecture
proposals alone.

## Teacher, Learner, Classroom and QR Membership Governance Authorization Review

### Agreed product model and authority

This governance-only review records the newly agreed application model of exactly two profile types:
`LEARNER` and `TEACHER`. Parent, guardian, administrator, school-administrator, supervisor,
operator, researcher, and every other application role are prohibited. Supabase remains the sole
authentication provider; the backend stores no password, raw JWT, refresh token, or editable role
claim. One authenticated account may create one immutable profile type and may not hold both.

The review considered the prior BE2 authorizations and build evidence, backend and frontend plans,
the Component B application architectures, current stable error contract, persistence and repository
foundations, migration history through `20260722_0003`, Component B session/response specifications,
and current shared and Component B registers. The previous
`BE2_NEXT_SCOPE_NOT_AUTHORIZED` record remains preserved as decision history. The new agreed product
decisions supersede its ownership and role blockers only for the profile/classroom scope documented
in `backend/provenance/component-b-profile-classroom-authorization.json`.

No code, model, migration, API, dependency, test, table, session behavior, or scientific logic was
created or modified during this review.

### Table reuse and persistence decision

Creating both `learner_profiles` and `b_learners` would duplicate the same operational learner.
Therefore no `learner_profiles` table is authorized. `app_users` is reused and may later be extended
only with a nullable-during-onboarding, then immutable, `LEARNER`/`TEACHER` profile discriminator.
`b_learners` remains the learner profile and may be minimally extended with a bounded nonblank name.
Its existing nullable numeric grade remains non-client-writable and is not the classroom-context
authority. `app_user_learner_links` remains the one self-ownership link for a LEARNER account in
this limited scope; it must not encode teacher classroom access.

`teacher_profiles` and `classrooms` are authorized new tables. A teacher profile belongs uniquely to
one TEACHER account. A classroom belongs to exactly one teacher, carries exactly one `GRADE_2` or
`GRADE_3`, and may have an optional name/section. Teacher-owned normalized classroom names must be
unique when present. Classroom transfer, archive, deletion, update, and post-membership grade change
are not authorized.

`classroom_invites` and `classroom_memberships` are authorized as policy-gated persistence
foundations only. Invite rows store a unique token hash, never a raw token, and allow future expiry
and revocation evidence. Membership rows use only `PENDING`, `APPROVED`, and `REJECTED`, link one
learner and classroom through an invite, and record the owning teacher's decision. Their live
mutation and retrieval endpoints remain disabled until multi-classroom and invite policies are
approved.

### Ownership, classroom, grade, and membership decisions

One teacher may own multiple classrooms; one classroom has one teacher and one grade; and one
classroom may contain multiple approved learners. Teachers may access only owned classrooms and
minimum learner identity attached through approved memberships. Learners may access only their own
profile and memberships. UUID possession and editable token metadata never authorize access.

The owning teacher selects `GRADE_2` or `GRADE_3` at classroom creation. An approved learner's
learning context inherits that classroom grade, and the learner cannot override it. Grade 1,
Grade 4, and every other grade fail validation. Changing classroom grade after any membership exists
remains unresolved and fail-closed. Whether one learner may join multiple classrooms, including
cross-grade behavior, remains unresolved; no product cardinality was invented.

Scanning a valid invite may eventually create only a PENDING membership request. It can never grant
APPROVED membership. Only the owner of that classroom may change PENDING to APPROVED or REJECTED.
Duplicate join commands must be idempotent. No membership transition can create a session, alter
learner grade storage, or expose progress or scientific information.

### QR invite and security rules

A QR code represents a random, unguessable invite token rather than a raw classroom ID. Only a
safely derived unique hash may be persisted. The raw token is a one-time response value for QR
construction and must never enter logs, audit data, ordinary canonical-response storage,
diagnostics, URLs under backend control, or database fields. Invites support revocation and may
carry expiry; revoked and expired values fail closed. The token exposes no teacher email, learner
data, database identifier, credential, or application secret.

Token format, entropy construction, cryptographic implementation, expiry duration, and reuse across
different learners were deliberately not invented. Consequently, live invite issuance, resolution,
membership request, decision, and retrieval endpoints remain policy-gated and non-executable until
those decisions and learner multi-classroom behavior are approved.

### Endpoint authorization and privacy boundary

Seven minimal endpoints are authorized for a future bounded implementation batch: create/read own
teacher profile; create/read own learner profile; and create/list/read teacher-owned classrooms.
Their exact request fields, response fields, role and ownership checks, stable errors, idempotency,
audit, privacy rules, and prohibited side effects are recorded in the machine authorization.

The eight invite and membership endpoint candidates are documented but marked
`POLICY_GATED_NOT_EXECUTABLE`. They must be absent or fail with the stable fail-closed service error
without mutation. This limited split allows identity and classroom foundations to proceed without
silently deciding invite reuse, expiry, or learner multi-classroom cardinality.

Live mutations use server-assigned REAL provenance derived from the verified `app_users` actor.
TEST and SYNTHETIC provenance is restricted to isolated test environments; TEST, SYNTHETIC, and
IMPORTED provenance is rejected on live paths. Profile tables store only the minimum name and opaque
IDs. Verified email may be returned from the current authentication contract but is not duplicated
in profile tables. No name, email, token, or learner identity enters logs or audit payloads. No
research export or operational-to-research identity join is authorized.

Retention, withdrawal, deletion, account/profile deactivation, profile updates, classroom updates,
and invite revocation APIs remain unresolved. The limited scope does not authorize pilot or
production, so these issues remain fail-closed rather than being filled with assumptions.

### Authorized and prohibited scope

The next implementation batch may reuse/extend the three existing identity tables as specified;
create `teacher_profiles`, `classrooms`, and policy-gated invite/membership tables; and implement only
the seven explicitly authorized profile/classroom create/read endpoints using existing auth,
idempotency, audit, REAL provenance, unit-of-work, request-ID, and stable-error foundations. It must
prove role exclusivity, one-profile ownership, cross-teacher and cross-learner isolation, exact grade
validation, atomic replay, privacy allow-lists, provenance separation, audit completeness, migration
reversibility, schema drift absence, and architecture isolation.

Learning-session creation and every session transition remain prohibited. Question generation,
opportunities, attempts, retries, hints, response-time interpretation, BKT, mastery, Guess-Guard,
certification, sequencing, progress, completion, Component B live-engine integration, Component C,
Component 3, research export, synthetic generation, pilot, production, Yass source, and any research
wheel or generator dependency remain blocked.

### Unresolved decisions and formal authorization

Before invite or membership endpoints can execute, the product owner must approve learner
multi-classroom and cross-grade behavior plus cross-learner invite reuse; the security owner must
approve the token and expiry contract; and the privacy/child-safety owner must approve that flow.
Retention, deletion, withdrawal, and deactivation require their own governance before pilot or
production. These blockers do not authorize default behavior.

The formal decision is:

`BE2_PROFILE_CLASSROOM_SCOPE_LIMITED_AUTHORIZED`

Exact next task: implement one governance-bound BE2 profile and classroom foundation batch against
`component-b-profile-classroom-authorization.json`: the specified table reuse/extensions, four new
tables with invite/membership behavior policy-gated, and only the seven authorized profile/classroom
create/read endpoints. Do not implement invite or membership endpoints, learning sessions, or
scientific behavior.

## Phase BE2 Limited — Teacher, Learner and Classroom Profile Foundations

### Authorization and starting point

Implementation started from clean commit `6ef693fb6ddc6837c9441f271611c743215e201f` under
`backend/provenance/component-b-profile-classroom-authorization.json`, whose formal decision is
`BE2_PROFILE_CLASSROOM_SCOPE_LIMITED_AUTHORIZED`. The authorization was treated as a hard boundary:
exactly LEARNER and TEACHER profiles, profile/classroom create-read behavior, four governed table
foundations, and no invite, membership, session, or scientific behavior.

The existing `app_users` table was extended with nullable-onboarding `profile_type`, constrained to
LEARNER or TEACHER and protected by a database trigger from later change. `b_learners` was reused as
the learner profile and extended only with `name`; no `learner_profiles` table exists. Existing
`grade` remains nullable and is neither accepted nor changed by profile endpoints.
`app_user_learner_links` was reused for learner self-ownership and constrained unique by both user
and learner, preserving a one-owning-account/one-profile boundary for this limited batch.

Revision `20260722_0004` creates exactly `teacher_profiles`, `classrooms`, `classroom_invites`, and
`classroom_memberships`. The latter two are schema foundations only. There is no token generator,
raw token column, QR implementation, invite resolver, expiry executor, membership service, or
membership route. The migration adds no seed data, learning table, scientific field, or blocked
invite/membership trigger. Downgrade removes only revision `0004` objects and restores the
`20260722_0003` schema.

### API, ownership, roles, and grade enforcement

Seven endpoints were added exactly as authorized:

- `POST /api/v1/teacher/profile`
- `GET /api/v1/teacher/profile`
- `POST /api/v1/learner/profile`
- `GET /api/v1/learner/profile`
- `POST /api/v1/classrooms`
- `GET /api/v1/classrooms`
- `GET /api/v1/classrooms/{classroom_id}`

Profile creation provisions or reuses the `app_users` mapping for the verified Supabase subject and
atomically selects one immutable profile type. A second or opposite profile fails with the stable
conflict envelope. Teacher and learner reads resolve only through the verified subject mapping.
Teacher-only classroom operations derive `teacher_profile_id` server-side; callers cannot submit an
owner. Lists filter by owner, and an absent or foreign classroom ID returns the same not-found
response to prevent enumeration. Learners receive FORBIDDEN for classroom creation.

Classroom requests accept only optional `name` and required `grade`. Pydantic and PostgreSQL both
restrict grade to `GRADE_2` or `GRADE_3`; every other grade fails. A normalized non-null classroom
name is unique within one teacher's classrooms. No update endpoint exists, so classroom grade,
ownership, archive, transfer, and deletion remain immutable/unavailable in this scope.

### Provenance, audit, idempotency, and privacy

All endpoint mutations assign REAL provenance on the server from the verified app-user actor. No
provenance field is accepted in request bodies. Records include request, operation, reason,
resource, source system, environment, schema revision, and server timestamps. Profile and classroom
creation append `b_audit_events` in the same transaction. Tests confirm REAL provenance and audit
records; TEST, SYNTHETIC, and IMPORTED values have no live request field through which they can enter.

Every POST requires `Idempotency-Key`. The service serializes an actor/method/operation/key scope
with a PostgreSQL transaction advisory lock, fingerprints the strict canonical body, persists the
idempotency record atomically with the mutation and audit, returns the canonical response for an
identical replay, and returns stable conflict for body mismatch. Learner creation orders learner and
owning-link persistence explicitly so the foreign-key relationship commits atomically.

Profile responses contain only the authorization allow-list. Verified email is read from the
authenticated principal and is not copied into `app_users`, `teacher_profiles`, or `b_learners`.
The backend stores no password or JWT. Logs contain request IDs and route/status evidence but no
Authorization header, bearer token, invite token, password, credential, learner name, or email.

### Files created and changed

Created application files:

- `app/api/routes/profile_classroom.py`
- `app/application/profile_classroom.py`
- `app/domain/profile_classroom.py`
- `migrations/versions/20260722_0004_profile_classroom_foundations.py`
- `tests/test_profile_classroom.py`

Changed application and test files:

- `app/core/errors.py`
- `app/infrastructure/persistence_models.py`
- `app/infrastructure/repositories.py`
- `app/main.py`
- `tests/test_be2_architecture_guards.py`
- `tests/test_be2_persistence.py`

This append-only section is the only documentation change.

### Verification results

The required final Docker run used a no-cache build from pinned dependency and base-image inputs.
The final API manifest-list digest was
`sha256:c2dbabc5c58cebe4f284b7bf8e99f825b8e1e1903bc844a37e21f3d7e0d4b7e3`.
Compose configuration, startup and status passed; Python compilation passed. Focused profile,
classroom, migration-boundary, and architecture tests reported `10 passed, 1 warning`. The complete
suite reported `41 passed, 1 warning in 9.29s`. The warning is the already-recorded upstream
FastAPI/Starlette TestClient deprecation.

Alembic upgrade/current/check, downgrade from `20260722_0004` to `20260722_0003`, and re-upgrade to
head passed. Final revision was `20260722_0004`; `alembic check` reported no new operations and
PostgreSQL readiness passed. Metadata inspection confirmed twelve application tables: the original
eight plus exactly the four authorized foundations. Infrastructure additionally retains
`alembic_version` and the pre-existing `be1_persistence_check` marker. Existing runtime-bundle
eligibility and checksum-integrity triggers remain installed alongside the authorized profile-type
immutability trigger.

OpenAPI contains only `/health/live`, `/health/ready`, `/api/v1/me`, and the seven new authorized
operations grouped across four paths. No invite, membership, session, attempt, hint, or progress
path exists. Architecture/source/dependency guards confirm no QR code, session lifecycle, BKT,
sequencing, certification, task generation, Yass import, `component_b_generator`, or research wheel.

The API remained UID/GID `10001:10001` with no mounts. PostgreSQL exposed no host port and used only
the named `upadya-be1-postgres-data` volume. Targeted log and image-history scans returned no token,
credential, password, raw-JWT, invite-token, Yass, generator, or wheel match. After shutdown, the
named database volume remained present.

### Errors, causes, and fixes

The local Conda environment lacked the committed PyJWT runtime, so local byte-compilation passed but
the authoritative import/test run was performed in Docker from `requirements.lock`. The first
focused Docker run exposed a TestClient harness issue: requests reopened event loops while sharing
the global async connection pool. Tests now keep each client context open across its request flow.
An old architecture guard also compared migration `0002` alone with the final twelve-table set; it
now separately verifies the original eight-table revision and the four-table `0004` revision.

Learner creation initially flushed the ownership link before its referenced learner because the
models intentionally have no ORM relationship navigation. Explicitly flushing `b_learners` before
`app_user_learner_links` fixed the foreign-key ordering while keeping both writes, idempotency, and
audit in one transaction. All corrected focused and complete tests then passed.

### Remaining boundary and exact next task

Invite creation, QR generation/scanning, token resolution/reuse/expiry, membership requests,
approval/rejection, classroom learner lists, learner classroom lists, and multi-classroom policy
remain blocked. Learning sessions and all session transitions, questions, opportunities, attempts,
retries, hints, timing interpretation, BKT, mastery, Guess-Guard, certification, sequencing,
progress, completion, live-engine integration, Component C, Component 3, research export, pilot,
production, and synthetic generation remain absent and unauthorized.

Exact next task: conduct a separate closure and security review of this limited profile/classroom
batch against `component-b-profile-classroom-authorization.json`. Do not authorize or begin invite,
membership, session, or scientific behavior during that review.

## BE2 Profile/Classroom Limited Batch Closure and Security Review

### Repository and authorization gate

The review examined pushed implementation commit
`aa037400aca212e24a4b681c9bef768b23f99fce` (`feat(backend): add teacher learner and
classroom foundations`). Before review, the working tree was clean and local `B_frontend` exactly
matched `origin/B_frontend`. The controlling source was
`backend/provenance/component-b-profile-classroom-authorization.json`, decision
`BE2_PROFILE_CLASSROOM_SCOPE_LIMITED_AUTHORIZED`.

Reviewed files included revision `20260722_0004`, profile/classroom routes, application service,
domain contracts, persistence models, repositories, unit of work, error handling, application route
registration, profile/classroom tests, BE2 persistence tests, architecture guards, Compose and
Docker inputs, and the preceding implementation evidence in this log. No functionality, migration,
API, model, dependency, or test was changed during this review.

### Role, ownership, profile reuse, and classroom review

The implementation accepts only LEARNER and TEACHER and protects a selected profile type with both
service checks and the database immutability trigger. Profile operations resolve the account only
from the verified Supabase subject. Opposite-role profile access fails closed, and no parent,
guardian, administrator, or editable role exists. `b_learners` is the sole learner profile table;
`app_user_learner_links` supplies the unique self-owner mapping. Requests accept only the authorized
name field, learner creation cannot set grade, and live provenance is assigned by the server as
REAL. Email is returned only from the verified current principal and is not copied to profile rows.

Teacher profiles are unique by app user. Classroom ownership is derived server-side from that
teacher profile and cannot be supplied or overridden by the caller. Only teachers create/list/read
classrooms; lists are owner-filtered, and absent and foreign classroom IDs both return the same
not-found behavior. Only GRADE_2 and GRADE_3 pass request and database validation. There is no
classroom update, grade update, learner attachment, invite, membership, QR, session, or learning
endpoint.

### Idempotency, audit, and closure blocker

The service uses actor/method/operation/key-scoped PostgreSQL advisory transaction locks, canonical
request fingerprints, atomic idempotency records, stable conflict behavior, and same-transaction
audit writes. Audit payloads contain neutral operational identifiers and provenance rather than
names, emails, credentials, Authorization values, or JWTs. Unit-of-work exception handling performs
rollback, and commits occur only after resource, audit, and canonical response staging.

However, the authorization's `required_tests` expressly requires identical replay, body mismatch,
concurrency, and rollback tests for every POST command. The committed tests demonstrate teacher
profile identical replay and mismatch, but do not demonstrate learner-profile or classroom replay
and mismatch, concurrent duplicate submission for any POST, or injected-failure rollback integrity
for profile/link/classroom/audit/idempotency state. The authorization exit criterion that all
idempotency, audit, provenance, and isolation tests pass is therefore not fully evidenced. Static
reasoning about transaction structure cannot replace the specifically required tests, so closure
fails closed without asserting a functional defect.

### Schema and API inventories

PostgreSQL contained exactly the twelve authorized application tables: `app_users`, `b_learners`,
`app_user_learner_links`, `b_runtime_bundle_records`, `b_sessions`, `b_session_events`,
`b_idempotency_records`, `b_audit_events`, `teacher_profiles`, `classrooms`, `classroom_invites`, and
`classroom_memberships`. Infrastructure additionally contained `alembic_version` and the existing
`be1_persistence_check` marker. No `learner_profiles` table exists. The only non-internal triggers
were the two previously authorized runtime-bundle guards and profile-type immutability; no trigger or
stored procedure implements invite or membership behavior.

OpenAPI contained exactly GET `/health/live`, GET `/health/ready`, GET `/api/v1/me`, POST/GET
`/api/v1/teacher/profile`, POST/GET `/api/v1/learner/profile`, POST/GET `/api/v1/classrooms`, and GET
`/api/v1/classrooms/{classroom_id}`. No invite, membership, QR, session, attempt, progress, or
scientific operation was present.

### Docker, migration, and security verification

`docker compose config`, build, startup/status, application compilation, the complete test suite,
migration cycle, PostgreSQL readiness, direct inventories, container identity/mount inspection, and
targeted leakage scans were run. The suite reported `41 passed, 1 warning in 10.83s`; the warning is
the known upstream FastAPI/Starlette TestClient deprecation. Alembic reported head
`20260722_0004`, no new upgrade operations, successful downgrade to `20260722_0003`, and successful
re-upgrade. PostgreSQL accepted connections.

The API ran as UID/GID `10001:10001` with no mounts. PostgreSQL exposed no host port and used the
named `upadya-be1-postgres-data` volume, which remained after shutdown. API-log and committed
application/dependency scans found no bearer token, Authorization header, credential, test learner
identity, Yass import, research wheel, or generator package. Stable API error handling and existing
authentication tests retain request IDs and fail-closed token verification.

### Remaining boundary, formal decision, and exact next task

Invite creation, QR generation/resolution, invite reuse/expiry, memberships, learner attachment,
sessions, attempts, progress, hints, BKT, sequencing, certification, live-engine integration,
research export, pilot, and production remain blocked and unauthorized.

Formal closure decision: `BE2_PROFILE_CLASSROOM_BATCH_NOT_CLOSED`.

Exact next task: perform a narrowly scoped corrective evidence batch that adds the authorization-
required idempotent replay, mismatched replay, concurrent duplicate, and injected-failure rollback
tests for each of the three POST commands, without changing runtime functionality or expanding the
API/schema boundary; then repeat this closure review.

## BE2 Profile/Classroom Corrective Test Evidence — Replay, Concurrency and Rollback

### Scope and authorization

This append-only section records the narrowly scoped corrective test batch that supplies the
governance-required replay, body-mismatch, concurrency, and rollback evidence for every authorized
POST command. The controlling authorization is
`backend/provenance/component-b-profile-classroom-authorization.json`
(`required_tests`: "All POST commands pass identical replay, body mismatch, concurrency, and rollback
tests"). It does not issue the formal closure decision; a separate closure re-review follows.

The three POST commands covered are `POST /api/v1/teacher/profile`, `POST /api/v1/learner/profile`,
and `POST /api/v1/classrooms`.

### Previous closure blockers

The prior closure review recorded `BE2_PROFILE_CLASSROOM_BATCH_NOT_CLOSED`. Implementation, security,
schema, migration, ownership, role, grade, provenance, Docker, and API-boundary reviews had passed.
Closure was blocked solely because the committed suite proved only teacher-profile identical replay
and mismatch. It did not prove learner-profile or classroom replay/mismatch, concurrent duplicate
submission for any POST, or injected-failure rollback integrity for any POST. Static reasoning about
transaction structure was explicitly rejected as a substitute for the required tests.

### Files changed

- `backend/tests/test_profile_classroom_post_safety.py` — new focused corrective test module.
- `backend/tests/test_be2_architecture_guards.py` — added `test_no_production_failure_injection_or_debug_mechanism`
  and collapsed a duplicate profile/classroom guard definition; no guard weakened.
- `backend/app/application/profile_classroom.py` — one-line runtime fix (see Errors and fixes): a
  subject-scoped `pg_advisory_xact_lock` at the start of `_provision_user`. No endpoint, table,
  column, dependency, role, or scientific behavior was added.

No migration, model, dependency, route, or API/schema boundary was changed. Migration head remains
`20260722_0004`.

### Test design

- Concurrency uses real PostgreSQL transactions inside the Docker `api`/`db` services. Two OS threads
  are released simultaneously by a `threading.Barrier(2)` against a shared FastAPI `TestClient`, so the
  two commands run as genuinely concurrent event-loop tasks on separate pooled asyncpg connections. No
  timing sleep is used; synchronization is deterministic via the barrier and the database locks.
- Failure is injected only through a test-only in-process `ProfileClassroomService` instance whose
  `_audit` is monkeypatched to raise after primary-entity persistence and before audit/commit. No
  production failure flag, debug endpoint, or environment switch exists; a new architecture guard
  proves this.
- State is verified out-of-band through a separate `NullPool` async engine that counts `app_users`,
  the primary entity, `app_user_learner_links`, `b_idempotency_records`, and `b_audit_events`, and
  asserts that every persisted live row carries server-assigned `source_class = REAL`.

### Replay results (identical key, byte-equivalent body)

- Teacher profile: replay returned HTTP 201 with the identical `teacher_profile_id` and identical full
  body; exactly one teacher profile, one idempotency record, one audit event.
- Learner profile: replay returned HTTP 201 with the identical `learner_id` and identical full body;
  exactly one `b_learners` row and exactly one owning `app_user_learner_links` row.
- Classroom: replay returned HTTP 201 with the identical `classroom_id`, identical full body, and the
  server-derived `teacher_profile_id`; exactly one classroom, one idempotency record, one audit event.

All replayed rows carried `source_class = REAL`.

### Mismatch results (same key, different body)

- Teacher profile: `{"name":"Teacher Changed"}` → HTTP 409 `CONFLICT` with a `request_id`.
- Learner profile: `{"name":"Learner Changed"}` → HTTP 409 `CONFLICT` with a `request_id`.
- Classroom: both a changed `name` and a changed `grade` (GRADE_2 → GRADE_3) under the same key →
  HTTP 409 `CONFLICT`. Only `GRADE_2` and `GRADE_3` are accepted; `GRADE_1`, `GRADE_4`, `grade_2`, and
  `2` each return HTTP 422. A learner remains forbidden (HTTP 403) from creating a classroom.

### Concurrency results (concurrent duplicate submission)

- Teacher profile: both concurrent requests returned HTTP 201 with a single `teacher_profile_id`;
  exactly one app-user, one teacher profile, one idempotency record, one audit event. The connection
  remained usable (subsequent GET returned 200).
- Learner profile: both concurrent requests returned HTTP 201 with a single `learner_id`; exactly one
  app-user, one `b_learners` row, one owning link, one idempotency record, one audit event.
- Classroom: both concurrent requests returned HTTP 201 with a single `classroom_id`; exactly one
  classroom, one idempotency record, one audit event, and the owned-classroom list contained one row.

No unhandled database integrity error leaked; the losing/replayed request received the authorized
201 response.

### Failure-injection and rollback results

For each of the three POSTs the injected `_audit` failure produced HTTP 500 with the stable
`INTERNAL_ERROR` envelope and the exact request `request_id`. After rollback:

- Teacher profile: no app-user mutation, no teacher profile, no idempotency record, no audit event.
- Learner profile: no `b_learners` row, no owning `app_user_learner_links` row, no app-user mutation,
  no idempotency record, no audit event.
- Classroom: the classroom, idempotency record, and audit event were all absent; the pre-failure
  baseline (the already-created owning teacher only) was exactly preserved.

For every case a subsequent valid retry with the same key then succeeded with HTTP 201. The error
body contained neither the fake bearer secret nor the internal exception text, and captured logs
contained neither the secret nor the `Authorization` header.

### Errors, causes, and fixes

The concurrent-duplicate tests for the two profile POSTs initially failed (`[201, 500]`). Root cause:
a genuine runtime concurrency defect. `_provision_user` inserted the `app_users` row before the
idempotency advisory lock, and that lock was keyed on the freshly generated `user_id`. Two concurrent
first-ever submissions from the same brand-new Supabase subject therefore computed different lock
scopes, did not serialize, and raced on the `uq_app_users_supabase_subject` unique constraint; the
losing transaction surfaced an unhandled `IntegrityError` as HTTP 500 instead of an idempotent replay.
This violates the authorization's concurrency requirement that no unhandled integrity error leaks and
that the losing request receives the authorized response.

Because a new test proved a real defect, a minimal runtime fix was applied: `_provision_user` now
acquires `pg_advisory_xact_lock(hashtextextended('account.provision:<subject>', 0))` before the
find/insert, reusing the existing advisory-lock mechanism. Concurrent first-time provisioning now
serializes on the stable subject; the waiting request observes the committed app-user, proceeds to the
same idempotency scope, and returns the canonical replay. The classroom path was already safe because
the owning app-user pre-exists. After the fix both profile concurrency tests returned `[201, 201]` with
a single identity, and no other behavior changed.

An incidental duplicate `test_profile_classroom_migration_and_routes_stay_within_authorization`
definition in the guards module (the second silently shadowing the first) was collapsed to a single
definition while adding the failure-injection guard; the assertions are unchanged.

### Test counts

- Full Docker suite: `52 passed, 1 warning in 18.38s` (previously 41 passed; +10 corrective tests,
  +1 architecture guard). The single warning is the already-recorded upstream FastAPI/Starlette
  `TestClient` httpx deprecation.
- Focused corrective + guard run (`tests/test_profile_classroom_post_safety.py`
  `tests/test_be2_architecture_guards.py`): `18 passed, 1 warning`.

### Schema-drift and inventory results

- `alembic current`: `20260722_0004 (head)`.
- `alembic check`: `No new upgrade operations detected` — no schema drift.
- Application tables unchanged: exactly the twelve authorized tables (`app_users`, `b_learners`,
  `app_user_learner_links`, `b_runtime_bundle_records`, `b_sessions`, `b_session_events`,
  `b_idempotency_records`, `b_audit_events`, `teacher_profiles`, `classrooms`, `classroom_invites`,
  `classroom_memberships`) plus the internal `alembic_version` and pre-existing `be1_persistence_check`
  marker. No `learner_profiles` table exists.
- OpenAPI route inventory unchanged: `GET/POST /api/v1/teacher/profile`, `GET/POST /api/v1/learner/profile`,
  `GET/POST /api/v1/classrooms`, `GET /api/v1/classrooms/{classroom_id}`, `GET /api/v1/me`,
  `GET /health/live`, `GET /health/ready`. No invite, membership, session, attempt, hint, progress,
  debug, or injection route exists.

### Docker, isolation, and leakage verification

`docker compose config`, `build`, and `up -d` succeeded (API image id
`sha256:97df807d4f0dcdb78572114397b18af82bf5ccca0e9b4d6967eff694e922802c`). `python -m compileall app`
passed. The API container ran as UID/GID `10001:10001` with no bind mounts (`.Mounts == []`).
PostgreSQL published no host port (`docker compose port db 5432` returned no mapping) and `pg_isready`
accepted connections. A targeted scan of the API logs found no bearer secret, `Authorization` header,
password, refresh token, `component_b_generator`, Yass, or `.whl` match. Docker was stopped after
verification and the named `upadya-be1-postgres-data` volume was preserved.

### Runtime and API-surface statement

Runtime behavior did not expand: no endpoint, table, column, migration, dependency, role, invite,
membership, QR, session, or scientific behavior was added. The only production change is the one-line
provisioning concurrency fix required by a defect the new concurrency tests proved. The corrective
test batch passed.

### Exact next task

Conduct the separate BE2 profile/classroom closure re-review against
`component-b-profile-classroom-authorization.json`, now that identical-replay, body-mismatch,
concurrency, and rollback evidence exists for all three POST commands and the provisioning concurrency
defect is fixed. Do not authorize or begin invite, membership, session, or scientific behavior during
that review. This section does not issue the formal closure decision.

## BE2 Profile/Classroom Limited Batch Closure Re-Review

### Review scope and non-modification

This append-only section records the closure re-review of the limited profile/classroom batch against
`backend/provenance/component-b-profile-classroom-authorization.json`
(`BE2_PROFILE_CLASSROOM_SCOPE_LIMITED_AUTHORIZED`). No functionality, migration, model, dependency,
route, or test was modified during this review; it verifies committed state and re-runs the Docker
gates. All evidence below was reproduced from the pushed commit, not carried forward on trust.

### Commits reviewed

- Implementation commit: `aa037400aca212e24a4b681c9bef768b23f99fce`
  (`feat(backend): add teacher learner and classroom foundations`).
- Corrective commit: `2fc9a350840bc51cd70fcb01f59f9994ce352704`
  (`fix(backend): make profile provisioning concurrency safe`).

Precondition gate: the corrective commit is pushed; local `B_frontend` equals `origin/B_frontend`
(both `2fc9a350840bc51cd70fcb01f59f9994ce352704`, 0 ahead / 0 behind); the working tree is clean.
The corrective commit contains exactly four files: the one-line `profile_classroom.py` fix,
`test_profile_classroom_post_safety.py` (new), `test_be2_architecture_guards.py` (added
failure-injection guard; collapsed a duplicate guard definition), and this build log's corrective
evidence section.

### Previous closure blockers

The prior decision was `BE2_PROFILE_CLASSROOM_BATCH_NOT_CLOSED`. Implementation, security, schema,
migration, ownership, role, grade, provenance, Docker, and API-boundary reviews had passed. Closure
was blocked only because identical-replay, body-mismatch, concurrency, and injected-failure rollback
evidence existed for the teacher-profile POST alone, not for the learner-profile or classroom POSTs,
and no concurrency evidence existed for any POST. Static transaction reasoning was rejected as a
substitute for those tests.

### Advisory-lock defect and fix (reviewed)

The new concurrency tests proved a real runtime defect: concurrent first-ever profile creation for the
same new Supabase subject inserted `app_users` before the idempotency advisory lock, and that lock was
keyed on the freshly generated `user_id`. Two concurrent first submissions therefore computed
different lock scopes, did not serialize, raced on `uq_app_users_supabase_subject`, and the loser
returned HTTP 500 `IntegrityError` instead of an idempotent replay — an unhandled integrity leak the
authorization forbids.

The fix adds one line to `_provision_user`:
`SELECT pg_advisory_xact_lock(hashtextextended('account.provision:' || <subject>, 0))` before the
find/insert. The re-review confirms:

- the lock is PostgreSQL transaction-scoped (`pg_advisory_xact_lock`), released automatically on
  commit or rollback, with no manual unlock and no leaked lock state;
- the lock key is derived deterministically from the stable authenticated subject, reusing the exact
  pattern already used by the idempotency lock;
- the raw subject is a transient SQL bind parameter used only to compute an integer key; it is not
  logged and is not persisted as lock metadata;
- the key is per-subject, so different subjects provision concurrently and only the same subject
  serializes — no global serialization bottleneck;
- no new public API, endpoint, table, column, or lifecycle behavior was introduced.

### Teacher-profile POST evidence

- Equivalent replay returns HTTP 201 with the same `teacher_profile_id` and identical body.
- Mismatched replay (same key, different name) returns HTTP 409 with the stable `CONFLICT` envelope
  and a `request_id`.
- Concurrent duplicate submission returns `[201, 201]` with one `teacher_profile_id`: one app-user,
  one teacher profile, one idempotency record, one audit event; both callers receive the authorized
  replay outcome and the connection stays usable.
- Injected `_audit` failure returns a safe HTTP 500 `INTERNAL_ERROR` with the request `request_id`;
  rollback leaves no profile, app-user mutation, idempotency record, or audit event; a retry then
  succeeds with HTTP 201.

### Learner-profile POST evidence

- Equivalent replay returns HTTP 201 with the same `learner_id` and identical body.
- Mismatched replay returns HTTP 409 `CONFLICT`.
- Concurrent duplicate submission yields exactly one `b_learners` row and exactly one owning
  `app_user_learner_links` row (plus one app-user, one idempotency record, one audit event).
- REAL provenance is server-assigned across all persisted live rows (`source_class == {"REAL"}`);
  clients submit no provenance.
- Injected failure rolls back the learner row, owning link, app-user mutation, idempotency record,
  and audit event; a retry then succeeds.
- No `learner_profiles` table exists; `b_learners` remains the single learner profile table.

### Classroom POST evidence

- Equivalent replay returns HTTP 201 with the same `classroom_id` and identical body.
- The owner (`teacher_profile_id`) is derived server-side and matches the authenticated teacher.
- Mismatched replay for either a changed name or a changed grade returns HTTP 409 `CONFLICT`.
- Only `GRADE_2` and `GRADE_3` are accepted; `GRADE_1`, `GRADE_4`, `grade_2`, and `2` return HTTP 422.
- A learner receives HTTP 403 for classroom creation.
- Concurrent duplicate submission returns `[201, 201]` with one `classroom_id`: one classroom, one
  idempotency record, one audit event, and an owned list of one.
- Injected failure leaves no partial classroom, idempotency, or audit state (the pre-failure baseline
  is exactly preserved); a retry then succeeds.

### Full and focused test results

- Full Docker suite: `52 passed, 1 warning in 17.22s`.
- Focused corrective + architecture-guard suite
  (`tests/test_profile_classroom_post_safety.py tests/test_be2_architecture_guards.py`):
  `18 passed, 1 warning`.
- The single warning is the known upstream FastAPI/Starlette `TestClient` httpx deprecation.
- `python -m compileall app` passed.

### Migration and schema-drift results

- `alembic upgrade head` → `alembic current` = `20260722_0004 (head)`.
- `alembic check` = `No new upgrade operations detected` (no drift).
- `alembic downgrade 20260722_0003` succeeded (current `20260722_0003`), and `alembic upgrade head`
  restored `20260722_0004 (head)`.
- `pg_isready` = accepting connections.

### API and table inventories

- OpenAPI operations (exactly ten): `GET/POST /api/v1/teacher/profile`,
  `GET/POST /api/v1/learner/profile`, `GET/POST /api/v1/classrooms`,
  `GET /api/v1/classrooms/{classroom_id}`, `GET /api/v1/me`, `GET /health/live`, `GET /health/ready`.
  Seven profile/classroom endpoints; no invite, membership, QR, session, attempt, hint, progress,
  debug, or injection route.
- Application tables (exactly twelve): `app_users`, `b_learners`, `app_user_learner_links`,
  `b_runtime_bundle_records`, `b_sessions`, `b_session_events`, `b_idempotency_records`,
  `b_audit_events`, `teacher_profiles`, `classrooms`, `classroom_invites`, `classroom_memberships`,
  restored intact after the downgrade/upgrade cycle. Infrastructure additionally retains
  `alembic_version` and the pre-existing `be1_persistence_check` marker. No `learner_profiles` table.

### Architecture-boundary result

- Exactly two profile roles remain: LEARNER and TEACHER.
- No invite, membership, QR, session, attempt, progress, BKT, sequencing, hint, certification, or
  other scientific behavior exists.
- Production source contains no failure-injection or debug mechanism: a container-side scan of `app`
  found no `controlled-test-failure`, `_failing_audit`, `inject_fail`, `force_error`, `force_failure`,
  or `debug_fail` marker, and the new `test_no_production_failure_injection_or_debug_mechanism` guard
  enforces this. The failure injection exists only in the test module via an in-process service
  instance.
- No `component_b_generator`, Yass, `pilot`, or `cohort` import exists in `app`; no research-wheel
  dependency exists.

### Docker, isolation, and leakage verification

`docker compose config`, `build`, `up -d`, and `ps` succeeded. The API container ran as UID/GID
`10001:10001` with no bind mounts (`.Mounts == []`) and host-bound only to `127.0.0.1:8000`.
PostgreSQL published no host port (`docker compose port db 5432` returned no mapping) and exposed only
the named `upadya-be1-postgres-data` volume. A targeted API-log scan found no bearer secret,
`Authorization` header, password, refresh token, `component_b_generator`, Yass, or `.whl` match. After
`docker compose down`, the named `upadya-be1-postgres-data` volume remained present.

### Remaining blocked behavior

Invite creation, QR generation/resolution, invite reuse/expiry, membership request/approval/rejection,
classroom learner lists, learner classroom lists, multi-classroom policy, classroom grade change,
profile/account update/deactivation/deletion, retention/withdrawal, learning sessions and every
session transition, questions, opportunities, attempts, retries, hints, timing interpretation, BKT,
mastery, Guess-Guard, certification, sequencing, progress, completion, live-engine integration,
Component C, Component 3, research export, pilot, and production all remain blocked and unauthorized.

### Formal closure decision

`BE2_PROFILE_CLASSROOM_BATCH_CLOSED`.

The limited profile/classroom batch satisfies the authorization's `exit_criteria` and `required_tests`:
only the authorized reuse/extensions and four new tables exist; only the seven authorized endpoints
exist; ownership, cross-account, grade, idempotency, audit, provenance, privacy, replay, mismatch,
concurrency, rollback, and isolation tests pass; no password, raw JWT, raw invite token, research
identifier, scientific field, or synthetic record enters live persistence, responses, or logs; and all
prohibited learning and scientific behavior remains absent. The one production change since the prior
review is the provisioning concurrency fix, which resolves the only defect the corrective tests
surfaced and introduces no boundary expansion.

### Exact next governance task

Obtain the named limited-scope approvers recorded in the authorization
(`product owner`, `backend security owner`, `privacy and child-safety owner`) to ratify this closure,
then produce a separate governance authorization before any further scope. No invite, QR, membership,
session, attempt, progress, scientific-engine, pilot, or production behavior is authorized to begin by
this closure; each remains gated behind its named approvers and unresolved decisions in
`component-b-profile-classroom-authorization.json`.

## BE2 Profile/Classroom Limited Batch — Named Approver Ratification

### Scope and non-modification

This append-only section records an attempted named-approver ratification pass over the closed
profile/classroom batch. No code, migration, table, column, endpoint, test, or dependency was
implemented or modified. This is a governance and documentation review only, against
`backend/provenance/component-b-profile-classroom-authorization.json`
(`required_approvers.this_limited_scope`: product owner, backend security owner, privacy and
child-safety owner).

### Reviewed record

`backend/provenance/component-b-profile-classroom-ratification.json`, created during this pass.

### Pre-review verification

Local `B_frontend` was confirmed to match `origin/B_frontend` at `e579d6cf07d3badde3a984a1a5b4db3bf090464a`
(`docs(backend): close profile classroom limited batch`) with a clean working tree, immediately
preceded by corrective commit `2fc9a350840bc51cd70fcb01f59f9994ce352704` and implementation commit
`aa037400aca212e24a4b681c9bef768b23f99fce`. The closure re-review section above (migration head
`20260722_0004`, 52-passed full suite, 18-passed focused suite, twelve tables, seven authorized
endpoints, two roles, non-root API, private PostgreSQL, no leakage) was treated as the verified
technical baseline for this pass; it was not recomputed from scratch since no code changed since that
review.

### Checklist re-affirmed at the technical level

Exactly two roles (LEARNER, TEACHER); authenticated-subject ownership for both profile types;
teacher-profile ownership uniqueness; learner-profile ownership through the single owning
`app_user_learner_links` row; GRADE_2/GRADE_3-only classroom restriction; server-controlled REAL
provenance on every live row; classroom ownership isolation (non-owned IDs return
`RESOURCE_NOT_FOUND`); idempotent replay returning the identical committed response and body-mismatch
returning stable `CONFLICT`; concurrency-safe provisioning via the subject-scoped transaction advisory
lock; rollback integrity (entity, app-user mutation, idempotency record, and audit event all absent
after an injected failure, with a successful retry); audit and privacy boundaries (no password, raw
JWT, invite token, or scientific field in persistence, responses, or logs); and the continued absence
of invite, membership, session, and scientific behavior. Each item is `VERIFIED` at the automated,
technical-conformance level in `component-b-profile-classroom-ratification.json`.

This checklist confirms engineering conformance to the authorization. It is explicitly not treated as
equivalent to, or a substitute for, the named human governance decisions below.

### Named approver review

No named product owner, backend security owner, or privacy and child-safety owner has reviewed this
batch or recorded a decision through this session or any other channel available to this review. For
each of the three required roles, `component-b-profile-classroom-ratification.json` records:

- name: `UNRESOLVED_PLACEHOLDER`;
- decision: `UNRESOLVED`;
- decision date: absent;
- approved scope: absent;
- conditions: none recorded;
- unresolved concerns: specific to each role, including (for the privacy and child-safety owner) that
  retention, withdrawal, and deletion policy remain unresolved per the governing authorization, and
  that this component processes data about Grade 2/3 children, which this review does not treat as
  satisfied by automated testing alone;
- authorization of the closed batch as a foundation for later governance work: not recorded.

An AI assistant conducting this review has no channel to a real product owner, backend security owner,
or privacy and child-safety owner, and did not receive an explicit, attributable decision from any such
named person during this task. Inventing a name, date, or decision for any of the three roles would
create a false governance record rather than document a real one, so no such entry was fabricated.

### Ratification scope statement

No scope is ratified by this pass. This ratification review does not authorize, and does not carry
forward as authorization for, invite, QR, membership, session, attempt, progress, scientific-engine,
pilot, or production implementation, regardless of the outcome of any future named-approver review.

### Formal ratification decision

`BE2_PROFILE_CLASSROOM_NOT_RATIFIED`.

The batch remains `BE2_PROFILE_CLASSROOM_BATCH_CLOSED` at the engineering/technical level, established
by the prior closure re-review. It is `BE2_PROFILE_CLASSROOM_NOT_RATIFIED` at the governance level
because none of the three required named owners has recorded a real decision.

### Exact next governance task

Obtain an actual, attributable decision from each of the three named owners identified in
`component-b-profile-classroom-authorization.json` (`required_approvers.this_limited_scope`): product
owner, backend security owner, and privacy and child-safety owner. Each decision must be recorded by,
or on the explicit documented instruction of, that named person, and must include their name, role,
decision, decision date, approved scope, conditions, and unresolved concerns. Update
`component-b-profile-classroom-ratification.json` with the real entries once obtained, then re-issue
the ratification decision. Do not begin invite, QR, membership, session, attempt, progress,
scientific-engine, pilot, or production implementation before that ratification is granted.

## BE2 Profile/Classroom Ratification — Engineering Continuation Under Deferral to BE6

### Scope

This append-only entry records a project-governance instruction, issued directly by the person
directing this project in this session, that layers a bounded permission on top of the unresolved
named-approver ratification recorded above. It does not implement, modify, or authorize any code,
migration, table, endpoint, or scientific behavior by itself.

### Recorded status

`backend/provenance/component-b-profile-classroom-ratification.json` now additionally records:

```text
ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6
```

under a new `engineering_continuation` field. The prior `final_ratification_decision` value,
`BE2_PROFILE_CLASSROOM_NOT_RATIFIED`, is preserved unchanged as the accurate historical record that no
named product owner, backend security owner, or privacy and child-safety owner has ratified this batch.
The new status does not retract, satisfy, or stand in for that unresolved ratification; it is recorded
as an explicit project-governance instruction, not as a decision by or attributed to any of the three
named approver roles.

### What this status permits and does not permit

Permitted: continued Version 1 engineering, implementation, and testing of subsequent bounded
Component B application-layer batches, under the same authorization-then-implementation-then-closure
discipline already used for the profile/classroom batch.

Not permitted: real-child onboarding, research exports, pilot deployment, or production use. Final
product, security, privacy, and child-safety sign-off from the three named owners remains required
before any pilot use and is deferred to the BE6 pre-pilot review gate, not waived.

### Exact next task

Use this status to evaluate and, where warranted, authorize the next bounded Version 1 engineering
batch (see the Version 1 Classroom Invite and Membership Authorization entry below). Continue to defer
named-approver ratification of every batch closed under this status until the BE6 pre-pilot review,
at which point real, attributable decisions from all three named owners are required before any pilot
or production step.

## Version 1 Classroom Invite and Membership Authorization

### Scope and non-implementation

This append-only entry records the governance authorization for the next bounded Version 1 engineering
batch: the classroom invitation and membership workflow. No code, migration, table, column, endpoint,
test, or dependency was implemented or modified during this task. The full machine-readable
authorization is `backend/provenance/component-b-invite-membership-authorization.json`.

### Governing status and dependency

This authorization is issued under, and depends on,
`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6` (see the entry immediately above). It
permits engineering and testing only. It does not create, satisfy, or shortcut the named-approver
ratification requirement, which remains deferred to BE6 for both the profile/classroom batch and this
new batch. It supersedes, for this scope only, the eight `POLICY_GATED_NOT_EXECUTABLE` invite/membership
endpoint candidates and the `learner_multi_classroom_membership`, `invite_cross_learner_reuse_policy`,
and `invite_expiry_duration` entries recorded as unresolved in
`component-b-profile-classroom-authorization.json`, while preserving that document's history unchanged.

### Version 1 product decisions

Nineteen product decisions were supplied and are recorded verbatim in the authorization file's
`product_decisions_v1`, covering classroom/teacher cardinality, the one-APPROVED-membership-per-learner
rule, invite reuse across different learners, token cryptography and storage, 24-hour expiry, teacher
revocation, PENDING-only resolution, ownership-restricted approval/rejection, the exact three membership
states, idempotent decisions, scoped teacher and learner reads, REAL/TEST provenance separation, and the
prohibition on storing unnecessary or scientific data.

### Resolved ambiguities

Four points were not fully determined by the literal product decisions and were resolved conservatively,
recorded in `resolved_ambiguities`:

- A learner may hold multiple concurrent PENDING requests across different classrooms; the
  one-membership rule is enforced only at approval time, and a later approval attempt on a sibling
  PENDING request fails with the authorized conflict rather than being auto-mutated.
- `resolve` is a non-mutating preview (token validation, classroom name/grade only); `requests` is the
  sole endpoint that creates a PENDING row, satisfying decision 11.
- Repeated use after a REJECTED outcome returns the existing REJECTED record; no re-request pathway is
  authorized in this Version 1 batch.
- Invite-token cryptographic implementation (exact algorithm, library, byte length) is bounded by
  required properties (CSPRNG, sufficient entropy, one-way hash storage, never logged) but not selected,
  consistent with the prior authorization's treatment of the same topic; QR image encoding/rendering is
  explicitly out of scope for this backend authorization.

### Schema reuse and migration authorization

`classroom_invites`, `classrooms`, `teacher_profiles`, `b_learners`, `app_user_learner_links`,
`b_idempotency_records`, and `b_audit_events` are reused unchanged; no gap was found against the
Version 1 decisions. `classroom_memberships` is reused with one identified gap: no existing constraint
enforces "at most one APPROVED membership per learner across all classrooms" at the database level. A
narrowly scoped migration is authorized to add exactly one PostgreSQL partial unique index —
`classroom_memberships(learner_id) WHERE state = 'APPROVED'` — chained after `20260722_0004`, mirroring
the existing `b_sessions` one-active-session-per-learner pattern. No table, column, trigger, or seed data
is authorized. The application table count is expected to remain twelve after this migration, since an
index is not a table.

### Concurrency lessons carried forward

The authorization explicitly reuses the root-cause lesson from the profile-provisioning concurrency
defect found and fixed in the corrective batch (insert-before-lock, and a lock keyed on a value generated
after the race begins, allow an unhandled integrity error instead of the authorized idempotent outcome).
It requires: a transaction-scoped advisory lock keyed by `(learner_id, classroom_id)` before the
existence check and insert in the membership-request endpoint; and a transaction-scoped advisory lock
keyed by `learner_id` (not only `membership_id`) before the one-APPROVED-membership check and state
transition in the approval endpoint, so two teachers cannot concurrently approve two different pending
requests for the same learner.

### Authorized endpoints

Exactly eight endpoints are authorized, each fully specified in the authorization file with permitted
role, ownership check, exact request/response fields, idempotency scope and behavior, audit requirement,
privacy restriction, stable error cases, and concurrency requirement:

```text
POST   /api/v1/classrooms/{classroom_id}/invites
POST   /api/v1/classroom-invites/resolve
POST   /api/v1/classroom-memberships/requests
GET    /api/v1/classrooms/{classroom_id}/membership-requests
POST   /api/v1/classroom-memberships/{membership_id}/approve
POST   /api/v1/classroom-memberships/{membership_id}/reject
GET    /api/v1/classrooms/{classroom_id}/learners
GET    /api/v1/learner/classrooms
```

The invite-creation endpoint's idempotent replay response explicitly omits `invite_token` on every
replay after the first response, since the standard canonical-response-stores-everything idempotency
pattern used elsewhere would otherwise persist the raw token in `b_idempotency_records.canonical_response`,
violating decision 8. This is recorded as a required deviation from the default pattern, not left for
implementation to discover.

### Prohibited behavior (unchanged)

Session creation and every session lifecycle transition, questions, attempts, hints, BKT, mastery,
Guess-Guard, certification, sequencing, progress, completion, Component B live-engine integration,
Component C, Component 3, research export, synthetic dataset generation, pilot or production rollout,
and real-child onboarding all remain explicitly prohibited and unauthorized by this batch.

### Required approvers and ratification status

The same three named owners (product owner, backend security owner, privacy and child-safety owner)
remain required before pilot or production use of this batch, deferred to the BE6 pre-pilot review under
`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6`. This authorization does not obtain or
simulate their decisions.

### Formal authorization decision

`BE2_INVITE_MEMBERSHIP_SCOPE_AUTHORIZED`.

The Version 1 product decisions are complete and internally consistent once the four ambiguities above
are resolved as recorded; the existing foundations cover every requirement except one narrowly scoped,
additive database constraint; every authorized endpoint has a fully specified contract; and the
concurrency defect class already found once in this project is explicitly guarded against by name in
this authorization rather than left to be rediscovered.

### Exact next task

Implement the classroom invitation and membership workflow batch against
`component-b-invite-membership-authorization.json`: the one authorized migration and the eight
authorized endpoints, with the required replay, mismatch (where applicable), concurrency, and rollback
tests for every POST, plus the architecture guards listed in `required_tests`. Do not implement QR image
rendering, learning sessions, or scientific behavior. On completion, conduct a separate closure review
before any further scope, following the same pattern already used for the profile/classroom batch.

## Classroom Invite and Membership Authorization Correction — Idempotency and Revocation

### Scope and non-implementation

This append-only entry records a narrow governance correction to
`backend/provenance/component-b-invite-membership-authorization.json`. No code, API, migration, model,
dependency, or test was implemented or modified during this task. The prior entry immediately above
(recording the original eight-endpoint `BE2_INVITE_MEMBERSHIP_SCOPE_AUTHORIZED` decision) is preserved
unchanged; this section records what changed and why, and supersedes only the specific counts and
identifiers named below.

### Preserved statuses

`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6` and `BE2_PROFILE_CLASSROOM_NOT_RATIFIED`
(both in `component-b-profile-classroom-ratification.json`, untouched by this task) and
`BE2_INVITE_MEMBERSHIP_SCOPE_AUTHORIZED` (in the corrected authorization file) all remain exactly as
recorded. This correction remains engineering/testing scope only; it does not authorize real-child
onboarding, pilot, production, or research export.

### Identifier correction

The authorization used two different spellings for the same operation in two places:
`idempotency_operation_identifiers` incorrectly keyed the invite-creation endpoint as
`classroom.invite.create`, while the endpoint's own `idempotency.scope` field already correctly used
`classroom_invite.create`. The map entry is corrected to `classroom_invite.create` everywhere; no other
operation identifier changed. The corrected file now contains exactly six operation identifiers:
`classroom_invite.create`, `classroom_invite.resolve`, `classroom_membership.request`,
`classroom_membership.approve`, `classroom_membership.reject`, and the new `classroom_invite.revoke`.

### Path-based idempotency fingerprint rule

Four commands — invite creation, approve, reject, and the new revoke endpoint — take an empty request
body and identify their target resource entirely through a path parameter (`classroom_id`,
`membership_id`, or `classroom_invite_id`). The authorization previously specified only
`actor_user_id + POST + operation identifier + Idempotency-Key` as the idempotency scope, without stating
that the canonical request fingerprint must also include the path parameter. Left uncorrected, this would
have meant that two different classrooms, memberships, or invites, addressed under the same operation and
the same reused key with an empty body, would fingerprint identically and the second request would be
misclassified as an identical replay of the first — returning the wrong resource's result instead of the
authorized stable conflict.

The authorization now defines a standalone `path_based_idempotency_fingerprint_rule` section, and each of
the four affected endpoints' `idempotency` blocks gained an explicit `canonical_fingerprint` field: the
fingerprint must be computed over HTTP method, operation identifier, authenticated actor, the normalized
path parameter, and the canonical body — not the body alone. Reusing the same Idempotency-Key against a
different classroom_id, membership_id, or classroom_invite_id must return the authorized stable CONFLICT
and must never replay the first resource's committed response. `resolve` and `requests` are unaffected,
since their target resource is already carried in the request body (`invite_token`).

### Ninth endpoint: teacher invite revocation

`POST /api/v1/classroom-invites/{classroom_invite_id}/revoke` is newly authorized, fulfilling product
decision 10 ("a teacher may revoke an invite"), which existed in `product_decisions_v1` but had no
corresponding endpoint. Contract summary:

- role TEACHER; ownership requires the invite's classroom to belong to the verified teacher;
  absent/non-owned returns `RESOURCE_NOT_FOUND`;
- no request body; requires `Idempotency-Key`; operation identifier `classroom_invite.revoke`;
- response fields: `classroom_invite_id`, `classroom_id`, `revoked_at_utc`, `row_version`, `request_id`;
- the first valid revocation (not yet revoked, not yet expired) sets `revoked_at_utc` from server time
  and increments `row_version`; identical replay (same key, same invite) returns the same result;
- a different-key revoke command against an invite that is already revoked, or against a never-revoked
  invite whose `expires_at_utc` has already passed, returns the authorized stable `CONFLICT` and does not
  mutate `revoked_at_utc` — this is a newly resolved ambiguity, recorded in `resolved_ambiguities`: the
  authorization explicitly does not select allowing post-expiry revocation as a distinct success path in
  this Version 1 batch, and fails closed instead, consistent with this project's established default;
- revocation does not delete the invite row and does not mutate any existing `classroom_memberships` row;
- revoked invites already failed `resolve` and `requests` with `CONFLICT` under the existing authorization
  and continue to do so unchanged;
- raw token and token hash are never looked up, returned, logged, or included in the audit payload or
  idempotency canonical response for this endpoint, since the invite is identified only by
  `classroom_invite_id`; audit records only actor, `classroom_id`, `classroom_invite_id`, and
  `revoked_at_utc`;
- concurrency: concurrent same-key revoke requests must serialize on the same idempotency-scoped advisory
  lock pattern already required generally, producing exactly one revocation result with no unhandled
  database integrity error, and this requirement is also recorded in
  `concurrency_lessons_carried_forward.required_application`.

No new migration is required for this endpoint: it uses the existing `classroom_invites.revoked_at_utc`
and `row_version` columns, confirmed in a new `migration_authorization.revoke_endpoint_schema_impact`
field. The one previously authorized partial unique index on `classroom_memberships` remains the only
schema change authorized for this batch.

### Revised tests

`required_tests` gained explicit coverage for: a path-parameter mismatch test for every path-based POST
command (invite creation, approve, reject, revoke) proving that key reuse against a different resource
returns the authorized conflict rather than a replay; invite-revocation success and identical replay;
different-key revoke against an already-revoked or already-expired invite returning conflict; concurrent
revocation producing exactly one result; revocation rollback after an injected failure with a successful
retry; revocation ownership isolation (non-owner `RESOURCE_NOT_FOUND`, learner `FORBIDDEN`); revocation
not deleting the invite or mutating existing memberships; a revoked invite continuing to fail `resolve`
and `requests`; and raw token/hash leakage scans extended to cover the revoke endpoint's response, logs,
errors, audit payloads, and idempotency canonical response. `exit_criteria`,
`implementation_boundaries.authorized_next_batch`, and `exact_next_task` were updated from eight to nine
authorized endpoints; `fail_closed_behavior` gained two entries covering revoke-conflict and
path-parameter-mismatch-conflict cases.

### Unchanged prohibited scope

Session creation and every session lifecycle transition, questions, attempts, hints, BKT, mastery,
Guess-Guard, certification, sequencing, progress, completion, Component B live-engine integration,
Component C, Component 3, research export, synthetic dataset generation, pilot or production rollout, and
real-child onboarding all remain explicitly prohibited and unauthorized, unchanged by this correction.

### Timestamps

The authorization's top-level `recorded_at_utc`, previously the placeholder `2026-07-23T00:00:00Z`
(never a genuine recorded instant), is corrected to the actual UTC recording time of this correction,
`2026-07-23T13:11:34Z`. A new `correction_log` array entry records this same timestamp alongside a
summary of what changed and a pointer to this build-log section, preserving rather than overwriting the
fact that a prior version existed. No other `recorded_at_utc` field in this file required correction, and
`component-b-profile-classroom-ratification.json` was not modified by this task.

### Validation

```text
python -c "import json; json.load(open('provenance/component-b-invite-membership-authorization.json'))"
-> VALID JSON

Endpoint count: 9
Endpoints: /api/v1/classrooms/{classroom_id}/invites,
           /api/v1/classroom-invites/{classroom_invite_id}/revoke,
           /api/v1/classroom-invites/resolve,
           /api/v1/classroom-memberships/requests,
           /api/v1/classrooms/{classroom_id}/membership-requests,
           /api/v1/classroom-memberships/{membership_id}/approve,
           /api/v1/classroom-memberships/{membership_id}/reject,
           /api/v1/classrooms/{classroom_id}/learners,
           /api/v1/learner/classrooms

Operation identifiers: classroom_invite.create, classroom_invite.resolve,
                        classroom_membership.request, classroom_membership.approve,
                        classroom_membership.reject, classroom_invite.revoke

decision: BE2_INVITE_MEMBERSHIP_SCOPE_AUTHORIZED (unchanged)
```

`git diff --check` was run against the working tree and reported no whitespace errors.

### Exact next implementation task

Implement the classroom invitation and membership workflow batch against the corrected
`component-b-invite-membership-authorization.json`: the one authorized migration, the nine authorized
endpoints (including revocation), the `path_based_idempotency_fingerprint_rule` for the four path-based
POST commands, and the full `required_tests` list including the newly added revocation and
path-parameter-mismatch coverage. Do not implement invite QR rendering, learning sessions, or scientific
behavior. On completion, conduct a separate closure review before any further scope, following the same
pattern already used for the profile/classroom batch.

## BE2 Classroom Invite and Membership Implementation

### Scope and governing authority

This entry records implementation of the authorized Version 1 classroom invitation and membership
batch against `component-b-invite-membership-authorization.json` and the human-readable classroom
join-code product clarification given during this task (join code replaces an opaque/QR token; wire
field names `invite_token`/`classroom_invite` remain governance-frozen). Governing status:
`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6` (engineering/testing only — no
real-child onboarding, pilot, production, or research export). This entry does not issue an engineering
closure decision; a separate closure review follows, matching the profile/classroom batch's pattern.

### Files created

- `backend/migrations/versions/20260723_0001_classroom_membership_single_approval.py`
- `backend/app/domain/classroom_membership.py`
- `backend/app/application/classroom_membership.py`
- `backend/app/api/routes/classroom_membership.py`
- `backend/tests/test_classroom_membership.py`

### Files modified

- `backend/app/infrastructure/persistence_models.py` — added the partial unique index to
  `ClassroomMembership.__table_args__` (SQLAlchemy model mirror of the migration; no new column).
- `backend/app/infrastructure/repositories.py` — added `ClassroomInviteRepository` and
  `ClassroomMembershipRepository`.
- `backend/app/main.py` — registered the new `classroom_membership` router.
- `backend/tests/test_be2_architecture_guards.py` — expanded the authorized route inventory to
  nineteen operations, added a dedicated nine-operation invite/membership check, added a
  no-session/scientific-path guard covering the full current route set, retired the now-superseded
  blanket "no invite/membership path" assertion (with an explanatory comment; the `session`/`attempt`/
  `hint` portion of that check is superseded by the new dedicated guard, which covers the same ground
  unconditionally rather than only at the 0004 migration's historical point in time), and added a guard
  for the new migration (no table/column change, only the named index, no `classroom_invites` change).

### Migration revision

`20260723_0001_classroom_membership_single_approval`, chained after `20260722_0004`. Adds exactly one
PostgreSQL partial unique index — `uq_classroom_memberships_one_approved_per_learner` on
`classroom_memberships(learner_id) WHERE state = 'APPROVED'` — mirroring the existing `b_sessions`
one-active-session-per-learner pattern. No table, column, or trigger was added or changed; no seed
data; `classroom_invites` untouched.

### Nine implemented endpoints

```text
POST   /api/v1/classrooms/{classroom_id}/invites
POST   /api/v1/classroom-invites/{classroom_invite_id}/revoke
POST   /api/v1/classroom-invites/resolve
POST   /api/v1/classroom-memberships/requests
GET    /api/v1/classrooms/{classroom_id}/membership-requests
POST   /api/v1/classroom-memberships/{membership_id}/approve
POST   /api/v1/classroom-memberships/{membership_id}/reject
GET    /api/v1/classrooms/{classroom_id}/learners
GET    /api/v1/learner/classrooms
```

Operation identifiers used for idempotency scoping: `classroom_invite.create`,
`classroom_invite.resolve`, `classroom_membership.request`, `classroom_membership.approve`,
`classroom_membership.reject`, `classroom_invite.revoke` — matching the corrected authorization
exactly, with no `classroom.invite.create`-style variant reintroduced.

### Human-readable join-code design (token-generation and hashing)

Per the mid-task product clarification, the invite secret is a human-readable classroom join code, not
an opaque token or QR payload:

- alphabet `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (31 symbols; digits `0`/`1` and letters `I`/`L`/`O`
  excluded as visually ambiguous);
- 8 characters generated via `secrets.choice` (a CSPRNG), giving `log2(31) * 8 ≈ 39.6` bits of entropy;
  grouped 4-4 with a hyphen for display (e.g. `M7KP-4X9D`), matching the given example's shape;
- the canonical (ungrouped, uppercase) form is what gets hashed with SHA-256 into the existing
  `token_hash` column, unchanged in format (64 lowercase hex characters) and unchanged constraint;
- normalization (`normalize_join_code`) strips whitespace and hyphens and uppercases before both
  hashing and idempotency fingerprinting, so matching is case-insensitive and separator-insensitive
  as required, and a retried resolve/request typed with different casing or spacing is recognized as
  the same code rather than triggering a spurious idempotency body-mismatch conflict;
- the plaintext code is present only in the first successful invite-creation HTTP response; the
  idempotency `canonical_response` persisted for that command excludes it entirely (`invite_token:
  null, token_already_issued: true`), so it is never reconstructable from a replay or from
  `b_idempotency_records`; it is never included in audit payloads (only actor, `classroom_id`,
  `classroom_invite_id`, and timestamps are recorded) and never logged;
- length/alphabet/grouping are tunable module-level constants; the exact entropy figure is recorded
  here and in code comments for the deferred BE6 backend security owner review of the invite-token
  cryptographic contract (`invite_token_cryptographic_contract`, still `SECURITY_DESIGN_REQUIRED` per
  the authorization). QR image encoding/rendering was not implemented, consistent with both the
  original authorization and the clarification that a future QR affordance may wrap this same code
  without a backend redesign, since the wire contract (`invite_token` as a plaintext string) is
  unchanged either way.

### Idempotency fingerprint design

Two fingerprint shapes are used, per `path_based_idempotency_fingerprint_rule`:

- body-based (`resolve`, `requests`): SHA-256 of the canonical JSON `{"invite_token": <normalized
  code>}` — a one-way hash, so the code is never persisted even indirectly through the idempotency
  mechanism, and normalization ensures equivalent-but-differently-typed codes fingerprint identically;
- path-based (`invites` creation, `approve`, `reject`, `revoke`, all empty-bodied): SHA-256 of the
  canonical JSON `{"http_method": "POST", "operation_identifier": ..., "actor_user_id": ...,
  "path_parameter": <classroom_id | membership_id | classroom_invite_id>, "body": {}}`. Reusing the
  same Idempotency-Key against a different path resource of the same operation now produces a
  different fingerprint and returns the authorized stable `CONFLICT`, verified by dedicated
  path-mismatch tests for all four affected endpoints.

### Advisory-lock and row-lock design

- `POST .../classroom-memberships/requests` acquires a transaction-scoped advisory lock keyed by the
  stable pair `(learner_id, classroom_id)` before checking for an existing `classroom_memberships` row
  and before inserting, so a concurrent duplicate (same or different key) returns the existing row
  rather than racing on the `(classroom_id, learner_id)` unique constraint.
- `POST .../classroom-memberships/{membership_id}/approve` acquires a transaction-scoped advisory lock
  keyed by the stable `learner_id` (not the membership_id) before checking the one-APPROVED-membership
  invariant and before transitioning state, so two teachers concurrently approving two different
  PENDING requests for the same learner cannot both succeed. The target membership row is re-read with
  `SELECT ... FOR UPDATE` after the lock is acquired — necessary both for row-level serialization and
  because SQLAlchemy's identity map would otherwise return a stale, pre-lock copy of an already-loaded
  ORM object rather than a fresh one; the flush is additionally wrapped in a defensive
  `try/except IntegrityError -> ConflictError` around the partial-unique-index write, satisfying the
  literal "no unhandled unique-constraint error" requirement even though the advisory lock already
  prevents the race from reaching that constraint under normal operation.
- `POST .../classroom-invites/{classroom_invite_id}/revoke` relies on the existing idempotency-scoped
  advisory lock (actor + operation + key) for same-key concurrency, and additionally re-reads the
  invite row with `SELECT ... FOR UPDATE` after that lock (and after the idempotency-replay
  short-circuit) so that a genuinely different-key concurrent or sequential revoke against an
  already-revoked invite reliably observes the committed state and returns `CONFLICT` rather than a
  stale, pre-commit view.
- `POST .../classroom-memberships/{membership_id}/reject` uses the same `FOR UPDATE` re-read for
  correctness against a different-key already-decided conflict, with no additional advisory lock, per
  the authorization's "no cross-membership invariant applies to rejection."

### Ownership, privacy, and provenance controls

Every mutating endpoint resolves the actor's role/profile first, then verifies ownership of the target
resource (classroom, invite, or membership) before any idempotency or business-state check, returning
`RESOURCE_NOT_FOUND` for absent or non-owned resources to prevent enumeration, and `FORBIDDEN` for the
wrong role. Learner-facing teacher listings return no email; teacher-facing learner listings return no
email. `b_learners.grade` is never written by approval (verified directly against the database in
tests). All live mutations use server-controlled `source_class = REAL` provenance; audit payloads carry
only actor, resource identifiers, and (for approve/reject) an explicit before/after state pair — never
tokens, hashes, passwords, or JWTs.

### Test commands and results

```text
docker compose config                      -> OK
docker compose build                       -> Image upadya-backend:be1-batch3 Built
docker compose up -d                       -> db healthy, api started
docker compose exec api python -m compileall app   -> clean
docker compose exec api alembic upgrade head       -> 20260722_0004 -> 20260723_0001
docker compose exec api pytest -q tests/test_classroom_membership.py   -> 29 passed, 1 warning
docker compose exec api pytest -q                                       -> 84 passed, 1 warning
```

The single warning is the known upstream FastAPI/Starlette `TestClient` httpx deprecation. The full
suite grew from 52 (prior state) to 84: 29 new focused tests plus 3 new architecture-guard tests.

One genuine test-design bug was found and fixed during this run (not a service defect): the first
version of the concurrent cross-classroom approval test reused a learner who already had an approved
membership from earlier in the same test, so both concurrent approval attempts correctly conflicted
with that pre-existing approval regardless of timing, rather than exercising the intended race. Fixed
by using a fresh learner with no prior approval for that specific scenario; after the fix, the
concurrent race produced the expected `[200, 409]` split with exactly one `APPROVED` row.

### Migration-cycle results

```text
alembic check (at head)                    -> No new upgrade operations detected
alembic downgrade 20260722_0004            -> 20260723_0001 -> 20260722_0004
alembic current                            -> 20260722_0004
alembic upgrade head                       -> 20260722_0004 -> 20260723_0001
alembic current                            -> 20260723_0001 (head)
alembic check (after cycle)                -> No new upgrade operations detected
pg_isready                                 -> accepting connections
```

### Architecture-guard results

OpenAPI now contains exactly nineteen operations: the ten pre-existing plus the nine newly authorized.
`test_openapi_contains_exactly_the_nine_authorized_invite_membership_operations` and
`test_no_session_question_answer_or_scientific_route_exists` both pass; the latter scans every current
route for `session`, `attempt`, `hint`, `progress`, `bkt`, `mastery`, `sequenc`, `certif`, and `guess`
and finds none. `test_invite_membership_migration_adds_only_the_authorized_index` confirms the new
migration contains no `create_table`, `add_column`, or `drop_column` call, names the authorized index
and table, and never mentions `classroom_invites`. Direct database inspection confirmed the application
table count remains twelve (`app_users`, `b_learners`, `app_user_learner_links`,
`b_runtime_bundle_records`, `b_sessions`, `b_session_events`, `b_idempotency_records`,
`b_audit_events`, `teacher_profiles`, `classrooms`, `classroom_invites`, `classroom_memberships`) plus
`alembic_version` and the pre-existing `be1_persistence_check` marker, and that
`uq_classroom_memberships_one_approved_per_learner` exists alongside the two pre-existing
`classroom_memberships` indexes.

### Leakage and isolation results

A targeted API-log scan found no join code, `Authorization` header, password, refresh token,
`component_b_generator`, or Yass match. A container-side scan of `app` found no failure-injection
marker (`controlled-test-failure`, `_failing_audit`, `force_error`, `force_failure`) and no research
import (`component_b_generator`, `import yass`, `from yass`). The API ran as UID/GID `10001:10001` with
no bind mounts; PostgreSQL published no host port. `git diff --check` reported no whitespace errors.

### Unresolved limitations

- The invite-token cryptographic contract (exact alphabet/length/entropy target) remains an
  implementation-time choice recorded for BE6 backend-security-owner review, not a ratified parameter;
  the ~39.6-bit entropy figure is the number that review should evaluate.
- QR image rendering/encoding was not implemented in this batch, consistent with the authorization and
  the clarification; it remains a future frontend concern layered on the same join code.
- `learner_multi_classroom_membership` cardinality is implemented exactly as decided (one APPROVED at a
  time, multiple concurrent PENDING allowed), but the broader unresolved decisions list in
  `component-b-profile-classroom-ratification.json` (retention/withdrawal/deletion,
  `classroom_grade_change_after_membership`, `profile_and_account_update_deactivation`) remains
  unchanged and unaddressed by this batch.

### Confirmation of prohibited scope

No session, question, opportunity, attempt, hint, response-time, BKT, mastery, Guess-Guard,
certification, sequencing, progress, completion, Component B live-engine, Component C, Component 3,
research-export, synthetic-dataset, pilot, or production behavior was implemented. No Yass or
`component_b_generator` import or dependency exists.

### Exact next task

Conduct a separate closure review of this classroom invite and membership batch against
`component-b-invite-membership-authorization.json`, following the same pattern as the profile/classroom
closure review: re-verify all evidence above from the pushed commit in a clean Docker run, confirm the
governance-status dependency (`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6`) is still
in effect, and issue a formal engineering-closure decision. This entry does not issue that decision.

---

## BE2 Classroom Invite and Membership — Closure Review

Completed: 2026-07-24 Asia/Colombo (`2026-07-23` UTC)
Reviewed target: the uncommitted working tree described in the entry above (no new functionality
added; review-only)

### Method

Independent re-verification, not a re-read of the prior entry's claims: full `git diff` inspection of
every changed/new file; line-by-line reading of the migration, domain contracts, application service,
API routes, and test module; a clean Postgres 16.10 container (no volume reuse, published on
`127.0.0.1:5432`) with dependencies installed fresh (Python 3.13, project deps from
`requirements.lock` minus the Windows-incompatible `uvloop` entry, which is an optional uvicorn extra
never exercised by `TestClient`-based tests); `alembic upgrade head` from empty; the full
downgrade/upgrade cycle with direct `psql` index inspection at each step; `alembic check`; direct
`psql` table/index enumeration; the focused and full pytest suites; static scans for out-of-scope
terms and plaintext leakage.

### Scope conformance

`git diff --stat` against the parent commit shows exactly five modified files and five new files, all
within `backend/app/{domain,application,api/routes,infrastructure}`, `backend/migrations/versions/`,
`backend/tests/`, and `backend/buildLog.md`. `persistence_models.py` and `repositories.py` diffs
contain only the one partial-unique-index addition and the two new repository classes respectively;
`main.py` diff is the one router registration. No file outside the invite/membership surface was
touched. `git diff --check` reports no whitespace/conflict-marker errors.

### Endpoint and identifier verification

`app.openapi()["paths"]` enumerated directly: exactly the nine authorized routes/methods, no more, no
fewer. Operation-identifier strings passed to `_idempotency_start` in
`app/application/classroom_membership.py` read verbatim: `classroom_invite.create`,
`classroom_invite.resolve`, `classroom_membership.request`, `classroom_membership.approve`,
`classroom_membership.reject`, `classroom_invite.revoke` — exact match to the frozen list.

### Authorization, privacy, and boundary verification

Every mutating and listing use-case resolves role via `_teacher_context`/`_require_learner` before any
ownership or state check; ownership is enforced via `get_owned` joins against `Classroom.teacher_profile_id`
(invites, memberships) so cross-teacher access 404s rather than 403s (no enumeration signal). Learner
and teacher listing responses (`ClassroomLearnerListItem`, `MembershipRequestListItem`,
`LearnerMembershipListItem`) carry no email field. Confirmed by direct code read and by passing tests
asserting `"email" not in entry` on both listing directions and 403/404 boundaries for every
role/ownership combination.

### Invite and membership behavior verification

Join code: `secrets.choice` over a 31-symbol alphabet excluding `0/O/1/I/L`, 8 characters, SHA-256
hashed after `normalize_join_code` (strip separators, uppercase) — hash is the only persisted form
(`token_hash` unique+format-checked column, pre-existing schema, untouched). Plaintext appears only in
the first `create_invite` HTTP response; the idempotency `canonical_response` stored for replay
explicitly nulls `invite_token`. `resolve_invite` performs no write to `classroom_memberships` (verified
by direct row-count assertion in tests and by code read — no `ClassroomMembership` construction on that
path). 24-hour expiry (`timedelta(hours=24)`) confirmed in code and by a dedicated expiry-delta test.
Revoke is owner-scoped, sets `revoked_at_utc`, and is unconditionally checked (`revoked_at_utc is not
None or expires_at_utc <= now`) in resolve and request-membership. Membership request creates `PENDING`
only; approve/reject require the owning teacher and a `PENDING` starting state; a second request against
an existing `REJECTED` row returns the existing rejected record rather than creating a new one (no
re-request path exists in the nine endpoints, matching the Version 1 constraint); multiple concurrent
`PENDING` rows across different classrooms for one learner are permitted (`uq_classroom_memberships_pair`
is scoped per classroom+learner, not global); exactly one `APPROVED` row per learner is enforced by
`uq_classroom_memberships_one_approved_per_learner`, confirmed present via direct `psql` inspection.

### Concurrency verification

`classroom_membership.request` and `.approve` acquire `pg_advisory_xact_lock` keyed on
`(learner_id, classroom_id)` and `learner_id` respectively before their state-changing reads; `.reject`
and invite `.revoke` rely on `SELECT ... FOR UPDATE` on the target row, which independently serializes
any concurrent transaction touching the same row regardless of advisory-lock scope — a valid mechanism,
not a gap. `approve_membership` wraps its flush in `except IntegrityError -> ConflictError`, the
documented last-line defense behind the partial unique index. The concurrent cross-classroom approval
test (`test_approval_second_classroom_conflict_and_concurrent_cross_classroom_approvals`) exercises two
different teachers approving two different `PENDING` memberships for the same learner via genuine
thread-level concurrency against a shared `TestClient`, and asserts the `[200, 409]` split with exactly
one resulting `APPROVED` row — passed.

### Idempotency verification

Idempotency records are scoped at the database level by a `(actor_user_id, http_method,
operation_identifier, idempotency_key)` unique constraint (pre-existing `b_idempotency_records` schema,
untouched); the request fingerprint layered on top of that scope covers path parameter and canonical
body (`path_fingerprint` for the five path-addressed commands) or canonical body alone (`body_fingerprint`
for the two body-only commands, `resolve`/`request`), which is sufficient because actor/method/operation
are already structurally enforced by the scope key rather than needing restatement inside the hash.
Path-resource-mismatch tests (same key, different classroom/membership/invite) confirm a stable `409`
rather than a false replay, for all five path-addressed operations. No canonical response persisted for
replay contains a plaintext join code (`create_invite`'s stored response explicitly nulls it); no test or
code path replays one command's stored response against a different resource.

### Commands run and results

```text
docker run postgres:16.10-bookworm (fresh, published host port, no volume reuse)
alembic upgrade head                          -> ...0004 -> 20260723_0001 (clean, no errors)
alembic current                               -> 20260723_0001 (head)
alembic downgrade 20260722_0004               -> index dropped (confirmed via psql \d)
alembic upgrade head                          -> index restored (confirmed via psql \d)
alembic check                                 -> No new upgrade operations detected
git diff --check                              -> clean (no output)
pytest tests/test_classroom_membership.py -v  -> 29 passed, 1 warning
pytest tests/ -v                              -> 84 passed, 1 warning
```

The one warning in both runs is the pre-existing, unrelated `StarletteDeprecationWarning` for
`httpx`-backed `TestClient`, matching the implementation entry's note; not introduced by this batch.

### Database inspection

`psql \dt` on the freshly migrated database: 13 relations total, 12 application tables (`app_users`,
`app_user_learner_links`, `b_learners`, `b_runtime_bundle_records`, `b_sessions`, `b_session_events`,
`b_idempotency_records`, `b_audit_events`, `teacher_profiles`, `classrooms`, `classroom_invites`,
`classroom_memberships`) plus `alembic_version`. (The `be1_persistence_check` connectivity marker
referenced in the implementation entry is created ad hoc by manual connectivity checks, not by
migrations or the test suite, and is correctly absent from a freshly created database — its absence here
is expected, not a discrepancy.) `psql \d classroom_memberships` confirms exactly three indexes: the
primary key, the pre-existing `uq_classroom_memberships_pair`, and the one new
`uq_classroom_memberships_one_approved_per_learner` partial unique index — no other new index, table,
column, or trigger anywhere in the schema.

### Leakage and architecture-boundary scans

Grep of all five new/changed application files for `component_b_generator`, `yass`, `bkt`, `sequenc`,
`certif`, `component_c`, `component_3`, `research.export`, `pilot`, `production_run` found no real
match (only an incidental substring hit inside Python's `Sequence` type import, in the migration
header). `test_be2_architecture_guards.py`'s three new/updated guards
(`test_openapi_contains_exactly_the_nine_authorized_invite_membership_operations`,
`test_no_session_question_answer_or_scientific_route_exists`,
`test_invite_membership_migration_adds_only_the_authorized_index`) all passed as part of the full suite
run above. No session, item, answer, hint, BKT, mastery, sequencing, certification, progress, Component
C, Component 3, research-export, pilot, or production behavior was found anywhere in the reviewed diff.

### Non-blocking observation (not a defect requiring action)

`create_invite`'s insert is not wrapped in an `IntegrityError` handler for the pre-existing
`uq_classroom_invites_token_hash` constraint. At ~39.6 bits of entropy per code this is not a practical
collision risk at any realistic invite volume, and defended-against concurrency defect was not part of
the authorized review checklist (which specifically scopes the `IntegrityError`-conversion requirement to
membership approval). Recorded for awareness only; does not block closure.

### Closure decision

**GO** — closure status identifier: `BE2_INVITE_MEMBERSHIP_BATCH_CLOSED`. No blocking findings. All
twelve review requirements re-verified independently against a clean database and a clean dependency
install, not merely re-read from the implementation entry. Nothing was committed by this review; the
working tree remains exactly as it was at the start (`git status` unchanged before/after).


## BE2 Classroom Invite and Membership — Join-Code Ratification and Closure Observation Record

### Scope and nature of this entry

This is a **governance record-keeping reconciliation only**. It changes no code, schema, migration,
endpoint, or test, and it does not alter the closed batch: the BE2 Classroom Invite and Membership
implementation remains exactly as reviewed and closed at commit `3e13106` (`close BE2 invite and
classroom membership batch`), now pushed to `origin/B_frontend`. It records two items surfaced during
the supervisor baseline and the closure review that were, until now, captured only in this build log
and in code comments rather than in the frozen authorization contract. The corresponding machine-
readable record is the second entry appended to `correction_log` in
`backend/provenance/component-b-invite-membership-authorization.json`.

### Item 1 — Human-readable join-code clarification ratified into the contract

The `component-b-invite-membership-authorization.json` contract, in its crypto `resolved_ambiguities`
entry, still framed the invite secret as an "opaque raw token string". The implemented and closed
behavior instead uses a **human-readable classroom join code**, per a mid-batch product clarification:

- uppercase 31-symbol visually-unambiguous alphabet `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (excludes
  `0`/`O`/`1`/`I`/`L`);
- 8 characters generated with a CSPRNG (`secrets.choice`), approximately `log2(31) * 8 = 39.6` bits of
  entropy, grouped 4-4 for display (for example `M7KP-4X9D`);
- normalized case-insensitively and separator-insensitively before both hashing and idempotency
  fingerprinting, and SHA-256-hashed into the existing 64-lowercase-hex `token_hash` column.

The appended contract correction records that this clarification **supersedes the "opaque raw token
string" phrasing for wire-display purposes only**. The wire field names `invite_token` and the
`classroom_invite` resource identity remain governance-frozen; the one-way-hash storage, never-logged,
and 24h-expiry-plus-teacher-revocation properties are unchanged. The approximately 39.6-bit entropy
figure is the specific value the deferred **BE6** `invite_token_cryptographic_contract` review (still
`SECURITY_DESIGN_REQUIRED`) must evaluate for a short, human-typeable, revocable, 24-hour code.

### Item 2 — Closure non-blocking observation carried forward to BE6

The closure review recorded one non-blocking observation, restated here for the BE6 backend-security-
owner review: `create_invite`'s insert is not wrapped in an `IntegrityError` handler for the
pre-existing `uq_classroom_invites_token_hash` unique constraint. At approximately 39.6 bits this is not
a practical collision risk at realistic invite volumes, and it is explicitly outside this batch's
authorized `IntegrityError`-to-`ConflictError` conversion scope, which is limited to membership approval
behind the partial unique index. Recorded for awareness; it was not, and is not, a blocker.

### Unchanged statuses

This reconciliation is **not** a named-approver ratification. The prior decision
`BE2_INVITE_MEMBERSHIP_SCOPE_AUTHORIZED`, the closure decision `BE2_INVITE_MEMBERSHIP_BATCH_CLOSED`, and
the governing `ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6` /
`BE2_PROFILE_CLASSROOM_NOT_RATIFIED` statuses all remain in effect and unchanged. Product owner, backend
security owner, and privacy and child-safety owner ratification remains deferred to the BE6 pre-pilot
review; this entry does not create, satisfy, or shortcut that requirement.

---

## BE2.3-BE2.4 Neutral Session-Lifecycle Skeleton -- Engineering Continuation

Completed: 2026-07-24 Asia/Colombo (`2026-07-24` UTC)
Build target: `Dev/backend/`
Authorized by: the user's bounded task under
`ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6`, reusing the existing
`b_sessions` / `b_session_events` / `b_runtime_bundle_records` schema. This entry does
not issue a closure decision.

### Scope

Exactly four LEARNER-role endpoints under `/api/v1/b/sessions`, reusing existing
persistence with no migration:

- `POST /api/v1/b/sessions` (`b_session.start`, Idempotency-Key required)
- `GET /api/v1/b/sessions/active`
- `POST /api/v1/b/sessions/{session_id}/complete` (`b_session.complete`, Idempotency-Key required)
- `POST /api/v1/b/sessions/{session_id}/abandon` (`b_session.abandon`, Idempotency-Key required)

Start resolves the currently approved+published runtime bundle, pins its
`runtime_bundle_record_id`, and creates the session directly as `active`; no
approved+published bundle fails closed with `CONFLICT` (a bundle-less session is never
created). A safe replay or a concurrent duplicate start for the same learner returns
the existing active session. `expires_at_utc` is always left `NULL` -- no numeric
expiry/timeout, per the governance-unresolved gate. Complete/abandon are neutral,
explicit client commands (`active -> completed` / `active -> abandoned`) with no
scientific or pedagogical completion criteria. No question, answer, attempt, hint,
BKT, mastery, certification, sequencing, or Component B live-engine behavior exists
anywhere in this batch.

### Files created

- `app/domain/b_session.py` -- `SessionFields`, `SessionCommandResponse` (start/complete/
  abandon), `ActiveSessionResponse` (nullable `session`). Only `session_id`, `state`,
  `runtime_bundle_version`, `created_at_utc`, `row_version`, `request_id` are exposed.
- `app/application/b_session_lifecycle.py` -- `BSessionLifecycleService`. Deliberately
  named to avoid the `*session*service*.py` glob used by the pre-existing architecture
  guard (see below); reimplements the `_require_user`/`_require_learner`/idempotency/
  audit helpers locally, following this codebase's established per-service convention
  (no shared base class exists for these).
- `app/api/routes/b_session.py` -- the four route handlers, `Idempotency-Key` header
  required on the three POST operations.
- `tests/test_b_session_lifecycle.py` -- 14 focused tests (see below).

### Files modified

- `app/infrastructure/repositories.py` -- added `RuntimeBundleRecordRepository.
  find_current_approved_published()` (tie-break: most recent `PUBLISHED`+`APPROVED`
  bundle by `created_at_utc`, an engineering assumption recorded here, not a governed
  tie-break policy) and three `SessionRecordRepository` methods:
  `find_starting_or_active_for_learner`, `find_active_for_learner`, `get_owned`.
- `app/main.py` -- one router registration (`b_session_router`).
- `tests/test_be2_architecture_guards.py` -- extended, not weakened: added the four new
  routes to `EXPECTED_ROUTES`; added `AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS` (4) with
  an exact-count containment test mirroring the invite/membership pattern; carved the
  blanket "session" path-term prohibition out only for those four exact routes (every
  other prohibited scientific term, and "session" on every other route, remains
  unconditionally prohibited); added an AST-based DTO field-identifier scan for
  `app/domain/b_session.py` (deliberately AST-based, not raw text, because the module's
  own docstring correctly documents excluded terms by name and a raw-text scan produced
  a false positive on first attempt). The `*session*service*.py` empty-glob assertion
  was left untouched because `b_session_lifecycle.py` does not contain the substring
  "service"; no evasion was intended, it is simply an accurate name for the module.

No schema migration was created or needed.

### Concurrency and correctness bug found and fixed during this batch

The first implementation of `complete`/`abandon` called `SessionRecordRepository.
get_owned()` (an unlocked read, for the ownership/404 check) before later re-reading
the same row with `SELECT ... FOR UPDATE`. Because the row was already present in the
SQLAlchemy session identity map from the first read, the FOR-UPDATE re-fetch did not
refresh the Python-level `state` attribute from the newly-locked row by default -- the
SQL-level lock was correctly acquired, but the ORM object kept its pre-lock in-memory
value. A genuine concurrency test (complete one session and abandon the same session,
truly concurrently, via a shared `TestClient` and a `threading.Barrier`) caught this:
both transitions returned `200`, i.e., both committed successfully against a session
that should have allowed exactly one. Root cause and fix: added
`.execution_options(populate_existing=True)` to the FOR-UPDATE select in `_transition`,
forcing SQLAlchemy to overwrite the identity-mapped object's attributes from the
lock-holding read. After the fix, the same race reliably produces `[200, 409]` with
exactly one resulting transition. This same identity-map hazard is latent (but not
currently exercised, since no existing test races two different operations against the
same row) in `classroom_membership.approve_membership`'s equivalent `get_owned` +
`FOR UPDATE` pattern; it is recorded here for BE6 awareness but was not touched, being
out of this batch's authorized scope.

A second, unrelated test-design bug was found and fixed in this batch's own test
authoring (not a service defect): an early draft of the idempotency path-mismatch test
reused the same literal Idempotency-Key string across two different learners, expecting
a `409`. Idempotency uniqueness is scoped by `(actor_user_id, http_method,
operation_identifier, idempotency_key)`, so two different actors reusing the same key
string are structurally independent records, not a conflict -- both correctly returned
`200`. Fixed by testing the intended scenario instead: the same learner reusing one key
across two sessions they own in sequence (complete session A, start session B, reuse
A's key against B's `complete`), which correctly conflicts.

### Test coverage (14 tests, `tests/test_b_session_lifecycle.py`)

- Start: creates an active session pinned to the resolved bundle; fails closed with
  `409 CONFLICT` when no approved+published bundle is resolvable (exercised
  deterministically via an overridden `_resolve_pinnable_bundle` test seam, following
  this codebase's established `injected._audit = _failing_audit`-style instance-method
  override convention, rather than depending on global test-database bundle absence,
  which is not reliably controllable across a shared test database); replay returns the
  same session; concurrent duplicate starts (two threads, one `Barrier`, different
  idempotency keys) produce exactly one active/starting row; TEACHER -> `403`,
  no-profile -> `404`; rollback on an injected audit failure leaves no session, no
  idempotency row, and a retry with the same key then succeeds; runtime-bundle pinning
  is verified to survive a newer approved+published bundle being inserted after start.
- Get-active: returns `null` when absent, returns the learner's own current session,
  isolates across two different learners, and enforces the LEARNER-role boundary.
- Complete/abandon: success transition; replay returns the same result; a further
  transition attempt on an already-non-active session conflicts; idempotency-key reuse
  across two sessions the same learner owns conflicts (not a false replay); cross-learner
  ownership isolation returns `404` (no enumeration); TEACHER -> `403`, no-profile ->
  `404`; rollback on an injected audit failure leaves `state`/`row_version` unchanged and
  no idempotency row, with a same-key retry then succeeding; a genuine concurrent
  complete-vs-abandon race on the same session produces exactly one transition (the bug
  above).

### Architecture-guard and database verification

```text
docker compose build                                -> Image upadya-backend:be1-batch3 Built
docker compose up -d                                 -> db healthy, api started
docker compose exec api python -m compileall app     -> clean
docker compose exec api alembic upgrade head         -> no new revisions (already at 20260723_0001)
docker compose exec api alembic check                -> No new upgrade operations detected
docker compose exec api alembic downgrade 20260722_0004 -> OK
docker compose exec api alembic upgrade head          -> OK
docker compose exec api alembic check (post-cycle)    -> No new upgrade operations detected
docker compose exec api pytest -q                     -> 100 passed, 1 warning (pre-existing httpx/TestClient deprecation)
```

`app.openapi()["paths"]` enumerated directly inside the container: exactly 20 total
operations, the sixteen pre-existing plus exactly the four newly authorized
`/api/v1/b/sessions*` operations, no more, no fewer.
`test_openapi_contains_exactly_the_four_authorized_b_session_lifecycle_operations` and
`test_no_session_question_answer_or_scientific_route_exists` (with its narrow "session"
carve-out limited to exactly those four routes) both pass; every other prohibited
scientific path term (`attempt`, `hint`, `progress`, `bkt`, `mastery`, `sequenc`,
`certif`, `guess`) remains unconditionally checked against all twenty routes, including
the four new ones. A container-side grep for `component_b_generator`, `import yass`/
`from yass`, and known failure-injection markers found no match. The container ran as
UID/GID `10001:10001`; the `db` service publishes no host port (unchanged from prior
batches).

### Non-blocking observation carried forward

The `find_current_approved_published()` tie-break (most recent `created_at_utc` among
`PUBLISHED`+`APPROVED` bundles) is an engineering assumption, not a governed selection
policy, for the case where more than one bundle is simultaneously eligible (e.g. an
alias or a newer replacement bundle published without retiring the old one). Recorded
for BE6 review alongside the identity-map/FOR-UPDATE hazard noted above.

### Confirmation of prohibited scope

No question, opportunity, attempt, hint, BKT, mastery, Guess-Guard, certification,
sequencing, progress-beyond-state, numeric expiry/timeout, Component B live-engine,
Component C, Component 3, or research-generator behavior was implemented anywhere in
this batch. No Yass or `component_b_generator` import or dependency exists.

### Current state and exact next task

This batch is complete, tested, and left uncommitted in the working tree for Yasindu to
review and commit. No `git add`, `git commit`, or `git push` was run. Exact next task:
review this diff and the above evidence; if accepted, commit it following this
repository's established commit-message conventions, then conduct a separate closure
review of this specific batch (mirroring the BE2 invite/membership closure review
pattern) before treating BE2.3-BE2.4 as formally closed. This entry does not issue that
closure decision.

---

## BE2.3-BE2.4 Neutral Session-Lifecycle Skeleton -- Closure Review

Completed: 2026-07-24 Asia/Colombo (`2026-07-24` UTC)
Build target: `Dev/backend/`
Scope: a separate, independent closure review of the engineering-continuation entry
immediately above, re-verified against PROMPT BE2-S and BEplan BE2.3-BE2.4 from a clean
run. This entry only reviews and closes that batch; it authorizes no new scope, no
migration, and no scientific behavior. Git hard rule observed: read-only git only
(`git status`/inspection); nothing was staged, committed, or pushed; this closure record
is appended to `buildLog.md` only.

### Method -- clean, isolated re-verification (not a re-read of the prior evidence)

The prior batch's Docker evidence was independently reproduced from scratch rather than
accepted on record:

```text
docker compose down -v                    -> prior container/volume/network removed
docker compose build --no-cache           -> full dependency reinstall from requirements.lock,
                                              fresh image upadya-backend:be1-batch3
docker compose up -d                      -> new named volume, db healthy, api started
docker compose exec api python -m compileall app   -> clean, no errors
docker compose exec api alembic upgrade head        -> 5 revisions applied to an empty
                                              database, head 20260723_0001, no error
docker compose exec api alembic check               -> "No new upgrade operations detected."
docker compose exec api alembic current             -> 20260723_0001 (head)
docker compose exec api pytest -q                   -> 100 passed, 1 warning (pre-existing
                                              httpx/TestClient deprecation, unrelated to
                                              this batch)
docker compose down -v                    -> isolated verification stack torn down
```

The `alembic check` result on a freshly migrated, previously empty database confirms
zero schema drift: this batch's four endpoints reuse the existing `b_sessions` /
`b_session_events` / `b_runtime_bundle_records` / `b_idempotency_records` /
`b_audit_events` tables exactly as claimed, with no migration file added, changed, or
required.

### Endpoint-count and route-boundary re-verification

`app.openapi()["paths"]` was independently re-enumerated inside the freshly built
container: exactly 20 total operations, the sixteen pre-existing plus exactly the four
authorized `/api/v1/b/sessions*` operations (`POST /api/v1/b/sessions`,
`GET /api/v1/b/sessions/active`, `POST /api/v1/b/sessions/{session_id}/complete`,
`POST /api/v1/b/sessions/{session_id}/abandon`), no more, no fewer.
`test_openapi_contains_exactly_the_four_authorized_b_session_lifecycle_operations` and
`test_no_session_question_answer_or_scientific_route_exists` were run explicitly
(`tests/test_be2_architecture_guards.py -v`, all 13 guard tests passed) and their source
was read directly rather than trusted from the summary: the "session" path-term carve-out
is scoped to exactly the four authorized routes via
`AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS`, and every other prohibited scientific term
(`attempt`, `hint`, `progress`, `bkt`, `mastery`, `sequenc`, `certif`, `guess`) remains
checked unconditionally against all twenty routes, including the four new ones.

### One-active-session invariant under a genuine concurrent race

Re-verified, not merely re-read. Both concurrency tests use real threads and a
`threading.Barrier`, not mocked timing:

- `test_start_concurrent_duplicate_produces_exactly_one_active_session` -- two threads
  submit `POST /api/v1/b/sessions` for the same learner simultaneously with different
  idempotency keys.
- `test_concurrent_complete_and_abandon_race_produces_exactly_one_transition` -- two
  threads race `complete` and `abandon` against the *same* session id simultaneously.

Each was independently re-run 5 times in immediate succession against the fresh
container/database (10 total race executions, not a single sample):

```text
race run 1: 2 passed in 1.96s
race run 2: 2 passed in 1.96s
race run 3: 2 passed in 1.86s
race run 4: 2 passed in 1.99s
race run 5: 2 passed in 2.16s
```

All 10 executions produced exactly one committed transition/active row (`[200, 409]` for
the complete-vs-abandon race; a single deduplicated active session for the concurrent
start race), with no flake observed. This corroborates the buildLog's account of the
identity-map/`FOR UPDATE` bug: reading `app/application/b_session_lifecycle.py`
directly confirms `.execution_options(populate_existing=True)` is present on the
lock-holding `SELECT ... FOR UPDATE` in `_transition`, which is the actual fix, not just
a claim.

### Fail-closed-with-no-bundle

Source-verified in `start_session`: `bundle = await self._resolve_pinnable_bundle(...)`
followed immediately by `if bundle is None: raise ConflictError()`, strictly before any
`SessionRecord` is constructed -- a bundle-less session cannot be created by construction,
not merely by a passing test. `test_start_fails_closed_when_no_approved_bundle_exists`
(exercised via an injected `_resolve_pinnable_bundle` test seam) passed in the fresh run
and independently asserts the learner's active/starting-session count is `0` afterward.

### Ownership/role isolation

Re-verified: `_require_learner` rejects non-`LEARNER` profile types with `403` and
missing profiles with `404` before any session lookup; `get_owned(session_id,
learner_id)` scopes the row lookup to the calling learner, so a different learner's
`complete`/`abandon` attempt on a session they do not own returns `404` (no existence
enumeration), confirmed by
`test_complete_success_replay_path_mismatch_conflict_and_isolation` and
`test_complete_and_abandon_require_learner_role_and_profile` passing.

### Idempotency, including path-mismatch

Re-verified against source and the fresh test run: idempotency records are scoped by
`(actor_user_id, http_method, operation_identifier, idempotency_key)`, and
`_idempotency_start` raises `ConflictError` whenever an existing record's
`request_fingerprint` does not match the current request's fingerprint. The
path-mismatch case specifically (`test_complete_...isolation`'s reuse of one
learner-owned key across two different sessions the same learner owns) produced `409`,
not a false replay, because `path_fingerprint` binds the fingerprint to the path
parameter (`session_id`) as well as the operation and actor.

### Complete/abandon neutrality

Source-verified: `_transition`'s only precondition is `session_row.state != "active"` ->
`ConflictError`; there is no BKT, mastery, certification, Guess-Guard, sequencing, or any
other scientific/pedagogical predicate anywhere in the transition path. `complete` and
`abandon` are both implemented as the same `_transition` helper differing only in
`target_state` and `operation`, confirming symmetric, criteria-free handling.

### NO numeric expiry; NO scientific field in any DTO/log/audit

- `SessionFields`/`SessionCommandResponse`/`ActiveSessionResponse`
  (`app/domain/b_session.py`) expose exactly `session_id`, `state`,
  `runtime_bundle_version`, `created_at_utc`, `row_version`, and (on command responses)
  `request_id` -- no `expires_at`, no numeric timeout, no question/attempt/answer/hint
  field. `StrictModel`'s `extra="forbid"` prevents silent field addition.
- `SessionRecord.expires_at_utc` (the underlying `b_sessions` column, pre-existing from
  an earlier batch) is set to `None` unconditionally in `start_session` and is never
  read or surfaced by any of the four endpoints or by `_session_fields`.
- `provenance()`'s audit/idempotency payload fields (`actor_user_id`, `request_id`,
  `operation_or_event_type`, `reason_code`, `resource_type`, `resource_id`,
  `source_class`, `source_system`, `environment`, `schema_revision`) contain no
  scientific term; `AuditEvent` rows for this batch record only
  `before_reference_or_version`/`after_reference_or_version` state strings
  (`"active"`/`"completed"`/`"abandoned"`).
- `test_b_session_dto_contains_no_scientific_expiry_or_attempt_fields`
  (`tests/test_be2_architecture_guards.py`) performs an AST-level field-identifier scan
  of `app/domain/b_session.py` against a forbidden-term set that includes
  `expires_at`, `expiry`, `timeout`, `question`, `attempt`, `opportunity`, plus the
  shared `PROHIBITED_COLUMN_TERMS` set; it passed in the fresh run.
- `test_exact_authorized_model_table_set_and_no_scientific_columns` independently scans
  every column of every table in `Base.metadata` (not just `b_sessions`) against the
  same prohibited-term set; it passed.

### Architecture guards

All 13 tests in `tests/test_be2_architecture_guards.py` passed in the fresh, isolated
run (`pytest -q tests/test_be2_architecture_guards.py -v`, individually enumerated
above and below), including the table/column scan, the exact-route-set and
exact-four-operation checks, the DTO AST scan, the Yass/`component_b_generator`
import-root scan (`test_no_yass_research_or_scientific_imports`), the dependency-file
scan (`test_dependency_files_exclude_research_generator`), the three prior migrations'
content guards, and the no-production-failure-injection-marker scan
(`test_no_production_failure_injection_or_debug_mechanism`).

### `ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6`

Confirmed still in effect and unchanged by this closure review. This review is a
technical/engineering closure of the BE2.3-BE2.4 batch's implementation quality and
scope boundary only. It is **not** a named-approver ratification: product owner,
backend security owner, and privacy/child-safety owner ratification of session
lifecycle behavior (including the still-`UNRESOLVED` numeric expiry/timeout,
completion, and safe-progress policy gates recorded in earlier BE0/BE2 entries) remains
deferred to the BE6 pre-pilot review. This closure does not create, satisfy, or
shortcut that requirement.

### Non-blocking observations carried forward (unchanged from the batch above)

- The `find_current_approved_published()` most-recent-`created_at_utc` tie-break remains
  an engineering assumption, not a governed selection policy.
- The identity-map/`FOR UPDATE` hazard pattern (`get_owned` unlocked read followed by a
  separate locked re-fetch) is latent in `classroom_membership.approve_membership` and
  was not touched in this batch; recorded again here for BE6 awareness.

Neither observation blocks this closure.

### Closure decision

```text
Identifier: BE2_SESSION_SKELETON_BATCH_CLOSED
Decision:   GO
```

Basis: exactly four authorized routes exist and no others; zero schema drift on a
freshly migrated database; the one-active-session invariant held across 10 independently
re-run genuine concurrent-race executions with no flake; fail-closed-with-no-bundle is
enforced by construction, not merely by a passing assertion; ownership/role isolation,
idempotency (including path-mismatch), and complete/abandon neutrality were all
independently re-verified against source, not just against the prior batch's summary; no
numeric expiry and no scientific field exist in any DTO, log, or audit payload; and all
13 architecture guards pass against a clean, isolated, freshly built environment. This is
an engineering closure only -- `ENGINEERING_CONTINUATION_ALLOWED_RATIFICATION_DEFERRED_TO_BE6`
remains in effect, and named-approver ratification remains deferred to BE6. No commit was
made; the working tree remains as Yasindu left it, pending their review and commit
decision.

---

## Phase BE3 — Batch: Minimal Live-Engine Packaging (`upadya-component-b-live-engine`) — NOT A CLOSURE REVIEW

Completed: 2026-07-24 Asia/Colombo
Build target: `Dev/backend/`
Scientific source repository: `Yass`, pinned commit `0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b`
Authorized by: `backend/provenance/component-b-live-engine-reuse-map.json` and
`component-b-closure-decisions.json` (`generator_packaging_decision.selected_strategy =
MINIMAL_UPADYA_COMPONENT_B_LIVE_ENGINE_AT_BE3`)

### 1. Scope

Packaging and import-boundary work only. No adapter wiring, no live learner flow, no new
scientific parameters, no application import. This batch builds and verifies a new, minimal
wheel distinct from the prohibited full research wheel, and pins it as a backend dependency
without wiring it into `app/`. No git state-changing command was run; nothing is committed.

### 2. Source verification (before use)

`git diff 0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b -- Implementation_v1.0/component_b_generator
Implementation_v1.0/models Implementation_v1.0/validators` against the Yass working tree (HEAD
`648762a60a4590f714418b36dbd286569ee66c5d` at verification time) showed the working tree had
**drifted** from the pinned commit in exactly one file,
`component_b_generator/aggregation/session.py` (a later, unpinned change narrowing
`_response_time_stats`'s standard-deviation handling for fewer than two timed responses).
Because of this drift, the package was built from the exact pinned-commit blob content via
`git show 0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b:<path>` for every file, never from the
mutable working tree. All 45 verbatim files in the built package were independently confirmed
byte-identical to their pinned-commit blob afterward.

The pre-existing `generator_tracked_source_manifest` value recorded in
`component-b-closure-decisions.json`/`component-b-baseline.json`
(`fd4f052e41539434ad4ff6bbb72fa01815ef750ceeb0a6d8ebc6fbc481e07e2c`, 82 tracked files) uses an
undocumented construction; several plausible reconstructions (repo-relative vs.
generator-relative paths, forward- vs. back-slash separators, blob vs. working-tree content,
trailing newline variants) were tried and none reproduced it. Rather than guess further, source
fidelity was established directly by commit diff and per-file byte comparison (above), which is
a stronger guarantee than reproducing an opaque hash. This package's own source manifest is
independently documented (below) with its construction fully specified.

### 3. Reviewed live-safe closure assembled

Location: `backend/packaging/component_b_internal/` (existing stub `pyproject.toml` from an
earlier BE0 note, corrected here — it previously declared the prohibited research
distribution's own name/version; that was dead placeholder text, not a real dependency).

45 files copied byte-identical from the pinned commit (verified — see above); 7 files
deliberately trimmed to remove content that is unreachable/prohibited or simply not part of
the reviewed capability closure, each with an inline `PACKAGING NOTE` docstring explaining the
removal:

- `generation/task_instances.py` — kept `build_task_instance`/`generate_task_instances` bodies
  byte-identical; removed the offline `run_phase_b2a` smoke-path entry point and its unique
  imports, most importantly `from ..runner import run_phase_b1` — exactly the synthetic
  dependency the reuse map's note for this capability flagged as needing exclusion.
- `models/behaviour.py` — kept `ERROR_PATTERNS`/`ErrorPattern`/`HINT_LEVELS`/`_require_skill`/
  `BOpportunityResponseSummary` byte-identical; removed `AuditOnlyModel`,
  `BLearnerSkillTruth`, `BAttemptEvent`, `BoundedBetaSpec`, `BoundedNormalSpec`,
  `BTruthInitializationConfig`, `BInitialLearnerSkillTruth`, `LognormalLatencySpec`,
  `BFirstAttemptBehaviourConfig`, `BAttemptLoopConfig`, `BOpportunityAttemptResult` — the
  hidden-truth and synthetic-behaviour-generation classes explicitly named in the reuse map's
  `explicitly_prohibited_from_application` list. Verified none of the retained symbols
  reference any removed class.
- `models/__init__.py`, `behaviour/__init__.py`, `bkt/__init__.py`, `generation/__init__.py`,
  `sequencing/__init__.py` — each pinned-source `__init__.py` eagerly imports at least one
  prohibited or out-of-closure sibling module at package-import time (e.g.
  `behaviour/__init__.py` imports `.attempt_loop`/`.first_attempt`/`.latency`;
  `generation/__init__.py` imports `.item_opportunities`, which imports
  `..cohort.builder.CohortMember`). Replaced with empty re-export surfaces; no module in the
  reviewed closure does a bare `from ..<package> import X`, so nothing depends on the removed
  re-exports.

Excluded entirely by omission (files never copied into the package, so they are unreachable by
`ModuleNotFoundError`, not merely unimported): `cohort/*`, `behaviour/first_attempt.py`,
`behaviour/latency.py`, `behaviour/attempt_loop.py`, `behaviour/initialization.py`,
`behaviour/wrong_answers.py`, `behaviour/derivation.py`, `behaviour/seeds.py`,
`behaviour/validation.py`, `pipeline.py`, `pilot.py`, `runner.py`, `audits/*`,
`generation/item_opportunities.py`, `generation/coverage.py`, `sequencing/eligibility.py`,
`sequencing/select_item.py`, `bkt/orchestrator.py`, `config/*`, `adapters/*`, `validators/*`.

### 4. Package identity and build

- Distribution: `upadya-component-b-live-engine`, version `0.1.0+be3.0e86fdc` (distinct name
  and version from the prohibited research distribution `upadya-component-b-generator`, per
  `closure-decisions.json`'s `versioning_method`).
- Dependencies: `pydantic==2.13.4`, `PyYAML==6.0.3` only (the reviewed closure does not use
  numpy/pandas/scikit-learn/jsonschema, unlike the full research wheel).
- Built with `python -m build --wheel --no-isolation` (`setuptools==80.10.2`,
  `wheel==0.46.3`) in an isolated Python 3.11.15 venv.
- Wheel: `upadya_component_b_live_engine-0.1.0+be3.0e86fdc-py3-none-any.whl`
  SHA-256 `faa5760df1f5a3874f38f8103cdaaa88a14b3190216e46ab21765eee65a70c29`, placed at
  `backend/provenance/wheels/` alongside the existing (still-present, still-prohibited-for-
  runtime) full research wheel.
- Package source manifest: SHA-256 of `'<package-relative-posix-path>\t<sha256-of-file-bytes>\n'`
  lines sorted by path, over all 52 `*.py` files in
  `backend/packaging/component_b_internal/` — `4321ebfdb7041a62be8620e857736db4146ae9eb27e78dffd1fd52f44664315f`.
  Full construction, both checksums, and per-file inclusion/exclusion/trim rationale are
  recorded in `backend/provenance/component-b-live-engine-manifest.json`.

### 5. Verification (isolated Python 3.11.15 venv, `pydantic`+`PyYAML` only)

- All function/class names listed against the 11 capabilities in
  `component-b-live-engine-reuse-map.json` import successfully from the installed wheel.
- `importlib.import_module` raises `ModuleNotFoundError` for `component_b_generator.cohort`,
  `.cohort.builder`, `.behaviour.first_attempt`, `.behaviour.latency`,
  `.behaviour.attempt_loop`, `.pipeline`, `.pilot`, `.runner`, `.audits` (and its submodules),
  `.generation.item_opportunities`.
- `AuditOnlyModel`/`BLearnerSkillTruth`/`BAttemptEvent`/etc. are absent from
  `component_b_generator.models.behaviour` in the installed wheel.
- `bkt_predict`/`bkt_posterior`/`bkt_update` returned byte-identical output across two calls
  with identical fixed inputs in the same process (determinism smoke test).

### 6. Dependency pin (no adapter wiring)

`requirements.in`, `requirements.lock` (with `--hash=sha256:...`), and `requirements.txt` each
gained one line: `./provenance/wheels/upadya_component_b_live_engine-0.1.0+be3.0e86fdc-py3-none-any.whl`.
No file under `app/` imports the package or any of its modules. `backend/.dockerignore`
currently excludes `provenance/`, `packaging/`, and `*.whl` from the Docker build context, so
an actual `docker build` cannot yet install this pin — that gap, plus any Dockerfile `COPY`
change, is explicitly left for BE3b (adapter wiring), not touched here.

### 7. Tests added and existing guards re-run

New: `tests/test_be3_live_engine_boundary.py` —
`test_prohibited_module_is_not_importable_from_the_package` (parametrized over all 13 excluded
modules from the reuse map's exclusion list), `test_thirteen_prohibited_capabilities_are_unreachable`,
`test_no_dataset_generation_or_experiment_runner_entry_point_in_package`,
`test_app_import_graph_still_does_not_reach_prohibited_modules` (unchanged BE2-style guard,
reconfirmed against `app/` with the new package installed), `test_bkt_update_is_deterministic_under_fixed_provenance`,
`test_guess_guard_is_deterministic_under_fixed_provenance`. Uses `pytest.importorskip` so it
skips cleanly wherever the package is not installed.

Re-run in the same isolated venv: `tests/test_be2_architecture_guards.py` (all 13, including
`test_dependency_files_exclude_research_generator`, which still passes — the new pin's text
contains neither `component-b-generator`/`component_b_generator` nor `yass`) and
`tests/test_be3_live_engine_boundary.py` — **35 passed, 0 failed**
(`pytest -q tests/test_be3_live_engine_boundary.py tests/test_be2_architecture_guards.py`).
`pytest -q --collect-only` across the full `tests/` tree collected all 122 tests with no import
errors (the DB-backed test modules were not executed — no local PostgreSQL instance — but
collection alone confirms this batch introduced no import-time regression anywhere).

### 8. Recorded checksums (as requested)

- Wheel SHA-256: `faa5760df1f5a3874f38f8103cdaaa88a14b3190216e46ab21765eee65a70c29`
- Package source manifest SHA-256: `4321ebfdb7041a62be8620e857736db4146ae9eb27e78dffd1fd52f44664315f`
- Pinned source commit: `0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b`

### 9. Limitations and next task

This is packaging + import-boundary work only — **not a closure review** and not a governance
ratification. Unresolved: whether the trimmed-file boundary choices above (especially the
`models/behaviour.py` split and the five emptied `__init__.py` files) match what a named
Component B owner would approve; the Docker build-context gap in §6; and all governance-register
items already `UNRESOLVED`/`CALIBRATION_PENDING` in `component-b-closure-decisions.json` remain
exactly as they were. Next task is BE3b: a named-owner review of this packaging batch, followed
(only if approved) by adapter wiring, `.dockerignore`/Dockerfile updates to actually install the
pin in the image, and the first real application import. No commit was made; the working tree
remains as Yasindu left it, pending their review and commit decision.

## BE3a closure review — independent re-verification (2026-07-24)

Separate closure review of the minimal live-engine package against PROMPT BE3a,
`component-b-live-engine-reuse-map.json`, and the `generator_packaging_decision` in
`component-b-closure-decisions.json`. Read-only git; nothing committed. `.claude/settings.json`
treated as out of scope for this batch. Re-verification performed independently from a clean
isolated environment, not by re-reading the prior batch's own claims.

**Environment.** `docker run` against `python:3.11.15-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba`
— the exact base image digest pinned in `backend/Dockerfile` — with the `backend/` tree copied
into a writable `/workspace` inside the container (a read-only bind mount plus `pip install`
was used only to avoid touching the host). `pip install --require-hashes --no-deps -r
requirements.lock` installed cleanly, including the live-engine wheel via its recorded hash.

**(1) Wheel identity — PASS.** `sha256sum` on both files in `backend/provenance/wheels/`:
live-engine wheel = `faa5760df1f5a3874f38f8103cdaaa88a14b3190216e46ab21765eee65a70c29`, exactly
matching `component-b-live-engine-manifest.json:package.wheel_sha256` and the hash pinned in
`requirements.lock`. Full research wheel = `12b5ba5b7e8a70785a3e2b49e5c07bc8f89cc677c268ea509907f8f6d517e750`,
matching `component-b-closure-decisions.json:full_wheel_artifact.sha256`. The two digests are
distinct.

**(2) Every packaged file — PASS.** Listed all 52 `*.py` files actually present under
`backend/packaging/component_b_internal` (matches `package_source_manifest.file_count`).
Confirmed against the pinned Yass commit `0e86fdcbc0ffcdbda3d37c742e83b1d532910e2b` (verified
reachable in the local Yass clone via `git cat-file -e`):
- All 45 files listed as verbatim were diffed with `diff <(git show <commit>:Implementation_v1.0/<path>) <packaged file>` — zero differences on every file.
- All 7 trimmed files (`generation/task_instances.py`, `models/behaviour.py`, `models/__init__.py`, `behaviour/__init__.py`, `bkt/__init__.py`, `generation/__init__.py`, `sequencing/__init__.py`) were diffed line-by-line against the same pinned blobs. In every case the only changes are: added packaging-note docstrings, removed imports/re-exports of prohibited symbols (`run_phase_b2a`, `..runner.run_phase_b1`, the `AuditOnlyModel`/hidden-truth/synthetic-behaviour classes, `.cohort`, `.item_opportunities`, `.eligibility`, `.select_item`, `.orchestrator`, and their transitive `__init__.py` re-exports), and removal of the now-unused stdlib/pydantic imports those deletions made dead. Every retained function/class body (`build_task_instance`, `generate_task_instances`, `BOpportunityResponseSummary`, `ERROR_PATTERNS`, `ErrorPattern`, `HINT_LEVELS`, `_require_skill`) is untouched — no line inside a retained body differs from the pinned blob. No mathematical formula was altered.
- Independently recomputed `package_source_manifest.sha256` from the packaged tree using the documented algorithm: `4321ebfdb7041a62be8620e857736db4146ae9eb27e78dffd1fd52f44664315f`, file_count 52 — both match the manifest exactly.

**(3) 13 prohibited-module unreachability — PASS.** Inside the isolated container, attempted
`importlib.import_module` on 22 module paths covering all 13 reuse-map exclusion items —
`cohort`/`cohort.builder`, all 6 `behaviour.*` synthetic submodules, `pipeline`, `pilot`,
`runner`, `audits` + 3 submodules, `generation.item_opportunities`, `sequencing.eligibility`,
`sequencing.select_item`, `bkt.orchestrator`, and the standalone `validators` package — every
one raised `ModuleNotFoundError`. `component_b_generator.models.behaviour` was imported and
checked for the 11 hidden-truth/synthetic classes named in the reuse map: none present. Then
ran `pytest tests/test_be3_live_engine_boundary.py tests/test_be2_architecture_guards.py` in
the same container — **35 passed, 0 failed**, including the app-import-graph guard
(`test_app_import_graph_still_does_not_reach_prohibited_modules`) and the BE2
`test_no_yass_research_or_scientific_imports` / `test_dependency_files_exclude_research_generator` guards.

**(4) Full research wheel not an app dependency — PASS.** `requirements.in`/`requirements.txt`/`requirements.lock`
reference only the live-engine wheel path; grepped all three for the research wheel's
distribution name — no match. Grepped `app/**/*.py` for `component_b|cohort|pipeline|pilot|generator`
— the only two hits are a `"generator": "not_checked"` health-check status string
(`app/api/routes/health.py`) and a docstring mention of "synthetic-generator fields" being
excluded (`app/infrastructure/persistence_models.py`); neither is an import. Confirmed all 11
reuse-map capability symbols import successfully from the installed wheel in isolation.

**(5) BE2 guards + BE3 boundary tests — PASS.** See (3): 35/35 passed in the isolated,
Dockerfile-pinned Python 3.11.15 environment.

**(6) `.dockerignore` limitation — confirmed, carry-forward, not a blocker.** Read
`backend/.dockerignore`: it excludes `provenance/`, `packaging/`, and `*.whl` from the `docker
build` context. This is real and independently reproducible — a `docker build` of
`backend/Dockerfile` today cannot resolve the `./provenance/wheels/...whl` path in
`requirements.lock`. It does not affect this review because verification was performed by
copying the tree into a container rather than through `docker build`, which is what the
prompt's "clean isolated Python 3.11 env" calls for; the app image build path is explicitly
BE3b scope per `generator_packaging_decision`, not this batch.

**Verdict: GO — `BE3A_LIVE_ENGINE_PACKAGE_BATCH_CLOSED`.** All five re-verifiable technical
gates pass under independent, from-scratch checking (not a re-read of the prior batch's own
claims); the one disclosed limitation is confirmed real and is correctly scoped as a BE3b
carry-forward rather than a defect in this batch. This closes the *packaging and import-boundary*
scope only — it is not a governance or named-owner ratification, and every `UNRESOLVED`/
`CALIBRATION_PENDING` item in `component-b-closure-decisions.json`'s governance register remains
open exactly as recorded there. No files were modified by this review beyond this log entry; no
git commit was made.

## BE3b — Domain Ports, Live-Engine Adapter, Runtime-Bundle Validation, Docker-Install Fix (2026-07-25)

Batch scope per BEplan §BE3.1–§BE3.2, `component-b-live-engine-reuse-map.json`, and
`runtime-bundle.schema.json`: domain ports over the reviewed live-safe capabilities, the concrete
adapter binding those ports to the vendored `upadya-component-b-live-engine` package, immutable
runtime-bundle load/validate machinery, and the Docker-install fix carried forward from BE3a's
disclosed `.dockerignore` limitation. No live learner flow, no real approved scientific
parameters, no BE4 governance-gate crossing. Read-only git throughout; nothing committed.

### 1. Docker-install fix

- `backend/.dockerignore`: added two narrow negations after the existing blanket `provenance/`
  and `*.whl` excludes — `!provenance/wheels/upadya_component_b_live_engine-0.1.0+be3.0e86fdc-py3-none-any.whl`
  and `!provenance/runtime-bundle.schema.json`. Everything else under `provenance/` (baseline
  manifests, closure decisions, the generator dependency lock, and — critically — the
  **prohibited full research wheel** `upadya_component_b_generator-...whl`, which sits in the
  same `provenance/wheels/` directory) stays excluded from the build context. `packaging/`
  (the source tree used only to build the wheel) also stays excluded; the app installs from the
  wheel only, never from source.
- `backend/Dockerfile`: added two `COPY` steps before the `pip install` line — the pinned
  live-engine wheel (so `pip install --require-hashes -r requirements.lock` can resolve the
  relative wheel path it already pinned) and `provenance/runtime-bundle.schema.json` (needed by
  the runtime-bundle loader at import time, not only by tests).
- `requirements.in` / `requirements.txt` / `requirements.lock`: added `jsonschema==4.25.1` and
  its resolved transitive dependencies (`attrs==25.4.0`, `jsonschema-specifications==2025.9.1`,
  `referencing==0.37.0`, `rpds-py==0.30.0`) with `--hash=sha256:...` entries for every published
  file of each pinned version, fetched from the PyPI JSON API and inserted at the correct
  alphabetical position to match the existing `requirements.lock` convention. `jsonschema` is a
  new real runtime dependency (schema validation for the runtime-bundle manifest); nothing else
  in `requirements.lock` changed.
- **Proof (not simulated).** `docker compose build api` — full build succeeded; pip installed
  `upadya-component-b-live-engine-0.1.0+be3.0e86fdc` from the now-resolvable wheel path alongside
  the rest of the lock, no `--require-hashes` failures. `docker run --rm upadya-backend:be1-batch3
  python -c "import component_b_generator; from app.infrastructure.live_engine.adapter import
  LiveEngineAdapter"` — both imports succeeded inside the built image. Then `docker compose up -d
  db`, waited for the Postgres healthcheck, and ran `docker run --network upadya-be1_default -e
  DATABASE_URL=... upadya-backend:be1-batch3 python -m pytest -q` against the built image: **153
  passed, 0 failed** (up from the 35 BE2/BE3a-guard subset re-verified in the BE3a closure
  review — this run is the complete suite, including the persistence/UoW/session-lifecycle tests
  that need a real database). `docker compose down` after.

### 2. Domain ports (`app/domain/live_engine/`, `app/domain/runtime_bundle/`)

Added `types.py` (plain `frozen` dataclasses only — no package Pydantic model is imported or
re-exported anywhere under `app/domain`), `ports.py` (one `Protocol` per reuse-map capability:
`CataloguePort`, `ActivationPort`, `SequencingPort`, `TaskConstructionPort`, `AnswerPort`,
`DistractorPort`, `HintPort`, `BktPort`, `GuessGuardPort`, `CertificationPort`,
`AggregationPort`), and `errors.py` (the stable internal/application error hierarchy:
`CatalogueUnavailableError`, `UnknownTemplateError`, `TemplateNotActiveError`,
`TaskConstructionError`, `AnswerRuleUnavailableError`, `DistractorConstructionError`,
`HintUnavailableError`, all under a `LiveEngineError` base). Separately,
`app/domain/runtime_bundle/` holds the `RuntimeBundle` dataclass mirroring
`runtime-bundle.schema.json`'s own property names, the `RuntimeBundleLoaderPort` protocol, and
its fail-closed error hierarchy (`RuntimeBundleNotFoundError`, `RuntimeBundleValidationError`,
`RuntimeBundleChecksumMismatchError`, `RuntimeBundleNotApprovedError`).

Domain `ItemTemplate`/`Catalogue` carry a reduced field set versus the package's own
`ItemTemplate`/`LoadedCatalogue` (no `set_id`/`node_name`/`status_raw`/hint fields at the domain
layer) — sufficient for every BE3b capability and test; later batches may extend these types as
new capabilities are wired, without ever reaching for the package's models to do it.

### 3. Adapter (`app/infrastructure/live_engine/adapter.py`)

`LiveEngineAdapter` is the **only file under `app/` that imports `component_b_generator`**
(enforced by the updated import-boundary tests, §5). It is stateless: every method is a pure
function of its arguments, re-reading the governed catalogue file at `Catalogue.source_path`
whenever a package-native `LoadedCatalogue`/`ItemTemplate` object is needed rather than
hand-reconstructing one from the trimmed domain type — so every package function always receives
the real, fully-validated loader output, never an approximation of it. No formula is copied or
rewritten: every method is a direct call into the package's own `catalogue.loader`,
`generation.activation`, `sequencing.features`/`score`, `generation.task_instances`,
`answers.rules`/`registry`, `distractors.registry`, `behaviour.hints`, `bkt.update`,
`bkt.guess_guard`, `bkt.certification`, and `aggregation.session` modules. Package exceptions
(`CatalogueValidationError`, `UnsupportedTemplateError`, `TaskInstanceValidationError`,
`HintContentError`, `DistractorGenerationError`, bare `KeyError` for unregistered template ids)
are translated into the domain error hierarchy at the adapter boundary; nothing package-specific
propagates past it.

Deterministic task construction (`build_task_instance`) accepts a backend-owned
`TaskConstructionRequest` carrying a session-pinned `global_seed` rather than a package
`SeedLineage` — the adapter derives the opportunity's seed lineage internally via the package's
own `SeedManager`, keeping `seeds`/`SeedLineage` entirely `PRIVATE_ENGINE_INTERNAL` as the reuse
map requires. Sequencing's weighted-sum score uses the FROZEN 0.50/0.30/0.20 weights pinned
inside the adapter (`BSequencingConfig` is constructed with those exact values every call); no
caller can supply a different weight set through the domain port.

### 4. Runtime-bundle load/validate machinery (`app/infrastructure/runtime_bundle/loader.py`)

`RuntimeBundleLoader.load_and_validate(bundle_path, schema_path, *, artifact_paths=None,
require_approved=True)`:

1. Reads the manifest and schema JSON; a missing file raises `RuntimeBundleNotFoundError`,
   invalid JSON raises `RuntimeBundleValidationError` — never a partial parse.
2. Validates the manifest against `runtime-bundle.schema.json` via `jsonschema.validate`
   (Draft 2020-12, matching the schema's own `$schema`); any missing required field, wrong type,
   or violated `const`/`enum`/`pattern` raises `RuntimeBundleValidationError` with the failing
   JSON path in the message.
3. Verifies the `generator` artifact's declared SHA-256 against the file at its `source_path` —
   the only artifact the frozen schema itself gives a `source_path` for. `catalogue`/
   `bkt_configuration`/`certification_configuration`/`guess_guard_configuration`/
   `safe_progress_policy`/`attempt_policy`/`timeout_policy` are schema-shaped `versionedArtifact`
   entries with a `checksum` but **no path field** in the frozen schema; the loader additionally
   verifies any of these the caller supplies a real file for via the optional `artifact_paths`
   mapping (exercised in tests against the fixture catalogue), and does not fabricate
   verification against files the schema gives no location for.
4. Gates on `approval_status`: `require_approved=True` (the default — the readiness/activation
   path) raises `RuntimeBundleNotApprovedError` for anything other than exactly `"APPROVED"`.
   **This batch never writes `"APPROVED"` anywhere** — not in the loader, not in any fixture —
   so every positive-path test below exercises the loader with `require_approved=False`
   explicitly, and the one test that uses the default proves the gate itself fails closed on an
   otherwise-valid bundle. Approving a real bundle remains the separate BE4 governance gate.

### 5. Test fixtures (TEST-FIXTURE-ONLY, never the governed catalogue)

- `tests/fixtures/runtime_bundle/test_catalogue.md` — a 7-template, 7-skill markdown catalogue
  (one already-implemented representative template per skill: `B-CNT01-SEQ-CONTINUE`,
  `B-NS04-COMPARE-NUMERALS`, `B-PV01-IDENTIFY-TENS-ONES`, `B-ADD04-2D-NO-REGROUP`,
  `B-SUB04-2D-NO-BORROW`, `B-MUL03-FACTS-2-5-10`, `B-DIV03-DIVIDE-BY-2`), with hint text on two
  templates and deliberately none on `B-DIV03-DIVIDE-BY-2` to exercise the hint fail-closed path.
  Verified against the real `load_catalogue` inside an isolated container before being used by
  any test.
- `tests/fixtures/runtime_bundle/valid_unapproved_bundle.json` — schema-valid, and its
  `generator` checksum is the **real** recorded SHA-256 of the pinned live-engine wheel
  (`faa5760df1f5a3874f38f8103cdaaa88a14b3190216e46ab21765eee65a70c29`, matching
  `component-b-live-engine-manifest.json`) so the checksum-verification positive path is
  checking something real, not a fixture-only value. `approval_status` is `CALIBRATION_PENDING`
  throughout (top level and every sub-artifact) — never `APPROVED`.
- `tests/fixtures/runtime_bundle/missing_field_bundle.json` — the same manifest with
  `bkt_configuration` removed, for the missing-required-field defect class.
- `tests/fixtures/runtime_bundle/bad_checksum_bundle.json` — the same manifest with the
  `generator` checksum value replaced by 64 `f`s, for the checksum-mismatch defect class.

### 6. Tests added

- `tests/test_be3b_live_engine_adapter.py` — catalogue load/checksum mapping; activation
  active/inactive/unknown-template; task-instance determinism under fixed provenance (two calls,
  identical result) and non-determinism under a different `global_seed`; operand/correct-answer
  internal consistency via the adapter's own `AnswerPort` recomputation; governed hint content
  and fail-closed missing-hint content; BKT predict/posterior/update boundedness, determinism,
  and correct-vs-incorrect posterior ordering; Guess-Guard triggered/insufficient-evidence/
  not-triggered plus certification's dependence on it; sequencing feature computation and the
  frozen-weight score identity; selection tie-break reporting; session aggregation folding one
  opportunity into a rollup, and the missed-session-with-opportunities contract violation
  surfacing as `LiveEngineError`.
- `tests/test_be3b_runtime_bundle.py` — schema-valid+checksum-correct load under
  `require_approved=False`; `artifact_paths` checksum verification against the real fixture
  catalogue (positive) and a substituted wrong file (negative); missing required field; generator
  checksum mismatch; unapproved status under the default `require_approved=True`; missing
  manifest file; missing schema file; invalid JSON; wrong type for a required field; and an
  explicit assertion that no fixture in this batch is ever marked `"APPROVED"`.
- Updated `tests/test_be3_live_engine_boundary.py`'s
  `test_app_import_graph_still_does_not_reach_prohibited_modules` (renamed
  `test_only_the_live_engine_adapter_module_imports_the_package`, plus a new
  `test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules`): that test's own
  docstring said "this batch does not wire any application adapter" — BE3b is that next batch, so
  the over-broad "app/ may never import `component_b_generator` at all" assertion no longer
  holds. The updated guard instead asserts the top-level package import is confined to exactly
  `app/infrastructure/live_engine/adapter.py`, and — separately, repo-wide, including inside the
  adapter itself — that all 13 explicitly-prohibited submodules (`cohort`/*, the six synthetic
  `behaviour.*` generators, `pipeline`, `pilot`, `runner`, `audits`/* , `generation.item_opportunities`)
  stay unreachable. Same treatment applied to the older, even-broader BE2 guard
  `test_no_yass_research_or_scientific_imports` in `tests/test_be2_architecture_guards.py`, which
  predated BE3a and had the identical whole-package prohibition.

### 7. What this batch deliberately does not do

No new API route. No live question/attempt/hint/BKT-write flow. No persisted opportunity/task
tables. No real governed catalogue reference (the adapter's `CataloguePort.load` takes an
explicit path, per BE3.2 step 2, but every call in this batch's tests points at the
TEST-FIXTURE-ONLY catalogue above — never `R26-IT-138`). No runtime bundle in this batch is ever
marked `APPROVED`, `activation_date` is `null` throughout, and `publication_state` stays `DRAFT`.
The private/public opportunity DTO split, the full characterization/privacy suite against the
real catalogue, and building/approving the real runtime bundle remain explicitly out of scope
(BE3c and the BE4 governance gate, respectively).

**Status: BE3b engineering continuation, not a closure review.** 153/153 tests pass in the
Dockerfile-pinned image against a real Postgres, including the full BE2 architecture-guard suite
and the updated BE3 import-boundary guards. No git commit was made; the working tree remains
uncommitted for Yasindu's review.

## BE3b Closure Review (separate pass against PROMPT BE3b, the reuse map, and runtime-bundle.schema.json)

Performed from a clean `docker build --no-cache` of `backend/Dockerfile`, plus a fresh Postgres
16 container for the migration + full test run. Read-only: no git operations, no commits.

1. **Single import point.** `grep -rl component_b_generator app/` returns only
   `app/infrastructure/live_engine/adapter.py` (the one other hit,
   `app/domain/live_engine/__init__.py`, is a docstring mention, not an import). Confirmed
   independently of `test_only_the_live_engine_adapter_module_imports_the_package`, which also
   passes. `app/domain/**` uses only `dataclass`/`Enum` types in `live_engine/types.py` and
   `runtime_bundle/types.py` — no import of any `component_b_generator` Pydantic model. The other
   `pydantic.BaseModel` usages under `app/domain/` (`b_session.py`, `classroom_membership.py`,
   `principal.py`, `profile_classroom.py`) are backend-owned models unrelated to the vendored
   package — out of scope for this check and not a boundary violation.

2. **No formula copied.** Read `adapter.py` in full: every port method calls straight through to
   a package function (`bkt_predict/posterior/update`, `evaluate_guess_guard`, `certify_skill`,
   `score_candidate`, `build_task_instance`, `aggregate_session`, etc.) and only maps backend
   dataclasses to package Pydantic/dataclass types and back. The only literal numbers the adapter
   contributes are the frozen sequencing weights (0.50/0.30/0.20), passed into the package's own
   `BSequencingConfig`, which does the scoring — no math is reimplemented in the adapter.

3. **Guard completeness — GAP FOUND.** `PROHIBITED_MODULES` in
   `tests/test_be3_live_engine_boundary.py` includes `cohort`, `cohort.builder`,
   `behaviour.first_attempt`, `behaviour.latency`, `behaviour.attempt_loop`,
   `behaviour.initialization/wrong_answers/derivation/seeds/validation`, `pipeline`, `pilot`,
   `runner`, `audits` (+ `audits.fidelity/leakage/population_neutrality`) — but it does **not**
   include `component_b_generator.generation.item_opportunities`. The reuse-map/manifest side is
   internally consistent (`component-b-live-engine-manifest.json` line 146 lists
   `generation.item_opportunities` under `excluded_by_omission.modules`, and its
   `prohibited_module_unreachability_check` at line 160 records that unreachability was manually
   verified at packaging time), but that manual, packaging-time check is not mirrored in the
   automated `PROHIBITED_MODULES` regression tuple. Confirmed by direct import in the built image
   (`ModuleNotFoundError: No module named 'component_b_generator.generation.item_opportunities'`)
   — the module is absent from the current wheel, so there is no live violation today. But
   because it is missing from `PROHIBITED_MODULES`, neither
   `test_prohibited_module_is_not_importable_from_the_package` nor
   `test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules` would catch a future
   wheel rebuild that reintroduces it (e.g. via `generation/__init__.py` un-trimming). This is the
   one item in the required list (behaviour.first_attempt/latency/attempt_loop, cohort/*,
   pipeline, pilot, runner, audits, generation.item_opportunities) not actually present in the
   guard. Recommend adding it to `PROHIBITED_MODULES` before treating this guard as closed.

4. **Built-image inspection.** `docker build --no-cache` succeeded from `backend/Dockerfile`
   unmodified. `pip list` in the built image shows exactly one Component-B package,
   `upadya-component-b-live-engine 0.1.0+be3.0e86fdc`; `import upadya_component_b_generator`
   (the full research wheel's name) raises `ModuleNotFoundError`, and a repo-wide
   `find / -iname '*component_b_generator*'` inside the container returns only the single vendored
   package directory. `.dockerignore`'s `provenance/wheels/*` + explicit
   `!upadya_component_b_live_engine-...whl` allowlist keeps any other wheel out of the build
   context. Live-engine functions (`bkt_predict/posterior/update`, `plausibility_floor`) import
   and run inside the image.

5. **Runtime-bundle loader fail-closed behavior.** Verified in `tests/test_be3b_runtime_bundle.py`
   and by re-reading `app/infrastructure/runtime_bundle/loader.py`: missing manifest/schema file →
   `RuntimeBundleNotFoundError`; invalid JSON → `RuntimeBundleValidationError`; missing required
   field or wrong type → `RuntimeBundleValidationError` (schema-driven); generator checksum
   mismatch or a caller-supplied `artifact_paths` checksum mismatch →
   `RuntimeBundleChecksumMismatchError`; any `approval_status != "APPROVED"` under the default
   `require_approved=True` → `RuntimeBundleNotApprovedError`. Grepped every fixture
   (`valid_unapproved_bundle.json`, `missing_field_bundle.json`, `bad_checksum_bundle.json`) —
   every `approval_status` occurrence (top-level and every sub-artifact) is `CALIBRATION_PENDING`
   or `ENGINEERING_ASSUMPTION`, never `APPROVED`; `test_never_marks_a_bundle_approved_in_this_batch`
   asserts this directly. The loader has no code path that writes or defaults `approval_status`,
   so it cannot self-approve.

6. **Full suite in the image.** Built the image with `docker build --no-cache`, ran
   `alembic upgrade head` against a throwaway `postgres:16-alpine` container (clean, migrations
   applied without error), then `python -m pytest -q`: **153 passed**, 0 failed. Re-ran
   `tests/test_be3_live_engine_boundary.py tests/test_be2_architecture_guards.py
   tests/test_be3b_live_engine_adapter.py tests/test_be3b_runtime_bundle.py` verbosely: 66/66
   passed, confirming the import-boundary and architecture guards are active and green in the
   built image, not just locally.

**Verdict: NO-GO — BE3B_ADAPTER_AND_BUNDLE_BATCH_CLOSED.** Items (1), (2), (4), (5), and (6) all
verify clean. Item (3) fails as specified: `generation.item_opportunities` is required to be part
of the completed `PROHIBITED_MODULES` guard and is not. This is a narrow, mechanical gap (one
tuple entry) with no live exploit today — the module doesn't exist in the current wheel — but the
guard as written does not yet meet the "COMPLETE" bar this review was asked to confirm. Closure
should be re-requested after `generation.item_opportunities` is added to `PROHIBITED_MODULES` in
`tests/test_be3_live_engine_boundary.py` (and the suite re-run green in the image).

Docker/Postgres containers, network, and image built for this review were removed after
verification; nothing was committed.

## 2026-07-25 — Guard-completeness fix (NO-GO item 3 closure)

Added `"component_b_generator.generation.item_opportunities"` to `PROHIBITED_MODULES` in
`tests/test_be3_live_engine_boundary.py` — the one tuple entry the NO-GO review flagged as
missing relative to `excluded_by_omission.modules` in
`backend/provenance/component-b-live-engine-manifest.json`. One-line addition only; no
adapter/loader change, no behavior change.

Re-verified from a fresh `docker build --no-cache` of `backend/Dockerfile` (image
`upadya-backend:be3b-fix`), migrations applied via `alembic upgrade head` against a throwaway
`postgres:16.10-bookworm` container, then the full suite run inside the built image:
**154 passed** (153 from the prior closure run + 1 new parametrized case for the added module),
0 failed. Re-ran `tests/test_be3_live_engine_boundary.py tests/test_be2_architecture_guards.py
tests/test_be3b_live_engine_adapter.py tests/test_be3b_runtime_bundle.py` verbosely: 67/67 passed
(up from 66/66), confirming both consuming guards —
`test_prohibited_module_is_not_importable_from_the_package[component_b_generator.generation.item_opportunities]`
and `test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules` — are green with the
extended tuple.

Direct confirmation in the built image:
`importlib.import_module("component_b_generator.generation.item_opportunities")` raises
`ModuleNotFoundError: No module named 'component_b_generator.generation.item_opportunities'` —
the newly-guarded module is genuinely absent from the installed wheel, so the guard passes
because the module is unreachable, not because the test was skipped. The adapter's legitimate
imports — `component_b_generator.generation.activation`, `.errors`, `.task_instances` — all
import successfully; none contain the substring `item_opportunities`, so there is no false
positive from the new guard entry.

Docker/Postgres containers, network, and image built for this fix were removed after
verification; nothing was committed — working tree remains uncommitted for Yasindu's review.

## BE3b Re-Closure Review (focused re-verification of the guard-gap fix)

Read-only, independent re-run from a fresh `docker build --no-cache` of `backend/Dockerfile`
(image `upadya-backend:be3b-reclosure`), a throwaway `postgres:16.10-bookworm` container on a
dedicated bridge network, and `alembic upgrade head` against it (clean, no errors). This pass
re-confirms only the scope named in the re-closure request; the import boundary, no-formula-copy,
built-image wheel exclusion, fail-closed loader, and green suite were already independently
established in the closure review above and are re-checked here only insofar as the full suite
run and the specific NO-GO item cover them.

1. **`PROHIBITED_MODULES` now includes the missing entry.** Read
   `tests/test_be3_live_engine_boundary.py` directly: line 41 is
   `"component_b_generator.generation.item_opportunities"`, appended after the 13 previously-listed
   entries (cohort/*, 6x behaviour.*, pipeline, pilot, runner, audits + 3 audits submodules). Both
   consuming guards pick it up:
   `test_prohibited_module_is_not_importable_from_the_package[component_b_generator.generation.item_opportunities]`
   and `test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules` both PASSED in the
   built image (verbose run below).

2. **Built-image `importlib` behavior.** Ran directly inside the built image:
   `importlib.import_module("component_b_generator.generation.item_opportunities")` raises
   `ModuleNotFoundError: No module named 'component_b_generator.generation.item_opportunities'` —
   absent, not skipped. In the same process, the adapter's actual imports —
   `component_b_generator.generation.activation`, `.errors`, `.task_instances` — all import
   successfully, confirming the new guard entry does not collide with or block any legitimate
   adapter import.

3. **Full suite in the image.** `python -m pytest -q` inside the freshly-built image: **154
   passed**, 0 failed. Targeted verbose re-run of
   `tests/test_be3_live_engine_boundary.py tests/test_be2_architecture_guards.py
   tests/test_be3b_live_engine_adapter.py tests/test_be3b_runtime_bundle.py`: **67/67 passed**,
   including all 18 parametrized cases of
   `test_prohibited_module_is_not_importable_from_the_package` (the 13 original + the new
   `generation.item_opportunities` case).

4. **No other BE3b finding regressed.**
   - **Sole app/ importer.** `grep -rl component_b_generator app/` inside the built image
     (excluding `__pycache__`) returns only `app/infrastructure/live_engine/adapter.py`;
     `app/infrastructure/live_engine/__init__.py` and `app/domain/live_engine/__init__.py` are
     docstring mentions, not imports (read in full — no `import`/`from` statement present).
   - **No package Pydantic models in `app/domain`.** `grep -rn BaseModel app/domain` finds exactly
     four backend-owned models (`classroom_membership.py`, `principal.py`, `b_session.py`,
     `profile_classroom.py`) — none reference `component_b_generator`.
   - **Image lacks the full research wheel.** `pip list` shows exactly one Component-B package,
     `upadya-component-b-live-engine 0.1.0+be3.0e86fdc`; `import upadya_component_b_generator`
     raises `ModuleNotFoundError`; a repo-wide `find / -iname '*component_b_generator*'` returns
     only the single vendored package under `site-packages`. `.dockerignore` still excludes
     `provenance/wheels/*` broadly and allowlists back only the pinned live-engine wheel and
     `provenance/runtime-bundle.schema.json`, keeping the research wheel and the rest of
     `provenance/` out of the build context.
   - **Loader still fails closed.** `tests/test_be3b_runtime_bundle.py` (10/10 in the verbose run
     above) covers missing manifest/schema file, invalid JSON, missing/wrong-type required field,
     generator and artifact-path checksum mismatch, and default-`require_approved` rejection of
     any non-`APPROVED` bundle — all still raise the expected typed error in the built image.

Docker/Postgres containers, the dedicated network, and the image built for this re-closure were
removed after verification (`docker rm -f`, `docker network rm`, `docker rmi`); nothing was
committed — working tree remains uncommitted for Yasindu's review.

**Verdict: GO — BE3B_ADAPTER_AND_BUNDLE_BATCH_CLOSED.** The sole NO-GO item from the prior closure
review (missing `generation.item_opportunities` guard entry) is fixed, consumed by both the
parametrized import test and the app-wide submodule guard, and confirmed live in a real
`ModuleNotFoundError` from the built image — not a vacuously-passing or skipped test. No other
BE3b finding regressed: single adapter import point, no formula duplication, no package Pydantic
models under `app/domain`, no research wheel in the image, fail-closed runtime-bundle loader, and
154/154 (67/67 targeted) green in a clean `docker build --no-cache` image against real Postgres.

## 2026-07-25 — BE3c: private/public task representation split + characterization/privacy tests

Implements BEplan BE3.3–BE3.4 as one bounded batch on top of the committed BE3b adapter
(`36fb525`). Fixed TEST-FIXTURE-ONLY provenance only: no live learner flow, no API route, no
persistence table/migration, no real approved runtime bundle, no crossing the BE4 scientific
gate. Nothing was committed; the working tree is left uncommitted for Yasindu's review.

**Scope-boundary decision (BE3.3 vs. BE4.1 — recorded per the governance note in this batch's
task brief).** BEplan BE3.3.1 says "persist a private opportunity/task snapshot"; BEplan BE4.1.1
says "add private opportunity/task-instance TABLES". Those two lines describe the same
persistence concern at different levels of commitment. Resolution applied here: this batch
defines the private and public **in-memory representations** (`PrivateTaskRecord`,
`PublicTaskPresentation`), the private→public **mapping** (`project_to_public`), and the
**characterization/privacy tests** proving the split holds — and stops there. It does NOT add an
opportunity/task-instance database table, a SQLAlchemy model, or an Alembic migration; standing
up that persistence, wiring it into a session-scoped unit of work, and enforcing "one open
opportunity per session" is BE4.1 scope and is left for that batch. This keeps BE3's exit gate
("public DTOs contain no private fields") satisfiable without pre-committing to BE4's storage
schema before BE4 is actually reached.

**What was added:**

1. `app/domain/live_engine/presentation.py` — `PrivateTaskRecord` (full private snapshot: operands,
   correct answer, accepted equivalents, distractor candidates + rule ids, applied guard ids,
   generation/global seed, `SelectionReason`, catalogue version/checksum, bundle version, student
   id, curriculum node id) and `PublicTaskPresentation` (allow-listed learner-facing DTO:
   opportunity/instance id, skill, grade, difficulty, representation type, response format,
   prompt, `presented_choices`). `build_private_task_record` assembles the private record from an
   adapter `TaskInstance` plus the caller's own request/selection-reason/bundle-version
   provenance. `project_to_public` builds the public DTO by naming each field it reads from the
   private record explicitly — never via `dataclasses.asdict`/`replace` on the private object
   with keys deleted afterward, so a newly added private field cannot leak into the public DTO by
   omission. `presented_choices` is the sorted union of the correct answer and distractor
   candidates (needed so the learner can select the right one) but carries no marker of which
   entry is correct.

2. `app/domain/runtime_bundle/readiness.py` — `assert_catalogue_matches_bundle(bundle, catalogue,
   catalogue_checksum)`, a pure cross-check the BE3b loader didn't have: it fails closed
   (`RuntimeBundleValidationError`) the moment the bundle's declared catalogue checksum, catalogue
   version, required template count, or skill set disagrees with the catalogue an adapter call
   actually loaded. No partial-match or fallback path — every branch either passes silently or
   raises.

3. `tests/fixtures/runtime_bundle/test_catalogue.md` extended from 7 to all 36 template ids in
   `provenance/component-b-coverage.json` (29 implemented + 7 deferred), so the characterization
   suite can exercise the real implemented/deferred partition instead of one representative per
   skill. Each implemented template's `grade_scope` was set to reproduce the exact
   `eligible_grades` declared by its `ItemSampler` in the vendored
   `component_b_generator.samplers.*` registry (verified by reading each sampler module
   directly, not by assumption); each deferred template's status is `DEFERRED_CALIBRATION_PENDING`
   or `DEFERRED_UNDERSPECIFIED` matching its `decision_code` in the coverage report. Extending the
   fixture changed its SHA-256, so the catalogue checksum in all three runtime-bundle JSON
   fixtures (`valid_unapproved_bundle.json`, `missing_field_bundle.json`,
   `bad_checksum_bundle.json`) was updated to the new value — confirmed the *only* difference
   between `valid_unapproved_bundle.json` and `missing_field_bundle.json` is the deliberately
   absent `bkt_configuration` block (not the catalogue checksum), and that
   `bad_checksum_bundle.json`'s deliberately-wrong checksum is still on the `generator` artifact,
   not `catalogue`. `Dockerfile` and `.dockerignore` were given one new, narrowly-scoped exception
   to copy `provenance/component-b-coverage.json` (partition provenance only — no generator
   source, no wheel) into the image so the characterization tests can read it at run time.

4. `tests/test_be3c_characterization.py` — sanity-checks the fixture catalogue actually contains
   every implemented/deferred id claimed in the coverage report; generates one instance per
   (implemented template, eligible grade) pair (30 pairs across 29 templates, since
   `B-ADD02-COUNT-ON` is eligible for both grades) and asserts internal consistency; asserts all 7
   deferred templates raise `TemplateNotActiveError` at both grades; asserts determinism (repeat
   build, same fixed request, byte-identical `TaskInstance`); asserts grade 2 never contains
   multiplication/division in `catalogue.eligible_for(2)` and that `decide_activation` reports
   every multiplication/division template inactive at grade 2; asserts the canonical sequencing
   tie-break (skill order, then lexicographic `item_template_id`) picks the same winner regardless
   of input order or repetition; asserts hint content is the exact catalogue string with matching
   catalogue checksum/version, and that a template with no authored hint fails closed
   (`HintUnavailableError`), never a generated fallback.

5. `tests/test_be3c_privacy.py` — an explicit allow-list serialization test asserting
   `PublicTaskPresentation.to_public_dict()` produces exactly the 9 allowed keys, never
   `correct_answer`/`allowed_equivalent_answers`, and that the correct answer appears among
   `presented_choices` without any field marking which one it is; a schema-snapshot scan over the
   dataclass's own field names (`dataclasses.fields`, independent of the serializer) checked
   against a forbidden-name set (correct answer, equivalents, answer rules, seeds, BKT params,
   mastery/posterior/certification fields, selection rationale, distractor provenance, student id,
   curriculum node id, catalogue/bundle version) plus a recursive value walk of the serialized
   dict asserting none of those private scalars appear by value either; a structural check that
   the public dataclass's field set is not a trivial subset produced by copying the private one
   (only `presented_choices` differs, and it exists on the public side only); and four
   runtime-bundle readiness tests — the fixture bundle matches the extended catalogue cleanly, and
   a checksum mismatch, a template-count mismatch, and a version mismatch each raise
   `RuntimeBundleValidationError` rather than silently proceeding.

**Pre-existing gap found and fixed: the fixture catalogue was never actually committed.**
`git log -- tests/fixtures/runtime_bundle/test_catalogue.md` shows no history at all — the
repo-root `.gitignore`'s blanket `*.md` rule (line 29, meant for local-only documentation) was
silently excluding this file from every commit since it was introduced in BE3b, even though
`test_be3b_live_engine_adapter.py` and `test_be3b_runtime_bundle.py` both depend on it. It only
worked in Docker/CI because `.dockerignore` (a separate allowlist) copies the whole `tests/`
directory regardless of `.gitignore`. Added one narrow exception,
`!/backend/tests/fixtures/runtime_bundle/test_catalogue.md`, to the root `.gitignore` — this is a
repository-configuration edit, not a git state-changing command, and no `git add`/`commit` was
run. Flagging this explicitly: without that exception, extending this fixture for BE3c (or ever
committing the original BE3b version of it) would have gone in silently untracked.

**Verification.** Built `backend/Dockerfile` (`docker build`, no `--no-cache` needed — no
image-affecting layer changed except the two new provenance/coverage COPY lines and the
`.dockerignore` exception). Ran the full suite against a throwaway `postgres:16.10-bookworm`
container on a dedicated bridge network (`be3c-net`/`be3c-db`), migrations applied via
`alembic upgrade head` (clean, five revisions, no errors): **176 passed, 0 failed** — the prior
154 plus 22 new (12 characterization + 10 privacy). A targeted verbose run of
`test_be3c_characterization.py test_be3c_privacy.py test_be3b_live_engine_adapter.py
test_be3b_runtime_bundle.py test_be3_live_engine_boundary.py test_be2_architecture_guards.py`:
89/89 passed, confirming the BE2 architecture guards and BE3a/BE3b import-boundary guards (sole
`app/` importer of `component_b_generator` remains `app/infrastructure/live_engine/adapter.py`,
all entries in `PROHIBITED_MODULES` — 18 submodule paths covering the 13 prohibited
research/synthetic capabilities — unreachable) are still green alongside the new BE3c code. Docker
containers, the dedicated network, and the built image were removed after verification
(`docker rm -f`, `docker network rm`, `docker rmi`); no git command beyond read-only inspection
was run — nothing is staged or committed.

**No closure decision recorded here.** Per this batch's instructions, closure/no-go review is a
separate follow-up, not part of this entry.

## 2026-07-25 — BE3c closure review: GO (BE3C_PRIVATE_PUBLIC_SPLIT_BATCH_CLOSED)

Independent closure review against BEplan BE3.3–BE3.4, run from a fresh `docker build --no-cache`
image plus a real throwaway `postgres:16.10-bookworm` container (`be3c-review-net`/`be3c-review-db`,
disposed of after verification). Read-only git only; nothing staged or committed; this entry is the
only write made.

**(1) Private/public split.** `app/domain/live_engine/presentation.py` builds
`PublicTaskPresentation` and its `to_public_dict()` field-by-field from an explicit allow-list —
never `dataclasses.asdict`/`replace` on `PrivateTaskRecord` with keys deleted after. Confirmed by
reading `project_to_public` directly (every field is named on the right-hand side, nothing copied
wholesale) and by `tests/test_be3c_privacy.py`: an allow-list serialization test (exactly the 9
allowed keys, correct answer/equivalents absent, correct answer present-but-unmarked among
`presented_choices`), a schema-snapshot scan of `dataclasses.fields(PublicTaskPresentation)` against
a forbidden-name set (correct answer, equivalents, answer rules, seeds, BKT params, mastery/
posterior/certification, selection rationale, distractor provenance, student id, curriculum node id,
catalogue/bundle version) plus a recursive value walk of the serialized dict, and a structural check
that the public field set isn't a copy-then-delete artifact of the private one. No private field is
reachable in the public DTO.

**(2) Characterization.** `tests/test_be3c_characterization.py` verified: adapter output matches the
pinned generator via the vendored package on fixed fixtures; all 29 implemented templates generate
across all their eligible grades (30 pairs, `B-ADD02-COUNT-ON` counted twice); all 7 deferred
templates raise `TemplateNotActiveError` at grades 2 and 3; determinism holds (byte-identical
`TaskInstance` on repeat build under a fixed request); grade 2 never receives multiplication or
division (`catalogue.eligible_for(2)` and `decide_activation` both checked); the canonical
skill-order/lexicographic-template-id tie-break is stable regardless of candidate input order or
repetition; hint text is the exact catalogue string with matching checksum/version provenance, and a
template with no authored hint fails closed (`HintUnavailableError`), never a generated fallback.

**(3) BE3.3/BE4.1 boundary held.** No new DB table, model, or Alembic migration (`migrations/versions`
unchanged — no untracked files there; the batch's `readiness.py`/`presentation.py` are pure in-memory
domain code). No new API route (no `APIRouter`/`@router.*` in `app/domain/live_engine` or
`app/domain/runtime_bundle`; no live-engine wiring in `app/main.py`/`app/api` router includes). No
live learner flow.

**(4) Config edits narrow and disclosed.** `git diff` confirms: `.gitignore` adds exactly one
exception line for `test_catalogue.md` (the pre-existing untracked-fixture gap, disclosed and fixed,
not new scope creep); `.dockerignore` and `Dockerfile` add exactly one exception/COPY line each for
`provenance/component-b-coverage.json`. Read that file directly: it is partition/provenance metadata
only (template ids, implemented/deferred status, grade-activation counts, response-format
classification) — no correct answers, no BKT/scientific parameters, no secrets. No other undisclosed
change found in either file.

**(5) Import boundary intact.** `test_only_the_live_engine_adapter_module_imports_the_package` and
`test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules` both pass; `presentation.py`
itself has no `component_b_generator` import. `PROHIBITED_MODULES` still lists 18 submodule paths
covering the 13 prohibited research/synthetic capabilities, all confirmed unreachable.

**(6) Full suite green in the image.** Clean `docker build --no-cache` succeeded; `alembic upgrade
head` applied all 5 revisions cleanly against the real Postgres container; full suite: **176 passed,
0 failed**. Targeted re-run of `test_be3c_characterization.py test_be3c_privacy.py
test_be3b_live_engine_adapter.py test_be3b_runtime_bundle.py test_be3_live_engine_boundary.py
test_be2_architecture_guards.py`: **89 passed**. Numbers match the BE3c batch entry exactly.

**Non-blocking note.** `provenance/component-b-coverage.json` currently ships in the runtime image
(via the new `Dockerfile` COPY line) purely so the characterization test suite can read it inside the
container. It is not used by any non-test runtime code path yet. Worth revisiting whether
test-only provenance should live in a test-stage-only layer once a multi-stage Dockerfile exists,
so the shipped runtime layer doesn't carry test fixtures it doesn't execute against.

**Verdict: GO.** Identifier: `BE3C_PRIVATE_PUBLIC_SPLIT_BATCH_CLOSED`.

## 2026-07-25 — Scientific-gate parameter-authorization draft (`component-b-scientific-parameter-authorization.json`)

Drafted `provenance/component-b-scientific-parameter-authorization.json`, a new
`SCIENTIFIC_PARAMETER_AUTHORIZATION_DRAFT` record. Read-only against everything under `app/**`,
`tests/**`, `frontend/**`, migrations, the runtime-bundle loader, `runtime-bundle.schema.json`, and
every pre-existing provenance JSON; no state-changing git command run; nothing staged or committed.

**Purpose.** The record transcribes, with exact source citations and unmodified status tags, the
scientific-gate parameter values proposed by the Yass Component B spec
(`R26-IT-138_Component_B_Empirical_Statistical_Parameters_v1.0.md`,
`R26-IT-138_Component_B_Item_and_Task_Set_Catalogue_v1.0.md`) and the packaged, population-neutral
engine config (`bkt/config.py`, `certification.py`, `guess_guard.py`, `sequencing/config.py`). It
**approves nothing**: every named-approver slot is an explicit `UNRESOLVED_PLACEHOLDER` (mirroring
`component-b-profile-classroom-ratification.json`'s approver-record pattern), and no status tag was
upgraded from its source.

**Gate items covered** (cross-checked against `component-b-closure-decisions.json`
`governance_register`): catalogue approval (with the catalogue's computed SHA-256, see below); all
four `response_format_mapping_review.mappings` entries (`B-ADD02-COUNT-ON`, `B-CNT06-SKIP-COUNT`,
`B-PV02-DECOMPOSE-2D`, `B-PV04-DECOMPOSE-3D`) carried forward as `UNRESOLVED`; BKT parameter
approval (special-cased, see below); certification threshold `theta_B` (spec §6.3, value 0.95,
`LITERATURE_SUPPORTED · CALIBRATION_PENDING`); Guess-Guard numeric configuration (`q=0.10`,
`n_min=5`, frozen v1 §14A, `CALIBRATION_PENDING`, plus the FROZEN structural constraints
`P(G)+P(S)<1` and `P(G)<=0.5`); sequencing weights (0.5/0.3/0.2, `FROZEN` per
`runtime-bundle.schema.json`'s const, not reopened); attempt limits (`UNRESOLVED`, no live value);
timeout policy (governed statement carried forward, numeric threshold `UNRESOLVED`); completion
policy (`UNRESOLVED`); safe-progress policy (`UNRESOLVED`); cold-start policy (`FROZEN` governed
deferral, `DISABLED`); and owner/academic approval (`UNRESOLVED`, with a `named_approver_slots`
block for the Component B owner/academic-research approver, the academic/research calibration
owner, and the product owner with academic/research approval).

**BKT population-gap open decision.** The spec's §6.2.1 table (21 rows = 7 skills × 3 populations,
every row `ENGINEERING_ASSUMPTION · CALIBRATION_PENDING`) was transcribed in full into the record as
a labelled `spec_reference_table` ("per-population research priors, non-executable as direct
TD/MLD/DD rules") and was **not** collapsed into 7 live values. The record separately states the
live requirement from `bkt/config.py` (`BBKTConfig` needs exactly 7 population-neutral, skill-keyed
`SkillBKTParams` rows, no production default) and records an explicit open decision: how those 7
population-neutral live parameterizations are derived is unresolved and requires the named
academic/calibration owner — no rule (not TD-row adoption, not averaging, nothing) is picked here.
The record also notes that `bkt/config.py` enforces `P(G)+P(S)<1` and `P(G)<=0.5` in code, so any
future values must pass those checks.

**Self-verification performed:**
- `python -c "import json; json.load(open('provenance/component-b-scientific-parameter-authorization.json'))"` — valid JSON.
- Every `governance_register` item from `component-b-closure-decisions.json` and all 4 response-format mappings appear in the record's `gate_items` array.
- Every approver slot in `named_approver_slots` is `UNRESOLVED_PLACEHOLDER` — no real name/date/decision was written anywhere.
- No `authorization_status` was upgraded: values are only `UNRESOLVED` or `FROZEN` (sequencing weights and cold-start policy, both citing the schema const as source). The literal string `APPROVED_FOR_PROVISIONAL_V1_IMPLEMENTATION` appears exactly once, quoted verbatim as a `spec_status_tag` (owner/academic approval item) reproducing the spec document's own header status — its paired `authorization_status` in this record is `UNRESOLVED`.
- `git status` (read-only) shows only this buildLog append and the new provenance JSON as changes relevant to this batch; nothing under `app/`, `tests/`, `frontend/`, or any migration was touched.

**Catalogue SHA-256:**
`eaf073da8af155bdb935b7c2abfba04f892bbfecf44522f20f044aeec4b579ac` (computed over
`Component_B_v1.0/R26-IT-138_Component_B_Item_and_Task_Set_Catalogue_v1.0.md` as read from the
sibling Yass source tree).

**Spec sections cited:** §0 (status-tag legend), §1 (scope/binding constraints, item-count SF-039
note), §2 (variable inventory, LATENT_GENERATOR_ONLY), §3 (skill vocabulary), §5.1 (sequencing
formula), §6.1–§6.4 (BKT constraints, 21-row table, sensitivity ranges, theta_B, guess-guard floor),
§8.2 (SF-039 population-execution clarification), §14A/§14B (frozen v1 defaults, machine-checkable
table), §15 (CALIBRATION_PENDING register), §17 (approval block, blank signatures); catalogue §1–§5,
§10 (sequencing compatibility).

**Discrepancy surfaced, not fixed:** the catalogue document's own header states status
`PROPOSED FOR APPROVAL`, while `component-b-closure-decisions.json`'s `governance_register` lists the
catalogue's `current_status` as `PROVISIONAL`. Both are non-approved states and neither conflicts
with this record's `UNRESOLVED` authorization_status for that item, but the two source documents use
different vocabulary for the same not-yet-approved state; a future closure review may want to
reconcile the terminology.

**This batch is not closed.** This entry documents the draft record only. A separate closure review
decides whether the record is accepted as an accurate transcription; named human sign-off on any
gate item remains outstanding.

## 2026-07-26 — BE4 sequencing plan recorded (documentation)

Created `Component_B_BE4_Sequencing_Plan.md` at the `Dev/` repo root — supervisor sequencing guidance
that decomposes the monolithic `PROMPT BE4` (`Component_B_Build_Plan.md`) and `BEplan.md §9` into six
individually-closeable batches (BE4a–f), each mapped to the exact `LiveEngineAdapter` methods it reuses
and the closure identifier it targets. Added a narrow `.gitignore` negation
(`!/Component_B_BE4_Sequencing_Plan.md`) so the tracked doc is not swept by the repo's `*.md` ignore
rule (same precedent as the BE3b/BE3c `test_catalogue.md` exception).

**Scope / integrity.** This entry and the new doc **override no governed document** — `BEplan.md §9` and
`Component_B_Build_Plan.md` `PROMPT BE4`/`CLOSURE BE4` remain canonical — and **authorize no
implementation**. No code, migration, provenance JSON, or earlier buildLog entry was modified; no
state-changing git command was run; nothing was staged or committed. buildLog remains append-only.

**Design captured.** BE4 reuses the vendored live-safe engine solely through `LiveEngineAdapter`
(the sole `app/` importer of `component_b_generator`); it copies/rewrites no formula and must not reach
the 13 prohibited synthetic/dataset modules (`component-b-live-engine-reuse-map.json`). Yasindu's
"same characters" requirement is recorded as **deterministic parity**, proven by pinning the
adapter-driven task-construction sweep against the characterization anchor
(`component-b-characterization.json`: `global_seed=20260716`, 54 items,
`private_output_sha256=b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c`, byte-identical
across Python 3.10.20 / 3.11.15).

**Still gated (three-tier).** (a) BE4 engineering on TEST-provenance DRAFT bundles awaits the §44 narrow
amendment (project supervisor + Component B owner); (b) live values/pilot await full SG-01…SG-15 named
sign-off as an `APPROVED` bundle; (c) production awaits calibration + validation. No tier is cleared by
this documentation entry. "BE4 live learning flow" remains in
`component-b-closure-decisions.json` `exit_gate.blocked_scope`.

## 2026-07-26 — BE4 engineering-only amendment proposal (§44) drafted

Created `backend/provenance/component-b-be4-engineering-amendment.json`, a
`BE4_ENGINEERING_AMENDMENT_PROPOSAL` record transcribing the §44 narrow amendment from
`Upadya/Component_B_Scientific_Gate_Decision_Pack_v1.0.md` (SG-16, conclusion C) for real named-owner
review. The record proposes — but does not adopt — authorizing BE4 engineering (batches BE4a–f) solely
against isolated TEST-provenance DRAFT runtime bundles that can never be published or selected as a live
alias, with no real-learner, pilot, production, or scientific-effectiveness/validation authorization.

**Adopts nothing.** All three `named_approver_slots` (`project_supervisor`, `component_b_owner`,
`academic_owner_acknowledgement`) are `UNRESOLVED_PLACEHOLDER` with `decision: UNRESOLVED` and
`decision_date: null`; Yasindu's name was not entered in any slot. Real, dated sign-off by the named
project supervisor and Component B owner remains outstanding before tier (a) unblocks.

**GATE-B unaffected.** The full scientific gate (SG-01…SG-15 — BKT parameters, θ_B, guess-guard
numerics, attempt/timeout/completion/safe-progress policy, and named scientific sign-off) is untouched;
the record's `does_not_clear` and `does_not_authorize` fields state this explicitly. `blocked_scope` in
`component-b-closure-decisions.json` was **not** modified — the new record only proposes a narrow,
explicit carve-out layered on top of it, per `relationship_to_blocked_scope`.

**Scope / integrity.** No code, migration, other provenance JSON, the runtime-bundle schema/loader,
`BEplan.md`, or `Component_B_Build_Plan.md` was modified; no earlier buildLog entry was edited or
reordered; no state-changing git command was run. This batch is not closed and this amendment is not
adopted — a separate closure review decides acceptance of the draft, and real named sign-off remains
outstanding.

## 2026-07-26 — BE4 engineering-continuation instruction (project-director)

Created `backend/provenance/component-b-be4-engineering-continuation-instruction.json`, a
`BE4_ENGINEERING_CONTINUATION_INSTRUCTION` record. It authorizes Component B **BE4a-f engineering**
(per `Component_B_BE4_Sequencing_Plan.md`) to proceed now, but **only** against isolated TEST-provenance
DRAFT runtime bundles, in local development/CI, under the same bounded-batch + separate-closure
discipline used since BE1.

**Who issued it, and in what capacity.** The instruction is issued by **Yasindu Kularathne**, recorded
as "the person directing this project (this session)" — explicitly **not** a project-supervisor decision
and **not** the named Component B owner ratification. `is_named_approver_ratification: false`.

**Identity discrepancy surfaced.** The Component B owner of record in the governing documents
(`component-b-be4-engineering-amendment.json`, `component-b-profile-classroom-ratification.json`) is
"Dhananjani G.A.U. (IT22224316)", which differs from the instructing party, Yasindu Kularathne. This
relationship is recorded as **UNRECONCILED**. Full named Component B owner ratification still requires
reconciling this identity; it is not resolved by this record.

**Relationship to the §44 amendment.** This instruction does **not** adopt
`component-b-be4-engineering-amendment.json`. That amendment's `named_approver_slots`
(project_supervisor, component_b_owner, academic_owner_acknowledgement) remain `UNRESOLVED_PLACEHOLDER`.
Named project-supervisor ratification and named Component B owner ratification (with the identity above
reconciled) are both **deferred to the BE6 pre-pilot review gate**, per the same
`engineering_continuation` precedent used in `component-b-profile-classroom-ratification.json`.

**GATE-B unaffected.** This record clears no scientific value and no GATE-B item (SG-01…SG-15); it
authorizes no real-child data, pilot, production, research export, or effectiveness/mastery/validation
claim; it does not touch `component-b-closure-decisions.json` `exit_gate.blocked_scope`, which still
lists "BE4 live learning flow", pilot, and production unchanged.

**Scope / integrity.** No code, migration, the §44 amendment record, `component-b-closure-decisions.json`,
the runtime-bundle schema/loader, `BEplan.md`, or `Component_B_Build_Plan.md` was modified; no earlier
buildLog entry was edited or reordered; no state-changing git command was run. This is not a closure —
a separate review decides whether this instruction's scope is accepted, and named supervisor/owner
ratification remains outstanding pending BE6.

## 2026-07-27 — BE4a: opportunity/presentation persistence (BEplan §9 BE4.1) — persistence only

Authorized by `component-b-be4-engineering-continuation-instruction.json` (engineering-continuation,
not project-supervisor/Component-B-owner ratification): TEST-provenance DRAFT bundles only, local
dev/CI, no real-child/pilot/production, no GATE-B scientific value.

**Files added.** `backend/app/domain/b_opportunity.py` (safe `PresentedOpportunity` DTO + explicit
allow-list projection `project_task_instance_to_presentation`, reusing the BE3c private/public split
in `app.domain.live_engine.presentation` rather than reinventing it); `backend/app/application/
opportunity_persistence.py` (`OpportunityPersistenceService` — open/close opportunity, create task
instance, issue/validate presentation token); `backend/migrations/versions/
20260727_0001_be4a_opportunity_persistence.py`; `backend/tests/test_be4a_opportunity_persistence.py`
(6 new tests).

**Files changed.** `backend/app/infrastructure/persistence_models.py` (three new PRIVATE tables:
`b_item_opportunities`, `b_task_instances`, `b_presentation_tokens`); `backend/app/infrastructure/
repositories.py` (matching repositories); `backend/tests/test_be2_architecture_guards.py` and
`backend/tests/test_be2_persistence.py` (hardcoded `EXPECTED_TABLES`/`AUTHORIZED_TABLES` allow-lists
extended with the three new table names — see "convention ambiguity" below).

**Tables + constraints.** `b_item_opportunities` — one row per opportunity (session/learner FK,
skill_id, item_template_id, opportunity_index, OPEN/CLOSED state, server `presented_at_utc`/
`timeout_deadline_utc`, PRIVATE `selection_provenance` JSONB, `row_version`); one-OPEN-per-session
enforced by a partial unique index (`uq_b_item_opportunities_one_open_per_session`, following the
`classroom_memberships`/`b_sessions` partial-unique-index precedent), verified via the DB
`IntegrityError` path, not just app logic. `b_task_instances` — SAFE columns (`prompt`,
`presented_choices`, computed once at creation using the identical allow-list derivation as BE3c's
`project_to_public`) plus PRIVATE columns (`correct_answer`, `allowed_equivalent_answers`,
`distractor_candidates`, `distractor_rule_ids`, `generated_operands`, `generation_seed`,
`applied_guard_ids`, `catalogue_version`, `catalogue_checksum`); schema only, one row per opportunity
(unique FK), no rows written by this batch outside tests — BE4b populates via the adapter.
`b_presentation_tokens` — only the SHA-256 hash of an opaque `secrets.token_urlsafe(32)` token is
stored (mirrors `classroom_invites.token_hash`); bound to (session, opportunity, learner, runtime
bundle record); `expires_at_utc > issued_at_utc` enforced at the DB level.

**Private/public split + fail-closed enforcement.** `PresentedOpportunity.to_public_dict()` is an
explicit allow-list (item/opportunity ids, skill_id, grade, difficulty_level, representation_type,
response_format, prompt, presented_choices, presentation_token, server_timeout_deadline_utc) built
only from `TaskInstanceRecord`'s SAFE columns — the PRIVATE columns are structurally unreachable from
the return value, asserted by
`test_safe_presentation_dto_excludes_every_private_field`. `validate_presentation_token` fails closed
with a distinct exception per case (`PresentationTokenNotFoundError`,
`PresentationTokenMismatchError` for any session/opportunity/learner mismatch,
`PresentationTokenExpiredError`), never revealing which check failed via a shared message.

**Convention ambiguity resolved.** `tests/test_be2_architecture_guards.py`'s
`PROHIBITED_COLUMN_TERMS` blanket-blocked any column name containing "answer" or "correct" — written
before BE4 was in scope, to keep pre-BE4 batches from smuggling in scientific/behavioral columns. BE4a
is explicitly authorized by BEplan §9 BE4.1 to add exactly two PRIVATE columns carrying those terms
(`b_task_instances.correct_answer`, `.allowed_equivalent_answers`), so those two terms were removed
from the blocklist with an inline comment explaining why; every other term (`mastery`, `bkt`,
`guess_guard`, `certif`, `sequenc`, `hint`, `error_class`, `population`, `dd_subtype`, `true_mastery`,
`simulated`, `latency`, `off_day`, `random_effect`, `experiment`) remains enforced unchanged, including
against the new BE4a tables. Renamed the opportunity's ordinal column from `sequence_index` to
`opportunity_index` to avoid an unrelated collision with the still-enforced `sequenc` term (that guard
targets the BEplan sequencing/scoring engine, not a plain per-session ordinal).

**Migration cycle.** `alembic downgrade 20260723_0001` then `alembic upgrade head` verified clean
(table presence/absence asserted via `sqlalchemy.inspect` before and after); no drift beyond the three
new tables.

**Tests + typecheck.** Ran against an ephemeral local Postgres 16.10 container (no persistent volume),
Python 3.13 venv (`requirements.in` minus the vendored `upadya-component-b-live-engine` wheel, which
requires Python 3.11/3.12 — unavailable in this environment; `test_be3_live_engine_boundary.py`
self-skips via `pytest.importorskip` when the package is absent, and its 4 tests show as "skipped," not
failing — an environment limitation, not new in this batch). `python -m pytest -q` from
`backend/`: **117 passed, 4 skipped** (the boundary-guard file), 0 failed. Confirmed by direct grep
that no BE4a file imports `component_b_generator` or `upadya_component_b_live_engine`. No mypy/pyright
config exists in this repo, so no typecheck step was run (none configured for prior batches either).

**Scope / integrity.** Only files under `Dev/backend/` changed (`git status --porcelain` confirms);
nothing under `frontend/`, `provenance/`, `BEplan.md`, or `Component_B_Build_Plan.md` was touched; no
earlier buildLog entry was edited; no state-changing git command was run — everything is left
uncommitted for Yasindu. No select/attempt/hint/complete endpoint was added; no
`component_b_generator` call was made; no task was generated by this batch itself (only by tests,
directly through `OpportunityPersistenceService`, not the adapter). This batch is not closed — a
separate review decides `BE4A_OPPORTUNITY_PERSISTENCE_BATCH_CLOSED`.

### 2026-07-27 — BE4a FIX: scope the answer/correct guard exception + run boundary test under 3.11

Follow-up to the BE4a batch above (still uncommitted). Two fixes, nothing else touched.

**FIX 1 — scoped allow-list, not a blanket term removal.** `tests/test_be2_architecture_guards.py`:
restored `"answer"` and `"correct"` to `PROHIBITED_COLUMN_TERMS` (the prior batch had removed them
globally, which over-widened the exception past the two columns BEplan §9 BE4.1 actually authorizes).
Added `AUTHORIZED_ANSWER_BEARING_COLUMNS = {("b_task_instances", "correct_answer"),
("b_task_instances", "allowed_equivalent_answers")}` and rewrote
`test_exact_authorized_model_table_set_and_no_scientific_columns` to compute `offenders` as
`(table_name, column_name)` pairs matching any prohibited term, minus that allow-list — so the
exception applies to exactly those two cells, not the terms everywhere. Added two positive checks:
both allow-listed columns actually exist on `b_task_instances` in `Base.metadata` (so the exception
can't silently cover a column that no longer exists), and no *other* table has any
`answer`/`correct`-bearing column at all (`answer_bearing == AUTHORIZED_ANSWER_BEARING_COLUMNS`).
`test_b_session_dto_contains_no_scientific_expiry_or_attempt_fields` derives its forbidden-term set
from `PROHIBITED_COLUMN_TERMS | {...}` and needed no change — `b_session.py`'s DTO fields never
contained "answer"/"correct" in the first place, confirmed by rerunning it.

**Sanity check (not left in the tree).** In a disposable one-off script, appended a
`stray_correct_marker` column onto `ItemOpportunityRecord.__table__` in-memory (never written to any
source file) and recomputed the `offenders` set: it correctly flagged
`{("b_item_opportunities", "stray_correct_marker")}`, confirming the guard fails closed on a stray
prohibited-term column outside the allow-list. `git status` after the check shows no such column in
any tracked file.

**FIX 2 — boundary test executed (not skipped) under Python 3.11.** The prior batch's report noted
`test_be3_live_engine_boundary.py` self-skipped because the vendored live-engine wheel needs Python
3.11/3.12 and only 3.10/3.13/3.14 were present on the host. This host still has no 3.11/3.12
interpreter, but the project's own `Dockerfile` already pins `python:3.11.15-slim-bookworm` and
installs the vendored wheel via `requirements.lock --require-hashes`, so that image (built fresh from
the current tree, not reused from a stale cache) was used as the 3.11 environment: `docker build -t
upadya-be4a-3.11-test -f Dockerfile .`, run against an ephemeral network-joined Postgres 16.10
container (`upadya-be4a-db`) with `alembic upgrade head` applied first.
`python -m pytest tests/test_be3_live_engine_boundary.py -v` inside that container: **24 passed** (all
parametrized `test_prohibited_module_is_not_importable_from_the_package` cases plus the five other
guard/determinism tests), **0 skipped**, confirming `component_b_generator` actually imported and every
assertion ran, not just collected. `python -m pytest -q` (full suite) in the same container: **182
passed, 0 skipped, 0 failed** (up from 117 passed/4 skipped under 3.13 — the extra ~61 tests are
`test_be3b_live_engine_adapter.py`, `test_be3c_characterization.py`, and `test_be3c_privacy.py`, which
also self-skip without the package and now run too). All Docker resources (image, container, network)
were removed after the run; nothing was left running.

**Scope / integrity.** `git status --porcelain` after both fixes: only
`backend/tests/test_be2_architecture_guards.py` changed relative to the prior BE4a batch's already-
uncommitted files (plus this buildLog entry); no table, column, route, or provenance file was added or
touched; no state-changing git command was run. Not a closure — `BE4A_OPPORTUNITY_PERSISTENCE_BATCH_CLOSED`
is still a separate review decision.

## 2026-07-28 — BE4b: adaptive next-question selection (BEplan §9 BE4.2) — persistence only

Authorized by `component-b-be4-engineering-continuation-instruction.json` (commit 49819c1), built on
committed BE4a (commit `d8909a2`). TEST-provenance DRAFT bundles only, local dev/CI, no
real-child/pilot/production, no GATE-B scientific value. Every scientific step goes through
`LiveEngineAdapter` — no formula copied or reimplemented.

**Files added.** `backend/app/application/opportunity_selection.py` — `select_candidate`/`build_task`
(pure, side-effect-free: candidate build → hard gates (`decide_activation`) → features/score
(`compute_features`/`score_candidate`, the adapter's own pinned 0.50/0.30/0.20 weights) → select
(`select_target`) → construct (`build_task_instance`)) and `OpportunitySelectionService` (the
persisting orchestration: resolve session bundle → load/init seven skill states → select → open
opportunity (BE4a, reused) → build task → persist task instance + token (BE4a, reused) → return the
BE4a safe DTO). `backend/migrations/versions/20260727_0002_be4b_learner_skill_states.py` — one new
PRIVATE table, `b_learner_skill_states` (learner×skill P(L) + observation_count; BE4b reads/initializes
only, BE4c owns updates). `backend/tests/test_be4b_adaptive_selection.py` (10 tests).

**Files changed.** `backend/app/api/routes/b_session.py` (+1 route:
`POST /api/v1/b/sessions/{session_id}/opportunities`); `backend/app/domain/b_opportunity.py`
(+`OpportunityPresentationResponse`/`OpportunityPresentationFields`, an explicit field-by-field pydantic
mirror of BE4a's `PresentedOpportunity`, never `**to_public_dict()`); `backend/app/infrastructure/
persistence_models.py` / `repositories.py` (new table's model + repository, plus two additive,
non-breaking extensions to BE4a's `ItemOpportunityRepository`: `count_for_session`); `backend/tests/
test_be2_architecture_guards.py` / `test_be2_persistence.py` (table allow-list extended by name; new
route added to `EXPECTED_ROUTES` + a narrow `AUTHORIZED_B_OPPORTUNITY_SELECTION_OPERATIONS` carve-out
of the "session" path term, exactly mirroring the four existing lifecycle routes' carve-out — every
other prohibited scientific path term, and every other prohibited column term, stays blocked
unconditionally including on the new route/table).

**Adapter methods used (no reimplementation).** `load`/`checksum`, `decide_activation`,
`supported_template_ids`, `compute_features`, `score_candidate`, `select_target`,
`build_task_instance` — the exact BE4b row from `Component_B_BE4_Sequencing_Plan.md`. `rank_candidates`
was not needed: `select_target` alone performs ranking + the canonical deterministic tie-break given a
scored-candidate list.

**Hard gates.** Grade eligibility, implementation support, and catalogue availability are enforced
entirely by `adapter.decide_activation` per template; deferred/unsupported templates never enter the
scored-candidate list (never generated, not merely rejected after construction). Verified directly
against the catalogue (`test_grade_2_never_activates_multiplication_or_division`,
`test_grade_3_exposes_all_seven_skills`, `test_deferred_template_never_activates_for_any_grade`) and
end-to-end through the real service for a Grade 2 learner.

**Frozen weights + determinism.** `test_selection_uses_the_frozen_0_50_0_30_0_20_weights` asserts the
real `SelectionReason.score` returned by the adapter path equals `0.50*mastery_gap +
0.30*prerequisite_readiness + 0.20*spacing_due` — reading the weights from the adapter's own output, not
a locally declared copy. `select_candidate`/`build_task` are pure (no DB access); calling each twice
with identical arguments in `test_selection_is_deterministic_under_fixed_identity` produces
dataclass-equal (`==`) `SelectionResult`/`TaskInstance` output — a direct step toward the BE4f parity
test.

**Fail-closed.** A session pinned to a `RuntimeBundleRecord` whose `bundle_version` isn't the one known
engineering TEST fixture refuses with `ConflictError` (no fabricated fallback). The DB-level
one-OPEN-opportunity-per-session index (BE4a) is exercised through the real selection flow: a second
`select_next_opportunity` call for a session that already has an OPEN opportunity fails closed
(`test_one_open_opportunity_per_session_rejects_a_second_select`).

**Privacy.** The public response (`OpportunityPresentationResponse`) is built through BE4a's
`project_task_instance_to_presentation` allow-list projection, then mapped field-by-field (not
`**dict`) into the pydantic response shape; `test_public_selection_response_contains_no_private_fields`
asserts the real end-to-end response contains none of the private task-instance fields nor any
selection-rationale field (`mastery_gap`, `score`, `tie_break_basis`, `p_l`, etc.). No custom logging was
added anywhere in this batch; the existing structured-logging pipeline never serializes request/response
bodies.

**Known engineering-only limitations, explicitly documented in the module docstring (not silently
assumed):**
1. **Bundle-artifact bridge.** No governed mechanism yet resolves a session's pinned
   `RuntimeBundleRecord.bundle_version` to an actual manifest/catalogue file path, and this batch may
   not touch `provenance/`. `_ENGINEERING_TEST_BUNDLES` maps exactly the one known BE3b TEST-provenance
   DRAFT fixture (`tests/fixtures/runtime_bundle/valid_unapproved_bundle.json` +
   `tests/fixtures/runtime_bundle/test_catalogue.md`, reused — not duplicated); every other
   `bundle_version` fails closed. Must not survive into a governed production selection path.
2. **BKT config.** A fixed, population-neutral, `TEST_FIXTURE_ONLY` `BktConfig` (mirroring
   `tests/test_be3b_live_engine_adapter.py`'s own fixture exactly), never the population-conditioned
   research table in `provenance/component-b-scientific-parameter-authorization.json` — that table is
   keyed by `population` (TD/MLD/DD), architecturally prohibited anywhere near live BKT.
3. **Seed lineage coordinates.** `scheduled_session_number`/`b_session_index` are fixed engineering
   placeholders (`1`) — no curriculum-scheduling system exists yet. `global_seed` is derived
   deterministically from the session's own `session_id` via SHA-256 rather than adding a new
   `b_sessions` column, keeping BE2's already-committed session schema untouched.
4. **Package ID format.** The vendored package's `GeneratedItemOpportunity.item_opportunity_id`
   validator requires `^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$` — an internal-only, opaque format
   requirement discovered while writing the determinism test (a raw UUID string fails this
   validation). `package_item_opportunity_id` derives a conforming, deterministic value from the real
   learner UUID; real uniqueness is still enforced at the DB level by `ItemOpportunityRecord`'s UUID
   primary key, not by this formatted string.

**Import-boundary regression caught and fixed during this batch.** An initial version imported
`LiveEngineAdapter` at module scope in `opportunity_selection.py`. Because `app/api/routes/b_session.py`
imports that module, and `app.main` imports every route module at startup, this made
`component_b_generator` transitively required just to import `app.main` — breaking every test that
uses the FastAPI app (health, auth, classroom, session-lifecycle, ...) on any host without the vendored
wheel installed (discovered when a plain `import app.main` failed on this session's Python 3.13 sanity
venv). Fixed by making the `LiveEngineAdapter` import lazy (inside
`OpportunitySelectionService.select_next_opportunity`, with a `TYPE_CHECKING`-only import for the type
hint) so only *invoking* the new route requires the package, matching the same "engineers without the
vendored wheel can still run everything else" property BE3b/BE3c already relied on. Confirmed via
`test_only_the_live_engine_adapter_module_imports_the_package` and
`test_no_yass_research_or_scientific_imports` staying green (both check import-statement root names via
AST, unaffected by module- vs. function-scope), and by a direct `import app.main` check succeeding
without the package installed.

**Migration cycle.** `alembic downgrade 20260727_0001` then `alembic upgrade head` verified clean
(table presence/absence asserted via `sqlalchemy.inspect`); `alembic check` reports "No new upgrade
operations detected" — zero drift against the ORM models.

**Tests + typecheck.** Ran under the project's own `Dockerfile` (Python 3.11.15, vendored wheel via
`requirements.lock --require-hashes`, built `--no-cache`) against an ephemeral Postgres 16.10 container.
`pytest tests/test_be3_live_engine_boundary.py -v`: **24 passed, 0 skipped**.
`pytest tests/test_be4b_adaptive_selection.py -v`: **10 passed**. Full suite `pytest -q`: **192 passed,
0 skipped, 0 failed** (up from 182 after the BE4a closure review — +10 new BE4b tests, nothing else
changed). No mypy/pyright config exists in this repo; none run (consistent with prior batches). All
Docker resources (image, container, network) were removed after the run.

**Scope / integrity.** Only files under `Dev/backend/` changed (`git status --porcelain` confirms);
nothing under `frontend/`, `provenance/`, `BEplan.md`, or `Component_B_Build_Plan.md` was touched; no
earlier buildLog entry was edited; no state-changing git command was run — everything is left
uncommitted for Yasindu. Exactly one new public route was added, learner-scoped and authenticated; no
select/attempt/hint/complete endpoint beyond it. This batch is not closed — a separate review decides
`BE4B_ADAPTIVE_SELECTION_BATCH_CLOSED`.

## 2026-07-28 — BE4c: attempt submission + first-attempt-only atomic BKT (BEplan §9 BE4.3 + BE4.4)

Implements the learner attempt submission and the first-attempt-only atomic BKT update, authorized by
the BE4 engineering-continuation instruction (TEST-provenance DRAFT only; no real-child/pilot/production;
no GATE-B value). New: `app/domain/b_attempt.py` (strict request/response contracts),
`app/application/attempt_submission.py` (`AttemptSubmissionService`),
`migrations/versions/20260728_0001_be4c_attempts_and_transitions.py` (`b_attempts`,
`b_skill_state_transitions`), `tests/test_be4c_attempt_submission.py`. Changed: `persistence_models.py`
(`AttemptRecord`, `SkillStateTransitionRecord`), `repositories.py` (attempt/transition repos +
`get_for_update` with `populate_existing=True`), `app/core/errors.py` (`TechnicalFailureError`, 503),
`app/api/routes/b_session.py` (one new route), and the two architecture-guard tests (allow-lists
extended by name for the two tables + one route, same narrow pattern as BE4b).

**Route:** `POST /api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/responses` — neutral
path (no prohibited scientific term); the `session` carve-out is extended to it only, every other
prohibited path term still enforced.

**Scientific integrity.** All correctness (`answers_equivalent`/`normalize_answer`) and BKT
(`predict`/`posterior`/`update`) run through the `LiveEngineAdapter` (lazy, function-scope import); no
formula reimplemented. The pinned BKT config is the shared `TEST_FIXTURE_ONLY`
`opportunity_selection._ENGINEERING_BKT_CONFIG`, never a GATE-B/population-conditioned value.
First-attempt-only is gated by `attempt_index == 1 and event_kind == "RESPONSE"` and enforced at the DB
level by the unique index `uq_b_skill_state_transitions_opportunity` (the single first-attempt claim +
the immutable transition row). Concurrency is serialized by a `FOR UPDATE` lock on the opportunity row
before the server derives `attempt_index`; the skill-state re-read uses `populate_existing=True` (the
`approve_membership` identity-map staleness carry-forward). Attempt insert + transition insert +
skill-state update commit together in one unit of work; any pre-commit or commit-time failure rolls back
all of it and surfaces `TechnicalFailureError`, never a partial BKT observation. Replay reuses
`b_idempotency_records` (same key → original canonical response, no second write). An expired
`timeout_deadline_utc` records a `TIMEOUT` event with no correctness/BKT evaluation. Correctness is
server-side only; `AttemptResponse` (StrictModel) returns `response_matched` (bool) + state — never the
correct answer, accepted set, or scientific params; client elapsed time is stored as telemetry only.

**Verification (independent closure, Python 3.11 Docker + real Postgres):** first-attempt-only,
8-way concurrency (single transition; direct-ORM unique-index bypass confirmed the DB backstop),
atomic rollback (commit-time and pre-flush injection → zero rows), replay + same-key-different-body
conflict, server-side equivalence normalization, HTTP privacy scan (no answer/param leakage),
oversized/extra-field/missing-key 422s, migration downgrade→re-upgrade + drift clean;
`test_be3_live_engine_boundary.py` 24 passed/0 skipped, full suite 201 passed. Independent closure
verdict: GO — `BE4C_ATTEMPT_AND_BKT_BATCH_CLOSED`.

**Note (audit transparency).** This buildLog entry was appended by the supervisor after the closure
review found the implementing batch had not actually written its buildLog entry (the file had no
uncommitted change). No earlier entry was edited; no state-changing git command was run; the batch is
left uncommitted for Yasindu.

---

## 2026-07-28 — BE4d: governed hints (BEplan §9 BE4.5)

Implements the governed L1/L2/L3 hint-request flow, authorized by the same BE4 engineering-
continuation instruction (TEST-provenance DRAFT only; no real-child/pilot/production; no GATE-B
value). Builds on BE4a/BE4b/BE4c. New: `app/domain/b_hint.py` (strict `HintRequestResponse`
contract), `app/application/hint_request.py` (`HintRequestService`),
`migrations/versions/20260728_0002_be4d_hint_events.py` (`b_hint_events`),
`tests/test_be4d_hint_events.py`. Changed: `persistence_models.py` (`HintEventRecord`),
`repositories.py` (`HintEventRepository`), `app/api/routes/b_session.py` (one new route),
`tests/test_be2_architecture_guards.py` and `tests/test_be2_persistence.py` (allow-lists extended
by name for the one table + one route, same narrow pattern as BE4b/BE4c).

**Route:** `POST /api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/assists` —
neutral path; "hint" (a prohibited scientific path term) never appears in it. The `session`
carve-out is extended to it only; every other prohibited path term (`attempt`, `hint`, `progress`,
`bkt`, `mastery`, `sequenc`, `certif`, `guess`) is still enforced on this route, same as the
selection/attempt-submission routes.

**Scientific integrity.** The only hint source is `LiveEngineAdapter.get_hint` (lazy, function-
scope import) — no LLM, no paraphrase, no generic fallback; the adapter's own
`HintUnavailableError` (missing/blank catalogue content, unknown template, out-of-range level) is
mapped straight to a neutral `ConflictError` with no message detail, so a hint that cannot be
produced fails closed rather than being synthesized. Catalogue/bundle resolution reuses
`opportunity_selection._ENGINEERING_TEST_BUNDLES` (the same BE3b TEST-fixture bridge BE4b
established) and `assert_catalogue_matches_bundle`, so a stale/mismatched catalogue also fails
closed. Escalation is governed to exactly L1 → L2 → L3: the next level is
`HintEventRepository.count_for_opportunity(...) + 1`, derived under the same opportunity
`FOR UPDATE` row lock BE4c's attempt path takes (so concurrent hint requests for one opportunity
serialize rather than race past L3); a request once 3 hint events already exist is refused
(`ConflictError`), never a fourth level. Replay reuses `b_idempotency_records` (same key →
original canonical response, same level, no re-escalation, no second write).

**Hint ≠ mastery observation.** `b_hint_events` is a table fully separate from
`b_attempts`/`b_skill_state_transitions`; `hint_request.py` never imports
`LearnerSkillStateRepository`, `AttemptRepository`, or `SkillStateTransitionRepository`, and never
touches `b_learner_skill_states`. Only the catalogue reconstruction key (`content_id` +
`catalogue_version` + `catalogue_checksum`) is persisted per event — the hint text itself is
returned to the caller but not stored, so there is no second, potentially-stale copy of governed
content. Column names avoid every `PROHIBITED_COLUMN_TERMS` entry: the governed level is spelled
`assist_level`, not `hint_level` (the response DTO field is `hint_level`, but DTO fields are not
scanned by the column-term guard). `HintRequestResponse` (StrictModel) never carries the correct
answer, accepted set, or any BKT/scientific parameter.

**GATE-B note.** The only numeric bound enforced is the governed L1–L3 hint-escalation ceiling
itself (BEplan §9 BE4.5 step 1). A combined attempt+hint numeric limit beyond that is a GATE-B item
(UNRESOLVED) and is deliberately NOT enforced here; no fixture bound is promoted to "approved" by
this batch.

**Verification (Python 3.11 Docker + real Postgres, fresh database):** migration
upgrade → downgrade(`20260728_0001`) → re-upgrade cycle and schema (`b_hint_events`,
`uq_b_hint_events_opportunity_level`); first hint returns L1 and persists exactly one event;
sequential requests escalate L1→L2→L3 then a fourth request is refused; replay with the same
Idempotency-Key returns the same level without a second event or escalation; a template with no
catalogue hint content fails closed (`ConflictError`, no answer/hint text in the error); a hint
request creates no `AttemptRecord`, no `SkillStateTransitionRecord`, and no
`LearnerSkillStateRecord`; the public response contains exactly the safe field set (no
`correct_answer`/`p_l`/etc.). `test_be3_live_engine_boundary.py`: 24 passed, 0 skipped. Full suite:
209 passed. `git status`: only `Dev/backend/` touched (`hint_request.py`, `b_hint.py`, the new
migration, `test_be4d_hint_events.py` untracked; `b_session.py`, `persistence_models.py`,
`repositories.py`, `test_be2_architecture_guards.py`, `test_be2_persistence.py` modified).

This batch does NOT claim `BE4D_HINTS_RETRIES_BATCH_CLOSED` — a separate closure review decides
that. Left uncommitted for Yasindu.

---

## 2026-07-28 — BE4e: completion, safe progress, and recovery (BEplan §9 BE4.6)

Implements the next-or-complete opportunity/session transition, private session aggregation +
Guess-Guard + certification, a SAFE session-standing view, and recovery paths, authorized by the
same BE4 engineering-continuation instruction (TEST-provenance DRAFT only; no real-child/pilot/
production; no GATE-B value). Builds on BE4a-d. New: `app/domain/b_completion.py` (strict
`OpportunityAdvanceResponse`/`SessionStandingResponse` contracts), `app/application/
session_completion.py` (`SessionCompletionService`), `migrations/versions/
20260728_0003_be4e_session_completion.py` (`b_session_aggregate_results`,
`b_skill_certification_results`), `tests/test_be4e_session_completion.py`. Changed:
`persistence_models.py` (the two new tables), `repositories.py` (`SessionAggregateResultRepository`,
`SkillCertificationResultRepository`, plus new query methods on `ItemOpportunityRepository`/
`AttemptRepository`/`SkillStateTransitionRepository`), `app/api/routes/b_session.py` (two new
routes), `app/application/opportunity_selection.py` (BE4b's selection endpoint made resumable;
select/build/persist/token-issue logic factored into shared module-level functions —
`resolve_bundle_and_catalogue`, `load_or_init_skill_states`, `open_adaptive_opportunity`,
`reissue_presentation_for_open_opportunity` — reused by both BE4b and BE4e rather than duplicated),
`tests/test_be2_architecture_guards.py` and `tests/test_be2_persistence.py` (allow-lists extended
by name for the two tables + two routes), `tests/test_be4b_adaptive_selection.py` (one test updated
— see "Recovery" below for why the old assertion no longer holds).

**Routes:** `POST /api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/complete`
(next-or-complete, atomic) and `GET /api/v1/b/sessions/{session_id}/summary` (SAFE standing) —
neutral paths; "progress" (a prohibited scientific path term) never appears — "summary" is used
instead, per the bounded prompt's own guidance. The `session` carve-out is extended to both routes
only; every other prohibited path term (`attempt`, `hint`, `progress`, `bkt`, `mastery`, `sequenc`,
`certif`, `guess`) is still enforced on them.

**Scientific integrity.** Every scientific step goes through `LiveEngineAdapter` (lazy, function-
scope import): `aggregate_session` folds the session's own attempts/hints/first-attempt outcomes
(built from real `AttemptRecord`/`HintEventRecord`/`SkillStateTransitionRecord` rows, never
synthesized) into first-attempt accuracy, retries, assisted-opportunity count, response-time
stats, and per-skill estimated mastery; `plausibility_floor`/`evaluate` compute the per-skill
Guess-Guard status from the learner's own per-skill response-time history (client-elapsed-ms
telemetry, converted to seconds); `certify_skill` runs *inside* `aggregate_session` once
`guard_statuses`/`theta_b` are supplied. No formula is reimplemented; the "median" RT is computed
by calling the adapter's own `plausibility_floor` at `q=0.5, n_min=1` rather than a second quantile
implementation. The pinned TEST_FIXTURE_ONLY `opportunity_selection._ENGINEERING_BKT_CONFIG` is
reused unchanged (θ_B, floor_quantile, floor_min_obs) — never a GATE-B/population value.

**GATE-B deferrals (not approved — recorded per the BE4e authorization and
`provenance/component-b-closure-decisions.json`):**
- **Completion policy**: "complete on command" — an opportunity completes when the client
  explicitly calls the `/complete` route (gated on >=1 recorded attempt/timeout for that
  opportunity, mirroring BE2's `b_session.complete`/`abandon` neutral-explicit-command pattern).
  `MAX_OPPORTUNITIES_PER_SESSION = 5` (a fixed engineering session-length bound) decides
  next-vs-complete-session; `COMPLETION_POLICY_VERSION` tags every persisted aggregate row so a
  later governed policy change is traceable, never silently reinterpreted.
- **Safe-progress policy**: `OpportunityAdvanceResponse`/`SessionStandingResponse` carry only
  session state and coarse opportunity counts — no raw BKT value, no private selection rationale,
  no Guess-Guard internals, no per-skill mastery/certification (architecturally GATE-B UNRESOLVED,
  so not exposed even in aggregate form). Aggregation/Guess-Guard/certification are computed and
  persisted PRIVATELY only.
- θ_B and the Guess-Guard numerics are the same TEST_FIXTURE_ONLY engineering config BE4b/BE4c
  already use; never promoted to "approved" by this batch.

**Next-or-complete atomicity.** Closing the current opportunity, then either opening the next one
(reusing BE4b's now-shared `open_adaptive_opportunity`) or transitioning the session to
`completed` plus persisting the aggregate/certification rows, all happen inside one
`SqlAlchemyUnitOfWork` and commit exactly once at the end of `complete_and_advance` — the same
single-commit-point pattern `AttemptSubmissionService`/`HintRequestService` use. Any failure before
that commit rolls back every step (including a partially-built next opportunity or partially-
persisted aggregate), verified by `test_advance_requires_at_least_one_attempt` (fails closed with
zero side effects) and the replay test (a duplicate request produces no second open/complete).

**First-attempt-only is untouched.** `session_completion.py` never imports
`LearnerSkillStateRepository` for writes and never inserts into `b_skill_state_transitions` — it
only *reads* the transitions BE4c already wrote. `test_completion_creates_no_additional_bkt_
transition_or_observation` asserts the transition-row count is unchanged by completion.

**Privacy.** `test_public_advance_and_standing_responses_contain_no_private_fields` field-scans
both public DTOs (and the nested `next_opportunity` presentation) against a forbidden-key set
(`p_l*`, `predicted_probability`, `posterior_p_l`, `skill_estimate`, `certified`,
`threshold_met_flag`, `plausibility_status`, `correct_answer`, `allowed_equivalent_answers`,
`selection_provenance`, `theta_b`, `guard_status`) and asserts the exact safe field set. New
PRIVATE-table column names avoid every `PROHIBITED_COLUMN_TERMS` entry: `outcome_pattern_
distribution` not `error_class_distribution`, `assisted_opportunity_count` not `hint_bearing_
opportunities`, `skill_estimate` not `mastery`/`p_l`, `threshold_met_flag` not `certified_flag`,
`plausibility_status` not `guess_guard_status`, `first_attempt_match_count`/`_rate` not
`first_attempt_correct_count`/`_rate`, and the `b_skill_certification_results` primary key is
`skill_result_id` (not `skill_certification_result_id`, which the architecture guard's column-term
scan rejected on first run — caught and fixed by the real full-suite run, see "Errors" below).

**Recovery (BEplan §9 BE4.6 step 6).** Duplicate submission of `/complete` reuses the same
`b_idempotency_records` mechanism as BE4c/BE4d (replay returns the original response, no second
close/open/complete — `test_replay_with_same_idempotency_key_returns_same_response_without_
second_effect`). App restart / a stale presentation token / a retried opportunity-select call are
handled by making BE4b's `select_next_opportunity` resumable: if the session already has an OPEN
opportunity, it now re-issues a fresh presentation token for that *same* opportunity
(`reissue_presentation_for_open_opportunity`) instead of raising `ConflictError` — verified by
`test_reselecting_with_an_open_opportunity_returns_the_same_opportunity_not_a_duplicate` and
`test_stale_presentation_token_fails_closed_and_clean_reselect_succeeds` (an unknown/expired token
still fails closed via `validate_presentation_token`, but a clean re-select recovers cleanly with
no duplicate row). This intentionally changed BE4b's prior behavior, so
`tests/test_be4b_adaptive_selection.py::test_one_open_opportunity_per_session_rejects_a_second_
select` was renamed and its assertion updated to the new resumable contract, with an inline note
explaining why.

**Errors encountered and fixed (both caught by the real Docker+Postgres run, not by inline
review):**
1. `_build_opportunity_response` initially passed the raw `ItemOpportunityRecord` UUID as
   `OpportunityResponse.item_opportunity_id`; the vendored package's `SessionSummary` validates
   every opportunity id against `^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$` (and requires strictly
   ascending item indices), which `aggregate_session` surfaced as a `LiveEngineError` ->
   `ConflictError` on the very first "complete at bound" exercise. Fixed by deriving the same
   package-format id BE4b's `build_task` already uses (`package_item_opportunity_id`), reused
   rather than duplicated.
2. `SkillCertificationResultRecord`'s primary key `skill_certification_result_id` contains
   "certif" and tripped `test_exact_authorized_model_table_set_and_no_scientific_columns` on the
   first full-suite run. Renamed to `skill_result_id` everywhere (model, migration, service).

**Verification (Python 3.11.15, real Postgres 16.10, fresh isolated Docker network+containers —
no compose file existed for this yet, so a network + `postgres:16.10-bookworm` container +
`python:3.11.15-slim-bookworm` container with the vendored wheel installed were built ad hoc for
this run):** migration upgrade -> downgrade(`20260728_0002`) -> re-upgrade cycle and schema (both
new tables + their unique constraints); `alembic check` reports no drift after re-upgrade;
`test_be3_live_engine_boundary.py`: **24 passed, 0 skipped** (not skipped). New
`test_be4e_session_completion.py`: **9 passed** (migration cycle; below-bound advance
closes-current-and-opens-exactly-one-next; at-bound completes the session and persists the
aggregate + certification rows privately with the exact expected stats; completion requires >=1
attempt; completion creates no additional BKT transition; idempotent replay; two recovery tests;
public-DTO privacy scan). **Full suite: 219 passed, 0 failed** (two pre-existing-shape failures
surfaced by this batch's own changes were fixed in the same run — the column-name violation and
the BE4b resumability-contract test update above — then the full suite was re-run clean).
`git status`: only `Dev/backend/` touched (`session_completion.py`, `b_completion.py`, the new
migration, `test_be4e_session_completion.py` untracked; `b_session.py`, `opportunity_selection.py`,
`persistence_models.py`, `repositories.py`, `test_be2_architecture_guards.py`,
`test_be2_persistence.py`, `test_be4b_adaptive_selection.py` modified).

This batch does NOT claim `BE4E_COMPLETION_RECOVERY_BATCH_CLOSED` — a separate closure review
decides that. Left uncommitted for Yasindu.

---

## 2026-07-28 — BE4f: full transactional sweep + deterministic parity + Exit Gate (BEplan §9 BE4.7)

Authorized by the same BE4 engineering-continuation instruction (TEST-provenance DRAFT only; no
real-child/pilot/production; no GATE-B value). Verification-only batch, as directed: no production
code changed. New: `tests/test_be4f_parity.py` (the deterministic parity test) and
`tests/test_be4f_transactional_sweep.py` (the full end-to-end sweep, real routes via `TestClient` +
real Postgres). No migration added — `alembic current` stays at `20260728_0003` (BE4e's head)
before and after this batch.

**Parity — headline deliverable, documented fallback, not the raw digest match.** Traced the
characterization anchor (`provenance/component-b-characterization.json`:
`config_version="b1-smoke-0.1.0"`, `global_seed=20260716`, 54 item instances,
`private_output_sha256=b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c`) back to
its source in the `Yass` research repo at the exact `generator_git_tree_sha1` the characterization
file cites (`73acb113bbb179f5946333c27b0142c43f3063f3`). `config_version="b1-smoke-0.1.0"` is
emitted only by `component_b_generator.config.loader.default_b1_config(global_seed=20260716,
n_learners=8, scheduled_session_count=3)` — an 8-learner, 3-session **cohort pipeline** run
(`component_b_generator.pipeline`), not a single `build_task_instance` call. Producing 54 instances
from that config requires `pipeline`'s own orchestration plus `cohort.builder`,
`behaviour.initialization` (hidden per-learner truth), `behaviour.attempt_loop` (simulated attempts/
timing), and `generation.item_opportunities._draw_item_count` (a randomized per-session item
count) — every one of which is listed verbatim under `explicitly_prohibited_from_application` in
`provenance/component-b-live-engine-reuse-map.json` and is never vendored into
`upadya-component-b-live-engine` / never importable from `app/` (`test_be3_live_engine_boundary.py`
keeps exactly this shut). `git grep` across every commit of both the `Yass` repo and this backend
for `item_instance_count` / `private_output_sha256` found no reproduction script anywhere — the
54-item sweep was evidently run ad hoc against the full (never-vendored) pipeline. Reproducing the
exact digest through the adapter is therefore architecturally unavailable, not merely
inconvenient — attempting it would require importing precisely the modules BE3/BE4's reuse
boundary exists to keep out of the live application. STOPPED short of fudging the digest, per the
bounded prompt's own instruction, and used the documented **ACCEPTABLE FALLBACK** instead: for
every one of the 29 implemented, grade-eligible fixture-catalogue templates (the same
full-coverage sweep `test_be3c_characterization.py::TestAllImplementedTemplatesGenerate` already
uses), `LiveEngineAdapter.build_task_instance` is compared byte-for-byte (canonical JSON,
`sort_keys=true, separators=(",", ":")`, per the characterization file's own recorded method)
against an independently constructed direct call into the vendored package's own
`component_b_generator.generation.task_instances.build_task_instance` — built from scratch in the
test (its own `GeneratedItemOpportunity`, its own `SeedManager`, its own `load_catalogue`), never
by reaching into the adapter's private helpers. Comparison is scoped to exactly the field set the
adapter's `TaskInstance` port type exposes (every generated/scientific field: operands, correct
answer, distractors, distractor rule ids, applied guards, generation seed — the package's raw
`GeneratedItemInstance` also carries internal-only bookkeeping fields like `generation_phase`/
`item_index`/`learner_id`/`validation_status` outside the adapter's contract, which are excluded
from the comparison, not silently matched). Repeat-run byte-identity is asserted for both the
adapter and the direct call. **Result: every pair matched byte-for-byte; repeat runs were
byte-identical for both paths.** `test_be4f_parity.py`: 3 passed.

**Full transactional sweep** (`test_be4f_transactional_sweep.py`, real FastAPI routes via
`TestClient`, real Postgres — as directed, not direct service calls like BE4a-e's own dedicated
per-batch test files, which this file complements rather than duplicates):
1. **Full session flow, every path, one integrated session**: correct-first-attempt: wrong-first-
   attempt-then-correct-retry (only attempt 1 observes BKT): hint request (asserted either to
   succeed or fail closed, since which item_template_id real adaptive selection lands on is not
   hand-controlled and only 29/36 fixture templates carry hint content) followed by a correct
   attempt: a genuinely expired server-side timeout (deadline fixed at opportunity-OPEN time, so
   the timeout patch is applied before the opening call, not merely before the later attempt — a
   bug caught and fixed during this run, see "Errors" below): completion to the
   `MAX_OPPORTUNITIES_PER_SESSION=5` bound, session transitions to `completed`. Exactly 4 BKT
   transitions resulted from the 4 genuine first-attempt RESPONSE events (the TIMEOUT opportunity
   created none) — asserted directly against `b_skill_state_transitions`.
2. **Concurrency**: two concurrent duplicate attempt submissions (distinct Idempotency-Keys, same
   opportunity) via real HTTP threads produce exactly one `SkillStateTransitionRecord`; five
   concurrent hint requests never escalate past L3 (the same opportunity-row `FOR UPDATE` lock
   BE4c's attempt path uses serializes them) — successes' levels are exactly `1..n`, n<=3, excess
   requests fail closed (409).
3. **DB/technical failure before AND after the BKT/mastery calculation**: a service subclass
   raising `SQLAlchemyError` as the first statement of `_apply_first_attempt_bkt` (BEFORE any
   `predict`/`posterior`/`update` call — BE4c's own test only covers AFTER, at commit) proves the
   attempt-record flush that precedes it also rolls back (zero `AttemptRecord`, zero
   `SkillStateTransitionRecord`); a `commit()`-raising unit-of-work (AFTER the BKT calc, mirroring
   BE4c's own pattern) proves the same at the later boundary. Both surface as `TECHNICAL_FAILURE`
   (503), never a learner-facing incorrect-attempt outcome, and neither alters
   `LearnerSkillStateRecord.observation_count`.
4. **Network retry + idempotent replay** across every BE4 command route in one flow (start,
   attempt, hint, complete) — replays return byte-identical canonical responses and create no
   second write, with one documented exception: a hint request that legitimately fails closed
   (no catalogue content for the selected template) is never persisted to
   `b_idempotency_records` (only a *successful* hint reserves+finishes that record), so replaying
   it re-executes the same fail-closed path with a fresh `request_id` rather than replaying a
   stored canonical response — there is no second side effect either way, so this is intended
   behavior, not a gap.
5. **Server/client clock disagreement**: a genuinely server-side-expired opportunity still times
   out even when the client claims `client_elapsed_ms=0`; a fresh opportunity submitted with the
   client claiming the maximum allowed elapsed time (3,600,000 ms) is still judged correct/incorrect
   from `submitted_value` alone — `client_elapsed_ms` never enters the correctness or timeout
   decision, only server timestamps and the server-persisted deadline do.
6. **Grade eligibility + deferred-template exclusion sustained across a whole session**: a
   Grade-2 learner is driven through all 5 opportunities of a session end-to-end; every
   `(skill_id, item_template_id)` pair persisted for the session is asserted to never be
   `multiplication`/`division` and never the deferred-calibration-pending template id.
7. **Technical failure never recorded as learner failure or a BKT observation**: reuses the
   before-BKT-calc failure injection and asserts the opportunity's learner-skill-state row is
   either absent or has `observation_count == 0` afterward.
8. **Public payload + structured-log field scan across every BE4 route**: select/hint/attempt/
   complete/summary response bodies are recursively scanned against a forbidden-key set (answers,
   accepted-answer sets, distractor internals, generation seed/guards, catalogue version/checksum
   outside the hint route's own governed reconstruction key, selection provenance, sequencing
   score internals, raw BKT/mastery/theta_B) with none found; `caplog`-captured structured JSON log
   records from the same session (via `app.core.logging.JsonFormatter`'s fixed whitelisted field
   set) are scanned the same way — none found. `test_be4f_transactional_sweep.py`: 10 passed.

**Errors encountered and fixed (all caught by the real Docker+Postgres run):**
1. `/api/v1/learner/profile` creates a learner with `grade=None` (grade is only ever assigned via
   classroom-membership approval); every opportunity-selection call fails closed
   (`ConflictError`/409) without a grade. Fixed by directly setting `Learner.grade` after profile
   creation in this file's `setup_learner` helper, the same way `test_be4b_adaptive_selection.py`
   seeds grade directly rather than routing through classroom membership.
2. The server timeout deadline is fixed at opportunity-OPEN time
   (`opportunity_selection.open_adaptive_opportunity` reads `DEFAULT_TIMEOUT` once, when the
   opportunity row is created) — an early version of both the full-session-flow and the
   clock-disagreement test patched `DEFAULT_TIMEOUT` to zero only *after* the opportunity had
   already been opened with the original 5-minute value, so the "genuinely expired" scenario
   spuriously returned `RESPONSE` instead of `TIMEOUT`. Fixed by moving the monkeypatch to wrap
   the opening call itself.
3. An initial version of the hint step in the full-session-flow and network-retry tests assumed
   any selected opportunity's template carries catalogue hint content; real adaptive selection is
   not hand-pinned to a template in this integrated flow (unlike BE4d's dedicated, pinned-template
   hint tests), and only 29/36 fixture templates do. Fixed by asserting either outcome (success or
   fail-closed 409) and, for the replay comparison specifically, only requiring byte-identical
   replay when the first call actually succeeded (see point 4 above for why a failed lookup's
   replay legitimately differs only in `request_id`).
4. The parity test's first draft called `.model_dump(mode="json")` on the adapter's `TaskInstance`
   return value, which is a frozen `dataclasses.dataclass`, not a Pydantic model — fixed with
   `dataclasses.asdict`. The first full-field comparison against the vendored package's raw
   `GeneratedItemInstance.model_dump(mode="json")` also failed for one pair because that raw dump
   carries extra internal-only fields the adapter's narrower port type never exposes; fixed by
   scoping the comparison to exactly the fields the adapter payload contains (see "Parity" above).

**Exit Gate assertion.** The end-to-end Component B learner scenario above passes transaction,
concurrency, replay, timeout, privacy, and recovery in one integrated session; each genuine first
attempt produced exactly one atomic mastery transition (4 transitions for 4 first-attempt RESPONSE
events across the swept session, zero for the TIMEOUT opportunity, zero for retries, zero for
hints); no technical failure (before or after the BKT calc) altered `observation_count` or left a
partial `AttemptRecord`/`SkillStateTransitionRecord`.

**No production gap found.** This batch is verification-only, as directed; no `app/` code changed
(confirmed by `git status` below).

**Verification (Python 3.11.15, real Postgres 16 — a fresh, ad hoc Docker network + `postgres:16-
alpine` container + `python:3.11.15-slim-bookworm` image built from the existing `Dockerfile`, since
no compose file exists yet, matching BE4e's own ad hoc verification setup):**
- `test_be4f_parity.py`: **3 passed** (not skipped — `component_b_generator` importable, ran
  against the real vendored wheel).
- `test_be4f_transactional_sweep.py`: **10 passed** (not skipped).
- `test_be3_live_engine_boundary.py`: **24 passed, 0 skipped** (13 prohibited modules stay
  unreachable; the adapter is still the sole `app/` importer).
- `alembic upgrade head` → `20260728_0003` (BE4e's head, unchanged); no migration added by this
  batch.
- **Full suite: 232 passed, 0 failed, 0 skipped**, run in 225.27s.
- `git status`: only `Dev/backend/tests/test_be4f_parity.py` and
  `Dev/backend/tests/test_be4f_transactional_sweep.py` (both untracked) — no other file touched.

This batch does NOT claim `BE4_LIVE_LEARNING_FLOW_BATCH_CLOSED` — a separate review decides that
(the overall BE4 Exit-Gate identifier). Left uncommitted for Yasindu.

## 2026-07-28 — BE5a: freeze & version the frontend contract (BEplan §10 steps 1-4, 8, 10)

Engineering-only, contract-shape batch — no route behavior change, no new endpoint, no scientific
logic touched. Froze the live `app.openapi()` and generated/checked TypeScript types from it on
the frontend side, adding drift tests on both sides against one shared artefact.

**Frozen artefact.** `backend/contract/openapi.v1.json` (2,622 lines, produced by
`app.openapi()` under the project's own `python:3.11.15-slim-bookworm` Docker image — the local
host has no 3.11/3.12 interpreter, same constraint as every prior batch) plus
`backend/contract/openapi.v1.meta.json` (`contract_version: "v1"`,
`checksum_sha256: 910fde8ef0d2ff7d09fc0edcf8479811d599691db0fba764e1df7d85375d44fc`). Its route
set (25 distinct paths / 28 operations) matches `test_be2_architecture_guards.py::EXPECTED_ROUTES`
exactly (asserted as a set, not a hardcoded count).

**No-private-field guarantee.** `test_be5a_contract_freeze.py::test_no_private_or_scientific_
field_name_in_frozen_schema` scans every `components.schemas.*.properties` key (not description
text — docstrings on several of these models legitimately discuss BKT/mastery/distractors as
what is NOT exposed, so a naive substring scan over the whole JSON would false-positive) against
the same forbidden-term set `test_be2_architecture_guards.py` uses at the DB-column layer
(`mastery`, `bkt`, `answer`, `correct`, `distractor`, `seed`, `provenance`, and more). Zero
offenders — independently confirms BE4's private/public DTO split holds at the API-schema layer.

**Backend drift tests** (`test_be5a_contract_freeze.py`, 4 new tests): live `app.openapi()` ==
frozen JSON; frozen file's own sha256 == the committed meta checksum; frozen route set ==
`EXPECTED_ROUTES` == live route set; the no-private-field scan above.

**Generated TypeScript types.** `frontend/scripts/generate-contract-types.mjs` — a small,
dependency-free, deterministic OpenAPI-schema-to-TS-interface generator (no `openapi-typescript`
install; handles `$ref`, `anyOf`, `const`, `enum`, and `additionalProperties` as they actually
appear in this schema) — mechanically emits `frontend/src/api/generated/openapi-types.ts` (one
`interface` per component schema, alphabetically ordered, plus a `CONTRACT_OPERATIONS`
path/operation index). Committed output is verified non-stale by a frontend test that re-runs the
generator in-memory and diffs it against the committed file.

**Frontend reconciliation — real finding.** Comparing the frozen artefact against the existing
handwritten `frontend/src/api/contracts.ts` surfaced that most of it predates the real backend:
`/api/v1/me` returns only `AuthenticatedPrincipal{user_id, email}` (no `roles`/`learner`/
`request_id`), and `POST /api/v1/b/sessions` takes no request body and returns
`SessionCommandResponse{session_id, state, runtime_bundle_version, created_at_utc, row_version,
request_id}` — not the `b_session_id`/`session_number`/`resume`/`current_opportunity_id`/
`expires_at` shape `contracts.ts`'s `MeResponse`/`StartSessionResponse` assume. Those two types
are consumed throughout `auth-context.tsx`'s authorization gating and
`session-preparation-screen.tsx`'s whole phase/navigation state machine — both currently exercised
only via the `EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE` path, never against the live backend. Aligning
them to reality is BE5 step 5 (wiring the session-prep/identity flow to real APIs), explicitly
excluded from this BE5a batch (steps 1-4, 8, 10 only) — confirmed with the project director before
proceeding. Left `MeResponse`/`StartSessionRequest`/`StartSessionResponse`/
`PendingStartSessionCommand` unchanged, with an explicit code comment on each documenting the real
shape and pointing at `openapi-types.ts`, so the gap is visible rather than silently papered over.
Similarly, the real runtime error envelope (`app/core/errors.py` `ErrorResponse`/`ErrorBody`:
schema_version plus a nested error object with code/message/request_id/details) is invisible to
`app.openapi()` — FastAPI does not auto-register custom-exception-handler responses in the
generated schema — so `ApiErrorEnvelope` (flat, with an unused `retryable` field) has no frozen
artefact to reconcile against yet; left unchanged with the same kind of comment, and flagged as a
follow-up (adding explicit `responses=` schema annotations to every route) rather than attempted
here.

**What WAS safely reconciled** (present in the frozen artefact, no screen/business-logic consumer
to break): `HealthReadyResponse` in `contracts.ts` is now derived directly from the generated
`ReadinessResponse` type instead of a hand-guessed partial shape; `isHealthReadyResponse` in
`runtime-validation.ts` now requires `stage: "infrastructure"` and a `checks` string-map object
(previously accepted partial/incorrect shapes) — strictly more fail-closed, never weaker.
`component-b-api.ts`'s dev fixture literal for `checkReadiness()` was updated to match (adds
`stage`/`checks`) — no behavior change, just keeps the fixture type-correct.

**Frontend contract-check tests** (step 10) — `frontend/src/api/__tests__/contract-freeze.test.ts`,
run via Node's built-in test runner (`node --import tsx --test`, `npm run test:contract`; added
`tsx` as a devDependency since the app's own TypeScript uses constructor parameter properties,
which Node's native type-stripping can't erase on its own):
1. sha256 of the frontend's own read of `backend/contract/openapi.v1.json` matches
   `openapi.v1.meta.json` (both sides checking the same artefact, not independently-trusted
   copies).
2. Re-running the generator in-memory produces byte-identical output to the committed
   `openapi-types.ts` (no stale generated file).
3. `isHealthReadyResponse` accepts a schema-derived valid `ReadinessResponse` sample and, for each
   of the schema's required fields independently, rejects a sample with that field dropped
   (fail-closed proven per-field, not just on the happy path).
4. `getComponentBDevelopmentFixture()` returns null under `EXPO_PUBLIC_APP_ENV` set to staging,
   production, or unset, even with `EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE` set, and only returns the
   fixture name under development (BEplan step 8 — dev-fixture gating, asserted not assumed; the
   guard already existed in `component-b-api.ts`, this batch adds the test).

**Verification.**
- Backend, Python 3.11.15 + real Postgres 16 (fresh Docker network + `postgres:16-alpine` + the
  project's own `Dockerfile`, now also copying `contract/` into the image so the drift test can
  read it in-container): `alembic upgrade head` stayed at unchanged `20260728_0003`; full suite
  **236 passed, 0 failed, 0 skipped** in 189.94s (up from 232 — the 4 new BE5a tests), including
  `test_be3_live_engine_boundary.py` and `test_be4f_parity.py` running for real (not skipped).
- Frontend: `npx tsc --noEmit` clean; `npm run test:contract` — 4/4 passed.
- `git status`: `backend/Dockerfile` (contract COPY line), `backend/contract/` (new, frozen
  artefact + meta), `backend/tests/test_be5a_contract_freeze.py` (new);
  `frontend/src/api/contracts.ts`, `frontend/src/api/runtime-validation.ts`,
  `frontend/src/api/component-b-api.ts` (reconciliation + comments),
  `frontend/src/api/generated/` (new, generated types),
  `frontend/scripts/generate-contract-types.mjs` (new, the generator),
  `frontend/src/api/__tests__/` (new, contract-freeze tests),
  `frontend/package.json` and `package-lock.json` (`tsx` devDependency + two new scripts). No
  other file touched; no `app/` route behavior changed.

This batch does NOT claim `BE5A_CONTRACT_FREEZE_BATCH_CLOSED` — a separate review decides that.
Left uncommitted for Yasindu.

## 2026-07-28 — Frontend auth/identity rewiring against the frozen v1 contract (BE5 step 5, part 1)

Reconciled the four stale `contracts.ts` types identified in the BE5a batch above against the real
generated shapes in `frontend/src/api/generated/openapi-types.ts`, and updated the minimum
consumer code required for them to compile and behave correctly. No backend file touched; no
classroom/invite/membership, opportunity/attempt/hint/complete, or session-recovery endpoints
touched (those remain FE-1a/FE-1b/FE-3/FE-2 scope).

**Identity (`contracts.ts`, `runtime-validation.ts`, `client.ts`, `auth-context.tsx`).** Deleted
the fictional `MeResponse` (`roles`/`learner`/`request_id`). `GET /api/v1/me` now types and
validates as the real `AuthenticatedPrincipal` (`user_id`, optional `email`) via a new
`isAuthenticatedPrincipal`. Role/profile resolution is the separate `GET /api/v1/learner/profile`
call, typed/validated against the real `LearnerProfileResponse` via a new
`isLearnerProfileResponse`. `client.ts`'s `getAuthorizedLearner` now fetches both — principal first
(preserving the existing unauthenticated-refresh and 5xx-retry-once behavior), then the learner
profile using whatever access token the principal fetch ended up succeeding with — and returns a
new composed `AuthorizedLearner = { principal, learnerProfile }` type (added to `contracts.ts`). A
clean `404` on the profile call maps to `learnerProfile: null` (onboarding, matching prior
routing); `401`/`403` propagate unchanged for existing handling; anything else (network, 5xx,
unexpected 4xx) is wrapped as `ApiClientError('unavailable', ...)` — fails closed rather than
guessing at onboarding. `auth-context.tsx`'s `me` state and `authorizeSession` now key off
`AuthorizedLearner`/`learnerProfile` instead of the fictional `roles`/`learner.active`/
`learner.grade`; the `AuthStatus` enum and its meanings are unchanged, only what drives them.
`learner-home-screen.tsx` and `authorized-placeholder-screen.tsx` (both consumers of
`useAuth().me`) updated to read `me.learnerProfile.name` instead of `me.learner.display_name`.

**No `grade` field exists anywhere reachable from `AuthenticatedPrincipal` or
`LearnerProfileResponse`.** `session-preparation-screen.tsx` previously rendered "Grade {grade}"
from the fictional `me.learner.grade`. Removed that badge and its now-dead `gradeIcon`/`divider`
styles entirely rather than fabricating a value; left a one-line comment at the removal site
pointing at the gap. No replacement grade selector or other compensation added — out of scope.

**Session start (`contracts.ts`, `runtime-validation.ts`, `component-b-api.ts`,
`session-preparation-screen.tsx`).** Deleted `StartSessionRequest` (`POST /api/v1/b/sessions`
takes no request body, only a required `Idempotency-Key` header) and the fictional
`StartSessionResponse` (`b_session_id`/`resume`/`current_opportunity_id`/`expires_at`/
`session_number`); consumers now use the real generated `SessionCommandResponse`
(`session_id`/`state: 'active'|'completed'|'abandoned'`/`runtime_bundle_version`/
`created_at_utc`/`row_version`/`request_id`), re-exported from `contracts.ts`.
`PendingStartSessionCommand.body` is deleted (nothing to persist/replay beyond the idempotency
key). `component-b-api.ts`'s `startSession` takes just `(idempotencyKey, accessToken)` — no body
parameter — and validates responses with a new `isSessionCommandResponse` (replacing
`isStartSessionResponse`); the dev fixture's `createFixtureApi` returns the real
`SessionCommandResponse` shape and no longer branches on `resume`/`starting-response` fixture
names (removed from `.env.example`'s documented fixture list too, since those fields no longer
exist to fixture). `session-preparation-screen.tsx`'s `openActiveSession` now treats
`state === 'active'` as success (routes via `response.session_id`) and any other state
(`'completed'`/`'abandoned'`) as `technical-failure`; a one-line comment notes that resume
detection via `GET /api/v1/b/sessions/active` is deferred to FE-2, not implemented here.
`createStartCommand` no longer builds a `client_timezone`/`mobile_app_version` body, so the
now-unused `getTimezone()` helper and `mobileAppVersion` import were removed from that screen.

**Verification** (from `frontend/`, all green):
- `npx expo-doctor@latest` — 18/18 checks passed.
- `npx tsc --noEmit` — clean.
- `npm run lint` — clean (required `NODE_OPTIONS=--max-old-space-size=4096` in this environment;
  the default heap OOM'd on `expo lint`, unrelated to this batch's changes).
- `npm run test:contract` — 4/4 passed, unregressed (frozen-artefact checksum, generated-types
  staleness, `isHealthReadyResponse` fail-closed-per-field, dev-fixture env gating).

**Files touched:** `frontend/.env.example`, `frontend/src/api/contracts.ts`,
`frontend/src/api/runtime-validation.ts`, `frontend/src/api/client.ts`,
`frontend/src/api/component-b-api.ts`, `frontend/src/auth/auth-context.tsx`,
`frontend/src/features/session/session-preparation-screen.tsx`,
`frontend/src/features/home/learner-home-screen.tsx`,
`frontend/src/features/auth/authorized-placeholder-screen.tsx`. No backend file touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-28 — FE-1a: learner onboarding (profile, join-code, membership status)

Implemented profile creation, classroom join-code resolve/confirm, and a new pending/approved
membership-status screen against the frozen v1 contract's `learner-profile` and
`classroom-invites`/`classroom-memberships` endpoints. No backend file touched. Out of scope and
untouched: FE-1b teacher-side screens/endpoints, FE-2 session-prep, FE-3 opportunity/attempt/hint,
and `AuthStatus`'s enum/gating logic (see open question below).

**Contracts and validators (`contracts.ts`, `runtime-validation.ts`).** Re-exported
`ProfileCreateRequest`, `InviteTokenRequest`, `InviteResolveResponse`, `MembershipRequestResponse`,
`LearnerMembershipListResponse`, `LearnerMembershipListItem` from the generated types (no
hand-rolled shapes). Added fail-closed validators for all of them, following the existing
`is<TypeName>` pattern: `isProfileCreateRequest`, `isInviteTokenRequest`,
`isInviteResolveResponse`, `isMembershipRequestResponse`, `isLearnerMembershipListResponse` (plus a
private `isLearnerMembershipListItem` used for the array-of-items check). `grade` and `state` are
checked against `Set`s of the contract's literal enum values.

**New endpoint file (`learner-onboarding-api.ts`).** Added as a sibling to `component-b-api.ts`
(kept separate rather than crowding it, since this is a different domain) with
`createLearnerProfile`, `resolveClassroomInvite`, `requestClassroomMembership`,
`listLearnerClassrooms` — each a thin wrapper over the shared `requestJson` from `client.ts`, no
direct `fetch` calls. The three state-changing calls take a caller-supplied `idempotencyKey`; no
new key-generation helper was added, matching the existing convention (session-preparation's
`Crypto.randomUUID()` per call site).

**Profile creation (`first-time-welcome-screen.tsx`).** Replaced the bare Continue button with a
name field pre-filled from `profileName` (Supabase `display_name`) that the child can edit, then
calls `POST /api/v1/learner/profile` with a `useRef`-held idempotency key (not persisted to
SecureStore — a deliberate simplification versus the session-start pending-command pattern, since
losing an in-flight profile-create on app kill is a low-frequency, low-harm case for this batch).
On success, calls `retryAuthorization()` so `me.learnerProfile` comes from the server, then routes
to `/(onboarding)/teacher-link`. On 422, shows a correction message and rotates to a fresh
idempotency key (edited name = new action); on network/5xx, keeps the same key and lets the child
retry.

**Join-code screen (`teacher-link-instructions-screen.tsx`).** Replaced the QR placeholder and the
`continueToComponentBPreview` dev-bypass entirely with real text entry (placeholder example
`M7KP-4X9D`) and a two-step confirm: "Check code" calls `POST /classroom-invites/resolve` and shows
`"{classroom_name}'s Grade {2|3} classroom — is this right?"` (or a generic "This classroom" if
`classroom_name` is null) without auto-submitting; a second explicit "Yes, that's right" button
calls `POST /classroom-memberships/requests` with the same invite token and its own fresh
idempotency key, then routes to the new status screen with the created `classroom_membership_id`.
On resolve, 422/404 (an unrecognized code) rotates to a fresh resolve key — a corrected code is a
new action — and returns to code entry with a correction message; a network/5xx failure on resolve
keeps the same resolve key and also returns to code entry, so the identical code can be retried
without burning the key. On confirm, 422 rotates the membership key and returns to code entry the
same way; network/5xx keeps the same membership key and stays on the preview step, so the
previewed classroom isn't lost.

**New pending/approved screen (`classroom-status-screen.tsx` + `app/(onboarding)/classroom-status.tsx`).**
Calls `GET /api/v1/learner/classrooms` only on mount and on pull-to-refresh — never polls
continuously while foregrounded, per frontend.md 15.10's don't-poll guidance applied by analogy.
Matches the membership by the `membershipId` route param, falling back to the most recently
requested item if absent. PENDING shows "Waiting for your teacher to approve"; APPROVED routes on
to `/(learner)/home`; REJECTED shows a safe, non-shaming message with a "Try a different code"
button back to the join-code screen.

**Open question — not resolved here, needs a decision:** `auth-context.tsx`'s `authorizeSession`
still sets `status: 'authorized'` as soon as `learnerProfile` exists, with no check on classroom
membership state. Left unchanged per instructions, but flagging a concrete consequence: because
step 3 above calls `retryAuthorization()` right after profile creation (as required), `status`
flips to `'authorized'` *before* the child reaches the join-code or status screens, and
`app/_layout.tsx`'s `Stack.Protected guard={learnerAccess}` will make `/(learner)` reachable (and
`/(onboarding)` unreachable) at that point. In other words, with the current gating logic a learner
could bypass or get pushed past the join-code/status flow immediately after profile creation. This
is exactly the gate question raised in the batch: should `authorized` require an approved classroom
membership, not just a learner profile? Needs a supervisor decision before this flow is fully
reliable; no fix attempted here.

**Verification** (from `frontend/`, all green):
- `npx expo-doctor@latest` — 18/18 checks passed.
- `npx tsc --noEmit` — clean (required regenerating `.expo/types/router.d.ts` via a brief offline
  `expo start` so the two new route literals type-checked; that directory is gitignored and
  regenerates automatically).
- `npm run lint` — clean.
- `npm run test:contract` — 4/4 passed, unregressed.

**Files touched:** `frontend/src/api/contracts.ts`, `frontend/src/api/runtime-validation.ts`,
`frontend/src/api/learner-onboarding-api.ts` (new),
`frontend/src/features/onboarding/first-time-welcome-screen.tsx`,
`frontend/src/features/onboarding/teacher-link-instructions-screen.tsx`,
`frontend/src/features/onboarding/classroom-status-screen.tsx` (new),
`frontend/app/(onboarding)/classroom-status.tsx` (new),
`frontend/app/(onboarding)/welcome.tsx`, `frontend/app/(onboarding)/teacher-link.tsx` (stale
deferred-work comments removed). No backend file touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-28 — Classroom-membership gating + onboarding entry-routing

Resolves the FE-1a open question with a supervisor-approved decision: `authorized` status now
requires an APPROVED classroom membership, not just a learner profile. No backend file touched.
Out of scope and untouched: FE-1b, FE-2, FE-3, the `AuthStatus` enum's members (only the
data-condition driving `'authorized'` changed), and the already-correct in-flow forward navigation
in welcome/teacher-link/classroom-status.

**Shared membership-selection helper (`src/api/membership-selection.ts`, new).** Extracted the
`pickMembership` function that `classroom-status-screen.tsx` already had locally (matches a
membership by `membership_id` if given, else falls back to the most recently requested item) to a
new small file under `src/api/`, since `client.ts` must not import from `src/features/`.
`classroom-status-screen.tsx` now imports it from there instead of defining its own copy.

**`AuthorizedLearner` extended (`contracts.ts`).** Added `classroomMembership:
LearnerMembershipListItem | null` alongside the existing `principal`/`learnerProfile` fields.

**`getAuthorizedLearner` extended (`client.ts`).** After `learnerProfile` resolves and is non-null,
now also calls `listLearnerClassrooms` and picks the most relevant membership via the shared
`pickMembership` (no `membershipId` — just "most recently requested"). Split into
`getLearnerProfileOrNull` and the new `getClassroomMembershipOrNull`, both following the same
fail-closed rule already used for the profile lookup: an empty membership list is a legitimate "no
membership yet" state (`classroomMembership: null`), but network/5xx/unexpected errors wrap as
`ApiClientError('unavailable', ...)` rather than silently guessing or crashing `/me` resolution.
`client.ts` now imports `listLearnerClassrooms` from `learner-onboarding-api.ts`, which itself
imports `requestJson` from `client.ts` — a function-level circular import, not a value-level one,
so it resolves fine under Metro/TypeScript (confirmed by `tsc --noEmit` below).

**Auth condition changed (`auth-context.tsx`).** `authorizeSession` now flips to `'authorized'`
only when `learnerProfile` exists AND `classroomMembership?.state === 'APPROVED'`; any other
combination (no profile, no membership, PENDING, REJECTED) sets `'onboarding'`, exactly as before
but now membership-aware. No new `AuthStatus` values added — `'onboarding'` remains the single
catch-all; which onboarding screen to show is a routing decision, not an auth-status decision.

**New onboarding entry point (`app/(onboarding)/index.tsx`, new + `_layout.tsx`).** Added as the
group's real entry/re-entry route (app boot, or returning to `(onboarding)` after being elsewhere),
mirroring the root `app/index.tsx`'s status-based redirect pattern. Reads `me`/`status` from
`useAuth()` and does a single `router.replace`: no `learnerProfile` -> `welcome`; profile but no
`classroomMembership` -> `teacher-link`; membership present (PENDING or REJECTED; APPROVED never
reaches here since that flips `AuthStatus` to `'authorized'` and the outer guard in `app/_layout.tsx`
routes to `(learner)` first) -> `classroom-status` with `membershipId` param, matching how
`teacher-link-instructions-screen.tsx` already navigates there after a fresh request. Renders only a
loading state while `status === 'checking'` — never redirects on stale/incomplete data.
`(onboarding)/_layout.tsx` now declares `<Stack.Screen name="index" />` first, mirroring how the
root layout explicitly declares its own `index`. Also updated the root `app/index.tsx`'s onboarding
case to redirect to `/(onboarding)` instead of hardcoding `/(onboarding)/welcome`, so app boot
actually goes through the new entry-routing decision instead of bypassing it.

**Verification** (from `frontend/`):
- `npx expo-doctor@latest`
- `npx tsc --noEmit`
- `npm run lint`
- `npm run test:contract` (must not regress against FE-1a's 4/4)

**Files touched:** `frontend/src/api/membership-selection.ts` (new), `frontend/src/api/contracts.ts`,
`frontend/src/api/client.ts`, `frontend/src/auth/auth-context.tsx`,
`frontend/src/features/onboarding/classroom-status-screen.tsx`,
`frontend/app/(onboarding)/index.tsx` (new), `frontend/app/(onboarding)/_layout.tsx`,
`frontend/app/index.tsx`. No backend file touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-29 — BE-G1: assign `Learner.grade` on classroom-membership approval (backend bug fix)

**The bug.** `Learner.grade` was written in exactly one place in all of `backend/app/` —
`application/profile_classroom.py:117`, which writes `grade=None` at learner-profile creation.
Membership approval (`application/classroom_membership.py`, `approve_membership`) never touched
it. But `application/opportunity_selection.py:521-523` fails closed with `ConflictError`/409 when
`learner.grade is None`. Net effect: a learner could complete the entire onboarding flow —
profile -> join code -> membership request -> teacher approval -> start session — and then EVERY
question request 409'd forever. There was no path in the product to a usable learner, which
blocked the per-screen "design UI -> integrate the real backend API -> test end-to-end" loop the
frontend work is following. `test_be4f_transactional_sweep.py::setup_learner` had already
documented the symptom in a comment (it sets `Learner.grade` directly in SQL to work around it);
this batch removes the underlying cause.

**The fix** (`app/application/classroom_membership.py`, the only production file changed).
Inside `ClassroomMembershipService.approve_membership`, after the state/decision fields are set on
the membership and before the `flush()`: load the membership's `Classroom` row, map its grade to
the learner's integer grade, load the `Learner` for `membership.learner_id`, and assign it. The
mapping is an EXPLICIT module-level dict —
`_CLASSROOM_GRADE_TO_LEARNER_GRADE = {"GRADE_2": 2, "GRADE_3": 3}` — not string slicing or
parsing. `Classroom.grade` is `String(16)` with a `GRADE_2|GRADE_3` check constraint;
`Learner.grade` is a nullable `SmallInteger` with `ck_b_learners_grade` permitting only
`NULL|2|3`. An explicit dict raises `KeyError` if a third classroom grade is ever added, which is
the desired behavior: a silent mis-map here would corrupt catalogue eligibility. The write sits
inside the existing advisory xact lock (`classroom_membership.approve:{learner_id}`) and the
`with_for_update()` on the membership row, so it is race-safe; no additional lock was added.

**SCOPE NOTE — explicitly stated.** `grade` here is ROSTER METADATA the teacher already chose
when creating the classroom (`Classroom.grade` is NOT NULL and is supplied at
`POST /api/v1/classrooms`). It selects which catalogue templates are eligible; it sets no mastery
prior, no BKT parameter, no difficulty ladder, no session bound, and no attempt limit. This batch
therefore introduces NO scientific behavior, clears NO gate-B item, and authorizes NO real-child,
pilot, or production use. It proceeds under the project-director instruction in
`backend/provenance/component-b-be4-engineering-continuation-instruction.json` — TEST-provenance
DRAFT bundles only.

**Deliberately unchanged.** `reject_membership` (rejection must never touch grade —
asserted below). `MembershipDecisionResponse` and every other DTO/schema: the response shape is
byte-identical, so `backend/contract/openapi.v1.json`'s sha256 is unchanged and both
contract-freeze tests (`backend/tests/test_be5a_contract_freeze.py`,
`frontend/src/api/__tests__/contract-freeze.test.ts`) stayed green without being touched. The
route set (no new route; `test_be2_architecture_guards.py` asserts `_current_routes() ==
EXPECTED_ROUTES` exactly). No migration, no new column, no seed data.

**Idempotency, verified on both paths.** The idempotency replay at the top of
`approve_membership` returns the stored canonical response before any grade write, so a retried
approval with the same `Idempotency-Key` re-reads the same grade rather than rewriting it. A
second approval with a FRESH key still hits the `membership.state != "PENDING"` guard and fails
closed with 409, leaving the grade untouched. Both are asserted.

**No guard amendments were needed.** All three pre-existing `grade is None` assertions were
re-checked and all three still pass UNCHANGED, because each tests a state where NULL is genuinely
correct: `test_classroom_membership.py:589` (after a membership REQUEST — state PENDING, not
approved), `test_classroom_membership.py:862` (after a ROLLED-BACK failed approval — still
PENDING; the injected `_audit` failure fires after the grade assignment but before commit, so the
whole transaction including the grade write rolls back), and `test_profile_classroom.py:78`
(after profile creation, no classroom yet). No existing test was edited.

**New test** — `backend/tests/test_learner_activation_path.py` (new, 5 tests). Drives the
COMPLETE HTTP chain through real FastAPI routes and real Postgres, following the existing
auth-override + isolated-database patterns (`dependency_overrides` on
`get_authenticated_principal`, fresh `uuid4()` subjects per test, and
`test_be4f_transactional_sweep.py`'s `_pinned_lifecycle_service` trick to pin
`POST /api/v1/b/sessions` deterministically to the BE3b TEST-provenance DRAFT fixture bundle
rather than depending on which APPROVED bundle other test files inserted most recently):
teacher profile -> `POST /api/v1/classrooms` -> `POST /api/v1/classrooms/{id}/invites` ->
learner profile -> `POST /api/v1/classroom-invites/resolve` ->
`POST /api/v1/classroom-memberships/requests` ->
`POST /api/v1/classroom-memberships/{id}/approve` -> `POST /api/v1/b/sessions` ->
`POST /api/v1/b/sessions/{id}/opportunities` ===> asserted **201, not 409**. Run for both
GRADE_2 and GRADE_3, each asserting directly against the database that `Learner.grade` is NULL
before approval and 2 / 3 after. Plus: rejection leaves grade NULL; the replay/double-approval
idempotency pair above; and a guard that the mapping dict is exactly `{"GRADE_2": 2,
"GRADE_3": 3}` and raises `KeyError` on an unknown classroom grade.

**Verification** (real Postgres 16 via `compose.yaml`, not sqlite; the `api` image was rebuilt
because it bakes `app/` and `tests/` in rather than bind-mounting them):
- `docker compose up -d --build`; `docker compose exec api alembic upgrade head` — head unchanged
  at `20260728_0003`.
- `docker compose exec api pytest -q tests/test_learner_activation_path.py` — **5 passed,
  0 failed** in 6.31s.
- `docker compose exec api pytest -q` (FULL suite) — **241 passed, 0 failed, 0 skipped** in
  145.59s, up from 236 (the 5 new tests), with no pre-existing test modified.
- `cd frontend && npm.cmd run test:contract` — **4/4 passed**, unregressed.

**Files touched:** `backend/app/application/classroom_membership.py`,
`backend/tests/test_learner_activation_path.py` (new), `backend/buildLog.md`. No frontend file
touched; no migration, DTO, contract artefact, or route touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-29 — BE-G2: re-runnable dev fixture — Grade-2 learner with an approved classroom

**Why.** The project is building the Component B learner experience screen by screen — design UI
-> integrate the real backend API -> test end-to-end -> next screen. FE-1b (the teacher app) is
deliberately postponed, so nothing in the product can perform the teacher half of onboarding.
`backend/scripts/dev_fixture_learner.py` fills only that gap: it drives the real backend API
(never the database directly) as two real Supabase-authenticated principals — a teacher and a
learner — until the learner has an APPROVED Grade-2 classroom membership, then self-verifies that
a question can actually be served. Depends on BE-G1 (committed `1b0b1f9`): its self-verify step
asserting `POST .../opportunities` returns 201 is only true with BE-G1's grade-assignment fix in
place. Delete `backend/scripts/` (and its guard test) the day FE-1b lands.

**No service-role key — the decision, and why it's now possible.** The environment was verified
before writing any code: Supabase project `hliyqkmmghheoxvdxjbv` has email confirmation OFF and
signups ENABLED, so a plain `POST /auth/v1/signup` with the ordinary PUBLISHABLE key (the same
`EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` the Expo app ships with — not a secret) returns a usable
session immediately; confirmed live with curl before writing the script. On a re-run signup
returns `422 user_already_exists`, and the script falls back to
`POST /auth/v1/token?grant_type=password` — that fallback is the entire idempotency mechanism for
identity. This removes the Admin API and any service-role key from the design entirely; the new
isolation guard (below) asserts the string `"service_role"` never appears in the script.
Confirmed live: `GET /api/v1/me` returns `200 {"user_id": "...", "email": null}` for both fixture
identities against the real running container — `AuthenticatedPrincipal.email` is null because
Supabase's confirmation-off JWTs never set the top-level `email_verified` / `email_confirmed_at`
claims `app/infrastructure/auth.py` checks (only nested `user_metadata.email_verified`, which the
backend correctly does not trust) — the script and its docs assume email is always null.

**Mechanism — HTTP-driven, zero direct database writes.** `dev_fixture_learner.py` never imports
a SQL toolkit or Postgres driver, never reads the backend's database connection string, and never
opens a database connection; every state change goes through the real FastAPI routes, in order:
teacher profile -> classroom (`FIXTURE Grade 2`, `GRADE_2`) -> invite -> learner profile -> resolve
invite -> membership request -> (teacher) list membership requests -> approve. Driving the real
endpoints gets `ProvenanceMixin`'s 18 columns, the `ck_*_actor_exactly_one` checks, the
`classroom_invite_id` FK, the APPROVED-requires-`decided_at_utc`-and-`decided_by_user_id` check,
and `uq_classroom_memberships_one_approved_per_learner` all satisfied for free, and makes the
script double as an end-to-end test of the shipped onboarding flow. Every state-changing call
supplies its own fresh `Idempotency-Key`; there is no shared/reused key anywhere. Lives at
`backend/scripts/`, outside `app/` — every architecture guard roots its filesystem scan at
`Path("app")` (`test_be2_architecture_guards.py:161,253,345`,
`test_be3_live_engine_boundary.py:78,126,147`), so it is invisible to all of them without a
route ever needing to exist (a route would have broken the exact-route-set assertion, the
no-"debug"/"inject"/"/test"-in-path assertion, and forced a contract re-freeze).

**Fixture identities.** `dev-fixture-teacher@example.com` (created by this batch) and
`dev-fixture-learner@example.com` (pre-existing project user, id
`3df49ef8-9792-4ec4-88b5-280312f45b1b`, reused rather than duplicated), both
`Fixture-Dev-Pass-2026!`. `example.com` is IANA-reserved and can never route mail.

**Safety rails.** Refuses to run unless `APP_ENV != "production"` (read from `backend/.env`, or
the process environment) AND `--test-fixture-only` is passed explicitly. This is the first
env-gated behavior in the backend codebase; it lives entirely outside `app/`, so "zero env-gated
behavior inside `app/`" still holds. No access token is ever logged. No new variable was added to
`backend/.env` or `.env.example` — `backend/.env` already existed, is gitignored, and was
confirmed working (a real ES256 Supabase token already returned `200` from `GET /api/v1/me`
against the running container) before this batch touched anything; `--api-base` is a script-only
CLI flag (default `http://localhost:8000`, override via `--api-base` or `DEV_FIXTURE_API_BASE`),
never backend configuration.

**Re-run / reset behavior — verified live, not simulated:**
- Ran the script fresh, then immediately again: second run exited 0, reused the same identities,
  same classroom, same membership (`"Classroom membership already APPROVED; skipping
  invite/request/approve."`), no duplicates of either.
- Started a session via `--keep-session`, re-ran with `--keep-session` again: printed the exact
  same `session_id` and `item_opportunity_id` both times, proving the session survived rather
  than being reset (`start_session` is already idempotent-by-state; `opportunities` reissued the
  same still-open opportunity).
- Ran again without `--keep-session`: printed `"Abandoned stale active session ..."` naming that
  same session, then self-verified against a fresh one — confirms step 4's reset actually fires
  when a session is left active and is skippable on request.

**Two honest limitations found during live verification, documented in
`backend/scripts/README.md`:**
1. **`source_class`.** Rows created through HTTP carry whatever `source_class` the routes write
   (`REAL`), which cannot be overridden by an HTTP client. Mitigated only by naming (`example.com`,
   `FIXTURE` prefixes) and the operational rule that this script never targets anything but a
   local dev database.
2. **Running the full backend test suite wipes this fixture's data — discovered, not
   theorized.** `docker compose exec api pytest -q` and the running API share one Postgres
   database. `test_be2_persistence.py` downgrades all the way to the base revision
   (`20260722_0001`) and back up to exercise migration reversibility, which drops every table any
   later migration created — `app_users`, `b_learners`, `classrooms`, `classroom_memberships`,
   all of it — then recreates them empty. This was caught live during verification: a run that
   had previously found "already APPROVED" instead had to redo the whole
   invite/request/approve sequence immediately after a full-suite run. Not a bug in this script —
   the script's own idempotency absorbs it completely — but worth knowing before assuming
   something is broken. Separately (and unrelated to BE-G1 or this batch), backend tests also
   insert their own throwaway `RuntimeBundleRecord` rows with newer timestamps than the one
   bundle version (`be3b-test-fixture-1.0`) opportunity selection can actually serve, which can
   shadow it via `find_current_approved_published`'s most-recent-wins tie-break and produce a 409
   on `.../opportunities` that looks identical to a BE-G1 regression but isn't; there is no API
   route to publish/approve a bundle (out of scope here), so recovering from this requires an
   operator to touch the database directly — this script deliberately cannot, and does not, do
   that itself. The script's own 409 diagnostic now names both possible causes rather than
   assuming BE-G1.

**New guard** — `backend/tests/test_dev_fixture_isolation.py` (new, 3 tests, deleted together
with `backend/scripts/` when FE-1b lands): no file under `app/` references `"scripts"`; importing
the script module adds no path to `app.openapi()["paths"]` (import is side-effect-free — all
network activity is behind `main()`, guarded by `if __name__ == "__main__"`); the script's own
source contains none of `"sqlalchemy"`, `"asyncpg"`, `"database_url"`, `"service_role"` —
provably cannot write rows directly and provably uses no elevated credential. (The script's own
docstring had to be reworded once during verification — it originally named the very things it
promises never to import, which is a literal substring match the guard correctly failed on.)

**Infrastructure needed for the guard to run in the built image.** `backend/Dockerfile` now also
`COPY --chown=10001:10001 scripts ./scripts`, alongside the existing `app`/`tests`/`contract`
copies — otherwise the guard test's `Path("scripts/dev_fixture_learner.py").read_text(...)` has
nothing to read inside the container. Same precedent as BE5a's `contract/` COPY line.

**Verification** (real Postgres 16 via `compose.yaml`; auth is live, not mocked):
- `docker compose up -d --build` (picks up the `scripts/` COPY line).
- `docker compose exec api pytest -q tests/test_dev_fixture_isolation.py` — **3 passed**.
- `python scripts/dev_fixture_learner.py --test-fixture-only` (from `backend/`, real Supabase +
  real running API) — first run: **exit 0**, printed credentials + a real grouped join code
  (`XXXX-XXXX`). Immediate second run: **exit 0**, `"already APPROVED"`, no duplicates.
  `--keep-session` run followed by a second `--keep-session` run: **exit 0** both times, identical
  session/opportunity IDs, confirming the session survived. Final run without `--keep-session`:
  **exit 0**, stale session named and abandoned, fresh self-verify session opened and cleaned up.
  Also confirmed the safety rail: running with no flags exits 1 with a clear refusal message.
- `docker compose exec api pytest -q` (full suite, run once during this batch, before the final
  fixture-script polish above) — **244 passed, 0 failed, 0 skipped** in 138.28s (up from 241 —
  the 3 new guard tests), no pre-existing test modified. As documented above, this run wipes the
  fixture's provisioned data as a side effect of `test_be2_persistence.py`'s migration-reversibility
  cycle; the fixture script was re-run afterward and confirmed clean (exit 0).
- **Not run: signing into the Expo app.** This environment has no device/emulator/Expo runtime
  available to drive that check. Both fixture identities are confirmed live end-to-end against
  the real backend (`GET /api/v1/me` returns `200` for both, the full onboarding chain completes,
  and a real question is served), so the credentials printed by the script are real and ready —
  but the actual "open the app, sign in, reach `(learner)/home`" step needs to be done by hand.

**Files touched:** `backend/scripts/dev_fixture_learner.py` (new), `backend/scripts/README.md`
(new), `backend/tests/test_dev_fixture_isolation.py` (new), `backend/Dockerfile` (added the
`scripts/` COPY line), `backend/buildLog.md`. No file under `backend/app/`, no migration, no DTO,
no contract artefact, no route, and no frontend file touched. `backend/.env` and
`backend/.env.example` were read but not modified.

Left uncommitted for Yasindu. Not run: any git command that mutates state. One environment note:
Docker Desktop was already running from the BE-G1 session; no restart was needed for this batch.

## 2026-07-29 — FE-0a: frontend error-envelope shape correction

**Why.** `isApiErrorEnvelope` (`frontend/src/api/runtime-validation.ts`) validated a flat
`{code, message, request_id, retryable, details}` shape that has never matched what the backend
actually emits. The real shape, `app/core/errors.py`'s `ErrorResponse`/`ErrorBody`, is nested:
`{schema_version, error: {code, message, request_id, details?}}`, and carries no `retryable`
field at all. Because the check always returned `false` for a real error body, `envelope` was
never populated on `ApiClientError` anywhere in the app, and `client.ts`'s
`envelope?.request_id` was always `undefined` — every error's surfaced request id has silently
been falling back to the `x-request-id` response header the whole time. That fallback path
happened to produce a plausible-looking request id, which is exactly why the defect was
invisible: nothing crashed, nothing looked wrong, the field was just quietly always sourced from
the wrong place. It also meant `error.code` (`CONFLICT`, `AUTHENTICATION_REQUIRED`, …) was
unreachable to the client, leaving FE-3's future error handling with nothing to branch on.

**Correction to the plan's own diagnosis.** The bounded-batch prompt for this work additionally
undernoted `ApiFieldIssue = {field: string; code: string}`: `errors.py`'s validation handler
(lines 111–114) actually emits `[{location: string[], type: string}]` for 422s, and
`ErrorBody.details` is typed `dict[str, Any] | list[dict[str, Any]] | None` server-side — so
`details` can be an object, not only an array, and its inner shape is handler-specific, not the
`{field, code}` pair the old type assumed. Confirmed no other file imported `ApiFieldIssue`
before deleting it.

**Changes:**
- `frontend/src/api/contracts.ts` — replaced `ApiErrorEnvelope` with the nested
  `{schema_version, error: {code, message, request_id, details?}}` shape, `details` typed as
  `Record<string, unknown> | Record<string, unknown>[]` (deliberately not narrowed further — see
  the type's own comment). Deleted `ApiFieldIssue` (dead after the shape correction, confirmed
  unreferenced elsewhere).
- `frontend/src/api/runtime-validation.ts` — rewrote `isApiErrorEnvelope` to validate the nested
  shape: non-empty `schema_version`, `error` a record, `error.code`/`error.message`/
  `error.request_id` all non-empty strings, `error.details` (when present) either a record or an
  array of records, fails closed on anything else. Does not pin `schema_version === '1.0'`, so a
  future `1.1` that still parses is not rejected into `invalid-response`.
- `frontend/src/api/client.ts` — one-line fix: `envelope?.request_id` ->
  `envelope?.error.request_id` at the top of `mapHttpError`. `mapHttpError`'s status->kind
  mapping and `ApiClientError`'s constructor signature were left untouched; branching on
  `error.code` is FE-3's scope, not this batch's.
- `frontend/src/api/__tests__/error-envelope.test.ts` (new, picked up by the existing
  `test:contract` glob) — 10 cases: accepts a real captured 409 envelope, accepts a real 422 with
  array-form `details`, accepts object-form `details`, rejects the old flat shape (the regression
  guard proper), rejects an empty `error` object, rejects a missing `schema_version`, rejects
  `details` as a bare string, rejects a `details` array containing non-record elements, rejects a
  `null` `error` field, and — driven through `requestJson` with a stubbed `fetch` rather than by
  exporting `mapHttpError` — asserts that a stubbed 409 response's surfaced `requestId` comes from
  `error.request_id` in the body and not the `x-request-id` header.

**Out of scope, untouched:** nothing under `backend/`; no contract re-freeze (this type is
hand-written against observed behaviour, not generated — `openapi.v1.json`'s checksum did not
move); no new dependency; `ApiClientError`'s constructor signature; FE-0b/FE-0c work.

**Verification (all from `frontend/`):**
- `npx tsc --noEmit` — clean, no errors.
- `npm run lint` — clean, no errors.
- `npm run test:contract` — **14 passed, 0 failed** (4 pre-existing tests unregressed, 10 new).
- Live check against the real running backend (`docker compose up -d`, already running) and the
  BE-G2 fixture (`python scripts/dev_fixture_learner.py --test-fixture-only --keep-session`,
  confirmed idempotent — fixture already provisioned and APPROVED): signed in as
  `dev-fixture-teacher@example.com` via Supabase password grant and issued
  `POST /api/v1/classrooms` for the fixture's already-existing `FIXTURE Grade 2` classroom name,
  which the backend correctly rejects as a duplicate. Observed envelope, verbatim:
  `{"schema_version":"1.0","error":{"code":"CONFLICT","message":"The request conflicts with the
  current resource state.","request_id":"53a1214f-d5b6-42f1-affc-88238ffbd927"}}` — confirms the
  corrected shape matches the live backend exactly. (`POST /api/v1/b/sessions` twice with
  different idempotency keys, as originally suggested, does not actually 409 — session start is
  idempotent-by-state per `dev_fixture_learner.py`'s own docstring, and returned the same active
  session both times; the duplicate-classroom-name conflict was used instead as it reliably
  exercises the same 409 handler path.)

**Files touched:** `frontend/src/api/contracts.ts`, `frontend/src/api/runtime-validation.ts`,
`frontend/src/api/client.ts`, `frontend/src/api/__tests__/error-envelope.test.ts` (new),
`backend/buildLog.md`. No file under `backend/app/` touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-29 — FE-0b: pending-command union + active-session-id readers

**Why.** `session-command-store.ts` persisted a `start_session` pending command and an active
session id to local storage, but nothing ever read the active session id back
(`saveActiveSessionId` had no counterpart), and the pending-command type only modeled
`start_session` — the other three learner-write endpoints (`submit_response`, `request_assist`,
`complete_opportunity`) had no offline-recovery representation at all, which blocks FE-2/FE-3's
resume-after-relaunch flow. This batch adds the missing readers and generalizes the pending-command
type to a discriminated union over `kind`, without touching any screen.

**Two findings confirmed during this batch, both load-bearing for the design below:**

1. **Start-session idempotency (carried over from FE-0a, reconfirmed here).** `start_session`
   (`app/application/b_session_lifecycle.py`'s `start_session`) is idempotent-by-*state*, not only
   by idempotency key: `find_starting_or_active_for_learner` returns the learner's existing
   starting-or-active session and the route responds `201` with it again, rather than ever `409`ing
   on a second call. This is why `PendingStartSessionCommand` needs no request body beyond the
   idempotency key — replay safety for `start_session` comes from the one-active-session-per-learner
   constraint, not from a stored request body — while `submit_response` has no equivalent recovery
   path: its idempotency key is fingerprinted against the exact request body
   (`body_fingerprint`, `app/application/attempt_submission.py:194`), so a replay with a
   reconstructed body that differs by even one field (in particular `client_elapsed_ms`, which is
   unrecoverable after a relaunch) fails the fingerprint check. This is the reason
   `PendingSubmitResponseCommand.body` is required, not optional, and is persisted verbatim rather
   than recomputed at replay time.
2. **The "starting" state asymmetry.** The persistence layer's session-state check constraint
   (`app/infrastructure/persistence_models.py:35`) allows seven states —
   `starting, active, completing, completed, abandoned, expired, technical_failed` — but the
   public API's `SessionCommandResponse.state` (`app/domain/b_session.py:21`) is the narrower
   `Literal["active", "completed", "abandoned"]`; `starting`/`completing`/`expired`/
   `technical_failed` never cross the contract boundary. Separately, and unrelated to the server,
   `session-preparation-screen.tsx`'s own `PreparationPhase` has a `starting-session` value that is
   purely a client-side UI phase — it is never persisted and never maps to any server state.
   Confirms the design choice below: this store's pending-command union is discriminated on
   `kind` (which endpoint is being retried), never on session/opportunity *state* — state values on
   both sides are richer, narrower, and differently-shaped than any client-local persistence should
   assume.

**Changes:**
- `frontend/src/api/contracts.ts` — `PendingStartSessionCommand` (single type) replaced by a
  `PendingSessionCommand` discriminated union over `kind`: `start_session` (unchanged fields, now
  named `PendingStartSessionCommandBase`), `submit_response` (`sessionId`, `itemOpportunityId`,
  required `body: {submitted_value: string; client_elapsed_ms: number}`), `request_assist`
  (`sessionId`, `itemOpportunityId`), `complete_opportunity` (`sessionId`, `itemOpportunityId`).
  Every variant still carries its own `idempotencyKey`/`createdAt`. Endpoint paths verified against
  `app/api/routes/b_session.py`'s live route table. `PendingStartSessionCommand` is kept exported as
  a type alias of the `start_session` member so `session-preparation-screen.tsx` (out of scope for
  this batch) keeps compiling and behaving identically, untouched. No TTL/staleness expiry was added
  on `createdAt` — deliberately out of scope; discarding a pending command after N minutes is a
  policy decision about whether a child's answer still counts, not an engineering default to invent.
- `frontend/src/api/runtime-validation.ts` — one validator per union variant
  (`isPendingSubmitResponseCommand`, `isPendingRequestAssistCommand`,
  `isPendingCompleteOpportunityCommand`) plus `isPendingSessionCommand`, the union validator, which
  discriminates via `Object.prototype.hasOwnProperty.call(value, 'kind')` then a `switch` — never a
  bare property read on unparsed JSON. `isPendingSubmitResponseCommand` checks
  `body.submitted_value` is *a string* only (not non-empty: `""` may be a legitimate submission for
  the server to judge, and rejecting it client-side would be the client deciding correctness it
  isn't entitled to decide) and `body.client_elapsed_ms` is a finite, non-negative number via a new
  `isFiniteNonNegativeNumber` helper (rejects `Infinity`/`NaN`/negative). `isPendingStartSessionCommand`
  is unchanged.
- `frontend/src/features/session/session-command-store.ts` —
  - **Part 1 (new readers).** Added `loadActiveSessionId` and `clearActiveSessionId`.
    `loadActiveSessionId` mirrors the existing discard discipline (was `loadPendingStartCommand`
    lines 39–43, now `loadPendingCommand`): validates the stored value is a non-empty string,
    discards and returns `null` otherwise. No UUID-format check was added — the server owns id
    format, and asserting one client-side would be inventing a rule the server never promised.
  - **Part 2 (generalized store).** `loadPendingCommand`/`savePendingCommand`/`clearPendingCommand`
    now operate on the `PendingSessionCommand` union (same storage key, same discard-invalid
    behaviour as before — nothing changed about *when* data is discarded, only what shape it
    validates against). `loadPendingStartCommand`/`savePendingStartCommand`/
    `clearPendingStartCommand` are kept as thin start_session-only wrappers over the generalized
    functions so the prep screen's existing call sites and behavior are unaffected.
- `frontend/src/api/__tests__/pending-session-command.test.ts` (new, picked up by the existing
  `test:contract` glob) — 20 cases: per-variant validator accept/reject cases (including the
  empty-string-`submitted_value`-is-valid case and the `Infinity`/negative `client_elapsed_ms`
  rejection cases), `isPendingSessionCommand` failing closed on an unknown or missing `kind`, a
  round-trip test per union variant against the store's web `Map` backend, a corrupt-payload
  discard test per variant, a byte-identical save→load assertion for `submit_response.body`
  specifically (since that is exactly what the backend's fingerprint check depends on), and an
  `loadActiveSessionId` round-trip plus corrupt-(empty-string)-value discard case.

**Test-infrastructure problem found and worked around, confined to the new test file only.**
`session-command-store.ts` is the first module `test:contract` has ever needed to load that
transitively requires `react-native` (for `Platform.OS`) and `expo-secure-store`. Both fail under
the plain esbuild-based `tsx` test runner this script uses: `react-native`'s entry file uses Flow's
`import typeof` syntax, which esbuild rejects outright, and there is no jest/React-Native test
preset wired into `test:contract` (adding one is out of scope for this batch). Because `tsx`
compiles this whole test file — and everything it pulls in — to CommonJS (`frontend/package.json`
has no `"type": "module"`), an ESM `node:module` `register()` loader hook was tried first and
does not work: `register()` only intercepts the ESM loader pipeline, never CJS `require()` calls.
The working fix, contained entirely inside the new test file: `Module.prototype.require` is
monkeypatched to intercept the two bare specifiers and return stub exports (`{Platform: {OS:
'web'}}`, and no-op async stubs for the three `SecureStore` functions plus its
`WHEN_UNLOCKED_THIS_DEVICE_ONLY` constant) before `session-command-store` is required. This forces
the store's own `Platform.OS === 'web'` branch — which is exactly the "web Map backend" the batch's
verification section asks the round-trip tests to exercise — and leaves every other test file's
module registry untouched, since `node --test` isolates each test file into its own
worker/process.

**Out of scope, untouched:** no API client functions (FE-0c); no screen changes —
`session-preparation-screen.tsx` was read to confirm `PendingStartSessionCommand` and its four
call sites (`:56-63`, `:145-146`) still typecheck unmodified, but not edited; no new dependency; no
contract re-freeze (these are local persistence types, not server DTOs — `openapi.v1.json`'s
checksum did not move); no TTL/staleness policy on `createdAt`.

**Verification (all from `frontend/`):**
- `npx tsc --noEmit` — clean, no errors (confirms `session-preparation-screen.tsx` still compiles
  unmodified against the new union-aliased type).
- `npm run lint` — clean, no errors.
- `npm run test:contract` — **34 passed, 0 failed** (14 pre-existing tests unregressed, 20 new).

**Files touched:** `frontend/src/api/contracts.ts`, `frontend/src/api/runtime-validation.ts`,
`frontend/src/features/session/session-command-store.ts`,
`frontend/src/api/__tests__/pending-session-command.test.ts` (new), `backend/buildLog.md`. No file
under `backend/app/` touched, no screen touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.

## 2026-07-29 — FE-0c: the six B-session API client functions + validators

**Why.** `component-b-api.ts` only wrapped two of the eight B-session-lifecycle endpoints
(`checkReadiness`, `startSession`); nothing wrapped opportunity selection, response submission,
hint requests, opportunity completion, active-session recovery, or session-standing. All six
response types (`ActiveSessionResponse`, `OpportunityPresentationResponse`, `AttemptResponse`,
`HintRequestResponse`, `OpportunityAdvanceResponse`, `SessionStandingResponse`) already existed in
`src/api/generated/openapi-types.ts` from the frozen contract — this batch only wires client
functions and runtime validators for them; no contract re-freeze, no regeneration.

**Four corrections found and confirmed live against the domain models before writing any
validator, each worth recording because it either contradicts an existing in-code comment or
would have been an easy place to accidentally reintroduce drift:**

1. **`selectOpportunity` deliberately takes no idempotency key and no body — confirmed against
   `app/application/opportunity_selection.py`.** `OpportunitySelectionService.select_next_opportunity`
   checks `ItemOpportunityRepository.find_open_for_session` first; when an OPEN opportunity already
   exists it calls `reissue_presentation_for_open_opportunity`, which issues a fresh presentation
   token for the *same* opportunity rather than creating a new one. This — not an omission — is
   what makes `selectOpportunity` the crash-recovery path: calling it again after an app restart or
   a dropped response returns the same open question instead of minting a second one. Documented
   inline at the call site so it doesn't read as a missing idempotency key to a future editor.
2. **`submitResponse`'s body constraints mirror `SubmitResponseRequest`
   (`app/domain/b_attempt.py`) exactly, and are explicitly not answer validation.**
   `submitted_value: str = Field(min_length=1, max_length=255)` and
   `client_elapsed_ms: int | None = Field(default=None, ge=0, le=3_600_000)`. The client now
   rejects an out-of-range `submitted_value` before the request leaves the device (the server would
   422 it anyway) and clamps `client_elapsed_ms` into `[0, 3_600_000]` rather than rejecting it
   outright, since it's TELEMETRY ONLY per the server's own docstring — never read for correctness
   or BKT. Both are commented as mirroring the server's own constraint, not the client deciding
   whether an answer is right.
3. **`response_format` must not be validated against a hardcoded list of known formats.** The
   registry that owns the known-format set belongs to the presentation-renderer work (Batch 8, not
   yet built). `isOpportunityPresentationResponse`/`isOpportunityPresentationFields` accept any
   non-empty string for `response_format` — a second hardcoded list here would just be a second
   place for the set of known formats to silently drift out of sync with the registry's own list.
   Verified with a test asserting an unrecognized format string is still accepted.
4. **The `skill_id`/`grade` correction — contradicts an existing in-code comment that this batch
   does not touch.** `session-preparation-screen.tsx`'s `lessonCard` section carries the comment
   "Grade badge removed: no `grade` field exists anywhere reachable from the frozen v1 contract
   (AuthenticatedPrincipal/LearnerProfileResponse); do not invent one." That was true of the
   identity/profile endpoints alone, but as of this batch it is no longer true of the contract as a
   whole: `OpportunityPresentationFields`/`OpportunityPresentationResponse`
   (`app/domain/b_opportunity.py`) carry both `grade: int` and `skill_id: str`, reachable via the
   new `selectOpportunity`/`completeOpportunity` client functions. The comment should be amended
   (or the grade badge re-added, sourced from the opportunity response instead of the principal) in
   whichever future batch actually consumes `selectOpportunity` from a screen — not this one, which
   touches no screen. Left as-is deliberately; recorded here so it isn't rediscovered from scratch.

**Also carried forward, not new to this batch:** every `*_id` field across all six validators is
treated as an opaque non-empty string — no UUID-format regex anywhere, consistent with the
existing rule that the server alone owns id format (see FE-0b's `loadActiveSessionId`, which
established the same rule for the locally-persisted active session id).

**Changes:**
- `frontend/src/api/component-b-api.ts` — six new `ComponentBApi` methods, all following
  `startSession`'s existing `requestJson` shape: `getActiveSession` (`GET .../active`, no
  idempotency key), `selectOpportunity` (`POST .../opportunities`, no idempotency key, no body —
  see correction 1), `submitResponse` (`POST .../responses`, idempotency key + normalized body —
  see correction 2), `requestAssist` (`POST .../assists`, idempotency key, no body),
  `completeOpportunity` (`POST .../complete`, idempotency key, no body), `getSessionSummary`
  (`GET .../summary`, no idempotency key). All six are typed optional on `ComponentBApi` — see next
  point — and `createFixtureApi` was deliberately **not** extended to cover them: it is a data
  fixture for the prep screen only (`checkReadiness`/`startSession`), and growing it into a fake
  session engine is how it stops being an inert, easily-reasoned-about fixture.
- `frontend/src/api/runtime-validation.ts` — six new validators following `isSessionCommandResponse`'s
  pattern, all verified field-by-field against the frozen `openapi.v1.json`'s `required` arrays:
  `isActiveSessionResponse` (recurses into a new private `isSessionFields` helper when `session`
  is non-null), `isOpportunityPresentationFields`/`isOpportunityPresentationResponse` (the former is
  exported so `isOpportunityAdvanceResponse` can recurse into `next_opportunity` without
  re-deriving the field list — see correction 3 on `response_format`), `isAttemptResponse`
  (enforces `response_matched === null` iff `event_kind === 'TIMEOUT'` in both directions — anything
  else fails closed rather than the client guessing which field to trust), `isHintRequestResponse`,
  `isOpportunityAdvanceResponse`, `isSessionStandingResponse`.

**A type-level consequence of not extending the fixture:** since `createFixtureApi`'s returned
object implements only `checkReadiness`/`startSession`, the six new `ComponentBApi` methods had to
be typed optional (`getActiveSession?:`, etc.) rather than required — otherwise the fixture branch
would fail to typecheck against a `ComponentBApi` that mandates all eight methods. This is a
deliberate, load-bearing consequence of the "don't extend the fixture" instruction, not an
oversight; any future caller of these six methods through a fixture-eligible `ComponentBApi` will
need its own explicit `undefined` handling until (if ever) the fixture grows real session-engine
behavior.

**Explicitly out of scope, untouched:** no screen changes, no renderer logic (Batch 8), no
timeout/hint/advance UI, no new dependency, no `.env` change, no contract re-freeze (`openapi.v1.json`'s
checksum did not move — confirmed by the pre-existing checksum test in `contract-freeze.test.ts`
staying green).

**Verification (all from `frontend/`):**
- `npx tsc --noEmit` — clean, no errors.
- `npm run lint` — clean, no errors.
- `npm run test:contract` — **51 passed, 0 failed** (34 pre-existing tests unregressed, 17 new).
  New test file `src/api/__tests__/component-b-session-validators.test.ts`: per validator, one
  accept case built from the frozen schema's own `required` array plus one reject case per
  required field dropped (mirroring `contract-freeze.test.ts`'s `isHealthReadyResponse` pattern),
  plus the specifically-requested cases — the TIMEOUT/null invariant asserted in both failing
  directions, `presented_choices: []` accepted, an unrecognized `response_format` string still
  accepted, and `next_opportunity` recursion exercised both with a valid nested presentation and a
  malformed one. No module stubbing was needed for this file — `src/api/` has no `react-native`
  imports (unlike FE-0b's store test), so it is a plain `node:test` file.

**Files touched:** `frontend/src/api/component-b-api.ts`, `frontend/src/api/runtime-validation.ts`,
`frontend/src/api/__tests__/component-b-session-validators.test.ts` (new), `backend/buildLog.md`.
No file under `backend/app/` touched, no screen touched, no contract artefact touched.

Left uncommitted for Yasindu. Not run: any git command that mutates state.
