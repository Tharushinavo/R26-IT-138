# component_d — build log

**Append-only.** Newest entry at the bottom. Never edit or delete an earlier entry; if something
recorded here turns out to be wrong, say so in a new entry.

---

## 2026-10-21 — D4: the research folder created (plan v5 Phase 4)

Created `Upadya\Dev\component_d\`, modelled on `..\component_c_rl\`, under the Component D
authorization (owner decision **D-011**).

### What is here

| file | origin |
|---|---|
| `cognitive_dataset.csv` | copied **byte-for-byte** from `compD\...\server\data\`, verified with `cmp` · sha256 `0fa37abb…f526bc` · 6,444 bytes · 75 data rows |
| `DATASET_GUIDE.md` | copied **byte-for-byte**, verified with `cmp` · sha256 `1e9b506d…17d0f071` · 7,491 bytes · **not corrected** |
| `README.md`, `manifest.json`, `BUILDLOG.md` | written for this folder |
| `notebooks\README.md` | placeholder; nothing to run |
| `.gitignore` | deny-then-allow, nested |

The guide is reproduced **unaltered, including the parts that are wrong.** It is received material,
and the record of what was handed over is worth more than a tidied copy. Every correction is in
`README.md` and in this entry instead.

### No training code, and no model — verified, not assumed

- `MODEL_PATH=./app/ml/cognitive_model.pkl` in compD's `server\.env`. **That directory does not
  exist** anywhere in the handover. A search of the whole compD tree for `*.pkl`, `*.joblib` and
  `*.parquet` (excluding `.venv`) returns **nothing**. So every profile compD ever produced came
  from its rule-based fallback, and the trained-model branch in `model.py` was never once taken in
  anger.
- Consequently nothing was ported: scikit-learn, pandas, numpy and joblib are forbidden until a
  trained model exists (plan v5), and `model_version` is `"rule-based-v1"` with no other
  possibility. The ML path is **absent**, not stubbed or feature-switched — there is no dormant
  branch to mistake for a working one.
- `notebooks\` is therefore empty. Unlike `component_c_rl`, there is nothing to execute.

### Four defects found in the dataset, measured

Counted from the file in this folder rather than taken from the guide's claims.

1. **It is a sample, not a training set.** 75 rows, 15 students. The guide's own target is
   3,000–5,000 rows across 150–200 students — short by roughly fortyfold.

2. **Its topics do not match the ones the app serves.** This is the one that would have wasted real
   training time:

   | source | topics |
   |---|---|
   | `cognitive_dataset.csv` | Addition, Counting, **Number Comparison**, Subtraction |
   | compD's own question bank | Addition, Counting, **Division**, Subtraction |
   | the host CHECK + the API contract | Counting, Addition, Subtraction, **Division** |

   A model trained on this file would have learned a topic the app never serves and never seen the
   one it does. **The dataset must be regenerated before it can train anything for this app.**
   Note where the fault is not: the host adopted compD's question-bank vocabulary exactly, so this
   is an inconsistency inside compD's own material.

3. **Label case disagrees with the API.** The dataset writes `High`/`Medium`/`Low`; the API and
   database use `low`/`medium`/`high`. `label_processing_speed` already agrees
   (`Slow`/`Moderate`/`Fast`). Three of the four targets need case folding.

4. **Column names predate the authorization.** The header carries `is_correct` and `hint_used`,
   which D-011 A4 renamed to `response_matched` and `assist_used`. Left as-is deliberately: this is
   a received data file, and the host's guards read database column names and public schema field
   names, **not CSV headers** — so nothing here can trip them. A training pipeline must map them,
   and whatever it produces must emit the host's names.

### One unresolved question handed forward, not answered here

The dataset is **per-interaction** (one row per question, ten feature columns, the four labels
repeated on every row). The live profile is **per-run**, over eight aggregated features
(`accuracy`, `avg_response_time_ms`, `response_time_std_ms`, `avg_attempts`, `retry_rate`,
`hint_rate`, `mean_clicks_per_question`, `total_questions`). compD's code contained **both** shapes
— `_predict_per_interaction` with majority voting, and a student-level pipeline — and never settled
which was authoritative.

That choice belongs to whoever picks up B2, and belongs written down in their NB00 rather than
discovered later from the code. It is not decided here.

### Why this folder needs its own `.gitignore`

The repository root's `.gitignore` ignores `*.md` wholesale and re-includes a named allow-list
("Markdown documentation is local-only except the three approved README files"), and
`cognitive_dataset.csv` matches no root allow-list either. Without a nested file, **every document
in this folder would be silently untracked.**

`component_c_rl` solved the same problem the same way, with its own nested `.gitignore` rather than
by extending the root's allow-list, so this follows that precedent. Verified rather than assumed —
`git status --untracked-files=all component_d/` lists all five files.

This also resolves the Phase 0.6 concern I raised in BE-000: the plan proposed a root rule
`!/component_d/**/*.md`, which would have tracked the documents and **silently dropped
`cognitive_dataset.csv`**, the one file in here that is actually data. No root `.gitignore` change
is needed now, and none was made.

Model artefacts (`*.pkl`, `*.joblib`, `*.onnx`) are explicitly **not** tracked. None exists; if B2
ever produces one, publishing it should be a decision with its own approval rather than a side
effect of someone dropping a file in this folder.

### Not verified, and not claimed

- Nothing in this folder was executed. There is nothing here to execute.
- The dataset's **contents** were not validated beyond the column domains, the row count and the
  student count reported above. Whether its 75 rows are internally plausible — whether a student
  labelled `High`/`High`/`High`/`Fast` actually behaves that way across their rows — has not been
  checked.
- The guide's synthetic-generation rules (its Profile A–D ranges) were **not** checked against the
  dataset. The dataset may or may not have been generated by them.
- The Sinhala recommendation text is unreviewed by anyone who reads Sinhala. Repeated here because
  this is where the research material lives.
- No claim is made that the heuristic is correct. The authorization approved storing what it
  produces, never the heuristic itself; `README.md` lists its known weaknesses.
