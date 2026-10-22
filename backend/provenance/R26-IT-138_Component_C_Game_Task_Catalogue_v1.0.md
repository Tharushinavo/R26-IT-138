# R26-IT-138 — Component C Game-Task Catalogue v1.0

**Project:** Interactive Learning Tool for Dyscalculia Kids  
**Component:** C — Adaptive Game-Based Learning Engine  
**Artefact type:** Authoritative game-family and task-template catalogue for the client statistical baseline  
**Version:** 1.0  
**Date:** 2026-07-13  
**Status:** **PROPOSED FOR APPROVAL**  
**Recommended repository location:** `Component_C_v1.0/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md`  
**Active architecture:** Component B → Component C → Component 3  
**Mandatory interpretation:** **Literature-informed synthetic data — not clinical evidence.**

---

## 0. Purpose and authority

This catalogue freezes the **client-baseline semantic content** required to implement Component C as a React Native game layer and a FastAPI statistical simulation kernel.

It defines:

- the baseline game-family bank;
- reviewed task-template identifiers;
- Grade 2–3 curriculum mappings;
- deterministic task correctness and completion rules;
- family-specific difficulty dimensions;
- C-owned scaffolds and recovery routes;
- gameplay telemetry obligations;
- accessibility and safety requirements;
- template-level validation and acceptance tests.

It does **not**:

- change the seven-skill B→C contract;
- import Component B items, hints, errors, attempts, timing, certification, or BKT internals;
- redefine Component C engagement, frustration, learner-state, RL, latency, or safety equations;
- create new shared curriculum skills;
- resolve formal academic approval;
- authorize clinical or diagnostic interpretation;
- authorize direct runtime lookup by `population` or `dd_subtype`.

### 0.1 Source precedence

This catalogue must be interpreted beneath the active source-of-truth order recorded in `CURRENT_DIRECTORY_CONTENTS.md`:

1. governance and approval-status records;
2. Shared Foundation Decision Register v0.3;
3. Component Variable Registers v0.3;
4. Shared Population and Study Protocol;
5. boundary contracts and validation rules;
6. Component B and Component C parameter specifications;
7. Component B Generator SPEC;
8. Component B Item and Task-Set Catalogue;
9. shared taxonomy and prerequisite DAG;
10. curriculum research synthesis;
11. shared simulator and leakage-control register;
12. blueprint and proposals as supporting/historical context.

If this catalogue conflicts with a higher-precedence active source, the higher-precedence source governs and the catalogue requires revision.

### 0.2 Frozen boundaries

Component C receives from Component B exactly:

- `mastery_counting`;
- `mastery_number_sense`;
- `mastery_place_value`;
- `mastery_addition`;
- `mastery_subtraction`;
- `mastery_multiplication`;
- `mastery_division`.

No additional B field may influence C task generation or adaptation.

---

## 1. Research basis and design conclusions

### 1.1 Evidence used

This catalogue was created from:

- the active R26-IT-138 taxonomy, prerequisite DAG, curriculum synthesis, Component C parameter specification, C variable register, and B→C/C→3 contracts;
- the uploaded deep-research synthesis that proposed a broader 16-family, approximately 70-template research bank;
- peer-reviewed intervention evidence from **Calcularis** and **The Number Race**;
- the W3C **Web Content Accessibility Guidelines 2.2** as a minimum engineering accessibility baseline.

### 1.2 Design principles retained from Calcularis

Calcularis supports the following design choices:

- train multiple linked number representations rather than one symbol format;
- organize games hierarchically;
- separate complex **main games** from focused **support games**;
- teach conceptual meaning before fluency/automation;
- adapt task difficulty and scaffolding to the learner;
- combine basic numerical cognition with arithmetic instead of training only one narrow comparison skill.

### 1.3 Design principles retained from The Number Race

The Number Race supports:

- multidimensional difficulty rather than a single “easy/hard” value;
- explicit control of numerical distance, conceptual complexity, and response demands;
- performance-adaptive task selection;
- repeated links between quantity, symbol, and spatial representation.

The historical 75% success target used by The Number Race is **not copied as a frozen R26-IT-138 value**. Component C must use the active project policy and calibration process.

### 1.4 Scope decision for the client baseline

The broader research synthesis proposed 16 families and approximately 70 templates. That is valuable as a future research/product expansion but is larger than necessary for the client baseline.

This authoritative baseline freezes:

- **8 reusable game families**;
- **30 reviewed task templates**;
- all seven frozen skills;
- deterministic procedural generation;
- main, support, and recovery routes;
- C difficulty levels 1–5;
- no live LLM-generated child-facing content.

This count is an **engineering scope decision**, not a literature-established optimal number.

---

## 2. Controlled vocabularies

### 2.1 Frozen skills

`counting`, `number_sense`, `place_value`, `addition`, `subtraction`, `multiplication`, `division`

### 2.2 Template status

| Value | Meaning |
|---|---|
| `BASELINE_ACTIVE` | May be implemented in baseline v1 within its stated grade/range limits. |
| `BASELINE_CONDITIONAL` | Valid design, but exact range or curriculum placement remains `CALIBRATION_PENDING`. |
| `DEFERRED_EXTENSION` | Not used in baseline v1. |
| `RETIRED` | Must not be generated. |

### 2.3 Functional role

| Value | Meaning |
|---|---|
| `MAIN` | Primary multi-step or integrative game task. |
| `SUPPORT` | Isolates one prerequisite or representation link. |
| `MAIN_SUPPORT` | Can serve either role depending on difficulty and scaffold state. |
| `RECOVERY_ONLY` | Lower-load success-restoration task. |

### 2.4 C scaffold ladder

| Code | Name | Meaning |
|---|---|---|
| `C0` | `no_scaffold` | Normal task presentation. |
| `C1` | `orienting_prompt` | Directs attention to the task rule without giving the answer. |
| `C2` | `perceptual_structure` | Highlights groups, positions, intervals, counted objects, or place-value columns. |
| `C3` | `guided_action` | Demonstrates or constrains one step. |
| `C4` | `recovery_task` | Switches to a lower-load representation or prerequisite task. |

C scaffold codes are Component C gameplay supports. They are not Component B hint levels and must not cross the B→C boundary.

### 2.5 Representation vocabulary

Templates may use only controlled values from the shared taxonomy, including:

`concrete_simulated`, `pictorial_objects`, `dot_sets`, `pictorial_groups`, `pictorial_comparison`, `structured_visual`, `ten_frame`, `number_line`, `base_ten_blocks`, `place_value_chart`, `array`, `number_cards`, `expanded_form`, `verbal`, `verbal_story`, `symbolic`, `symbolic_sequence`, `symbolic_algorithm`, `mixed_representation`.

---

## 3. Catalogue architecture

Component C uses four separate identifiers.

| Layer | Identifier | Meaning |
|---|---|---|
| Game family | `game_family_id` | Reusable interaction mechanic. |
| Task template | `game_task_template_id` | Reviewed curriculum/mechanic definition. |
| Difficulty configuration | `difficulty_config_id` | Family-specific level/vector mapping. |
| Generated task | `game_task_instance_id` | One deterministic playable instance. |

A `game_task_template_id` must never be reused as the generated task-instance ID.

Every generated instance must retain:

- `template_version`;
- `catalogue_version`;
- `generator_seed`;
- `generator_config_version`;
- `policy_version`;
- `difficulty_level`;
- the full family-specific difficulty vector.

---

## 4. Baseline game-family bank

| Family ID | Family | Primary skills | Functional role | Template count |
|---|---|---|---|---:|
| `C-GF-01` | Count and Collect | counting, number_sense | support/main | 4 |
| `C-GF-02` | Number Path and Order | counting, number_sense | support/main | 4 |
| `C-GF-03` | Match, Compare and Locate | number_sense | support/main | 4 |
| `C-GF-04` | Build and Trade | place_value | support/main | 4 |
| `C-GF-05` | Join and Bridge | addition | main | 4 |
| `C-GF-06` | Take Away and Compare | subtraction | main | 4 |
| `C-GF-07` | Equal Groups and Arrays | multiplication | main/support | 3 |
| `C-GF-08` | Share Fairly | division | main/support | 3 |
|  | **Total** |  |  | **30** |

---

# 5. Complete task-template register

## 5.1 C-GF-01 — Count and Collect

**Core mechanic:** touch, select, move, or mark objects so that one-to-one correspondence, cardinality, set production, and quantity conservation are observable actions.

### C-CC-01 — Mark and Count Objects

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-CC-01` |
| Primary skill/node | `counting`; `CNT-02`, `CNT-03` |
| Grade scope | Grade 2 baseline; Grade 3 review |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects` |
| Learner action | Tap/select every object exactly once, then submit total. |
| Correctness | Every valid object selected once; no invalid object selected; submitted total equals set cardinality. |
| Error signatures | omission, double count, invalid-object selection, cardinality mismatch. |
| Main difficulty levers | set size, spatial scatter, overlap, distractor objects, visible count markers. |
| Recovery | Align objects; mark counted objects automatically; remove distractors. |

