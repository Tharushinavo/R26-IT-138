# NB00 — Simulator audit (sections 3–11)

_Literature-informed synthetic data — not clinical evidence. Simulation-only; not approved for use with children._

Plain-markdown export of sections 3–11 of `notebooks/NB00_setup_and_simulator_audit.ipynb` (executed notebook is the source of truth; section 1–2 environment and outcome-model probe are in the notebook, with `figures/00_p_correct_by_difficulty.png`). Yass pin `8d552a11af01d4fc11f00070e769e3ef83ad9b3a`. Tables are the executed outputs; Findings are quoted from the notebook.

## 3. What responds to difficulty?

Trace table first (producer → consumer, `file:line`), then an empirical probe: `generate_task_gameplay` at each
difficulty level, **2,000 seeded tasks per level** (200 learners-ids × 10 task slots), mid learner, combined mode,
mastery 0.5. The same seed lineages are used at every level (common random numbers), so a quantity that does not
depend on difficulty is *exactly* identical across levels.

```text
                       quantity                class                                                                                                       producer -> consumer trace (file:line)  \
0        P(correct) per attempt               direct  session.py:216-230 / selector -> task_instance.difficulty_level; attempt_loop.py:178-187 passes it to outcome_model.py:43-48 (combined: ...
1            number of attempts  indirect-via-errors  p fixed per task (attempt_loop.py:178-187); loop attempt_loop.py:193-303 repeats until a correct answer (L279-281) or cap (L285-291, max...
2                       latency               direct                    latency.py:43 difficulty_shift = 0.06*(d-3) -> L47-54 log_latency; called at attempt_loop.py:253-256; clock advanced L262
3         timeout (no response)               direct                                                        latency.py:57-58 raw_sec >= 90 s -> attempt_loop.py:257-260 quit(timeout_no_response)
4              quit_after_error  indirect-via-errors                  decisions.py:28-37 takes (consecutive_error_max, persistence) only - no difficulty argument; called attempt_loop.py:296-300
5     quit_without_recent_error                 none                               attempt_loop.py:203-206, constant config.quit.quit_without_recent_error_probability (0.01), first attempt only
6                          skip                 none                                                    attempt_loop.py:198-201, constant config.quit.skip_probability (0.02), first attempt only
7               technical issue                 none                                                                                           attempt_loop.py:209-213, constant 0.01 per attempt
8  pauses (learner / technical)                 none                                                                                   attempt_loop.py:215-233, constants 0.08 / 0.02 per attempt
9      scaffold request / level  indirect-via-errors                                request: attempt_loop.py:246-250 constant 0.10; level decided attempt_loop.py:239-245 from consecutive_errors

                                                                      note
0               Combined: only when d_norm > mastery. c_only: every level.
1        Geometric in P(correct); difficulty acts only through P(correct).
2                               Weak: +-0.12 log-units across levels 1..5.
3  Direct through latency but vanishingly small (see timeout table below).
4              Rises with the error streak, which is driven by P(correct).
5                              Independent of difficulty, mastery, errors.
6                                               Independent of everything.
7              Per-attempt: more attempts -> more exposure (second order).
8                                               Independent of difficulty.
9                                          Level follows the error streak.
component_c_generator/behaviour/attempt_loop.py: 196          # --- pre-attempt checks (only meaningful before the first submitted attempt) ---
component_c_generator/behaviour/attempt_loop.py: 197          if attempt_index == 1:
component_c_generator/behaviour/attempt_loop.py: 198              skip_rng = _rng(gseeds.skip_lineage(attempt))
component_c_generator/behaviour/attempt_loop.py: 199              if _bernoulli(skip_rng, config.quit.skip_probability):
component_c_generator/behaviour/attempt_loop.py: 200                  builder.emit("game_task_skipped", attempt, terminal_reason="skipped")
component_c_generator/behaviour/attempt_loop.py: 201                  return GameplayResult(events=tuple(builder.events))
component_c_generator/behaviour/attempt_loop.py: 202
component_c_generator/behaviour/attempt_loop.py: 203              quit_early_rng = _rng(gseeds.quit_lineage(attempt))
component_c_generator/behaviour/attempt_loop.py: 204              if _bernoulli(quit_early_rng, config.quit.quit_without_recent_error_probability):
component_c_generator/behaviour/attempt_loop.py: 205                  builder.emit("game_task_quit", attempt, terminal_reason="quit_without_recent_error")
component_c_generator/behaviour/attempt_loop.py: 206                  return GameplayResult(events=tuple(builder.events))
component_c_generator/behaviour/attempt_loop.py: 207
component_c_generator/behaviour/attempt_loop.py: 208          # --- technical issue (full task-ending contamination) ---
component_c_generator/behaviour/attempt_loop.py: 209          technical_rng = _rng(gseeds.technical_issue_lineage(attempt))
component_c_generator/behaviour/attempt_loop.py: 210          if _bernoulli(technical_rng, config.technical.probability_per_attempt):
component_c_generator/behaviour/attempt_loop.py: 211              builder.emit("technical_issue", attempt, technical_flag=True)
component_c_generator/behaviour/attempt_loop.py: 212              builder.emit("game_task_quit", attempt, technical_flag=True, terminal_reason="technical_issue")
component_c_generator/behaviour/attempt_loop.py: 213              return GameplayResult(events=tuple(builder.events))

component_c_generator/behaviour/attempt_loop.py: 293          # C3 §13.2: the ONLY decision governing retry-vs-quit after a non-terminal incorrect
component_c_generator/behaviour/attempt_loop.py: 294          # attempt is the quit-after-error model (C Parameters §8.4 logit). If it does not fire,
component_c_generator/behaviour/attempt_loop.py: 295          # the loop retries -- there is no separate retry-probability gate.
component_c_generator/behaviour/attempt_loop.py: 296          quit_rng = _rng(gseeds.quit_lineage(attempt))
component_c_generator/behaviour/attempt_loop.py: 297          p_quit = quit_after_error_probability(config.quit, consecutive_errors, local_state.c_persistence_tendency)
component_c_generator/behaviour/attempt_loop.py: 298          if _bernoulli(quit_rng, p_quit):
component_c_generator/behaviour/attempt_loop.py: 299              builder.emit("game_task_quit", attempt, terminal_reason="quit_after_error")
component_c_generator/behaviour/attempt_loop.py: 300              return GameplayResult(events=tuple(builder.events))
```

```text
       n_tasks  n_attempted  completed  eventual_correct  first_attempt_correct  mean_attempts  mean_err_run  quit_after_error  quit_any  skipped  technical  timeout  mean_latency_s  mean_scaffolds
level
1         2000         1927     0.9425            0.9425                 0.8531         1.1505        0.1660            0.0190    0.0370   0.0205      0.010      0.0         10.6251          0.1065
2         2000         1927     0.9425            0.9425                 0.8531         1.1505        0.1660            0.0190    0.0370   0.0205      0.010      0.0         11.2821          0.1065
3         2000         1927     0.9425            0.9425                 0.8531         1.1505        0.1660            0.0190    0.0370   0.0205      0.010      0.0         11.9797          0.1065
4         2000         1927     0.9150            0.9150                 0.7260         1.3181        0.3550            0.0435    0.0645   0.0205      0.013      0.0         12.8063          0.1250
5         2000         1927     0.8540            0.8540                 0.5537         1.6238        0.7105            0.1005    0.1255   0.0205      0.017      0.0         13.4808          0.1525

terminal_reason mix by level:

terminal  completed_correct  quit_after_error  quit_without_recent_error  skipped  technical_issue
level
1                    0.9425            0.0190                      0.008   0.0205            0.010
2                    0.9425            0.0190                      0.008   0.0205            0.010
3                    0.9425            0.0190                      0.008   0.0205            0.010
4                    0.9150            0.0435                      0.008   0.0205            0.013
5                    0.8540            0.1005                      0.008   0.0205            0.017

c_only (fallback model) outcomes by level:

       n_tasks  n_attempted  completed  eventual_correct  first_attempt_correct  mean_attempts  mean_err_run  quit_after_error  quit_any  skipped  technical  timeout  mean_latency_s  mean_scaffolds
level
1         2000         1927     0.9270            0.9270                 0.7763         1.2392        0.2670            0.0335    0.0525   0.0205     0.0110      0.0         10.6575          0.1205
2         2000         1927     0.9030            0.9030                 0.6809         1.3887        0.4350            0.0545    0.0765   0.0205     0.0140      0.0         11.3684          0.1340
3         2000         1927     0.8685            0.8685                 0.5864         1.5599        0.6345            0.0860    0.1110   0.0205     0.0170      0.0         12.0023          0.1480
4         2000         1927     0.8150            0.8150                 0.4826         1.7613        0.8820            0.1390    0.1645   0.0205     0.0175      0.0         12.7295          0.1660
5         2000         1927     0.7500            0.7500                 0.3819         2.0322        1.2080            0.2020    0.2295   0.0205     0.0195      0.0         13.4785          0.1920

nominal P(correct) (outcome_model) vs REALIZED first-attempt correctness (after choose_action + evaluate):


       mode  mastery  level  n_attempted  nominal_p  realized_first_attempt    diff       z
0  combined      0.5      1         1927     0.8389                  0.8531  0.0142  1.7014
1  combined      0.5      2         1927     0.8389                  0.8531  0.0142  1.7014
2  combined      0.5      3         1927     0.8389                  0.8531  0.0142  1.7014
3  combined      0.5      4         1927     0.7109                  0.7260  0.0150  1.4573
4  combined      0.5      5         1927     0.5374                  0.5537  0.0163  1.4334
5    c_only      NaN      1         1927     0.7638                  0.7763  0.0125  1.2959
6    c_only      NaN      2         1927     0.6669                  0.6809  0.0140  1.3026
7    c_only      NaN      3         1927     0.5685                  0.5864  0.0179  1.5882
8    c_only      NaN      4         1927     0.4686                  0.4826  0.0140  1.2308
9    c_only      NaN      5         1927     0.3672                  0.3819  0.0147  1.3379
mean realized-nominal: combined +0.0148 (pooled z=3.51); c_only +0.0146 (pooled z=3.02)
component_c_generator/behaviour/action_provider.py:   1  """``ActionProvider`` (C3 §7.1/§7.2) -- the synthetic generator's action-generation seam (D2).
component_c_generator/behaviour/action_provider.py:   2
component_c_generator/behaviour/action_provider.py:   3  ``choose_action`` generates a real, syntactically valid candidate action from the template's
component_c_generator/behaviour/action_provider.py:   4  own ``valid_action_space`` shape. It is deliberately biased toward a target outcome
component_c_generator/behaviour/action_provider.py:   5  (``target_correct``) using ONLY the instance's own ``correct_answer_payload`` -- but it never
component_c_generator/behaviour/action_provider.py:   6  computes or asserts correctness itself: the returned action is always passed to the committed
component_c_generator/behaviour/action_provider.py:   7  C2.1 ``evaluate()`` (the sole correctness authority, C3 §7.2) and the bias may occasionally miss
component_c_generator/behaviour/action_provider.py:   8  (a "correct-biased" draw is not guaranteed correct, and vice versa, mirroring how a real learner
component_c_generator/behaviour/action_provider.py:   9  sometimes slips) -- this is intentional realism, not a defect: whatever the evaluator returns is
component_c_generator/behaviour/action_provider.py:  10  what gets stored, unconditionally.
component_c_generator/behaviour/action_provider.py:  11
component_c_generator/behaviour/action_provider.py:  12  The per-template action-SHAPE knowledge here (which JSON keys/types a candidate action needs)
```

