# Vendor self-registration — resolved

## Original problem

When `install.sh` runs in a new consumer repo, the dogfood loop was broken because
`resolve` gated on the existence of a vendor config file. Fresh repos had no config,
so resolve silently output nothing and the dogfood workflow did nothing.

## Resolution

The config existence check was an erroneous gate. The real gate is the workflow
trigger itself — `dogfood.yml` only fires after Bump & Release succeeds.

Resolve now unconditionally derives the vendor name from `GITHUB_REPOSITORY`
(convention: `acme/my-tool` → `my-tool`) and outputs it. No config lookup needed.

If the consumer doesn't have a vendor config or install.sh set up for self-vendoring,
`install-vendored` (downstream) fails loudly — which is the correct behavior. Silent
success with no action was the actual bug.

## What changed

| File | Change |
|------|--------|
| `dogfood/resolve` | Removed `vendor_config_exists()` gate and config loading |
| `tests/test_resolve.py` | Removed config-dependent tests, simplified to pure convention tests |

## What didn't change

- `install.sh` — no self-registration needed; consumer config is the consumer's concern
- `dogfood.yml` — no changes needed
- `.vendored/configs/` — git-dogfood doesn't create consumer configs

## Filed under

`gdf-744b.4` in `docs/planning/epics/gdf-744b.md`