### C-CC-02 — Produce the Requested Set

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-CC-02` |
| Primary skill/node | `counting`; `CNT-04` |
| Grade scope | Grade 2 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects`, `symbolic` |
| Learner action | Move/select exactly `N` objects into a target area. |
| Correctness | Final target area contains exactly `N` valid objects. |
| Error signatures | under-production, over-production, invalid-object inclusion. |
| Main difficulty levers | N, available-object count, distractors, visual organization, numeral/audio prompt. |
| Recovery | Ten-frame or linear slots; snap-to-slot; count markers. |

### C-CC-03 — Count and Match Numeral

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-CC-03` |
| Primary skill/nodes | `counting`, `number_sense`; `CNT-03`, `NS-02` |
| Grade scope | Grade 2 baseline; Grade 3 review |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `pictorial_objects`, `symbolic`, `mixed_representation` |
| Learner action | Count a set and choose/enter the matching numeral. |
| Correctness | Selected numeral equals set cardinality. |
| Error signatures | neighboring numeral, reversed digit where applicable, random mismatch. |
| Main difficulty levers | set size, arrangement, numeral distractor distance, symbol entry mode. |
| Recovery | Object alignment, counted-object highlighting, reduced distractors. |

### C-CC-04 — Conservation Rearrangement

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-CC-04` |
| Primary skill/node | `number_sense`; `NS-07` |
| Grade scope | Grade 2 |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects` |
| Learner action | Judge whether quantity changed after the same objects are rearranged. |
| Correctness | “Same” when object identity/count is preserved; “changed” only in controlled add/remove trials. |
| Error signatures | spacing bias, object-size bias, arrangement bias. |
| Main difficulty levers | spacing difference, layout change, controlled add/remove catch trials. |
| Recovery | Animate one-to-one correspondence between pre/post arrangements. |

---

## 5.2 C-GF-02 — Number Path and Order

**Core mechanic:** continue, repair, or arrange number sequences and spatial paths.

### C-NP-01 — Continue a Forward Sequence

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-NP-01` |
| Primary skill/node | `counting`; `CNT-01`, `CNT-05` |
| Grade scope | Grade 2 foundation; Grade 3 review |
| Status | `BASELINE_CONDITIONAL` because full Grade 2 range remains pending |
| Role | `SUPPORT` |
| Representations | `symbolic_sequence`, `verbal`, `number_line` |
| Learner action | Select or enter the next number(s). |
| Correctness | Each next value equals prior value + 1. |
| Main difficulty levers | start value, sequence length, missing position, visible number-line support. |
| Recovery | Show adjacent numbers and animate +1 jumps. |

### C-NP-02 — Continue a Backward Sequence

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-NP-02` |
| Primary skill/node | `counting`; `CNT-05` |
| Grade scope | Grades 2–3 |
| Status | `BASELINE_CONDITIONAL` |
| Role | `SUPPORT` |
| Representations | `symbolic_sequence`, `verbal`, `number_line` |
| Learner action | Select or enter preceding number(s). |
| Correctness | Each next response equals prior value − 1. |
| Main difficulty levers | start value, length, hidden terms, support visibility. |
| Recovery | Visible descending number line; one guided −1 step. |

### C-NP-03 — Skip Count by 2, 5, or 10

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-NP-03` |
| Primary skill/node | `counting`; `CNT-06` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `pictorial_groups`, `number_line`, `symbolic_sequence` |
| Learner action | Continue or repair an equal-step sequence. |
| Correctness | Consecutive values differ by the configured step 2, 5, or 10. |
| Main difficulty levers | step size, start value, hidden positions, group/line/symbolic representation. |
| Recovery | Show equal groups and animated number-line jumps. |

### C-NP-04 — Order Number Cards

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-NP-04` |
| Primary skill/node | `number_sense`; `NS-05` |
| Grade scope | Grade 3; Grade 2 only after range review |
| Status | `BASELINE_ACTIVE` for Grade 3 |
| Role | `MAIN_SUPPORT` |
| Representations | `number_cards`, `symbolic`, `number_line` |
| Learner action | Arrange values ascending or descending. |
| Correctness | Strict configured order; duplicates only when explicitly permitted. |
| Main difficulty levers | list length, numerical closeness, direction, number range, number-line support. |
| Recovery | Reduce list to three values; show endpoints/relative positions. |

---

## 5.3 C-GF-03 — Match, Compare and Locate

**Core mechanic:** connect quantities, symbols, comparisons, and number-line positions.

### C-MCL-01 — Numeral–Quantity Match

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-MCL-01` |
| Primary skill/nodes | `number_sense`; `NS-01`, `NS-02` |
| Grade scope | Grade 2 1–50 minimum; Grade 3 through approved ranges |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `symbolic`, `pictorial_objects`, `dot_sets`, `verbal` where audio is available |
| Learner action | Match two equivalent number representations. |
| Correctness | Matched representations encode the same cardinal value. |
| Main difficulty levers | number range, representation pair, distractor similarity, spoken/written mode. |
| Recovery | Display a third bridging representation. |

### C-MCL-02 — Compare Quantities

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-MCL-02` |
| Primary skill/node | `number_sense`; `NS-03` |
| Grade scope | Grade 2 intervention scope; Grade 3 review |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `dot_sets`, `pictorial_objects` |
| Learner action | Select larger, smaller, or equal quantity. |
| Correctness | Based on exact cardinalities, not visual area. |
| Main difficulty levers | numerical ratio/distance, equality trials, density, object size/area controls. |
| Recovery | Pair objects one-to-one or reveal matching numerals after response. |

### C-MCL-03 — Compare Numerals

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-MCL-03` |
| Primary skill/node | `number_sense`; `NS-04` |
| Grade scope | Grade 3 below 1000; Grade 2 small-range proposal |
| Status | `BASELINE_ACTIVE` for Grade 3 |
| Role | `MAIN_SUPPORT` |
| Representations | `symbolic`, `number_line` |
| Learner action | Choose larger/smaller/equal or place comparison sign. |
| Correctness | Exact integer comparison. |
| Main difficulty levers | number range, numerical distance, digit similarity, place-value conflict. |
| Recovery | Base-ten or number-line visualization. |

### C-MCL-04 — Number-Line Landing

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-MCL-04` |
| Primary skill/node | `number_sense`; `NS-06` |
| Grade scope | Grades 2–3 intervention extension |
| Status | `BASELINE_CONDITIONAL` |
| Role | `MAIN` |
| Representations | `number_line`, `symbolic`, `pictorial_objects` |
| Learner action | Tap or move a marker to a target position. |
| Correctness | Mathematical interval/location error within configured tolerance; motor error tracked separately. |
| Main difficulty levers | interval range, tick labels, midpoint visibility, target type, tolerance. |
| Recovery | Labeled ticks, highlighted sub-interval, guided example jump. |

---

## 5.4 C-GF-04 — Build and Trade

**Core mechanic:** construct, decompose, regroup, and ungroup numbers using place-value representations.

### C-BT-01 — Build Tens and Ones

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-BT-01` |
| Primary skill/nodes | `place_value`; `PV-01`, `PV-02` |
| Grade scope | Grade 2 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `base_ten_blocks`, `place_value_chart`, `symbolic` |
| Learner action | Build a two-digit number or decode blocks into tens/ones. |
| Correctness | `number = 10 × tens + ones`, with canonical ones 0–9 unless non-canonical form is intentional. |
| Main difficulty levers | number range, zero digit, direction of transcoding, labels visible/hidden. |
| Recovery | Labeled columns and snap-to-place behavior. |

### C-BT-02 — Build Hundreds, Tens and Ones

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-BT-02` |
| Primary skill/nodes | `place_value`; `PV-03`, `PV-04` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` with exact range governed by curriculum config |
| Role | `MAIN` |
| Representations | `base_ten_blocks`, `place_value_chart`, `expanded_form`, `symbolic` |
| Learner action | Build/decompose a three-digit number. |
| Correctness | `number = 100 × hundreds + 10 × tens + ones`. |
| Main difficulty levers | zeros in places, compose/decompose direction, representation support. |
| Recovery | Place-value labels; one component pre-filled. |

### C-BT-03 — Trade Ten Ones for One Ten

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-BT-03` |
| Primary skill/node | `place_value`; `PV-05` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `base_ten_blocks`, `place_value_chart`, `symbolic_algorithm` |
| Learner action | Exchange exactly ten ones for one ten. |
| Correctness | Quantity conserved and post-trade place-value counts valid. |
| Main difficulty levers | starting block count, guided/unguided exchange, addition context. |
| Recovery | Animated exchange, then learner repeats. |

### C-BT-04 — Ungroup One Ten into Ten Ones

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-BT-04` |
| Primary skill/node | `place_value`; `PV-06` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `base_ten_blocks`, `place_value_chart`, `symbolic_algorithm` |
| Learner action | Exchange one ten for ten ones. |
| Correctness | Quantity conserved and post-trade counts valid. |
| Main difficulty levers | starting configuration, borrowing context, visibility of transformation. |
| Recovery | Animated exchange with highlighted destination column. |

---

## 5.5 C-GF-05 — Join and Bridge

**Core mechanic:** combine quantities and move from concrete addition to symbolic and regrouping tasks.

