# Component C — RL difficulty policy: summary (simulation only)

*Literature-informed synthetic data — not clinical evidence. Simulation-only; not approved for use with children.*

## What was built
- A step-wise Component C environment (`rl_core/env.py`) that reproduces the generator's rule policy exactly (360 / 360 decisions identical), plus two switchable simulator additions: mastery growth between sessions and boredom-driven dropout.
- A tabular Q-learning agent (`rl_core/agent.py`): 135 states (difficulty × first-try × strain × mastery buckets), 3 actions, reward from the next task. It sees only the observation dict.
- Trained on 3,000 simulated learners × 25 sessions (about 15 min); a second model with the strain weight set to 0 serves as the frustration ablation. Evaluated on new learners (seeds ≥ 9,000,000). Notebooks NB00–NB03.

## Main results (300 new learners × 25 sessions, mean ± SE)

| arm | mastery gain | first-try | time-in-band (0.6–0.8) | frustration | safety events / session | dropout / session | mean difficulty |
|---|---|---|---|---|---|---|---|
| rule | 0.210 ± 0.003 | 0.710 | 0.539 | 0.298 | 0.172 | 0.204 | 2.64 |
| hold level 1 | 0.090 ± 0.001 | 0.723 | 0.565 | 0.284 | 0.052 | 0.286 | 1.20 |
| hold level 3 | 0.279 ± 0.005 | 0.779 | 0.467 | 0.197 | 0.068 | 0.195 | 2.54 |
| **Q main** | **0.281 ± 0.003** | 0.749 | 0.522 | 0.269 | 0.079 | 0.179 | 2.57 |
| Q no-strain | 0.217 ± 0.004 | 0.773 | 0.512 | 0.320 | 0.044 | 0.252 | 1.95 |

Q main vs rule (paired, same learners): mastery gain +0.071 ± 0.002, frustration −0.029, safety events −0.093, dropout −0.025; time-in-band −0.016 (slightly worse). Q main vs the best fixed level (hold level 3): mastery gain +0.002 ± 0.003 — a tie — with higher frustration (0.269 vs 0.197). The learned policy mostly finds a good difficulty level; it does not beat a well-chosen fixed level in this simulator. It helps beginner, middle and advanced starting levels alike (gain +0.062 / +0.074 / +0.078 over the rule) without pushing advanced learners down or overloading beginners.

In short: Q beats the rule and finds the best difficulty level by itself. Hold level 3 is a hindsight baseline: level 3 was picked by sweeping every level on the simulator (NB02 step 1), which a real deployment cannot do. It also does well partly because the simulated children start close together (starting mastery 0.16–0.51).

## Ablation verdict (strain weight 0)
The strain penalty does change behaviour (greedy policies agree in 64 % of states): the no-strain agent stays at easier levels (mean difficulty 1.95 vs 2.57; 28 % of decisions at level 1 vs 13 %) and has fewer safety events (0.044 vs 0.079) and lower rolling strain, but also a **higher frustration index** (0.320 vs 0.269), more dropout (0.252 vs 0.179) and less learning (gain 0.217 vs 0.281). Splitting the index into its six components shows that the whole gap comes from **floor_hits** (+0.068 of a +0.052 total gap, z 53; 87 % of its sessions contain a floor hit vs 42 %). Every component that measures actual struggle (error runs, extra attempts, quitting after errors, safety overrides) is *lower* for the no-strain agent. So the higher index reflects how the frustration formula is built (time at the difficulty floor counts as frustration even when the child is succeeding), not more distress. The no-strain agent is still the worse policy (less learning, more dropout), so the penalty is kept; the frustration index should not be compared on its own across policies that sit at very different difficulty levels.

## Cold start (100 new learners × 25 sessions, one agent per child)
- Learning from scratch is fast in reward terms: a fresh agent is above the rule's reward within the first 5 learners and plateaus at about 0.51 by about 25 learners.
- Per child, a scratch agent reaches the same reward as the pretrained model but learns less: whole-run mastery gain 0.170, below the rule (0.212). The pretrained model gives 0.282 (frozen) and 0.280 (fine-tuned, alpha 0.05, eps 0.05).
- Pretrained + fine-tune beats scratch on mastery gain from the first acting sessions (+0.004 per session, z 23), but not on reward. Fine-tuning does not improve on the frozen pretrained model by session 25 (reward −0.003 ± 0.003; gain +0.0002 ± 0.0002).

## Limitations
- Synthetic data; no real child data were used.
- The simulator additions are assumptions: only eta (growth step) was fitted to the dataset's median mastery change; the stretch zone, boredom margin and dropout constants are assumed.
- tau (0.70) was derived from the simulator, not taken from the Blueprint §7B target band (documented deviation).
- c_only mode is not evaluated: only difficulty levels 1–2 are reachable there, so there is almost nothing for RL to choose.
- Starting mastery spans only about 0.16–0.51 (mean of 7 skills), so no truly advanced learners are simulated.
- Per-child learning is simulation-only and needs ethics approval before any use with children.

*Literature-informed synthetic data — not clinical evidence. Simulation-only; not approved for use with children.*
