# notebooks — placeholder

**Empty on purpose.** Component D ships no training code and no trained model, so there is nothing
to run here yet. See `..\README.md`, "What does not exist".

If and when a model is built (plan v5 calls this **B2**), the notebooks belong here, numbered the
way `..\..\component_c_rl\notebooks\` numbers them (`NB00_`, `NB01_`, ...), with their figures,
tables and reports under `outputs\` prefixed by notebook number.

Two things to settle **before** writing the first notebook, both from `..\README.md`:

1. **The dataset cannot train a model for this app as it stands.** Its topics disagree with the
   ones the app actually serves -- it has `Number Comparison`, which the app never serves, and
   lacks `Division`, which it does. Regenerate first.
2. **Decide what a prediction is made from.** The dataset is per-interaction; the live profile is
   per-run over eight aggregated features. compD had both and never settled which was
   authoritative. That choice belongs in NB00, written down, not discovered later from the code.
