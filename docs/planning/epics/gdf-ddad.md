# Docs cohesion: git-dogfood changes

> Per-repo planning doc for git-dogfood.
>
> **Parent:** [orchestrator.md](orchestrator.md)
> **Phase:** 3

## What ships

### 1. Align madreperla.yaml to canonical shape

Same field name bug as git-vendored (`docs:` instead of `usage:`). Fix to canonical shape: `usage:` fields, remove `designs`, add `planning` + `epics` path keys (currently missing).

### 2. pearls.yaml — no changes

Already correct: `prefix: gdf`, `eval.threshold: 80`.

### 3. Audit/update root README.md, create AGENTS.md

- README.md (74 lines) — audit for accuracy
- AGENTS.md — currently missing, create with contributing conventions

### 4. Create docs/README.md

Contents for git-dogfood's docs/:
- docs/planning/ — active planning (initial-consumer-self-install.md)

## Acceptance criteria

- Config aligned, field name bugs fixed
- AGENTS.md created, README.md audited
- docs/README.md exists
- `madp configure --provider claude` succeeds