```text
   skipped identical task-by-task across levels: True
quit_without_recent_error identical task-by-task across levels: True
share of COMPLETED tasks with correct_task=True: 1.0

   level  mu_log  median_latency_s  z_to_timeout  p_timeout_per_attempt
0      1    2.28              9.78          5.55           1.432241e-08
1      2    2.34             10.38          5.40           3.340894e-08
2      3    2.40             11.02          5.25           7.624629e-08
3      4    2.46             11.70          5.10           1.702542e-07
4      5    2.52             12.43          4.95           3.719757e-07
```

### Findings — step 3


**Trace + probe (2,000 tasks per level, combined, mastery 0.5, mid learner, same seeds at every level):**

| quantity | level 1 → 5 | class |
|---|---|---|
| first-attempt correct | 0.8531, 0.8531, 0.8531, **0.7260**, **0.5537** | **direct** (via P(correct); only above d_norm = mastery) |
| mean attempts | 1.1505 (×3), 1.3181, 1.6238 | indirect (geometric in P) |
| quit_after_error | 0.0190 (×3), 0.0435, **0.1005** | indirect-via-errors (`decisions.py:28-37` has no difficulty argument) |
| any quit | 0.0370 → 0.1255 | indirect |
| task eventually correct (= completed) | 0.9425 (×3), 0.9150, 0.8540 | indirect |
| latency (s) | 10.63, 11.28, 11.98, 12.81, 13.48 (+27%) | direct but weak (`latency.py:43`) |
| timeout | 0 observed; analytic 1.4e-8 … 3.7e-7 per attempt | direct, negligible |
| skip | 0.0205 at every level, **identical task-by-task** | none |
| quit_without_recent_error | 0.008 at every level, **identical task-by-task** | none |
| technical issue | 0.010 → 0.017 (only because more attempts mean more exposure) | none (second order) |

- **c_only** (same seeds): first-attempt correct 0.7763, 0.6809, 0.5864, 0.4826, 0.3819; quit_after_error 0.0335 → **0.2020**; completed 0.927 → 0.750.
- **Retries make `correct_task` uninformative.** `max_attempts` = 10 (`gameplay_config.py:239`), so **the share of completed tasks with `correct_task=True` is 1.000**. Eventual correctness equals the completion rate, and difficulty acts mainly on *first-attempt* correctness and attempts. This matters for §6 and §11.
- **Realized vs nominal.** Realized first-attempt correctness is higher than the nominal P at every level. The mean excess is **+0.0148** (combined) and **+0.0146** (c_only), 1.2–1.8 points per level. The per-level z-scores are 1.2–1.7. The pooled z of 3.5 / 3.0 is overstated because the levels share seeds. The documented cause is `action_provider.py:7-10`: a "wrong" draw can still evaluate as correct. It is small, but NB03's calibration compares realized rates, not nominal ones.

![outcomes by difficulty](figures/00_outcomes_by_difficulty.png)

## 4. Is there any penalty for a too-easy task?

Hypothesis (master plan §6, expected finding): **no**. R0 requires the full chain, so we check every place a
too-easy task could be punished: (a) the outcome model, (b) the quit / skip / pause models, (c) the learner's
engagement trait, (d) the aggregate → composites → learner-state path, (e) the policy, safety and reward code.

```text
(a) outcome model: the gap term is clipped at zero, so an easier-than-mastery task cannot lower P(correct)
component_c_generator/behaviour/outcome_model.py:  43      difficulty_norm = (difficulty_level - 1) / 4.0
component_c_generator/behaviour/outcome_model.py:  44      challenge_gap = difficulty_norm - selected_skill_mastery
component_c_generator/behaviour/outcome_model.py:  45      logit_correct = (
component_c_generator/behaviour/outcome_model.py:  46          coefficients.beta0
component_c_generator/behaviour/outcome_model.py:  47          + coefficients.beta_mastery * selected_skill_mastery
component_c_generator/behaviour/outcome_model.py:  48          - coefficients.beta_gap * max(0.0, challenge_gap)
component_c_generator/behaviour/outcome_model.py:  49          + coefficients.beta_tolerance * (challenge_tolerance - 0.5)

(c) consumers of the engagement trait c_engagement_propensity (anywhere in component_c_generator):

                                             file  line                                                                                    text
0   component_c_generator/models/learner_state.py    30  ``c_challenge_tolerance``, ``c_engagement_propensity``) are population-neutral C-local
1   component_c_generator/models/learner_state.py    40                                                    c_engagement_propensity: Probability
2  component_c_generator/pipeline/pilot_cohort.py   142                          c_engagement_propensity=0.3 + 0.4 * (learner_index % 5) / 4.0,

(d)+(e) every CODE identifier mentioning 'difficulty' in composites/*, aggregation/derive.py and rewards.py (AST, docstrings excluded):

                                                          file  line                                identifier
0                  component_c_generator/aggregation/derive.py    64  min_completed_tasks_for_difficulty_trend
1                  component_c_generator/aggregation/derive.py    66                          difficulty_after
2                  component_c_generator/aggregation/derive.py    66                         difficulty_before
3                  component_c_generator/aggregation/derive.py   144                     difficulty_floor_hits
4                  component_c_generator/aggregation/derive.py   147                          difficulty_after
5                  component_c_generator/aggregation/derive.py   165                  current_difficulty_level
6                  component_c_generator/aggregation/derive.py   165                          difficulty_after
7                  component_c_generator/aggregation/derive.py   167                  current_difficulty_level
8                  component_c_generator/aggregation/derive.py   169                  _decide_difficulty_trend
9                  component_c_generator/aggregation/derive.py   169                          difficulty_trend
10                 component_c_generator/aggregation/derive.py   185                     difficulty_floor_hits
11                 component_c_generator/aggregation/derive.py   190                  current_difficulty_level
12                 component_c_generator/aggregation/derive.py   191                          difficulty_trend
13  component_c_generator/composites/engagement_frustration.py   104                     difficulty_floor_hits
14           component_c_generator/composites/learner_state.py    90                     difficulty_floor_hits
15           component_c_generator/composites/learner_state.py   115                     difficulty_floor_hits
identifiers per file: {'component_c_generator/aggregation/derive.py': 13, 'component_c_generator/composites/engagement_frustration.py': 1, 'component_c_generator/composites/learner_state.py': 2} | rewards.py hits: 0
identifiers beyond floor-hits / trajectory bookkeeping: ['_decide_difficulty_trend', 'min_completed_tasks_for_difficulty_trend']
component_c_generator/aggregation/derive.py: 144      difficulty_floor_hits = sum(
component_c_generator/aggregation/derive.py: 145          1
component_c_generator/aggregation/derive.py: 146          for d in adaptation_decisions
component_c_generator/aggregation/derive.py: 147          if d.difficulty_after == 1
component_c_generator/aggregation/derive.py: 148          and (d.applied_action == "decrease_difficulty" or d.selected_action == "decrease_difficulty")
component_c_generator/composites/engagement_frustration.py: 104      floor_hit_component = _clamp01(aggregate.difficulty_floor_hits / 3)
```

