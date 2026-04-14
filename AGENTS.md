# AGENTS.md

git-dogfood automates self-updating for vendored tools via GitHub Actions — when a tool releases, repos that vendor it get a PR to update.

## Key files

- `dogfood/resolve` — Python script that derives the vendor name from `GITHUB_REPOSITORY`
- `install.sh` — installer script (v2 env-var contract, v1 positional-arg fallback)
- `templates/github/workflows/dogfood.yml` — workflow template installed into consumer repos
- `.github/workflows/dogfood.yml` — this repo's own dogfood workflow
- `.vendored/` — vendored tool configs and packages
- `madreperla.yaml` — project configuration for AI tooling

## Testing

```bash
python3 -m pytest tests/
```

Tests cover the resolve script (`test_resolve.py`) and install behavior (`test_install.py`).

## Conventions

- Branch naming: `<type>/<description>` (e.g. `feat/add-resolve`, `chore/install-git-dogfood`)
- Commit messages: `<type>: <description>` (e.g. `feat: add resolve script`, `chore: bump version`)
- Issues tracked via `prl` — run `prl docs` for CLI reference

## Project config

See `madreperla.yaml` for provider configuration and doc pointers.
