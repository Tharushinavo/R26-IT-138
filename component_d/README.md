# component_d — cognitive skill profiling for Component D (research material)

*Synthetic, literature-informed material — not clinical evidence. The live profile is a
**rule-based heuristic**, not a trained model, and no trained model exists.*

This folder holds the **research material** for Component D's cognitive skill profiling: the
dataset it was going to be trained from, the guide describing how to generate more of it, and a
place for notebooks. Modelled on `..\component_c_rl\`.

**There is no training code here, and that is deliberate.** compD shipped none — see
[What does not exist](#what-does-not-exist). The feature code that actually runs lives in the host
backend, and its tests live in the **host test suite**, where the code runs:

| what runs in production | where it lives | tested by |
|---|---|---|
| feature computation | `..\backend\app\application\d_features.py` | `..\backend\tests\test_d2_component_d_api.py` |
| the four level heuristics + confidence | `..\backend\app\application\d_rule_profile.py` | same |
| the bilingual recommendation text | `..\backend\app\application\d_recommendation.py` | same |
| the six routes | `..\backend\app\api\routes\d_profile.py` | same |
| the three tables | `..\backend\migrations\versions\20261021_0010_component_d_tables.py` | `..\backend\tests\test_d1_component_d_tables.py` |

Governed by the **Component D authorization** (owner decision **D-011**, 2026-10-21) and the API
contract at v5 (LIVE).

## Layout

| path | purpose |
|---|---|
| `cognitive_dataset.csv` | the seed dataset as received from compD, **copied byte-for-byte** |
| `DATASET_GUIDE.md` | compD's own generation guide, **copied byte-for-byte and not corrected** |
| `notebooks\` | placeholder; nothing here yet |
| `manifest.json`, `BUILDLOG.md` | provenance; the build log is append-only |
| `.gitignore` | deny-then-allow, so only the deliverables are tracked |

`DATASET_GUIDE.md` is reproduced **unaltered**, including the parts that are wrong (below). It is
received material and the record of what was handed over is more useful than a tidied version.
Every correction is recorded here and in `BUILDLOG.md` instead.

## What does not exist

Stated plainly, because the opposite is easy to assume from reading compD's code:

- **No trained model.** compD's `MODEL_PATH` points at `./app/ml/cognitive_model.pkl`. **That
  directory does not exist** anywhere in the handover, and no `.pkl`, `.joblib` or `.parquet`
  artefact exists either. Every profile compD ever produced came from its rule-based fallback.
- **No training code.** The host port carries none. scikit-learn, pandas, numpy and joblib are all
  forbidden until a trained model exists (plan v5), so the ML path was not ported, stubbed or
  feature-switched — it is simply absent. `model_version` is `"rule-based-v1"` and nothing else
  can produce a profile.
- **No notebooks.** The folder is a placeholder. Unlike `component_c_rl`, there is nothing to run.

## Four things wrong with the dataset, which a reader needs before using it

Measured against the file in this folder, not inherited from the guide's claims.

### 1. It is a sample, not a training set

75 rows across 15 students. `DATASET_GUIDE.md` asks for **3,000–5,000 rows across 150–200
students** — so the file falls short of its own guide by roughly fortyfold. It is a shape example.

### 2. Its topics do not match the ones the app serves

| source | topics |
|---|---|
| `cognitive_dataset.csv` | Addition, Counting, **Number Comparison**, Subtraction |
| compD's own question bank (`client\src\data\questionBank.ts`) | Addition, Counting, **Division**, Subtraction |
| the host's CHECK constraint and the API contract | Counting, Addition, Subtraction, **Division** |

The dataset is the odd one out, against compD's own app. A model trained on this file would have
learned a topic the app never serves (`Number Comparison`) and would never have seen the one it
does (`Division`). **The dataset must be regenerated before it can train anything for this app.**
This is not a host/compD disagreement — the host adopted compD's question bank vocabulary exactly.

### 3. Its label case does not match the API

The dataset writes `High` / `Medium` / `Low`; the API and the database use `low` / `medium` /
`high`. `label_processing_speed` happens to agree already (`Slow` / `Moderate` / `Fast`). Any
training pipeline needs to fold case on three of the four targets.

### 4. Its column names are the pre-authorization ones

`is_correct` and `hint_used` are in the header. D-011 A4 renamed those to **`response_matched`**
and **`assist_used`** for the host's database and public API, because the originals collide with
the host's prohibited-term guards. They are left as-is here: this is a received data file, and the
guards read database column names and public schema field names, not CSV headers. **A training
pipeline must map them**, and whatever it produces must emit the host's names.

## The shape mismatch B2 will have to resolve

The dataset and the live code disagree about what a prediction is made from, and nothing in the
handover reconciles them:

- **The dataset is per-interaction.** One row is one question, with ten feature columns, and
  carries the four labels on every row. It trains a model that classifies a single question.
- **The live profile is per-run.** `d_features.compute_features` aggregates a whole run into eight
  derived features (`accuracy`, `avg_response_time_ms`, `response_time_std_ms`, `avg_attempts`,
  `retry_rate`, `hint_rate`, `mean_clicks_per_question`, `total_questions`) and the heuristic reads
  those.

compD had both shapes in its code (`_predict_per_interaction` plus majority voting, and a
student-level pipeline) and never settled which was authoritative. Whoever picks up B2 decides
this; it is not decided here.

## Known weaknesses in the live heuristic

Recorded here because this is the research folder, and because the authorization approved
**storing what the heuristic produces** — never the heuristic itself:

- **`attention_level` is derived partly from click volume.** A child on a touch screen that
  registers stray taps, or one who simply likes tapping, scores lower on "attention" for reasons
  that have nothing to do with attending.
- **The click term carries an unexplained normaliser.** compD divided mean clicks per question by
  the number of questions in the run. The division is load-bearing — without it the term saturates
  and nearly every child scores "low" attention — but nothing documents why run length is the right
  scale. Preserved exactly as compD had it, and flagged.
- **The Sinhala recommendation text has never been reviewed by anyone who reads Sinhala.** It was
  extracted from compD's source by script rather than retyped, so it is faithful to what was handed
  over — which is not the same as correct.

## Standing rules

- Nothing here runs with real children.
- `..\backend\` is the only place Component D code executes. This folder is material, not a service.
- `BUILDLOG.md` is append-only.