```text
       n_tasks  n_attempted  completed  eventual_correct  first_attempt_correct  mean_attempts  mean_err_run  quit_after_error  quit_any  skipped  technical  timeout  mean_latency_s  mean_scaffolds
level
1         2000         1927     0.9610            0.9610                 0.9663         1.0327        0.0340            0.0020    0.0185   0.0205     0.0085      0.0         10.6291          0.0935
2         2000         1927     0.9610            0.9610                 0.9663         1.0327        0.0340            0.0020    0.0185   0.0205     0.0085      0.0         11.2863          0.0935
3         2000         1927     0.9610            0.9610                 0.9663         1.0327        0.0340            0.0020    0.0185   0.0205     0.0085      0.0         11.9842          0.0935
4         2000         1927     0.9610            0.9610                 0.9663         1.0327        0.0340            0.0020    0.0185   0.0205     0.0085      0.0         12.7253          0.0935
5         2000         1927     0.9585            0.9585                 0.9538         1.0431        0.0465            0.0045    0.0210   0.0205     0.0085      0.0         13.4950          0.0960

levels 1..4 identical on every non-latency outcome rate: True
mean latency d4/d1: 1.197 (latency.py:43 shift only; slower when harder, never penalising ease)
quit_after_error  d1: 0.002  d5: 0.0045
```

### Findings — step 4


**Answer: no. Nothing in the generator penalises a task that is too easy** (R0 chain, each link checked):
1. *Outcome model* (`outcome_model.py:48`): `max(0.0, challenge_gap)`, so an easier-than-mastery task cannot lower P(correct).
2. *Probe at mastery 0.9* (levels 1–4 are all ≤ mastery): first-attempt correct **0.9663**, mean attempts 1.0327, quit_after_error 0.0020, skip 0.0205, technical 0.0085, scaffolds 0.0935 are **identical at levels 1, 2, 3 and 4** (asserted). Only latency moves (d4/d1 = **1.197**, slower when harder). Level 5, the only level above mastery, is worse: first-attempt 0.9538, quit_after_error 0.0045.
3. *Engagement trait*: `c_engagement_propensity` appears in 3 places in `component_c_generator`: the model field (`models/learner_state.py:40`), its docstring, and the pilot cohort producer (`pipeline/pilot_cohort.py:142`). It has **no consumer**. No boredom mechanism exists.
4. *Composites / aggregation / rewards*: the only difficulty-dependent quantity is `difficulty_floor_hits` (`aggregation/derive.py:144-148`), which counts decisions that hit **level 1 under downward pressure**, so it penalises tasks that are too *hard*. It feeds `engagement_frustration.py:104` and `learner_state.py:115`. There is no ceiling or "too easy" analogue, and `rewards.py` has **0** identifiers mentioning difficulty.
5. *Policy / safety*: no input or branch depends on "too easy" (section 7).

**Consequence:** in the unextended simulator the dominant strategy is "stay at the lowest difficulty" (highest P, fewest errors, lowest strain). Master plan §6's expectation is confirmed, and extension 6.1 (mastery growth with a fit term) is what creates a reason to go up. Without it, any agent will learn to keep the child at level 1.

## 5. Mastery dynamics: does C ever write to mastery?

Expected: C receives a `BToCMasteryPayload` per session and never writes mastery. This matters for master plan §2.3
point 2 (the data cannot show the causal effect of C difficulty on learning). Evidence: (a) an AST scan of every module for
stores to anything mastery-named, (b) the call order in the shared orchestrator, (c) an empirical before/after on a run.

```text
                                              file  line  kind                         target                                                                                                       statement
0         component_c_generator/gameplay_config.py    40  name                   beta_mastery                                                                beta_mastery: float = Field(allow_inf_nan=False)
1          component_c_generator/models/session.py    73  name              b_mastery_payload                                                                    b_mastery_payload: BToCMasteryPayload | None
2       component_c_generator/pipeline/evidence.py    32  name        _MASTERY_FIELD_BY_SKILL  _MASTERY_FIELD_BY_SKILL = {'counting': 'mastery_counting', 'number_sense': 'mastery_number_sense', 'place_valu
3          component_c_generator/pipeline/pilot.py   378  name                mastery_payload  mastery_payload = fresh_mastery_payload(global_seed=cfg.global_seed, student_id=learner.student_id, session_in
4   component_c_generator/pipeline/pilot_cohort.py    60  name         MASTERY_LEVEL_PROFILES                                    MASTERY_LEVEL_PROFILES: Tuple[float, ...] = (0.05, 0.2, 0.4, 0.6, 0.8, 0.95)
5   component_c_generator/pipeline/pilot_cohort.py    93  name                  mastery_level                                                                                  mastery_level: Optional[float]
6   component_c_generator/pipeline/pilot_cohort.py   175  name                  mastery_level                                   mastery_level = learner_mastery_level if session_mode == 'combined' else None
7   component_c_generator/pipeline/pilot_cohort.py   212  name                  mastery_level                                                     mastery_level = _mastery_level_for(global_seed, student_id)
8        component_c_generator/pipeline/session.py   236  name         selected_skill_mastery                                                                  selected_skill_mastery: Optional[float] = None
9        component_c_generator/pipeline/session.py   238  name         selected_skill_mastery                               selected_skill_mastery = mastery_value_for_skill(mastery_payload, selected_skill)
10     component_c_generator/scaffolds/recovery.py    42  name                  MasteryBucket                                                                MasteryBucket = Literal['low', 'medium', 'high']
11     component_c_generator/scaffolds/recovery.py    54  name    prerequisite_mastery_bucket                                                                      prerequisite_mastery_bucket: MasteryBucket
12     component_c_generator/selection/selector.py    40  name             MasteryContextMode                                      MasteryContextMode = Literal['same_session_fresh', 'unavailable_fallback']
13     component_c_generator/selection/selector.py    56  name           mastery_context_mode                                                                        mastery_context_mode: MasteryContextMode
14     component_c_generator/selection/selector.py    57  name         mastery_selected_skill                                                                  mastery_selected_skill: Optional[float] = None
15     component_c_generator/selection/selector.py   132  name                        mastery                                                                    mastery = _mastery_by_skill(mastery_payload)
16     component_c_generator/selection/selector.py   228  name           mastery_context_mode                                                 mastery_context_mode: MasteryContextMode = 'same_session_fresh'
17     component_c_generator/selection/selector.py   229  name         mastery_selected_skill                                                                                   mastery_selected_skill = None
18     component_c_generator/selection/selector.py   235  name         mastery_selected_skill                                     mastery_selected_skill = _mastery_by_skill(mastery_payload)[selected_skill]
19     component_c_generator/selection/selector.py   237  name           mastery_context_mode                                                                     mastery_context_mode = 'same_session_fresh'
20     component_c_generator/selection/selector.py   242  name           mastery_context_mode                                                                   mastery_context_mode = 'unavailable_fallback'
21     component_c_generator/selection/selector.py   243  name         mastery_selected_skill                                                                                   mastery_selected_skill = None
22        shared_orchestrator/app_shaped_writer.py   243  name           mastery_context_mode                                                     mastery_context_mode = _mastery_context_mode(session_phase)
23        shared_orchestrator/app_shaped_writer.py   248  name         mastery_selected_skill                                                                  mastery_selected_skill: Optional[float] = None
24        shared_orchestrator/app_shaped_writer.py   250  name         mastery_selected_skill                 mastery_selected_skill = mastery_value_for_skill(record.b_to_c_payload, task_instance.skill_id)
25             shared_orchestrator/session_loop.py   129  name  mastery_payload_consumed_by_c                                                               mastery_payload_consumed_by_c: BToCMasteryPayload
attribute / subscript / setattr / model_copy stores touching mastery: 0 of 26 hits
```

