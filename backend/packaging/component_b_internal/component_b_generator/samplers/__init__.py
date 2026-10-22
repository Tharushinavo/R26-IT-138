"""Deterministic task-instance samplers (Phase B2A).

One representative, fully-specified, curriculum-safe template per frozen skill. Each sampler
is a pure function of ``(rng, grade)`` that draws operands strictly inside the catalogue's
number/operand envelope (catalogue §8) and returns structured operands + renderable prompt
data. No ``eval``; no free-text catalogue expression is executed.
"""
