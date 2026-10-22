"""Deterministic mathematical distractor-candidate generation (Phase B2A).

Distractors here are **mathematical candidate answers only** — this phase does NOT choose a
learner's wrong answer or assign an error class (those belong to later learner-response
phases). Candidates are reproducible, de-duplicated, exclude the correct answer, obey the
response format, stay within valid bounds, and each records its generating rule id
(catalogue §8).
"""