```text
run_c_session: where the payload is consumed (parameter L125; read per task at L236-238; select_task L198-213)
component_c_generator/pipeline/session.py: 125      mastery_payload: Optional[BToCMasteryPayload],
component_c_generator/pipeline/session.py: 236          selected_skill_mastery: Optional[float] = None
component_c_generator/pipeline/session.py: 237          if session_mode == "combined":
component_c_generator/pipeline/session.py: 238              selected_skill_mastery = mastery_value_for_skill(mastery_payload, selected_skill)

select_task receives the same, unmodified payload:
component_c_generator/pipeline/session.py: 207                  mastery_payload=mastery_payload,

shared orchestrator: B sessions are produced for the WHOLE learner BEFORE any C session runs
shared_orchestrator/session_loop.py: 261  def run_all_combined_for_learner(learner: SharedLearner, config: OrchestratorConfig) -> Tuple[CombinedSessionRecord, ...]:
shared_orchestrator/session_loop.py: 262      """SO-1: the ALL-COMBINED per-learner loop. Every scheduled session runs Component B then
shared_orchestrator/session_loop.py: 263      Component C, in that order (SF-043); no B-side missed/attendance/attrition (out of scope)."""
shared_orchestrator/session_loop.py: 264      b_result = _run_b_sessions(learner.b_member, config)
shared_orchestrator/session_loop.py: 265      ledger = _HandoffLedger()
shared_orchestrator/session_loop.py: 266      c_state = initial_learner_session_state()
shared_orchestrator/session_loop.py: 267
shared_orchestrator/session_loop.py: 268      records = []
shared_orchestrator/session_loop.py: 269      for b_session in b_result.sessions:
shared_orchestrator/session_loop.py: 270          record, c_state = run_one_combined_session(

what is handed to C each session, and what comes back (state carries no mastery):
shared_orchestrator/session_loop.py: 208              mastery_payload=handoff.b_to_c_payload,  # the REAL, just-consumed B handoff (SF-043)
shared_orchestrator/session_loop.py: 210              session_context_c=learner.session_context_c,
shared_orchestrator/session_loop.py: 193      next_c_state, run_result = advance_session(

second mastery producer: the pilot harness fabricates B payloads without running B (inputs: seed, student, session index, a fixed level profile):
component_c_generator/pipeline/pilot.py: 378      mastery_payload = (
component_c_generator/pipeline/pilot.py: 379          fresh_mastery_payload(
component_c_generator/pipeline/pilot.py: 380              global_seed=cfg.global_seed, student_id=learner.student_id, session_index=slot.session_index,
component_c_generator/pipeline/pilot.py: 381              level=slot.mastery_level,
component_c_generator/pipeline/pilot.py: 382          )
component_c_generator/pipeline/pilot.py: 383          if slot.session_mode == "combined" else None
component_c_generator/pipeline/pilot_cohort.py: 228  def fresh_mastery_payload(
component_c_generator/pipeline/pilot_cohort.py: 229      *, global_seed: int, student_id: str, session_index: int, level: float,
component_c_generator/pipeline/pilot_cohort.py: 230  ) -> BToCMasteryPayload:
component_c_generator/pipeline/pilot_cohort.py: 231      """A FRESH, per-session synthetic TEST_FIXTURE_ONLY B->C mastery payload (SF-043: never
component_c_generator/pipeline/pilot_cohort.py: 232      cached -- a brand-new object every call; deterministic only in that the SAME
component_c_generator/pipeline/pilot_cohort.py: 233      ``(global_seed, student_id, session_index)`` always reproduces the SAME payload, never carried

CLearnerSessionState fields: ['eligible_combined_handoffs_completed', 'sessions_since_last_practice', 'prior_session_end_state'] | extra: forbid
CLocalLearnerState mastery-like fields: none
BToCMasteryPayload.model_config: {'extra': 'forbid'}
```

```text
B payload unchanged after a 12-task session  : True
CLocalLearnerState unchanged after the session: True
tasks: 12 | difficulty trajectory: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
skills practised: ['subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction', 'subtraction']
payload is MUTABLE (assignment accepted)
```

### Findings — step 5


**Answer: C never writes mastery — confirmed, with a stronger trace than the work order expected.**
- *AST scan* of `component_c_generator` + `shared_orchestrator`: 26 stores to mastery-named targets, **0** of them attribute / subscript / `setattr` / `model_copy` stores. All 26 are declarations, constants or locals; the only one inside the C session loop is the local scalar read at `session.py:238`.
- *Producer → consumer.* `mastery_payload` enters `run_c_session` as a parameter (`session.py:125`), goes unmodified to `select_task` (L207) and is read per task at L238. The orchestrator hands over `handoff.b_to_c_payload` (`session_loop.py:208`). The C-side state carries no mastery: `CLearnerSessionState` has only `eligible_combined_handoffs_completed`, `sessions_since_last_practice`, `prior_session_end_state` (`extra="forbid"`), and `CLocalLearnerState` has no mastery-like field.
- ***The decisive break:*** `run_all_combined_for_learner` computes **all** of a learner's B sessions first (`session_loop.py:264`, `b_result = _run_b_sessions(...)`) and only then loops over C sessions (L269). So B's mastery trajectory **cannot** be a function of C's difficulty. This grounds master plan §2.3 point 2 structurally. The data's difficulty→mastery correlation is confounded by construction.
- *Empirical:* after a 12-task combined session the payload dump and `CLocalLearnerState` dump are unchanged (**True / True**). A second producer exists, `pilot.py:378-383` → `pilot_cohort.py:228`, which fabricates payloads from `(seed, student, session, level)` only; it does not read C either.
- **Nuance against the work order.** "C reads B mastery once per session" is imprecise: the payload is *handed over* once per session but *read per task* (`session.py:198-213, 238`), always the session-start value. `BToCMasteryPayload` has only `extra="forbid"` (assignment is accepted), so immutability rests on the AST evidence, not the type.
- Observation: in the sample session the selector picked `subtraction` (mastery 0.4) for all 12 tasks at difficulty 3. The policy controls only the difficulty of the *next* task (`session.py:326`); skill and the first task's difficulty come from the selector.

## 6. Evidence window

What `pipeline/evidence.py:77-133` computes, the window sizes, and the defaults when no task has completed. Demonstrated
by calling the real `build_policy_evidence` on real task summaries from the section-3 probe.

```text
                                                                    evidence field  \
0                                                          recent_correctness_rate
1                                                              recent_avg_attempts
2                                                        recent_inactivity_periods
3                                                        recent_scaffold_use_count
4                                                     recent_consecutive_error_max
5                                                             rolling_strain_score
6                                                     technical_issue_current_task
7  is_recovery_context / safety_increase_block_remaining / prior_session_end_state

                                                                                                                               computation                                  default when no completed task  \
0                                                                                  last N=5 tasks, completed only: share with correct_task                                                             0.5
1                                                                                       last 5 tasks with >=1 attempt: mean total_attempts                                                             1.0
2                                                                                                                    sum over last 5 tasks                                                               0
3                                                                                                                    sum over last 5 tasks                                                               0
4                                                                                  max consecutive_error_max_within_task over last 5 tasks                                                               0
5  clamp01(0.5*err/5 + 0.3*excess_attempts/3 + 0.2*quit), err & attempts over last w=3 COMPLETED tasks, quit over last 3 tasks of any kind  0.0 (returns early if none completed, even if a quit occurred)
6                                                                                                  technical_issue flag of the latest task                                                from latest task
7                                                                                           supplied by run_c_session (session.py:283-293)                                                             n/a

                                         source
0  evidence.py:95-103; N: pipeline/config.py:48
1                           evidence.py:105-109
2                               evidence.py:111
3                               evidence.py:112
4                               evidence.py:113
5         evidence.py:59-74; w=3 hard-coded L25
6                               evidence.py:131
7                            session.py:284-293
recent_window_task_count = 5 | parameter_source_status = TEST_FIXTURE_ONLY
component_c_generator/pipeline/evidence.py:  98      if completed_in_window:
component_c_generator/pipeline/evidence.py:  99          recent_correctness_rate = sum(1.0 for s in completed_in_window if s.correct_task) / len(completed_in_window)
component_c_generator/pipeline/evidence.py: 100      else:
component_c_generator/pipeline/evidence.py: 101          # No completed-task evidence yet in the window -- a neutral, non-biasing default
component_c_generator/pipeline/evidence.py: 102          # (ENGINEERING_ASSUMPTION; not specified by any committed source).
component_c_generator/pipeline/evidence.py: 103          recent_correctness_rate = 0.5
component_c_generator/pipeline/evidence.py: 104
component_c_generator/pipeline/evidence.py: 105      attempted_in_window = [s for s in window if s.total_attempts > 0]
component_c_generator/pipeline/evidence.py: 106      if attempted_in_window:
component_c_generator/pipeline/evidence.py: 107          recent_avg_attempts = sum(s.total_attempts for s in attempted_in_window) / len(attempted_in_window)
component_c_generator/pipeline/evidence.py: 108      else:
component_c_generator/pipeline/evidence.py: 109          recent_avg_attempts = 1.0
component_c_generator/pipeline/evidence.py:  63      completed = [s for s in recent_summaries if s.task_completed]
component_c_generator/pipeline/evidence.py:  64      window = completed[-_ROLLING_STRAIN_WINDOW:]
component_c_generator/pipeline/evidence.py:  65      if not window:
component_c_generator/pipeline/evidence.py:  66          return 0.0
component_c_generator/pipeline/evidence.py:  67      recent_consecutive_errors = max(s.consecutive_error_max_within_task for s in window)
component_c_generator/pipeline/evidence.py:  68      recent_excess_attempts = max(0.0, (sum(s.total_attempts for s in window) / len(window)) - 1.0)
component_c_generator/pipeline/evidence.py:  69      recent_quit = 1.0 if any(s.task_quit for s in recent_summaries[-_ROLLING_STRAIN_WINDOW:]) else 0.0
```

