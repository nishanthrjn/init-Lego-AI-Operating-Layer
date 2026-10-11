# Experiment decision: bounded synthetic quality, no bridge

Status: proposed implementation; maintainer validation pending, 2026-10-11.

The existing Kaggle bridge contract remains CONTRACT_BLOCKED_SECURITY_GAP.
Manual file transfer avoids claiming transport semantics that are not established.
The only runtime choice is the exact qualified 1G model/revision and package pins.
Longer prompts require an explicitly recorded, unqualified context-size variation.

Frozen evaluation-side contract duplication avoids uploading production source.
It is a subset harness, not another ModelPort, worker, approval or disclosure layer.
The manifest binds schema, fixture, rubric, thresholds, runner and notebook together.

Arbitrary generated Python in the notebook's process boundary is unacceptable.
The selected alternative is a small statically admitted pure scalar language,
fixed tool commands and disposable fixtures. Docker or a general remote sandbox
would expand infrastructure scope and is not introduced. This restriction reduces
representativeness; results must not be extrapolated to arbitrary repositories.

One rework is conditional on real completed findings; inventing a model failure
or modifying its first output would bias the measurement. If the model gets the
first attempt right, the rework coverage gate reports incomplete. No additional
call is spent just to manufacture coverage.

Thresholds and reviewer lexical rubric are fixed before live evidence. Lexical
scoring is conservative and imperfect but deterministic and independently visible.
No model judges itself. Infrastructure failure and unavailable coverage remain
distinct from poor model quality.
