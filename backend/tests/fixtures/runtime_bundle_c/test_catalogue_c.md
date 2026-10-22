# TEST-FIXTURE-ONLY Component C Game-Task Catalogue

This file is a minimal, non-authoritative catalogue used only to exercise Component C's
`catalogue.loader`/checksum machinery and the C runtime-bundle chain (Phase 2). It is **not**
the governed R26-IT-138 Component C Game-Task Catalogue (which remains **PROPOSED FOR
APPROVAL** with open `CALIBRATION_PENDING` items) and must never be referenced by a production
runtime bundle.

**Every field value below is arbitrary.** None of it was copied, transcribed, paraphrased, or
derived from the real catalogue document — that file was never opened while building this
fixture. Structural values that the loader itself validates (the 30 template ids, the 8 family
ids, the per-family template counts, the seven frozen skill names, the reviewed
`grade_scope_text` -> grade-gate vocabulary, the `status`/`functional_role` enumerations) were
taken directly from the installed `component_c_generator` package's own code-resident constants
(`tasks.registry.supported_template_ids()`, `catalogue.loader.EXPECTED_FAMILY_IDS`,
`catalogue.loader.SEVEN_SKILLS`, `catalogue.loader._GRADE_GATE_MAP`,
`catalogue.loader._STATUS_VOCAB`, `catalogue.loader._ROLE_VOCAB`) — never from the catalogue
file. The 30 template ids are partitioned across the 8 families by an ARBITRARY, deterministic
rule (each id's own naming prefix determines which of the 8 code-defined per-family template
counts it can satisfy; which family NUMBER (`C-GF-01`..`C-GF-08`) is assigned to which prefix
group is an arbitrary alphabetical-by-prefix choice, not the real, reviewed family grouping).
Every free-text field (`family_name`, `template_title`, `status_note`, `representations`,
`representations_note`, `learner_action`, `correctness`, `error_signatures`,
`main_difficulty_levers`, `recovery`, `curriculum_node_ids`) is a visibly-labelled
`TEST_FIXTURE_ONLY` placeholder string with no bearing on any reviewed content.

**Exactly one template (`C-SF-03`) is marked `status: "DEFERRED_EXTENSION"`.** This status
assignment is an arbitrary fixture choice made so the fail-closed "deferred templates are never
silently substituted" behaviour has something to exercise; it does not reflect the real
catalogue's status for that or any template id.

**What this fixture proves, and what it does not.** It proves the Markdown/YAML parsing, the
checksum chain, the fail-closed paths (unmapped grade text, deferred/inactive templates, wrong
per-family counts, duplicate ids, unrecognized fields), the runtime-bundle integration, and that
this fixture's 30 template ids cannot silently drift from `tasks.registry`'s own 30 — a test
asserts the two id sets are equal, not merely equal in count. It does **not** prove the real,
reviewed catalogue loads; that remains unprovable until a governed catalogue exists (Phase 0).