```text
                                                            0                         1                      2                                3
case                          only a QUIT (no task completed)  one clean completed task  quit, then clean task  8 clean tasks (window = last 5)
recent_correctness_rate                                   0.5                       1.0                    1.0                              1.0
recent_avg_attempts                                       2.0                       1.0                    1.5                              1.0
recent_inactivity_periods                                   0                         0                      0                                0
recent_scaffold_use_count                                   0                         0                      0                                0
recent_consecutive_error_max                                2                         0                      2                                0
rolling_strain_score                                      0.0                       0.0                    0.2                              0.0
rule_proposes                                            hold       increase_difficulty                   hold              increase_difficulty
quit_s: task_quit = True task_completed = False terminal = quit_after_error

rolling strain with a lone quit: 0.0 | time_in_target_band_sec is a caller-supplied placeholder:
shared_orchestrator/session_loop.py: 224              # SPEC-disclosed placeholder (component_c_generator's own known limitation, not
shared_orchestrator/session_loop.py: 225              # invented here): C3 emits no target-band signal; this stays a caller-supplied seam.
shared_orchestrator/session_loop.py: 226              time_in_target_band_sec=0.0,
```

### Findings — step 6


- **Windows:** `recent_*` fields use the last **N = 5** tasks (`pipeline/config.py:48`, TEST_FIXTURE_ONLY). Rolling strain uses the last **w = 3** *completed* tasks, hard-coded (`evidence.py:25`), with the quit term over the last 3 tasks of any kind (L69).
- **Defaults when nothing completed:** `recent_correctness_rate` = **0.5** (L103), `recent_avg_attempts` = **1.0** (L109), inactivity / scaffold / consecutive-error max = 0, `rolling_strain_score` = **0.0** (L65-66, an early return).
- **Demonstrated on real summaries:** a lone `quit_after_error` task (2 attempts) → correctness 0.5, avg attempts 2.0, error run 2, **strain 0.0** (the quit is invisible because the early return precedes the quit term) → rule proposes **hold**. "Quit, then one clean task" → strain 0.2, correctness 1.0 → hold. Eight clean tasks → correctness 1.0, attempts 1.0, strain 0.0 → **increase**.
- Two things RL must know: (i) `recent_correctness_rate` counts `correct_task` only among *completed* tasks, so quits never lower it; (ii) given the retry cap it saturates at 1.0 (section 3, and section 10: 99.6% / 99.3% of simulated decisions). The rule's "correctness ≤ 0.40 → decrease" branch is almost never what fires; decisions are driven by `recent_avg_attempts` and strain.
- `time_in_target_band_sec` is a caller-supplied **0.0 placeholder** (`session_loop.py:226`, "C3 emits no target-band signal"). The simulator has no time-in-band measure; NB04/NB08 must define their own.

## 7. Safety override table

`safety/controller.py::apply_safety` runs after every policy proposal. First the rules with their line numbers; then an
**exhaustive enumeration** of the real function over the cross-product of its inputs (phase / mode, prior session state,
recovery context, increase-block, error run, strain, technical flag, current difficulty 1..5, proposed action).

```text
                        rule                        source                                                                                                condition                        affects proposals
0   technical neutralisation           controller.py:58-60                                                       decrease -> hold when technical_issue_current_task                                 decrease
1   severe error-run trigger  controller.py:64,67-68,71-72                                        recent_consecutive_error_max >= 5: force decrease + recovery flag                           hold, increase
2      severe strain trigger        controller.py:65,69-72                                             rolling_strain_score >= 0.85: force decrease + recovery flag                           hold, increase
3             increase block           controller.py:74-83  after a trigger the next 3 decisions veto increase (-> hold); veto also applies on the trigger decision                                 increase
4               recovery cap           controller.py:87-89                                          is_recovery_context: ceiling = floor = 1 (difficulty_after = 1)              any (increase, hold if d>1)
5        familiarization cap           controller.py:91-93                                                              session_phase == familiarization: ceiling 2  increase (at/above cap), hold above cap
6      c_only (fallback) cap           controller.py:94-96                                                                        session_mode == c_only: ceiling 2  increase (at/above cap), hold above cap
7            prior-state cap           controller.py:97-99                                           prior_session_end_state in (overloaded, disengaged): ceiling 2  increase (at/above cap), hold above cap
8        floor/ceiling clamp         controller.py:102-108            target = d +/- 1 clamped to [floor, ceiling]; applied_action derived from the NUMERIC outcome         decrease at d=1, increase at d=5
9           safe termination         controller.py:123-125                 recent_consecutive_error_max >= 7: request_safe_termination (does not change the action)                      n/a (stops session)
10       override definition             controller.py:127                                                    action_overridden = applied_action != selected_action                                        -
caps: familiarization = 2 | c_only = 2 | prior overloaded/disengaged = 2 | W by grade = {2: 2, 3: 3}
```

```text
detail for the no-prior-state rows (the prior-state rows differ only by the prior_state_cap):

        mode            phase prior_state             proposed  n_overridden_of_5  \
0   combined   mastery_driven        None  decrease_difficulty                  1
2   combined   mastery_driven        None  increase_difficulty                  1
15  combined  familiarization        None  decrease_difficulty                  1
16  combined  familiarization        None                 hold                  3
17  combined  familiarization        None  increase_difficulty                  4
30    c_only           c_only        None  decrease_difficulty                  1
31    c_only           c_only        None                 hold                  3
32    c_only           c_only        None  increase_difficulty                  4

                                                                                                                                         detail
0                                                                                                            d1->hold[difficulty_bound_clamped]
2                                                                                                            d5->hold[difficulty_bound_clamped]
15                                                                                                        d1->hold[familiarization_session_cap]
16              d3->decrease[familiarization_session_cap]; d4->decrease[familiarization_session_cap]; d5->decrease[familiarization_session_cap]
17  d2->hold[familiarization_session_cap]; d3->decrease[familiarization_session_cap]; d4->decrease[familiarization_session_cap]; d5->decreas...
30                                                                                                               d1->hold[fallback_session_cap]
31                                   d3->decrease[fallback_session_cap]; d4->decrease[fallback_session_cap]; d5->decrease[fallback_session_cap]
32   d2->hold[fallback_session_cap]; d3->decrease[fallback_session_cap]; d4->decrease[fallback_session_cap]; d5->decrease[fallback_session_cap]

number of difficulty levels (of 5) at which the proposal is overridden, clean evidence:

proposed                                      decrease_difficulty  hold  increase_difficulty
mode     phase           prior_state
c_only   c_only          disengaged                             1     3                    4
                         engaged                                1     3                    4
                         none                                   1     3                    4
                         overloaded                             1     3                    4
                         productive_struggle                    1     3                    4
combined familiarization disengaged                             1     3                    4
                         engaged                                1     3                    4
                         none                                   1     3                    4
                         overloaded                             1     3                    4
                         productive_struggle                    1     3                    4
         mastery_driven  disengaged                             1     3                    4
                         engaged                                1     0                    1
                         none                                   1     0                    1
                         overloaded                             1     3                    4
                         productive_struggle                    1     0                    1
```

```text
evaluated 21600 apply_safety calls

override share by proposed action over the whole cross-product:

                     override_share
proposed
decrease_difficulty           0.227
hold                          0.747
increase_difficulty           0.973

mastery_driven, no prior state, d=3 - applied action by trigger level (err = recent_consecutive_error_max):

proposed    decrease_difficulty                 hold  increase_difficulty
err strain
0   0.0     decrease_difficulty                 hold  increase_difficulty
    0.5     decrease_difficulty                 hold  increase_difficulty
    0.9     decrease_difficulty  decrease_difficulty  decrease_difficulty
3   0.0     decrease_difficulty                 hold  increase_difficulty
    0.5     decrease_difficulty                 hold  increase_difficulty
    0.9     decrease_difficulty  decrease_difficulty  decrease_difficulty
5   0.0     decrease_difficulty  decrease_difficulty  decrease_difficulty
    0.5     decrease_difficulty  decrease_difficulty  decrease_difficulty
    0.9     decrease_difficulty  decrease_difficulty  decrease_difficulty
7   0.0     decrease_difficulty  decrease_difficulty  decrease_difficulty
    0.5     decrease_difficulty  decrease_difficulty  decrease_difficulty
    0.9     decrease_difficulty  decrease_difficulty  decrease_difficulty
grid contexts: 7200
number of allowed actions per context:

           contexts
n_allowed
1              6852
2               312
3                36
contexts with NO allowed action: 0 | contexts where 'hold' itself is overridden: 0.747
safety_decrease_never_vetoed_except_tech_or_floor = True
safety_can_force_decrease_from_hold_or_increase = True
safety_never_raises_difficulty_beyond_proposal = True
```

### Findings — step 7


- Rules and lines are tabled above. Defaults: error trigger **5**, strain trigger **0.85**, increase-block **3** decisions, safe-termination error run **7**, and **all three caps = 2** (familiarization, c_only fallback, prior overloaded/disengaged). W by grade = {2: 2, 3: 3}.
- Enumeration: **21,600** real `apply_safety` calls. Three structural facts hold (asserted): the controller never vetoes a decrease except for technical neutralisation / the floor / recovery; it can force a decrease from hold or increase; it never lifts difficulty beyond the proposal.
- **Clean evidence (no triggers):** in `mastery_driven` with no prior state (or engaged / productive_struggle) the only overrides are at the bounds — decrease at d=1 and increase at d=5 (1 of 5 levels each; **hold is never overridden**). With a prior `overloaded`/`disengaged` state, or in `familiarization`, or in **c_only**, the cap of 2 overrides **hold at 3 levels** (d=3,4,5 → decrease) and **increase at 4 levels**.
- **Triggers (d=3):** `recent_consecutive_error_max` ≥ 5, or strain ≥ 0.85 (grid value 0.9), turns every proposal into `decrease`; an error run of 3 alone does not.
- **Implication for the live app (c_only):** because of the cap, the reachable difficulty is **{1, 2}**; the RL action space there is effectively two-valued. The simulated c_only runs confirm it (section 10: 98.5% of decisions have exactly 2 allowed actions, mean difficulty after = 1.77).
- Across the whole 7,200-context grid, 6,852 contexts have exactly one allowed action; the grid is dominated by trigger contexts and is not a frequency estimate. Section 10 gives realistic frequencies.

