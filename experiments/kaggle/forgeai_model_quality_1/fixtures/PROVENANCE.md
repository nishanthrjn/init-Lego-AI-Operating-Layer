# Synthetic provenance

All ten scenario objectives, functions, test examples, reference solutions and
read-only policy text were authored specifically for this evaluation on 2026-10-11.
They describe fictional integer counters, intervals and arithmetic. They contain
no customer task, account, secret or existing repository implementation.

Storage is deliberately centralized in `scenarios.py`: this directory does not
duplicate the fixture corpus. Prompt construction selects only the named case's
objective, initial synthetic source and synthetic policy; hidden oracles/reference
solutions are not initial model input. Rework receives only that case's proposal
and a bounded deterministic finding. Production was inspected only for contract
shapes, never copied into scenario content.