**BUILDER JUDGMENT — UNRATIFIED (Phase 5, discovered not invented):** the top-level `status`
field was originally `"TEST_FIXTURE_ONLY"`, a value the loader accepts (it applies no vocabulary
check to this specific field — `catalogue.loader.py`'s `catalogue_status=str(root.get("status",
"unknown"))` is a pass-through) but which the package's OWN `eligibility.decide_activation`
(`RECOGNIZED_CATALOGUE_STATUSES = ("PROPOSED_FOR_APPROVAL", "BASELINE_ACTIVE", "APPROVED",
"ACTIVE")`) does not recognize — meaning EVERY template in this fixture was permanently
`inactive` and `select_task` could never return a result for ANY grade, a gap invisible until
Phase 5 first called that code path (Phase 2-4 only ever loaded/checksummed this file, never
selected against it). Corrected to `"PROPOSED_FOR_APPROVAL"` — the value that is also literally
true of Component C's real status (v3.0 §2: "Component C is PROPOSED, not approved"), not a new
invented value. No template content, skill, grade mapping, or difficulty data changed.

## Machine-readable catalogue

```yaml
component_c_game_task_catalogue:
  version: "TEST-FIXTURE-1.0"
  status: "PROPOSED_FOR_APPROVAL"
  skills:
    - counting
    - number_sense
    - place_value
    - addition
    - subtraction
    - multiplication
    - division
  family_id_mapping:
    - game_family_id: "C-GF-01"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-01)"
      template_id_prefix: "C-BT"
    - game_family_id: "C-GF-02"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-02)"
      template_id_prefix: "C-CC"
    - game_family_id: "C-GF-03"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-03)"
      template_id_prefix: "C-JB"
    - game_family_id: "C-GF-04"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-04)"
      template_id_prefix: "C-MCL"
    - game_family_id: "C-GF-05"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-05)"
      template_id_prefix: "C-NP"
    - game_family_id: "C-GF-06"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-06)"
      template_id_prefix: "C-TC"
    - game_family_id: "C-GF-07"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-07)"
      template_id_prefix: "C-EG"
    - game_family_id: "C-GF-08"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-08)"
      template_id_prefix: "C-SF"
  templates:
    - game_family_id: "C-GF-01"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-01)"
      game_task_template_id: "C-BT-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-BT-01)"
      primary_skill_ids:
        - counting
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-BT-01"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-01"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-01)"
      game_task_template_id: "C-BT-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-BT-02)"
      primary_skill_ids:
        - number_sense
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-BT-02"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-01"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-01)"
      game_task_template_id: "C-BT-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-BT-03)"
      primary_skill_ids:
        - place_value
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-BT-03"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-01"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-01)"
      game_task_template_id: "C-BT-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-BT-04)"
      primary_skill_ids:
        - addition
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-BT-04"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-02"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-02)"
      game_task_template_id: "C-CC-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-CC-01)"
      primary_skill_ids:
        - subtraction
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-CC-01"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-02"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-02)"
      game_task_template_id: "C-CC-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-CC-02)"
      primary_skill_ids:
        - multiplication
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-CC-02"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-02"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-02)"
      game_task_template_id: "C-CC-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-CC-03)"
      primary_skill_ids:
        - division
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-CC-03"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-02"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-02)"
      game_task_template_id: "C-CC-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-CC-04)"
      primary_skill_ids:
        - counting
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-CC-04"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-03"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-03)"
      game_task_template_id: "C-JB-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-JB-01)"
      primary_skill_ids:
        - number_sense
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-JB-01"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-03"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-03)"
      game_task_template_id: "C-JB-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-JB-02)"
      primary_skill_ids:
        - place_value
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-JB-02"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-03"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-03)"
      game_task_template_id: "C-JB-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-JB-03)"
      primary_skill_ids:
        - addition
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-JB-03"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-03"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-03)"
      game_task_template_id: "C-JB-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-JB-04)"
      primary_skill_ids:
        - subtraction
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-JB-04"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-04"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-04)"
      game_task_template_id: "C-MCL-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-MCL-01)"
      primary_skill_ids:
        - multiplication
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-MCL-01"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-04"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-04)"
      game_task_template_id: "C-MCL-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-MCL-02)"
      primary_skill_ids:
        - division
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-MCL-02"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-04"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-04)"
      game_task_template_id: "C-MCL-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-MCL-03)"
      primary_skill_ids:
        - counting
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-MCL-03"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-04"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-04)"
      game_task_template_id: "C-MCL-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-MCL-04)"
      primary_skill_ids:
        - number_sense
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-MCL-04"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-05"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-05)"
      game_task_template_id: "C-NP-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-NP-01)"
      primary_skill_ids:
        - place_value
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-NP-01"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-05"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-05)"
      game_task_template_id: "C-NP-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-NP-02)"
      primary_skill_ids:
        - addition
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-NP-02"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-05"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-05)"
      game_task_template_id: "C-NP-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-NP-03)"
      primary_skill_ids:
        - subtraction
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-NP-03"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-05"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-05)"
      game_task_template_id: "C-NP-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-NP-04)"
      primary_skill_ids:
        - multiplication
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-NP-04"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-06"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-06)"
      game_task_template_id: "C-TC-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-TC-01)"
      primary_skill_ids:
        - division
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-TC-01"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-06"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-06)"
      game_task_template_id: "C-TC-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-TC-02)"
      primary_skill_ids:
        - counting
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-TC-02"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-06"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-06)"
      game_task_template_id: "C-TC-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-TC-03)"
      primary_skill_ids:
        - number_sense
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-TC-03"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-06"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-06)"
      game_task_template_id: "C-TC-04"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-TC-04)"
      primary_skill_ids:
        - place_value
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-TC-04"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-07"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-07)"
      game_task_template_id: "C-EG-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-EG-01)"
      primary_skill_ids:
        - addition
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-EG-01"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-07"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-07)"
      game_task_template_id: "C-EG-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-EG-02)"
      primary_skill_ids:
        - subtraction
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-EG-02"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-07"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-07)"
      game_task_template_id: "C-EG-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-EG-03)"
      primary_skill_ids:
        - multiplication
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-EG-03"
      grade_scope_text: "Grades 2–3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN_SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-08"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-08)"
      game_task_template_id: "C-SF-01"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-SF-01)"
      primary_skill_ids:
        - division
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-SF-01"
      grade_scope_text: "Grade 2"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "RECOVERY_ONLY"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-08"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-08)"
      game_task_template_id: "C-SF-02"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-SF-02)"
      primary_skill_ids:
        - counting
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-SF-02"
      grade_scope_text: "Grade 3"
      status: "BASELINE_ACTIVE"
      status_note: null
      functional_role: "MAIN"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
    - game_family_id: "C-GF-08"
      family_name: "TEST_FIXTURE_ONLY family placeholder (C-GF-08)"
      game_task_template_id: "C-SF-03"
      template_title: "TEST_FIXTURE_ONLY template placeholder (C-SF-03)"
      primary_skill_ids:
        - number_sense
      curriculum_node_ids:
        - "TEST-FIXTURE-NODE-C-SF-03"
      grade_scope_text: "Grades 2–3"
      status: "DEFERRED_EXTENSION"
      status_note: null
      functional_role: "SUPPORT"
      representations:
        - "TEST_FIXTURE_ONLY_REPRESENTATION"
      representations_note: null
      learner_action: "TEST_FIXTURE_ONLY placeholder learner action"
      correctness: "TEST_FIXTURE_ONLY placeholder correctness rule"
      error_signatures: null
      main_difficulty_levers: "TEST_FIXTURE_ONLY placeholder"
      recovery: "TEST_FIXTURE_ONLY placeholder recovery note"
```