### C-JB-01 — Combine Two Groups

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-JB-01` |
| Primary skill/node | `addition`; `ADD-01` |
| Grade scope | Grade 2 baseline; Grade 3 review |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects`, `verbal_story` |
| Learner action | Move/join two sets and identify total. |
| Correctness | Total equals cardinality of union of disjoint valid sets. |
| Main difficulty levers | addend sizes, arrangement, symbolic prompt, story load. |
| Recovery | Count-all path with visible markers. |

### C-JB-02 — Count On from an Addend

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-JB-02` |
| Primary skill/node | `addition`; `ADD-02` |
| Grade scope | Grades 2–3 |
| Status | `BASELINE_ACTIVE` |
| Role | `SUPPORT` |
| Representations | `number_line`, `verbal`, `symbolic` |
| Learner action | Start at one addend and make the required forward jumps. |
| Correctness | Final position equals sum; jump count/size matches configured strategy. |
| Main difficulty levers | addends, start-from-larger support, visible jumps, missing final value. |
| Recovery | Highlight larger addend and animate first jump. |

### C-JB-03 — Single-Digit Addition

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-JB-03` |
| Primary skill/node | `addition`; `ADD-03` |
| Grade scope | Grade 2 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN` |
| Representations | `symbolic`, `pictorial_objects`, `ten_frame` |
| Learner action | Solve two-single-digit-addend task within configured curriculum envelope. |
| Correctness | Exact integer sum. |
| Main difficulty levers | sum range, visual support, missing-value form, distractor distance. |
| Recovery | Ten-frame or object model; no forced timer. |

### C-JB-04 — Two-Digit Addition and Regrouping

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-JB-04` |
| Primary skill/nodes | `addition`; `ADD-04`, `ADD-05` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE`, with exact operand/regrouping bands `CALIBRATION_PENDING` |
| Role | `MAIN` |
| Representations | `base_ten_blocks`, `place_value_chart`, `symbolic_algorithm`, `verbal_story` |
| Learner action | Add two numbers; regroup where configured. |
| Correctness | Exact sum plus valid exchange sequence where manipulation is required. |
| Main difficulty levers | no-regroup/regroup, number of digits, missing step, representation support. |
| Recovery | Switch to `C-BT-03`, then return to an easier addition instance. |

---

## 5.6 C-GF-06 — Take Away and Compare

**Core mechanic:** remove quantities, compare sets, and move from concrete subtraction to symbolic and borrowing tasks.

### C-TC-01 — Remove Objects

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-TC-01` |
| Primary skill/node | `subtraction`; `SUB-01` |
| Grade scope | Grade 2 baseline; Grade 3 review |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects`, `verbal_story` |
| Learner action | Remove specified quantity and identify remainder. |
| Correctness | `remainder = initial_count − removed_count`; removed count cannot exceed initial count. |
| Main difficulty levers | initial quantity, removal size, hidden/visible remainder, language load. |
| Recovery | One-by-one animated removal with count markers. |

### C-TC-02 — Compare and Find the Difference

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-TC-02` |
| Primary skill/node | `subtraction`; `SUB-02` |
| Grade scope | Grades 2–3 |
| Status | `BASELINE_CONDITIONAL` |
| Role | `MAIN_SUPPORT` |
| Representations | `pictorial_comparison`, `number_line`, `verbal_story` |
| Learner action | Pair or align two quantities and identify how many more/less. |
| Correctness | Absolute or directed difference according to prompt. |
| Main difficulty levers | quantity distance, representation, directed language, alignment support. |
| Recovery | One-to-one pairing and highlighted unmatched objects. |

### C-TC-03 — Subtraction Within 9

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-TC-03` |
| Primary skill/node | `subtraction`; `SUB-03` |
| Grade scope | Grade 2 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN` |
| Representations | `symbolic`, `pictorial_objects`, `number_line` |
| Learner action | Solve `a − b`, with `a ≤ 9`, `0 ≤ b ≤ a`. |
| Correctness | Exact non-negative difference. |
| Main difficulty levers | minuend, subtrahend, visual support, missing-value form. |
| Recovery | Object removal or backward number-line jumps. |

### C-TC-04 — Two-Digit Subtraction and Borrowing

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-TC-04` |
| Primary skill/nodes | `subtraction`; `SUB-04`, `SUB-05` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE`, exact borrowing bands `CALIBRATION_PENDING` |
| Role | `MAIN` |
| Representations | `base_ten_blocks`, `place_value_chart`, `symbolic_algorithm`, `verbal_story` |
| Learner action | Subtract two numbers; ungroup where configured. |
| Correctness | Exact difference plus valid ungrouping sequence where manipulation is required. |
| Main difficulty levers | no-borrow/borrow, number range, missing step, support. |
| Recovery | Switch to `C-BT-04`, then return to easier subtraction. |

---

## 5.7 C-GF-07 — Equal Groups and Arrays

**Core mechanic:** construct and interpret equal groups, repeated addition, arrays, and facts for 2, 5, and 10.

### C-EG-01 — Build Equal Groups

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-EG-01` |
| Primary skill/node | `multiplication`; `MUL-01` |
| Grade scope | Grade 3 only |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `pictorial_groups`, `concrete_simulated`, `symbolic` |
| Learner action | Create `number_of_groups` groups of equal size. |
| Correctness | Every group has configured size and total equals product. |
| Main difficulty levers | group count, group size, pre-structured containers, symbolic link. |
| Recovery | Containers shown; one group pre-filled. |

### C-EG-02 — Build or Read an Array

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-EG-02` |
| Primary skill/node | `multiplication`; `MUL-02` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN` |
| Representations | `array`, `symbolic`, `pictorial_groups` |
| Learner action | Build rows/columns from an expression or identify expression/product from an array. |
| Correctness | Rectangular equal-row/column structure and correct product. |
| Main difficulty levers | row/column counts, orientation, missing factor/product, grid support. |
| Recovery | Grid lines and one completed row. |

### C-EG-03 — Facts for 2, 5, and 10

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-EG-03` |
| Primary skill/node | `multiplication`; `MUL-03` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `symbolic_sequence`, `array`, `pictorial_groups`, `symbolic` |
| Learner action | Complete equal-step facts or match fact to model. |
| Correctness | Exact product for multipliers 2, 5, or 10 within approved Grade 3 range. |
| Main difficulty levers | table, multiplier, model visibility, missing-factor form. |
| Recovery | Skip-count sequence or array model; no speed-only scoring. |

---

## 5.8 C-GF-08 — Share Fairly

**Core mechanic:** distribute quantities equally or form equal-sized groups.

### C-SF-01 — Equal Sharing

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-SF-01` |
| Primary skill/node | `division`; `DIV-01` |
| Grade scope | Grade 3 only |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN_SUPPORT` |
| Representations | `concrete_simulated`, `pictorial_objects`, `verbal_story` |
| Learner action | Distribute objects equally among recipients. |
| Correctness | All recipients have equal count and all objects are allocated when no remainder is allowed. |
| Main difficulty levers | total, recipient count, pre-allocated objects, story load. |
| Recovery | Round-robin guidance and recipient slots. |

### C-SF-02 — Form Equal Groups

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-SF-02` |
| Primary skill/node | `division`; `DIV-02` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN` |
| Representations | `pictorial_groups`, `concrete_simulated`, `symbolic` |
| Learner action | Partition total into groups of configured size and determine group count. |
| Correctness | Each group has exact size; group count × group size = total. |
| Main difficulty levers | total, group size, container support, symbolic link. |
| Recovery | Group containers visible; one group modeled. |

### C-SF-03 — Divide by 2 without Remainder

| Field | Specification |
|---|---|
| `game_task_template_id` | `C-SF-03` |
| Primary skill/node | `division`; `DIV-03` |
| Grade scope | Grade 3 |
| Status | `BASELINE_ACTIVE` |
| Role | `MAIN` |
| Representations | `symbolic`, `concrete_simulated`, `pictorial_groups` |
| Learner action | Solve approved even-number division-by-2 cases. |
| Correctness | Exact quotient; dividend even and within curriculum-approved range. |
| Main difficulty levers | dividend magnitude, concrete/symbolic mode, missing-value form. |
| Recovery | Split objects between two visible recipients. |

`DIV-04` multiplication–division inverse tasks are deliberately deferred from baseline v1 until curriculum/supervisor confirmation.

---

# 6. Global difficulty architecture

## 6.1 Separate curriculum level from C policy difficulty

The shared curriculum taxonomy uses proposed levels `L1–L3`. Component C policy uses difficulty levels `1–5`.

These are related but not interchangeable:

- curriculum level describes the mathematical/representational concept;
- C difficulty level describes a calibrated configuration within a task template.

## 6.2 Family-independent difficulty dimensions

Each template must explicitly parameterize applicable dimensions:

1. `number_magnitude`;
2. `representation_abstraction`;
3. `numerical_distance_or_ratio`;
4. `step_count`;
5. `working_memory_load`;
6. `visual_density`;
7. `motor_precision`;
8. `distractor_similarity`;
9. `representation_support`;
10. `regrouping_or_borrowing`;
11. `time_pressure_mode`;
12. `context_novelty`.

A dimension not applicable to a template must be `not_applicable`, not silently omitted.