## 8. Seed lineages

Every `seed_manager.*` and `derive_child_lineage` call reached from `run_c_session`, with arguments. **NB02 must reproduce these exactly.**
Method: instrument `SeedManager` and every module-level binding of `derive_child_lineage`, run representative sessions
(default combined; a rigged c_only session that triggers recovery; one that triggers safe termination), and log the real call sites.

```text
recovery run: recovery_task_indices = (2,) | stop run: terminated_safe_stop = True | tasks: 2
logged calls: 328
```

```text
Calls made DIRECTLY in run_c_session:

                                             site                               fn                                                                                                                first_args  n_calls
13  component_c_generator/pipeline/session.py:171  SeedManager.component_c_session                                                   (student_id=STU-0001, intervention_session_number=3, c_session_index=1)        4
14  component_c_generator/pipeline/session.py:176     SeedManager.task_opportunity                                     (student_id=STU-0001, intervention_session_number=3, c_session_index=1, task_index=1)       15
15  component_c_generator/pipeline/session.py:240     SeedManager.gameplay_process  (student_id=STU-0001, intervention_session_number=3, c_session_index=1, task_index=1, instance_index=1, process_index=1)       15
16  component_c_generator/pipeline/session.py:305             derive_child_lineage                                                                                          (parent, "policy_decision", "1")       14
Calls made by modules run_c_session delegates to:

                                               site               caller                    fn               level key  n_calls
0       component_c_generator/behaviour/seeds.py:59      attempt_lineage  derive_child_lineage             attempt   1       14
1       component_c_generator/behaviour/seeds.py:59      attempt_lineage  derive_child_lineage             attempt   2        7
2       component_c_generator/behaviour/seeds.py:59      attempt_lineage  derive_child_lineage             attempt   3        3
3       component_c_generator/behaviour/seeds.py:59      attempt_lineage  derive_child_lineage             attempt   4        3
4       component_c_generator/behaviour/seeds.py:59      attempt_lineage  derive_child_lineage             attempt   5        3
5       component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage       action_choice   1       30
6       component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage             latency   1       30
7       component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage               pause   1       30
8       component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage                quit   1       30
9       component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage    scaffold_request   1       30
10      component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage                skip   1       14
11      component_c_generator/behaviour/seeds.py:63            _decision  derive_child_lineage     technical_issue   1       30
12           component_c_generator/generation.py:76  build_task_instance  derive_child_lineage  game_task_instance   1       25
17  component_c_generator/selection/selector.py:219          select_task  derive_child_lineage     selection_skill   1       14
18  component_c_generator/selection/selector.py:220          select_task  derive_child_lineage  selection_template   1       14
19  component_c_generator/selection/selector.py:224          select_task  derive_child_lineage  selection_rotation   1        3
component_c_generator/pipeline/session.py: 171      component_c_session_lineage = seed_manager.component_c_session(
component_c_generator/pipeline/session.py: 172          student_id, intervention_session_number, c_session_index
component_c_generator/pipeline/session.py: 173      )
component_c_generator/pipeline/session.py: 176          task_opportunity_lineage = seed_manager.task_opportunity(
component_c_generator/pipeline/session.py: 177              student_id, intervention_session_number, c_session_index, task_index
component_c_generator/pipeline/session.py: 178          )
component_c_generator/pipeline/session.py: 240          gameplay_process_lineage = seed_manager.gameplay_process(
component_c_generator/pipeline/session.py: 241              student_id, intervention_session_number, c_session_index, task_index, 1, 1
component_c_generator/pipeline/session.py: 242          )
component_c_generator/pipeline/session.py: 305          decision_lineage = derive_child_lineage(task_opportunity_lineage, "policy_decision", "1")
component_c_generator/pipeline/session.py: 306          adaptation_decisions.append(

SUBSTREAMS available in SeedManager: ('selection', 'instance_content', 'outcome', 'latency', 'attempts', 'actions', 'inactivity', 'scaffold', 'policy_exploration', 'technical_issue')
any 'policy_exploration' substream call in the logged runs: False
RNG use in policy/rule_based.py and safety/controller.py: none

task_opportunity path (no difficulty / action component): (('learner', 'STU-0001'), ('scheduled_intervention_slot', '3'), ('component_c_session', '1'), ('task_opportunity', '4'))
```

### Findings — step 8


**Calls made directly in `run_c_session` (NB02 must reproduce these exactly):**
| site | call | args | frequency |
|---|---|---|---|
| `session.py:171` | `seed_manager.component_c_session` | `(student_id, intervention_session_number, c_session_index)` | once per session |
| `session.py:176` | `seed_manager.task_opportunity` | `(student_id, intervention_session_number, c_session_index, task_index)` | per task |
| `session.py:240` | `seed_manager.gameplay_process` | `(student_id, intervention_session_number, c_session_index, task_index, 1, 1)` | per task |
| `session.py:305` | `derive_child_lineage(task_opportunity_lineage, "policy_decision", "1")` | → `decision_id = AD-{seed:016x}` | per decision |

**Made by delegates** (328 calls logged over 4 runs: default combined, recovery, safe-stop, familiarization): `selector.py:219/220` (`"selection_skill"`, `"selection_template"`, key `"1"`, from the task lineage), `selector.py:224` (`"selection_rotation"`, from the session lineage, familiarization only — it appeared in the familiarization run), `generation.py:76` (`"game_task_instance"`, `"1"`, on every built or rebuilt instance), `behaviour/seeds.py:59` (`"attempt"`, key = attempt index, from the gameplay lineage), `behaviour/seeds.py:63` (siblings off the attempt: `action_choice`, `latency`, `pause`, `quit`, `scaffold_request`, `technical_issue`, plus `skip` on attempt 1 only; key `"1"`).
- The policy and safety layers use **no RNG** (no `random`/`rng` in `policy/` or `safety/`).
- `SeedManager.substream(..., "policy_exploration")` exists (`seeds.py:41-52`) and is **never called** by `run_c_session`; it is a ready-made, non-perturbing lineage for an RL agent's exploration RNG (NB05/06). The `retry` domain is defined (`behaviour/seeds.py:41`) but was not called in the logged runs.
- Seed paths contain **no difficulty and no action component**, so gameplay RNG streams are keyed by (learner, session, task, attempt) only. Two arms see the same random draws until their histories diverge (common random numbers). The task *content* seed is the same lineage but the instance depends on the difficulty argument.

## 9. Config status

Is `default_gameplay_config()` `TEST_FIXTURE_ONLY` or `SMOKE_ONLY`, and what does `validate_not_test_fixture_in_research_mode`
imply for our simulation use?

```text
            config             class_name              config_version parameter_source_status
0         gameplay       C3GameplayConfig           c3-gameplay-1.0.0       TEST_FIXTURE_ONLY
1       generation      CGenerationConfig       c2.1-generation-1.0.0       TEST_FIXTURE_ONLY
2        selection       CSelectionConfig        c4.0-selection-1.0.0       TEST_FIXTURE_ONLY
3           policy          CPolicyConfig           c4.1-policy-1.0.0       TEST_FIXTURE_ONLY
4           safety          CSafetyConfig           c4.1-safety-1.0.0       TEST_FIXTURE_ONLY
5         scaffold        CScaffoldConfig         c4.2-scaffold-1.0.0       TEST_FIXTURE_ONLY
6         recovery        CRecoveryConfig         c4.2-recovery-1.0.0       TEST_FIXTURE_ONLY
7  evidence_window  CEvidenceWindowConfig  c6.0-evidence-window-1.0.0       TEST_FIXTURE_ONLY
8      aggregation     CAggregationConfig      c5.0-aggregation-1.0.0       TEST_FIXTURE_ONLY
gameplay: parameter_source_status = TEST_FIXTURE_ONLY | smoke_mode = True
validate(mode='research'): ValueError - C3GameplayConfig.parameter_source_status='TEST_FIXTURE_ONLY' is rejected in research mode (C3 §17); a signed-off calibration status is required.
validate(mode='smoke'): passes
validate(mode='simulation'): passes
component_c_generator/gameplay_config.py: 189  def validate_not_test_fixture_in_research_mode(config: C3GameplayConfig, mode: str) -> None:
component_c_generator/gameplay_config.py: 190      """C3 §17: ``SMOKE_ONLY`` / ``TEST_FIXTURE_ONLY`` parameters must be REJECTED in a
component_c_generator/gameplay_config.py: 191      research/full mode. Raises ``ValueError`` if a fixture-tagged config is used with
component_c_generator/gameplay_config.py: 192      ``mode == "research"``."""
component_c_generator/gameplay_config.py: 193      if mode == "research" and config.parameter_source_status in _REJECTED_STATUSES_IN_RESEARCH_MODE:
component_c_generator/gameplay_config.py: 194          raise ValueError(
component_c_generator/gameplay_config.py: 195              f"C3GameplayConfig.parameter_source_status={config.parameter_source_status!r} is "
component_c_generator/gameplay_config.py: 196              f"rejected in research mode (C3 §17); a signed-off calibration status is required."
component_c_generator/gameplay_config.py: 197          )


callers of the validator outside tests/ and its own definition:

Empty DataFrame
Columns: [file, line, text]
Index: []
```

