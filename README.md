# git-dogfood

Automated self-updating for vendored tools via GitHub Actions. When a tool releases a new version, repos that vendor it automatically get a PR to update.

## How it works

git-dogfood bridges the Bump & Release workflow to the vendor install workflow, creating a self-update loop:

```
merge → Bump & Release → dogfood.yml → install-vendored → PR
```

1. A code change merges to `main`, triggering **Bump & Release** (via git-semver)
2. Bump & Release completes successfully
3. This triggers **dogfood.yml**, which runs `.dogfood/resolve` to find the `git-dogfood` vendor key in `.vendored/config.json`
4. dogfood.yml calls **install-vendored.yml** with the resolved vendor
5. install-vendored downloads the new version and opens a **PR**
6. The PR merges (manually or via automerge)

### Infinite loop prevention

The version-bump workflow skips commits whose message starts with `chore: bump version` or `chore: install`. Since install-vendored PRs merge with `chore: install ...` messages, they don't re-trigger version-bump — breaking the cycle.

## Prerequisites

- [git-vendored](https://github.com/mangimangi/git-vendored) — provides `.vendored/config.json` and the `install-vendored.yml` workflow
- [git-semver](https://github.com/mangimangi/git-semver) — provides the `Bump & Release` workflow

## Installation

```bash
# From a consumer repo that already has git-vendored and git-semver installed:
curl -fsSL https://raw.githubusercontent.com/mangimangi/git-dogfood/main/install.sh | bash -s -- <version>
```

This creates:
- `.dogfood/resolve` — the vendor resolver script
- `.dogfood/.version` — installed version
- `.github/workflows/dogfood.yml` — the self-update workflow (first install only, not overwritten on update)

And registers `git-dogfood` in `.vendored/config.json` (if present).

## Configuration

git-dogfood uses the vendor key convention — `.dogfood/resolve` looks for a `"git-dogfood"` key in `.vendored/config.json`. No extra flags needed.

Relevant fields in `.vendored/config.json`:

```json
{
  "vendors": {
    "git-dogfood": {
      "repo": "mangimangi/git-dogfood",
      "install_branch": "chore/install-git-dogfood",
      "protected": [".dogfood/**", ".github/workflows/dogfood.yml"],
      "allowed": [".dogfood/.version"]
    }
  }
}
```

| Field | Purpose |
|-------|---------|
| `repo` | Source repository for downloads |
| `install_branch` | Branch prefix for update PRs (also bypasses vendor file protection) |
| `protected` | Files that can't be modified in regular PRs |
| `allowed` | Exceptions within protected paths |
| `private` | Set `true` if the vendor repo is private (requires VENDOR_PAT) |
| `automerge` | Set `true` to auto-merge update PRs |

## Token requirements

| Token | When needed | Scopes |
|-------|------------|--------|
| `GITHUB_TOKEN` | Always (automatic, no setup) | Default workflow permissions |
| `VENDOR_PAT` | Only for private vendor repos | `repo` scope on the vendor repo |

The install-vendored workflow resolves tokens in order: `secrets.token` → `secrets.VENDOR_PAT` → `github.token`. For public vendor repos, no additional setup is needed.