## 6.3 Baseline mapping to C difficulty 1–5

| C level | General interpretation |
|---:|---|
| 1 | Small range; concrete/pictorial; one step; full structure; large targets; untimed. |
| 2 | Small/moderate range; mixed representation; one step; visible support. |
| 3 | Independent symbolic or mixed task; moderate range; reduced support. |
| 4 | Larger approved range, closer distractors, multiple steps, or one regroup/borrow operation. |
| 5 | Transfer/application or fluency variant within approved safety limits; reduced support; still not speed-only. |

Every family must define its own level-to-vector mapping. Level 3 in `C-GF-03` is not mathematically equivalent to level 3 in `C-GF-07`.

## 6.4 Time pressure

- conceptual levels default to `untimed`;
- time limits must be adjustable or removable;
- response speed must never be the sole basis for success, engagement, frustration, or overload;
- slow-but-accurate safeguards from the Component C parameter specification remain binding.

---

# 7. Deterministic generation requirements

Every template generator must define:

- valid operand/value domains;
- sampling without invalid cases;
- exact answer function;
- completion state;
- failure state;
- retry rules;
- distractor-generation rules where applicable;
- ambiguous-case exclusions;
- recovery template or recovery configuration;
- seeded reproducibility.

## 7.1 Global mathematical invariants

- counting sets contain exactly the stored cardinality;
- every comparison has a uniquely determined relation;
- ordering tasks have a deterministic valid ordering;
- place-value tasks conserve numeric value;
- addition and subtraction results are exact integers within scope;
- no subtraction task produces a negative result unless explicitly added in a future approved scope;
- multiplication groups/arrays are equal by construction;
- baseline division tasks have no remainder unless a future catalogue revision authorizes remainders;
- `DIV-03` dividends are even;
- regrouping and borrowing instances must actually require the configured exchange;
- catch trials and distractors must not create multiple correct answers.

## 7.2 Population neutrality

Task generation must not branch on:

- `population`;
- `dd_subtype`;
- diagnosis labels;
- Component 3 risk;
- hidden future outcomes.

Population may be used only in audit-only simulator calibration under SF-039/SF-038. The catalogue and runtime selection policy remain population-neutral.

---

# 8. Runtime selection and orchestration rules

## 8.1 Combined B+C session

1. Component B runs first.
2. B completes its BKT update.
3. C receives the same-session seven-field post-B mastery payload.
4. C determines eligible skills/templates.
5. C selects a family/template using the baseline selection policy.
6. RL may adjust only difficulty by `{decrease_difficulty, hold, increase_difficulty}` within ±1.
7. Safety rules may override the RL action.
8. C executes tasks, aggregates telemetry, computes deterministic composites, and exports C→3.

## 8.2 C-only session

- no B→C payload exists;
- no B mastery is reconstructed, read from B history, or cached;
- the safe fallback uses grade-valid baseline tasks at difficulty 1–2;
- fallback rotates across active skills/templates with deterministic seeded selection;
- multiplication/division are excluded for Grade 2;
- safety and sufficient-evidence rules remain active.

> **Fallback status (SF-043 reconciliation).** This is the **proposed** C-only safe-fallback shape. Consistent with SF-043 and the B→C mastery contract note, the exact fallback (template rotation order, evidence thresholds, difficulty defaults) is **frozen in the Component C Generator SPEC** (`Component_C_Generator_v1.0/SPEC.md`, not yet created); `CALIBRATION_PENDING` until then. No B mastery inference, reconstruction, or cache is permitted.

## 8.3 Baseline template-selection policy

The statistical baseline must:

1. filter by learner grade;
2. filter to `BASELINE_ACTIVE` plus explicitly enabled conditional templates;
3. filter by target skill;
4. respect design-time prerequisite readiness without consuming prohibited B internals;
5. avoid the same template more than two consecutive times unless in recovery;
6. prefer a `MAIN` task when state is stable;
7. prefer `SUPPORT` after repeated task-specific difficulty;
8. use `C4` recovery after a safety trigger or approved overload condition;
9. balance representation exposure across recent sessions;
10. break ties using the recorded seed.

The RL action space does not silently expand to game selection, reward modification, or content generation in baseline v1.

---

# 9. Gameplay event and telemetry mapping

## 9.1 Required task-event sequence

The implementation should support:

1. `game_task_offered`;
2. `game_task_started`;
3. `action_performed`;
4. `answer_submitted` or `goal_state_reached`;
5. `answer_evaluated`;
6. optional `scaffold_requested` / `scaffold_shown`;
7. optional `retry_started`;
8. optional `pause_started` / `pause_ended`;
9. optional `difficulty_changed`;
10. optional `recovery_task_started`;
11. optional `reward_delivered`;
12. one terminal event: `game_task_completed`, `game_task_skipped`, or `game_task_quit`;
13. optional `safety_override_triggered`;
14. optional `technical_issue`.

## 9.2 Required internal task fields

Each task instance/event must be able to produce or derive:

- identifiers and timestamps;
- family/template/instance IDs;
- skill and curriculum node;
- task index;
- difficulty level/vector;
- attempt and retry counts;
- task correctness/success;
- completion;
- C-owned latency;
- inactivity periods/time;
- pause count/time;
- answer/action changes;
- scaffold use;
- skip/quit;
- quit after error;
- error-run position;
- difficulty action;
- reward event;
- recovery event;
- safety override;
- technical issue flag.

## 9.3 C→3 session export compatibility

The catalogue must support aggregation into the active C→3 fields, including:

- `task_opportunity_count`;
- `completed_task_count`;
- `correct_task_count`;
- `total_attempt_count`;
- `accuracy_rate`;
- `avg_attempts_per_task`;
- `task_completion_rate`;
- `inactivity_periods`;
- `inactive_time_sec`;
- `session_duration_sec`;
- `time_in_target_band_sec`;
- `consecutive_error_max`;
- `difficulty_floor_hits`;
- `quit_after_error`;
- `safety_override_count`;
- `c_mean_game_task_latency_sec`;
- `c_median_game_task_latency_sec`;
- `current_difficulty_level`;
- `difficulty_trend`.

Engagement, frustration, learner state, and state reason remain deterministic outputs of the active Component C formulas. They must never be directly sampled by a task template.

---

# 10. Feedback, reward, recovery, and safety

## 10.1 Feedback

- immediate, neutral correctness feedback;
- show the mathematical transformation where useful;
- no shame, loss of all progress, or public comparison;
- no child-facing diagnosis or risk language;
- no live LLM-generated child-facing scaffold in baseline v1.

## 10.2 Reward

Rewards may acknowledge:

- completion;
- appropriate persistence;
- recovery after difficulty;
- accurate task performance;
- safe continuation.

Rewards must not be based only on speed and must not directly overwrite engagement, frustration, or learner state.

## 10.3 Recovery

A recovery configuration must:

- remain within the same target skill or an approved prerequisite;
- use difficulty level 1;
- remove time pressure;
- increase visual/perceptual structure;
- avoid punitive loss;
- log `recovery_task_started`;
- return to a normal task only after the active safety rules allow it.

## 10.4 Safety precedence

The Component C parameter specification remains binding:

- a safety trigger can force `safety_decrease` or `safety_scaffold`;
- difficulty cannot decrease below 1;
- after a safety override, increases are blocked for the configured next decisions;
- safety overrides are logged and aggregated;
- RL cannot bypass safety.

---

# 11. Accessibility requirements

The React Native implementation must treat WCAG 2.2 as a minimum engineering baseline and additionally account for young learners.

Required:

- never communicate mathematical meaning by color alone;
- provide tap/select alternatives to dragging;
- separate mathematical placement tolerance from motor error;
- use sufficiently large targets and spacing;
- support adjustable/untimed modes;
- provide pause/stop controls;
- provide reduced-motion mode;
- avoid flashing;
- provide audio and text alternatives where instructions use language;
- use short, consistent instructions;
- avoid decorative clutter that obscures quantities;
- maintain readable contrast and non-text contrast;
- distinguish technical failure from learner error;
- ensure technical failure does not produce disengagement/frustration evidence.

---

# 12. Task-template data model

Every template record must contain at least:

## 12.1 Identity and governance

- `game_family_id`
- `game_task_template_id`
- `template_version`
- `catalogue_version`
- `template_status`
- `component_owner = "C"`
- `title`
- `description`
- `source_references`
- `approval_status`
- `active_flag`

## 12.2 Curriculum alignment

- `primary_skill_id`
- `curriculum_node_ids`
- `prerequisite_node_ids`
- `grade_scope`
- `number_range_scope`
- `curriculum_status`
- `calibration_notes`

## 12.3 Mathematical definition

- `mathematical_construct`
- `input_representation`
- `target_representation`
- `generator_constraints`
- `correctness_function`
- `completion_condition`
- `invalid_case_exclusions`
- `error_signatures`

## 12.4 Gameplay and adaptation

- `core_mechanic`
- `valid_action_space`
- `retry_policy`
- `skip_policy`
- `pause_policy`
- `feedback_rule`
- `functional_role`
- `difficulty_dimensions`
- `difficulty_level_map`
- `allowed_scaffold_levels`
- `recovery_template_or_config`
- `safety_behavior`