### Findings — step 9


- All **9** default configs (gameplay, generation, selection, policy, safety, scaffold, recovery, evidence_window, aggregation) carry `parameter_source_status = "TEST_FIXTURE_ONLY"`; `default_gameplay_config()` also has `smoke_mode=True`.
- `validate_not_test_fixture_in_research_mode(GP, "research")` **raises** (`gameplay_config.py:193-197`); with `"smoke"` or `"simulation"` it passes.
- R0 trace: the validator has **0 callers** outside `tests/` and its own definition. Nothing in `run_c_session`, the orchestrator or the pilot calls it, so the guard is not enforced by any production path.
- **Implication for us:** the simulator can only be used in a non-"research" mode, and every parameter it uses (outcome coefficients, quit logit, latency, thresholds, caps) is `CALIBRATION_PENDING`. Everything we report must carry "Simulation-only, parameters TEST_FIXTURE_ONLY", and our own extension constants (η, δ, σ, dropout a/b/c/d) are `ENGINEERING_ASSUMPTION` + `CALIBRATION_PENDING`. We must never call the validator in research mode.

## 10. Config recipe and two reference sessions

The recipe is `tests/test_c_generator_phase_c6_0_pipeline.py:66-122` (reproduced in `session_kwargs()` in section 5; the rigged configs
in section 8 are from L123-150). Below: one **combined** and one **c_only** session of 12 tasks under the rule policy, as decision tables.
After that, an **informational** batch of sessions (not a calibration — that is NB03) to see what the rule policy + safety layer does in the simulator.

```text
=== combined (mastery_driven, grade 2): payload emitted = True | learner_state = None | safety_override_count = 0 | terminated_safe_stop = False

    task        skill template  difficulty  recovery scaffold_start correct first_try  attempts           terminal             selected              applied  overridden safety_reason  d_after strain_bucket  block_left
0      1  subtraction  C-TC-01           3     False             C0    True     False         2  completed_correct                 hold                 hold       False          None        3           low           0
1      2  subtraction  C-TC-03           3     False             C0    True      True         1  completed_correct                 hold                 hold       False          None        3           low           0
2      3  subtraction  C-TC-01           3     False             C0    True     False         2  completed_correct                 hold                 hold       False          None        3           low           0
3      4  subtraction  C-TC-01           3     False             C0    True      True         1  completed_correct                 hold                 hold       False          None        3           low           0
4      5  subtraction  C-TC-02           3     False             C0    True     False         2  completed_correct                 hold                 hold       False          None        3           low           0
5      6  subtraction  C-TC-02           3     False             C0    True     False         2  completed_correct                 hold                 hold       False          None        3           low           0
6      7  subtraction  C-TC-01           3     False             C0    True      True         1  completed_correct                 hold                 hold       False          None        3           low           0
7      8  subtraction  C-TC-03           3     False             C0    True      True         1  completed_correct                 hold                 hold       False          None        3           low           0
8      9  subtraction  C-TC-03           3     False             C0    None      None         0    technical_issue                 hold                 hold       False          None        3      moderate           0
9     10  subtraction  C-TC-01           3     False             C0    True     False         2  completed_correct                 hold                 hold       False          None        3      moderate           0
10    11  subtraction  C-TC-01           3     False             C0    True      True         1  completed_correct                 hold                 hold       False          None        3      moderate           0
11    12  subtraction  C-TC-02           3     False             C0    True      True         1  completed_correct  increase_difficulty  increase_difficulty       False          None        4           low           0

=== c_only (grade 2): payload emitted = True | learner_state = None | safety_override_count = 0 | terminated_safe_stop = False

    task         skill template  difficulty  recovery scaffold_start correct first_try  attempts           terminal             selected              applied  overridden         safety_reason  d_after strain_bucket  \
0      1   place_value  C-BT-01           1     False             C0    True     False         2  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
1      2  number_sense  C-CC-04           1     False             C0    True      True         1  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
2      3   place_value  C-BT-01           1     False             C0    True     False         2  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
3      4   subtraction  C-TC-01           1     False             C0    True      True         1  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
4      5      addition  C-JB-02           1     False             C0    True     False         2  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
5      6      addition  C-JB-02           1     False             C0    True     False         2  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
6      7      counting  C-CC-03           1     False             C0    True      True         1  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
7      8   subtraction  C-TC-03           1     False             C0    True      True         1  completed_correct                 hold                 hold       False  fallback_session_cap        1           low
8      9      counting  C-NP-02           1     False             C0    None      None         0    technical_issue                 hold                 hold       False  fallback_session_cap        1      moderate
9     10   subtraction  C-TC-01           1     False             C0    True     False         2  completed_correct                 hold                 hold       False  fallback_session_cap        1      moderate
10    11      counting  C-CC-03           1     False             C0    True      True         1  completed_correct                 hold                 hold       False  fallback_session_cap        1      moderate
11    12   place_value  C-BT-01           1     False             C0    True      True         1  completed_correct  increase_difficulty  increase_difficulty       False  fallback_session_cap        2           low

    block_left
0            0
1            0
2            0
3            0
4            0
5            0
6            0
7            0
8            0
9            0
10           0
11           0
```

```text
evidence replay reproduces every recorded decision (rule + safety): {'combined': True, 'c_only': True}

mode                          combined     c_only
sessions                      100.0000   100.0000
decisions                    1200.0000  1200.0000
selected_hold                   0.4292     0.4108
selected_dec                    0.1450     0.0983
selected_inc                    0.4258     0.4908
applied_hold                    0.7008     0.8917
applied_dec                     0.1058     0.0183
applied_inc                     0.1933     0.0900
override_rate                   0.2717     0.4808
allowed_1                       0.0458     0.0150
allowed_2                       0.5450     0.9850
allowed_3                       0.4092     0.0000
allowed_0                       0.0000     0.0000
hold_is_overridden              0.0050     0.0008
override_is_structural_only     0.8988     0.9948
safety_recovery_flag_rate       0.0250     0.0033
mean_difficulty_after           4.1242     1.7700
telemetry_complete              0.6600     0.6500
sess_with_recovery              0.0600     0.0100
sess_safe_stop                  0.0000     0.0000
recent_correctness_eq_1         0.9958     0.9933
recent_correctness_mean         0.9979     0.9967
recent_first_try_mean           0.6839     0.6966
strain_mean                     0.1755     0.1529

master plan §6 cites (data, NOT verified here - NB01): applied mix ~ 85/9/6 % hold/decrease/increase; override rate ~ 42 %

why sessions are 'technical_issue':
component_c_generator/aggregation/derive.py: 152      session_technical_issue_flag = any(s.technical_issue for s in summaries) or any(
component_c_generator/aggregation/derive.py: 153          e.technical_flag for e in events
component_c_generator/aggregation/derive.py: 154      )
component_c_generator/behaviour/attempt_loop.py: 217          if pauses_used < config.pause.max_pauses_per_task:
component_c_generator/behaviour/attempt_loop.py: 218              if _bernoulli(pause_rng, config.pause.technical_pause_probability):
component_c_generator/behaviour/attempt_loop.py: 219                  duration_ms = _sample_pause_duration_ms(
component_c_generator/behaviour/attempt_loop.py: 220                      pause_rng, config.pause.technical_pause_duration_mean_sec, config.pause.pause_duration_sd_sec
component_c_generator/behaviour/attempt_loop.py: 221                  )
component_c_generator/behaviour/attempt_loop.py: 222                  builder.emit("pause_started", attempt, technical_flag=True)
component_c_generator/behaviour/attempt_loop.py: 223                  builder.advance(duration_ms)
component_c_generator/behaviour/attempt_loop.py: 224                  builder.emit("pause_ended", attempt, technical_flag=True)

                                 combined  c_only
session_flag                         0.34    0.34
from_task_level_technical_issue      0.18    0.18
from_technical_pause_only            0.16    0.16

telemetry_quality_status mix:

                       combined  c_only
telemetry
complete                   0.66    0.65
technical_issue            0.34    0.34
insufficient_evidence       NaN    0.01

learner_state mix (complete-telemetry sessions only; the state is None otherwise):

                     combined  c_only
learner_state
overloaded              0.606   0.538
engaged                 0.394   0.308
productive_struggle       NaN   0.154

top safety reasons (combined):

                                    n
reason
difficulty_bound_clamped          293
consecutive_error_safety_trigger   30
recovery_cap                       29
increase_blocked_active_window      9
rolling_strain_safety_trigger       1
```

### Findings — step 10


