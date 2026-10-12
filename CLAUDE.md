# Repository engineering instructions

Read and follow [AGENTS.md](AGENTS.md), the shared repository engineering policy.
Applicable module-local instructions also apply. Canonical specifications and
accepted ADRs remain the architecture authority; this entry point adds no policy.

For substantial implementation work, use
[the shared engineering workflow](.agents/skills/engineering-implementation/SKILL.md).
The Claude skill entry point references that same workflow.

## Documentation rules
- Do not create new .md files unless asked. Update existing ones instead.
- Plans for a feature go in docs/specs/<yyyy-mm-slug>/ only.
- When a feature is merged: set the spec's status to done and move it to docs/archive/.
- Any significant architectural choice gets a new ADR; never edit an accepted ADR — supersede it.
- After changing behavior, update ARCHITECTURE.md if it is now wrong.