## 12.5 Telemetry and accessibility

- `telemetry_events`
- `latency_start_event`
- `latency_end_event`
- `motor_error_measure`
- `technical_failure_rule`
- `drag_alternative`
- `audio_available`
- `text_available`
- `color_independent_encoding`
- `reduced_motion_support`
- `timing_adjustable`
- `target_size_check`

---

# 13. Example generated task instance

```json
{
  "catalogue_version": "1.0",
  "template_version": "1.0",
  "game_family_id": "C-GF-04",
  "game_task_template_id": "C-BT-01",
  "game_task_instance_id": "CGT-S008-C04-I003",
  "generator_seed": 713008403,
  "student_id": "S008",
  "c_session_id": "C-S008-04",
  "task_index": 3,
  "grade_scope": 2,
  "primary_skill_id": "place_value",
  "curriculum_node_ids": ["PV-01", "PV-02"],
  "difficulty_level": 2,
  "difficulty_vector": {
    "number_magnitude": 47,
    "representation_abstraction": "base_ten_blocks_to_symbolic",
    "representation_support": "visible_place_value_columns",
    "step_count": 1,
    "motor_precision": "low",
    "time_pressure_mode": "untimed"
  },
  "task_parameters": {
    "target_number": 47,
    "tens": 4,
    "ones": 7
  },
  "correctness_rule": "10*tens + ones == target_number",
  "allowed_scaffold_levels": ["C0", "C1", "C2", "C3", "C4"],
  "recovery_configuration": "C-BT-01@difficulty1",
  "policy_version": "C-RL-v1"
}
```

---

# 14. Validation and acceptance criteria

## 14.1 Coverage

- all seven frozen skills represented;
- 30 registered baseline templates;
- Grade 2 excludes multiplication/division;
- Grade 3 includes multiplication and division only within confirmed scope;
- every active template has a support or recovery route;
- `DIV-04` excluded from baseline;
- conditional nodes are clearly tagged.

## 14.2 Mathematical validity

For every template:

- deterministic answer/correctness function;
- no ambiguous answer;
- bounded generator;
- impossible cases excluded;
- at least 100 property-generated instances pass invariants per difficulty configuration;
- regrouping/borrowing cases verified to require the stated exchange;
- distractors never duplicate the correct answer.

## 14.3 Difficulty validity

- family-specific 1–5 map documented;
- expected difficulty monotonicity tested empirically;
- no accidental conflation of motor precision and mathematics;
- no compulsory speed pressure at conceptual levels;
- safety floor/ceiling behavior tested;
- changing one difficulty dimension does not silently alter unrelated dimensions.

## 14.4 Telemetry validity

- valid event order;
- `completed_task_count ≤ task_opportunity_count`;
- `correct_task_count ≤ completed_task_count`;
- `total_attempt_count ≥ completed_task_count` where completed tasks require at least one attempt;
- inactivity does not exceed session duration;
- quit-after-error is traceable to actual sequence;
- error runs derive from task outcomes;
- technical failures are not counted as mathematical errors;
- engagement/frustration/learner state are never sampled directly.

## 14.5 Boundary validity

- B→C contains exactly seven mastery values;
- no B item/hint/error/attempt/timing/BKT internals are consumed;
- C→3 includes only active contract fields;
- internal scaffold and task-instance fields remain internal;
- no population, dd_subtype, diagnosis, or hidden latent is exported;
- C-only sessions do not access cached B mastery.

## 14.6 Accessibility and safety

- every drag interaction has an alternative;
- target-size and contrast review passes;
- timing is adjustable or absent;
- pause/stop and reduced motion work;
- no color-only task meaning;
- recovery can be triggered at every difficulty floor;
- slow-but-accurate cases do not trigger false overload;
- technical-failure paths do not alter learner-state evidence.

## 14.7 Leakage/fairness

After generation, audit:

- family exposure by population;
- template exposure by population;
- difficulty exposure by population;
- reward/recovery/safety rates by population;
- task-count signatures;
- SF-038 depth-4 classifier balanced accuracy `< 0.70`, plus raw accuracy, majority baseline, macro-F1, one-vs-rest ROC-AUC, and confusion matrix.

No fixed population difference may override SF-038.

---

# 15. Implementation handoff

The next required artefact is:

`Component_C_Generator_v1.0/SPEC.md`

It must operationalize this catalogue without redefining it and must specify:

1. configuration loading;
2. grade and skill eligibility;
3. combined-session and C-only selection;
4. family/template selection;
5. family-specific difficulty-vector generation;
6. deterministic task-instance generation;
7. task event generation;
8. attempts, completion, latency, inactivity, quit, and safety generation using the active C parameter specification;
9. RL difficulty action and safety precedence;
10. session aggregation;
11. deterministic engagement/frustration/learner-state computation;
12. C→3 export;
13. reproducibility, property tests, leakage audits, and release gates.

---

# 16. Deferred research/product expansion

The following families from the broader research synthesis are valuable but are not required for the client baseline:

- Quick Quantity/subitizing support tasks;
- Fact Family House;
- standalone Story Mission family;
- separate Trade Ten family;
- separate Number-Line family;
- mixed-representation transcoding bank beyond baseline templates;
- multiplication–division inverse (`DIV-04`);
- optional fluency modes;
- LLM-controlled learner action selection.

They may be added only through a catalogue version change, curriculum review, and updated validation.

---

# 17. Approval checklist

| Check | Status |
|---|---|
| Seven skills covered | READY FOR REVIEW |
| Eight families frozen | READY FOR REVIEW |
| Thirty templates registered | READY FOR REVIEW |
| Grade 2/3 safeguards stated | READY FOR REVIEW |
| Deterministic correctness defined | READY FOR REVIEW |
| Difficulty architecture defined | READY FOR REVIEW |
| C scaffold/recovery ladder defined | READY FOR REVIEW |
| Telemetry mapping defined | READY FOR REVIEW |
| B→C boundary preserved | READY FOR REVIEW |
| C→3 compatibility preserved | READY FOR REVIEW |
| Population-neutral runtime rule stated | READY FOR REVIEW |
| Accessibility/safety requirements stated | READY FOR REVIEW |
| Formal Component C academic sign-off | PENDING |
| Exact conditional-node ranges | CALIBRATION_PENDING |
| Generator SPEC | NOT YET CREATED |
| C implementation | NOT YET CREATED |

Recommended owner disposition:

> **APPROVE WITH RECORDED CONDITIONS FOR COMPONENT C GENERATOR-SPEC DEVELOPMENT**

This wording is a technical owner-review recommendation, not evidence of formal academic approval.

---

# 18. References

## 18.1 External research and standards

1. Käser, T., Baschera, G.-M., Kohn, J., Kucian, K., Richtmann, V., Grond, U., Gross, M., & von Aster, M. (2013). *Design and evaluation of the computer-based training program Calcularis for enhancing numerical cognition*. Frontiers in Psychology, 4, 489. DOI: `10.3389/fpsyg.2013.00489`.
2. Wilson, A. J., Dehaene, S., Pinel, P., Revkin, S. K., Cohen, L., & Cohen, D. (2006). *Principles underlying the design of “The Number Race,” an adaptive computer game for remediation of dyscalculia*. Behavioral and Brain Functions, 2, 19. DOI: `10.1186/1744-9081-2-19`.
3. Wilson, A. J., Revkin, S. K., Cohen, D., Cohen, L., & Dehaene, S. (2006). *An open trial assessment of “The Number Race,” an adaptive computer game for remediation of dyscalculia*. Behavioral and Brain Functions, 2, 20. DOI: `10.1186/1744-9081-2-20`.
4. Kucian, K., Grond, U., Rotzer, S., Henzi, B., Schönmann, C., Plangger, F., Gälli, M., Martin, E., & von Aster, M. (2011). *Mental number line training in children with developmental dyscalculia*. NeuroImage, 57(3), 782–795. DOI: `10.1016/j.neuroimage.2011.01.070`.
5. World Wide Web Consortium. (2023, current Recommendation). *Web Content Accessibility Guidelines (WCAG) 2.2*.

## 18.2 Active local project sources

- `CURRENT_DIRECTORY_CONTENTS.md`
- `Registers_v0.3/R26-IT-138_Shared_Foundation_Decision_Register_v0.3.md`
- `Registers_v0.3/R26-IT-138_Component_C_Variable_Register_v0.3.md`
- `Study_Protocol_v1.0/R26-IT-138_Shared_Population_and_Study_Protocol_v1.0.md`
- `Boundary_Contracts_v1.0/R26-IT-138_Component_B_to_Component_C_Mastery_Contract_Spec_v1.0.md`
- `Boundary_Contracts_v1.0/R26-IT-138_Component_C_to_Component_3_Contract_Spec_v1.0.md`
- `Component_C_v1.0/R26-IT-138_Component_C_Empirical_Statistical_Parameters_v1.0.md`
- `Curriculum_v1.0/R26-IT-138_Shared_Math_Skill_and_Level_Taxonomy_v1.0.md`
- `Curriculum_v1.0/R26-IT-138_Grade_2_3_Math_Prerequisite_DAG_v1.0.md`
- `Curriculum_Research_v1.0/R26-IT-138_Grade_2_3_Curriculum_Source_Extraction_and_Research_Synthesis_v1.0.md`
- `Simulation_v1.0/R26-IT-138_Shared_Longitudinal_Learner_Simulator_Design_v1.0.md`
- `Simulation_v1.0/R26-IT-138_Population_Influence_and_Leakage_Control_Register_v1.0.md`
- `R26-IT-138_Component_C_Game_Task_Catalogue_Deep_Research_and_Design_Recommendations_v1.0.md`