**Reference sessions** (grade 2, mid learner, 12 tasks, rule policy):
- *combined* (B payload 0.8 … 0.2): selector picks `subtraction` (mastery 0.4) → difficulty **3 for all 12 tasks**; policy proposes hold 11 times and increase once (task 12 → 4); 0 overrides; payload emitted, but `learner_state = None` because task 9 had a technical issue.
- *c_only*: skills rotate, difficulty 1 throughout (every row's `safety_reason` is `fallback_session_cap`, though nothing is overridden); one increase at task 12 → 2.

**Informational batch** (100 sessions per mode, uniform mastery 0.5; not a calibration — that is NB03). The evidence replay reproduces **every** recorded rule + safety decision (True / True), so our model of the loop is correct.
| | combined | c_only |
|---|---|---|
| applied hold / decrease / increase | 70.1 / 10.6 / 19.3 % | 89.2 / 1.8 / 9.0 % |
| override rate | 27.2 % | 48.1 % |
| …of which caps / bound clamps only | 89.9 % | 99.5 % |
| real safety-trigger rate (recovery flag per decision) | 0.025 | 0.0033 |
| mean difficulty after | 4.12 | 1.77 |
| `recent_correctness_rate` == 1.0 | 99.6 % | 99.3 % |
| mean first-attempt success over last 5 | 0.684 | 0.697 |
| allowed-action set size 1 / 2 / 3 | 4.6 / 54.5 / 40.9 % | 1.5 / 98.5 / 0 % |
| hold itself overridden | 0.5 % | 0.08 % |
| telemetry `complete` | 66 % | 65 % |

- **`action_overridden` is not a safety event.** Roughly 90–99% of overrides are structural. The real safety signal is the recovery flag (`safety_override_count`), at 0.0033–0.025 per decision. The reward's `w_safe·safety_event` must use that, not `action_overridden`.
- **Telemetry is often incomplete.** **34%** of sessions are flagged `technical_issue` in both modes (18% from a task-level technical issue, 16% from a technical *pause* alone, because `aggregation/derive.py:152-153` counts any `technical_flag` event). The two modes are identical because they share seeds. Such sessions have no `engagement_score`, `frustration_index` or `learner_state`. Among complete sessions the combined learner_state is 60.6% overloaded / 39.4% engaged (c_only: 53.8 / 30.8 / 15.4 productive_struggle).
- Plan §6 cites the data at ≈ 85 / 9 / 6 % applied hold/decrease/increase with ≈ 42 % overrides; this notebook does **not** verify that (NB01). The c_only simulation (89 / 2 / 9 %, 48 %) is in the same neighbourhood; combined (70 / 11 / 19 %) is not, but the mastery distribution here (uniform 0.5) is not the data's, so no conclusion yet.

## 11. Implications for NB02 / NB03

Each master-plan claim from §2.3, §5 and §6 is checked against the values computed above (status comes from `CHECKS`, not typed by hand).

```text
                                                       master-plan / work-order claim                                    status  \
0                                 §6 'P(correct) falls with difficulty above mastery'                                 CONFIRMED
1                                     §6 c_only P(correct) depends on difficulty only                                 CONFIRMED
2                                  §6 'Quits depend on error streaks and persistence'                   CONFIRMED (with nuance)
3                                      §6 'Nothing penalises tasks that are too easy'                                 CONFIRMED
4                                           §6 'Mastery is static within a C session'                                 CONFIRMED
5                                          §2.3(2) 'C never writes back to B mastery'                                 CONFIRMED
6                                    work order: 'C reads B mastery once per session'                                    NUANCE
7                 §1 rule thresholds / §5 hook at session.py:295, evidence at 284-293                                 CONFIRMED
8                                                                 §6.4 W = {2:2, 3:3}                                 CONFIRMED
9   §7 reward uses a 'rolling_success' derived from policy-visible recent_correctness                CONTRADICTED (as a signal)
10                                         §6.2 'session dropout hazard needs adding'                                 CONFIRMED
11                                                          §10 'time-in-band' metric                      NEEDS OWN DEFINITION
12                                                   §5 'policy hook is the only one'                                 CONFIRMED
13                                                         §9 research-mode readiness           CONTRADICTS 'configs are final'
14                                                         §8 ColdStartTS / LinTS RNG                                 AVAILABLE
15                    sim fidelity: nominal P(correct) == realized first-attempt rate  SMALL POSITIVE BIAS (realized > nominal)
16                                     §5 'allowed = not overridden; fallback = hold'                     CONFIRMED WITH CAVEAT
17                                                 action_overridden == safety event?                                        NO
18                                 one technical issue voids the session's composites                                  OBSERVED
19                                    Evidence replay (our understanding of the loop)                                 CONFIRMED

                                                                                                                                       evidence
0                                                                                       flat while d_norm<=mastery, then non-increasing (sec 2)
1                                                                                                      fallback has no mastery argument (sec 2)
2          only quit_after_error does; skip, quit_without_recent_error, technical, pauses are constants - identical across levels: True (sec 3)
3                                                          levels 1-4 identical at mastery 0.9; c_engagement_propensity has no consumer (sec 4)
4                                                                                                                                       (sec 5)
5                                           no attribute/payload store; B sessions generated before C loop (session_loop.py:264 vs 269) (sec 5)
6                             payload handed once per session, but READ per task (session.py:198-213, 238) - same session-start value each time
7                                                                   matches policy/config.py defaults and the source lines printed in secs 6, 8
8                                                                                                                                  {2: 2, 3: 3}
9   recent_correctness_rate counts correct_task, which retries drive to ~1: 1.000 of completed tasks correct; = 1.0 at 100% (combined) / 99%...
10                                 no dropout in run_c_session; only safe-termination (session.py:333-336); quits end a TASK, never the session
11                                                               time_in_target_band_sec is a caller-supplied placeholder (session_loop.py:226)
12                                     propose_action(policy_mode, evidence, policy_config) at session.py:295; policy_mode Literal has 3 values
13                                                               every config is TEST_FIXTURE_ONLY: True; validator has 0 callers outside tests
14                                                SeedManager.substream(...,'policy_exploration') exists but is unused by run_c_session (sec 8)
15  realized - nominal = +0.0148 (combined m=0.5, pooled z 3.5, overstated: levels share seeds); +0.0146 (c_only, z 3.0); action_provider ca...
16  hold itself is overridden at 0% (combined) / 0% (c_only) of simulated decisions; allowed-set size 1/2/3 = 5%/55%/41% (combined), 2%/98%/...
17  90% (combined) / 99% (c_only) of overrides are caps / bound clamps only; real safety trigger rate (recovery flag per decision) = 0.025 /...
18  telemetry complete in 66% (combined) / 65% (c_only) of 12-task sessions; flagged by technical PAUSES (aggregation/derive.py:152-153) as ...
19                                                                                rule+safety replay reproduces all recorded decisions (sec 10)
```

### Findings — step 11


**Confirmed — the master-plan §6 extensions are necessary:**
- **6.1 mastery growth (+ a "fit" term):** mastery is static in a session and across C (no writes; B is generated before C), and nothing penalises easy tasks, so the unextended agent learns "stay at level 1".
- **6.2 dropout hazard:** `run_c_session` has no dropout. Quits end a *task* (`attempt_loop.py:299`), never the session; the only session ender is safe termination (`session.py:333-336`, never fired in the 200-session batch, 0%). `c_engagement_propensity` has no consumer, so the plan's `−d·engagement_propensity` term is entirely ours to define.
- **6.3 learner types:** learner heterogeneity enters only through four trait parameters plus mastery.
- **6.4 multi-session runner:** `CLearnerSessionState` semantics (N, spacing, prior state) are exactly as the plan assumes, W = {2: 2, 3: 3}.

**Contradicted or nuanced — plan / work order text needs a note (the plan is not edited):**
1. **§7 reward `rolling_success`:** if it is derived from the policy-visible `recent_correctness_rate`, it is degenerate. That field counts `correct_task`, which retries push to 1.000 of completed tasks (99.6% / 99.3% of decisions equal 1.0). NB04 should base success on *first-attempt* correctness (available on the summaries, mean ≈ 0.68–0.70 here), which is a different feature from the one the rule policy reads.
2. **`action_overridden` ≠ safety event** (sec 10): use the recovery flag for `w_safe`.
3. **c_only has only two reachable levels (1–2)** and the allowed-set is 2 actions in 98.5% of decisions, which weakens the c_only bandit/Q comparison. Combined mode ranges over 1–5.
4. **Plan §5 "fallback = hold":** hold is itself overridden in 0.5% (combined) of decisions; the allowed set was never empty in 2,400 decisions, but the fallback needs a guard.
5. **"Once per session" (work order):** read per task, handed once.
6. **Technical *pauses* void a session's composites** (34% of sessions), so session-level reward validation (NB04) shrinks to ~65% of sessions.
7. **Realized > nominal P(correct)** by ≈ 1.5 points (section 3), and `time_in_target_band_sec` is a placeholder (NB08 needs its own time-in-band).
8. **Config status:** every parameter is TEST_FIXTURE_ONLY and the research-mode guard is unenforced (section 9).

**For NB02:** reproduce the 4 direct seed calls (section 8) and the config recipe; NB02's parity test can lean on the fact that policy/safety consume no RNG and that the seed path carries no difficulty or action. **For NB03:** calibrate against realized (not nominal) rates, and remember that `recent_correctness` carries almost no signal.

---
_Literature-informed synthetic data — not clinical evidence. Simulation-only; not approved for use with children._
