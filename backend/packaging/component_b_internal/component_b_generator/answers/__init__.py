"""Pure correct-answer functions + deterministic answer normalization (Phase B2A).

Answers are **recomputed** from instantiated operands (catalogue §8: stored answers are never
trusted). Each rule is a pure function of the sampled operands; normalization gives a single
canonical string form so equivalence checks and distractor de-duplication are deterministic.
"""