## Appendix M — Machine-readable catalogue (component_c_game_task_catalogue)

**Added:** 2026-07-20, Phase C2.0 (structural transcription only -- no science changed, no
prose above this appendix altered or deleted). Mirrors how Component B embeds its
machine-readable catalogue (`Component_B_v1.0/...Item_and_Task_Set_Catalogue_v1.0.md` Section
11 / `component_b_item_catalogue`), for a future `component_c_generator/catalogue/loader.py`
(Phase C2.1, not built by this step) to consume.

**Transcription rule:** every value below is copied verbatim from this document's own Section 5
per-template tables, or from the global Section 9.1 / Section 10 / Section 11 rule blocks (cited
inline in the YAML as comments-equivalent key names). No numeric bound, discrete
`failure_condition`, per-template scaffold-level mapping, or per-template version/checksum is
invented -- those fields do not exist per-template anywhere in this document (see the Phase C2.0
build report for the full gap list). `null` values below are genuine table gaps in the source
(e.g. no "Error signatures" row for that template), not omissions by the transcriber.

**Family-ID naming note (flagged for an owner decision, not silently resolved):** the SPEC
(`Component_C_Generator_v1.0/SPEC.md` Section 7) names families `C-GF-01`..`C-GF-08`, while this
catalogue's own per-template IDs use family-specific prefixes (`C-CC`, `C-NP`, `C-MCL`, `C-BT`,
`C-JB`, `C-TC`, `C-EG`, `C-SF`) with no `C-GF-*` template ever appearing. The `family_id_mapping`
list below reconciles the two vocabularies by family **name**, which is unambiguous in both
documents (each `## 5.N C-GF-0N -- Family Name` header in Section 5 directly precedes that
family's own `C-XX-*` templates). No catalogue template ID was renamed to close this gap.

```yaml
component_c_game_task_catalogue:
  version: '1.0'
  status: PROPOSED_FOR_APPROVAL
  source_document: R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md
  transcription_scope_note: 'This block transcribes ONLY fields present in the catalogue''s own per-template
    tables (Section 5) plus the global section 9.1/10/11 rule blocks below. It intentionally excludes
    fields the SPEC''s loader-check list and GameTaskInstance shape (SPEC section 6.3/7) would eventually
    require but which do not exist per-template anywhere in this document: numeric/bounded operand-object
    generator ranges, a discrete failure_condition distinct from the correctness prose, a per-template
    C0-C4 scaffold-level mapping (only the global ladder vocabulary and free-text recovery prose exist),
    and a per-template version/checksum (only a single catalogue-wide version exists, matching how component_b_generator''s
    own ItemTemplate model carries no per-item version either). See the build report for the full gap
    list; none of these are invented here.'
  skills:
  - counting
  - number_sense
  - place_value
  - addition
  - subtraction
  - multiplication
  - division
  template_status_vocabulary:
  - BASELINE_ACTIVE
  - BASELINE_CONDITIONAL
  - DEFERRED_EXTENSION
  - RETIRED
  functional_role_vocabulary:
  - MAIN
  - SUPPORT
  - MAIN_SUPPORT
  - RECOVERY_ONLY
  scaffold_ladder_vocabulary:
    C0: no_scaffold
    C1: orienting_prompt
    C2: perceptual_structure
    C3: guided_action
    C4: recovery_task
  family_id_mapping:
  - game_family_id: C-GF-01
    family_name: Count and Collect
    template_id_prefix: C-CC
  - game_family_id: C-GF-02
    family_name: Number Path and Order
    template_id_prefix: C-NP
  - game_family_id: C-GF-03
    family_name: Match, Compare and Locate
    template_id_prefix: C-MCL
  - game_family_id: C-GF-04
    family_name: Build and Trade
    template_id_prefix: C-BT
  - game_family_id: C-GF-05
    family_name: Join and Bridge
    template_id_prefix: C-JB
  - game_family_id: C-GF-06
    family_name: Take Away and Compare
    template_id_prefix: C-TC
  - game_family_id: C-GF-07
    family_name: Equal Groups and Arrays
    template_id_prefix: C-EG
  - game_family_id: C-GF-08
    family_name: Share Fairly
    template_id_prefix: C-SF
  global_required_task_event_sequence:
    mandatory:
    - game_task_offered
    - game_task_started
    - action_performed
    - answer_submitted_or_goal_state_reached
    - answer_evaluated
    - 'terminal_event: one of game_task_completed, game_task_skipped, game_task_quit'
    optional:
    - scaffold_requested
    - scaffold_shown
    - retry_started
    - pause_started
    - pause_ended
    - difficulty_changed
    - recovery_task_started
    - reward_delivered
    - safety_override_triggered
    - technical_issue
  global_feedback_reward_recovery_safety_rules:
    feedback:
    - immediate, neutral correctness feedback
    - show the mathematical transformation where useful
    - no shame, loss of all progress, or public comparison
    - no child-facing diagnosis or risk language
    - no live LLM-generated child-facing scaffold in baseline v1
    reward_may_acknowledge:
    - completion
    - appropriate persistence
    - recovery after difficulty
    - accurate task performance
    - safe continuation
    reward_prohibitions:
    - must not be based only on speed
    - must not directly overwrite engagement, frustration, or learner state
    recovery_requirements:
    - remain within the same target skill or an approved prerequisite
    - use difficulty level 1
    - remove time pressure
    - increase visual/perceptual structure
    - avoid punitive loss
    - log recovery_task_started
    - return to a normal task only after the active safety rules allow it
    safety_precedence:
    - a safety trigger can force safety_decrease or safety_scaffold
    - difficulty cannot decrease below 1
    - after a safety override, increases are blocked for the configured next decisions
    - safety overrides are logged and aggregated
    - RL cannot bypass safety
  global_accessibility_requirements:
  - never communicate mathematical meaning by color alone
  - provide tap/select alternatives to dragging
  - separate mathematical placement tolerance from motor error
  - use sufficiently large targets and spacing
  - support adjustable/untimed modes
  - provide pause/stop controls
  - provide reduced-motion mode
  - avoid flashing
  - provide audio and text alternatives where instructions use language
  - use short, consistent instructions
  - avoid decorative clutter that obscures quantities
  - maintain readable contrast and non-text contrast
  - distinguish technical failure from learner error
  - ensure technical failure does not produce disengagement/frustration evidence
  deferred_out_of_baseline:
  - node: DIV-04
    reason: multiplication-division inverse tasks are deliberately deferred from baseline v1 until curriculum/supervisor
      confirmation
  templates:
  - game_family_id: C-GF-01
    family_name: Count and Collect
    game_task_template_id: C-CC-01
    template_title: Mark and Count Objects
    primary_skill_ids:
    - counting
    curriculum_node_ids:
    - CNT-02
    - CNT-03
    grade_scope_text: Grade 2 baseline; Grade 3 review
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    representations_note: null
    learner_action: Tap/select every object exactly once, then submit total.
    correctness: Every valid object selected once; no invalid object selected; submitted total equals
      set cardinality.
    error_signatures:
    - omission
    - double count
    - invalid-object selection
    - cardinality mismatch
    main_difficulty_levers: set size, spatial scatter, overlap, distractor objects, visible count markers.
    recovery: Align objects; mark counted objects automatically; remove distractors.
  - game_family_id: C-GF-01
    family_name: Count and Collect
    game_task_template_id: C-CC-02
    template_title: Produce the Requested Set
    primary_skill_ids:
    - counting
    curriculum_node_ids:
    - CNT-04
    grade_scope_text: Grade 2
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    - symbolic
    representations_note: null
    learner_action: Move/select exactly N objects into a target area.
    correctness: Final target area contains exactly N valid objects.
    error_signatures:
    - under-production
    - over-production
    - invalid-object inclusion
    main_difficulty_levers: N, available-object count, distractors, visual organization, numeral/audio
      prompt.
    recovery: Ten-frame or linear slots; snap-to-slot; count markers.
  - game_family_id: C-GF-01
    family_name: Count and Collect
    game_task_template_id: C-CC-03
    template_title: Count and Match Numeral
    primary_skill_ids:
    - counting
    - number_sense
    curriculum_node_ids:
    - CNT-03
    - NS-02
    grade_scope_text: Grade 2 baseline; Grade 3 review
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - pictorial_objects
    - symbolic
    - mixed_representation
    representations_note: null
    learner_action: Count a set and choose/enter the matching numeral.
    correctness: Selected numeral equals set cardinality.
    error_signatures:
    - neighboring numeral
    - reversed digit where applicable
    - random mismatch
    main_difficulty_levers: set size, arrangement, numeral distractor distance, symbol entry mode.
    recovery: Object alignment, counted-object highlighting, reduced distractors.
  - game_family_id: C-GF-01
    family_name: Count and Collect
    game_task_template_id: C-CC-04
    template_title: Conservation Rearrangement
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-07
    grade_scope_text: Grade 2
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    representations_note: null
    learner_action: Judge whether quantity changed after the same objects are rearranged.
    correctness: “Same” when object identity/count is preserved; “changed” only in controlled add/remove
      trials.
    error_signatures:
    - spacing bias
    - object-size bias
    - arrangement bias
    main_difficulty_levers: spacing difference, layout change, controlled add/remove catch trials.
    recovery: Animate one-to-one correspondence between pre/post arrangements.
  - game_family_id: C-GF-02
    family_name: Number Path and Order
    game_task_template_id: C-NP-01
    template_title: Continue a Forward Sequence
    primary_skill_ids:
    - counting
    curriculum_node_ids:
    - CNT-01
    - CNT-05
    grade_scope_text: Grade 2 foundation; Grade 3 review
    status: BASELINE_CONDITIONAL
    status_note: because full Grade 2 range remains pending
    functional_role: SUPPORT
    representations:
    - symbolic_sequence
    - verbal
    - number_line
    representations_note: null
    learner_action: Select or enter the next number(s).
    correctness: Each next value equals prior value + 1.
    error_signatures: null
    main_difficulty_levers: start value, sequence length, missing position, visible number-line support.
    recovery: Show adjacent numbers and animate +1 jumps.
  - game_family_id: C-GF-02
    family_name: Number Path and Order
    game_task_template_id: C-NP-02
    template_title: Continue a Backward Sequence
    primary_skill_ids:
    - counting
    curriculum_node_ids:
    - CNT-05
    grade_scope_text: Grades 2–3
    status: BASELINE_CONDITIONAL
    status_note: null
    functional_role: SUPPORT
    representations:
    - symbolic_sequence
    - verbal
    - number_line
    representations_note: null
    learner_action: Select or enter preceding number(s).
    correctness: Each next response equals prior value − 1.
    error_signatures: null
    main_difficulty_levers: start value, length, hidden terms, support visibility.
    recovery: Visible descending number line; one guided −1 step.
  - game_family_id: C-GF-02
    family_name: Number Path and Order
    game_task_template_id: C-NP-03
    template_title: Skip Count by 2, 5, or 10
    primary_skill_ids:
    - counting
    curriculum_node_ids:
    - CNT-06
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - pictorial_groups
    - number_line
    - symbolic_sequence
    representations_note: null
    learner_action: Continue or repair an equal-step sequence.
    correctness: Consecutive values differ by the configured step 2, 5, or 10.
    error_signatures: null
    main_difficulty_levers: step size, start value, hidden positions, group/line/symbolic representation.
    recovery: Show equal groups and animated number-line jumps.
  - game_family_id: C-GF-02
    family_name: Number Path and Order
    game_task_template_id: C-NP-04
    template_title: Order Number Cards
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-05
    grade_scope_text: Grade 3; Grade 2 only after range review
    status: BASELINE_ACTIVE
    status_note: for Grade 3
    functional_role: MAIN_SUPPORT
    representations:
    - number_cards
    - symbolic
    - number_line
    representations_note: null
    learner_action: Arrange values ascending or descending.
    correctness: Strict configured order; duplicates only when explicitly permitted.
    error_signatures: null
    main_difficulty_levers: list length, numerical closeness, direction, number range, number-line support.
    recovery: Reduce list to three values; show endpoints/relative positions.
  - game_family_id: C-GF-03
    family_name: Match, Compare and Locate
    game_task_template_id: C-MCL-01
    template_title: Numeral–Quantity Match
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-01
    - NS-02
    grade_scope_text: Grade 2 1–50 minimum; Grade 3 through approved ranges
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - symbolic
    - pictorial_objects
    - dot_sets
    - verbal
    representations_note: verbal where audio is available
    learner_action: Match two equivalent number representations.
    correctness: Matched representations encode the same cardinal value.
    error_signatures: null
    main_difficulty_levers: number range, representation pair, distractor similarity, spoken/written mode.
    recovery: Display a third bridging representation.
  - game_family_id: C-GF-03
    family_name: Match, Compare and Locate
    game_task_template_id: C-MCL-02
    template_title: Compare Quantities
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-03
    grade_scope_text: Grade 2 intervention scope; Grade 3 review
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - dot_sets
    - pictorial_objects
    representations_note: null
    learner_action: Select larger, smaller, or equal quantity.
    correctness: Based on exact cardinalities, not visual area.
    error_signatures: null
    main_difficulty_levers: numerical ratio/distance, equality trials, density, object size/area controls.
    recovery: Pair objects one-to-one or reveal matching numerals after response.
  - game_family_id: C-GF-03
    family_name: Match, Compare and Locate
    game_task_template_id: C-MCL-03
    template_title: Compare Numerals
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-04
    grade_scope_text: Grade 3 below 1000; Grade 2 small-range proposal
    status: BASELINE_ACTIVE
    status_note: for Grade 3
    functional_role: MAIN_SUPPORT
    representations:
    - symbolic
    - number_line
    representations_note: null
    learner_action: Choose larger/smaller/equal or place comparison sign.
    correctness: Exact integer comparison.
    error_signatures: null
    main_difficulty_levers: number range, numerical distance, digit similarity, place-value conflict.
    recovery: Base-ten or number-line visualization.
  - game_family_id: C-GF-03
    family_name: Match, Compare and Locate
    game_task_template_id: C-MCL-04
    template_title: Number-Line Landing
    primary_skill_ids:
    - number_sense
    curriculum_node_ids:
    - NS-06
    grade_scope_text: Grades 2–3 intervention extension
    status: BASELINE_CONDITIONAL
    status_note: null
    functional_role: MAIN
    representations:
    - number_line
    - symbolic
    - pictorial_objects
    representations_note: null
    learner_action: Tap or move a marker to a target position.
    correctness: Mathematical interval/location error within configured tolerance; motor error tracked
      separately.
    error_signatures: null
    main_difficulty_levers: interval range, tick labels, midpoint visibility, target type, tolerance.
    recovery: Labeled ticks, highlighted sub-interval, guided example jump.
  - game_family_id: C-GF-04
    family_name: Build and Trade
    game_task_template_id: C-BT-01
    template_title: Build Tens and Ones
    primary_skill_ids:
    - place_value
    curriculum_node_ids:
    - PV-01
    - PV-02
    grade_scope_text: Grade 2
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - base_ten_blocks
    - place_value_chart
    - symbolic
    representations_note: null
    learner_action: Build a two-digit number or decode blocks into tens/ones.
    correctness: number = 10 × tens + ones, with canonical ones 0–9 unless non-canonical form is intentional.
    error_signatures: null
    main_difficulty_levers: number range, zero digit, direction of transcoding, labels visible/hidden.
    recovery: Labeled columns and snap-to-place behavior.
  - game_family_id: C-GF-04
    family_name: Build and Trade
    game_task_template_id: C-BT-02
    template_title: Build Hundreds, Tens and Ones
    primary_skill_ids:
    - place_value
    curriculum_node_ids:
    - PV-03
    - PV-04
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: with exact range governed by curriculum config
    functional_role: MAIN
    representations:
    - base_ten_blocks
    - place_value_chart
    - expanded_form
    - symbolic
    representations_note: null
    learner_action: Build/decompose a three-digit number.
    correctness: number = 100 × hundreds + 10 × tens + ones.
    error_signatures: null
    main_difficulty_levers: zeros in places, compose/decompose direction, representation support.
    recovery: Place-value labels; one component pre-filled.
  - game_family_id: C-GF-04
    family_name: Build and Trade
    game_task_template_id: C-BT-03
    template_title: Trade Ten Ones for One Ten
    primary_skill_ids:
    - place_value
    curriculum_node_ids:
    - PV-05
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - base_ten_blocks
    - place_value_chart
    - symbolic_algorithm
    representations_note: null
    learner_action: Exchange exactly ten ones for one ten.
    correctness: Quantity conserved and post-trade place-value counts valid.
    error_signatures: null
    main_difficulty_levers: starting block count, guided/unguided exchange, addition context.
    recovery: Animated exchange, then learner repeats.
  - game_family_id: C-GF-04
    family_name: Build and Trade
    game_task_template_id: C-BT-04
    template_title: Ungroup One Ten into Ten Ones
    primary_skill_ids:
    - place_value
    curriculum_node_ids:
    - PV-06
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - base_ten_blocks
    - place_value_chart
    - symbolic_algorithm
    representations_note: null
    learner_action: Exchange one ten for ten ones.
    correctness: Quantity conserved and post-trade counts valid.
    error_signatures: null
    main_difficulty_levers: starting configuration, borrowing context, visibility of transformation.
    recovery: Animated exchange with highlighted destination column.
  - game_family_id: C-GF-05
    family_name: Join and Bridge
    game_task_template_id: C-JB-01
    template_title: Combine Two Groups
    primary_skill_ids:
    - addition
    curriculum_node_ids:
    - ADD-01
    grade_scope_text: Grade 2 baseline; Grade 3 review
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    - verbal_story
    representations_note: null
    learner_action: Move/join two sets and identify total.
    correctness: Total equals cardinality of union of disjoint valid sets.
    error_signatures: null
    main_difficulty_levers: addend sizes, arrangement, symbolic prompt, story load.
    recovery: Count-all path with visible markers.
  - game_family_id: C-GF-05
    family_name: Join and Bridge
    game_task_template_id: C-JB-02
    template_title: Count On from an Addend
    primary_skill_ids:
    - addition
    curriculum_node_ids:
    - ADD-02
    grade_scope_text: Grades 2–3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: SUPPORT
    representations:
    - number_line
    - verbal
    - symbolic
    representations_note: null
    learner_action: Start at one addend and make the required forward jumps.
    correctness: Final position equals sum; jump count/size matches configured strategy.
    error_signatures: null
    main_difficulty_levers: addends, start-from-larger support, visible jumps, missing final value.
    recovery: Highlight larger addend and animate first jump.
  - game_family_id: C-GF-05
    family_name: Join and Bridge
    game_task_template_id: C-JB-03
    template_title: Single-Digit Addition
    primary_skill_ids:
    - addition
    curriculum_node_ids:
    - ADD-03
    grade_scope_text: Grade 2
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN
    representations:
    - symbolic
    - pictorial_objects
    - ten_frame
    representations_note: null
    learner_action: Solve two-single-digit-addend task within configured curriculum envelope.
    correctness: Exact integer sum.
    error_signatures: null
    main_difficulty_levers: sum range, visual support, missing-value form, distractor distance.
    recovery: Ten-frame or object model; no forced timer.
  - game_family_id: C-GF-05
    family_name: Join and Bridge
    game_task_template_id: C-JB-04
    template_title: Two-Digit Addition and Regrouping
    primary_skill_ids:
    - addition
    curriculum_node_ids:
    - ADD-04
    - ADD-05
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: with exact operand/regrouping bands CALIBRATION_PENDING
    functional_role: MAIN
    representations:
    - base_ten_blocks
    - place_value_chart
    - symbolic_algorithm
    - verbal_story
    representations_note: null
    learner_action: Add two numbers; regroup where configured.
    correctness: Exact sum plus valid exchange sequence where manipulation is required.
    error_signatures: null
    main_difficulty_levers: no-regroup/regroup, number of digits, missing step, representation support.
    recovery: Switch to C-BT-03, then return to an easier addition instance.
  - game_family_id: C-GF-06
    family_name: Take Away and Compare
    game_task_template_id: C-TC-01
    template_title: Remove Objects
    primary_skill_ids:
    - subtraction
    curriculum_node_ids:
    - SUB-01
    grade_scope_text: Grade 2 baseline; Grade 3 review
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    - verbal_story
    representations_note: null
    learner_action: Remove specified quantity and identify remainder.
    correctness: remainder = initial_count − removed_count; removed count cannot exceed initial count.
    error_signatures: null
    main_difficulty_levers: initial quantity, removal size, hidden/visible remainder, language load.
    recovery: One-by-one animated removal with count markers.
  - game_family_id: C-GF-06
    family_name: Take Away and Compare
    game_task_template_id: C-TC-02
    template_title: Compare and Find the Difference
    primary_skill_ids:
    - subtraction
    curriculum_node_ids:
    - SUB-02
    grade_scope_text: Grades 2–3
    status: BASELINE_CONDITIONAL
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - pictorial_comparison
    - number_line
    - verbal_story
    representations_note: null
    learner_action: Pair or align two quantities and identify how many more/less.
    correctness: Absolute or directed difference according to prompt.
    error_signatures: null
    main_difficulty_levers: quantity distance, representation, directed language, alignment support.
    recovery: One-to-one pairing and highlighted unmatched objects.
  - game_family_id: C-GF-06
    family_name: Take Away and Compare
    game_task_template_id: C-TC-03
    template_title: Subtraction Within 9
    primary_skill_ids:
    - subtraction
    curriculum_node_ids:
    - SUB-03
    grade_scope_text: Grade 2
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN
    representations:
    - symbolic
    - pictorial_objects
    - number_line
    representations_note: null
    learner_action: Solve a − b, with a ≤ 9, 0 ≤ b ≤ a.
    correctness: Exact non-negative difference.
    error_signatures: null
    main_difficulty_levers: minuend, subtrahend, visual support, missing-value form.
    recovery: Object removal or backward number-line jumps.
  - game_family_id: C-GF-06
    family_name: Take Away and Compare
    game_task_template_id: C-TC-04
    template_title: Two-Digit Subtraction and Borrowing
    primary_skill_ids:
    - subtraction
    curriculum_node_ids:
    - SUB-04
    - SUB-05
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: exact borrowing bands CALIBRATION_PENDING
    functional_role: MAIN
    representations:
    - base_ten_blocks
    - place_value_chart
    - symbolic_algorithm
    - verbal_story
    representations_note: null
    learner_action: Subtract two numbers; ungroup where configured.
    correctness: Exact difference plus valid ungrouping sequence where manipulation is required.
    error_signatures: null
    main_difficulty_levers: no-borrow/borrow, number range, missing step, support.
    recovery: Switch to C-BT-04, then return to easier subtraction.
  - game_family_id: C-GF-07
    family_name: Equal Groups and Arrays
    game_task_template_id: C-EG-01
    template_title: Build Equal Groups
    primary_skill_ids:
    - multiplication
    curriculum_node_ids:
    - MUL-01
    grade_scope_text: Grade 3 only
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - pictorial_groups
    - concrete_simulated
    - symbolic
    representations_note: null
    learner_action: Create number_of_groups groups of equal size.
    correctness: Every group has configured size and total equals product.
    error_signatures: null
    main_difficulty_levers: group count, group size, pre-structured containers, symbolic link.
    recovery: Containers shown; one group pre-filled.
  - game_family_id: C-GF-07
    family_name: Equal Groups and Arrays
    game_task_template_id: C-EG-02
    template_title: Build or Read an Array
    primary_skill_ids:
    - multiplication
    curriculum_node_ids:
    - MUL-02
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN
    representations:
    - array
    - symbolic
    - pictorial_groups
    representations_note: null
    learner_action: Build rows/columns from an expression or identify expression/product from an array.
    correctness: Rectangular equal-row/column structure and correct product.
    error_signatures: null
    main_difficulty_levers: row/column counts, orientation, missing factor/product, grid support.
    recovery: Grid lines and one completed row.
  - game_family_id: C-GF-07
    family_name: Equal Groups and Arrays
    game_task_template_id: C-EG-03
    template_title: Facts for 2, 5, and 10
    primary_skill_ids:
    - multiplication
    curriculum_node_ids:
    - MUL-03
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - symbolic_sequence
    - array
    - pictorial_groups
    - symbolic
    representations_note: null
    learner_action: Complete equal-step facts or match fact to model.
    correctness: Exact product for multipliers 2, 5, or 10 within approved Grade 3 range.
    error_signatures: null
    main_difficulty_levers: table, multiplier, model visibility, missing-factor form.
    recovery: Skip-count sequence or array model; no speed-only scoring.
  - game_family_id: C-GF-08
    family_name: Share Fairly
    game_task_template_id: C-SF-01
    template_title: Equal Sharing
    primary_skill_ids:
    - division
    curriculum_node_ids:
    - DIV-01
    grade_scope_text: Grade 3 only
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN_SUPPORT
    representations:
    - concrete_simulated
    - pictorial_objects
    - verbal_story
    representations_note: null
    learner_action: Distribute objects equally among recipients.
    correctness: All recipients have equal count and all objects are allocated when no remainder is allowed.
    error_signatures: null
    main_difficulty_levers: total, recipient count, pre-allocated objects, story load.
    recovery: Round-robin guidance and recipient slots.
  - game_family_id: C-GF-08
    family_name: Share Fairly
    game_task_template_id: C-SF-02
    template_title: Form Equal Groups
    primary_skill_ids:
    - division
    curriculum_node_ids:
    - DIV-02
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN
    representations:
    - pictorial_groups
    - concrete_simulated
    - symbolic
    representations_note: null
    learner_action: Partition total into groups of configured size and determine group count.
    correctness: Each group has exact size; group count × group size = total.
    error_signatures: null
    main_difficulty_levers: total, group size, container support, symbolic link.
    recovery: Group containers visible; one group modeled.
  - game_family_id: C-GF-08
    family_name: Share Fairly
    game_task_template_id: C-SF-03
    template_title: Divide by 2 without Remainder
    primary_skill_ids:
    - division
    curriculum_node_ids:
    - DIV-03
    grade_scope_text: Grade 3
    status: BASELINE_ACTIVE
    status_note: null
    functional_role: MAIN
    representations:
    - symbolic
    - concrete_simulated
    - pictorial_groups
    representations_note: null
    learner_action: Solve approved even-number division-by-2 cases.
    correctness: Exact quotient; dividend even and within curriculum-approved range.
    error_signatures: null
    main_difficulty_levers: dividend magnitude, concrete/symbolic mode, missing-value form.
    recovery: Split objects between two visible recipients.
```

---

**End of Component C Game-Task Catalogue v1.0**
