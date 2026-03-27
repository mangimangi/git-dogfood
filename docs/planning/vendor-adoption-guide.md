# Adopt git-vendored Framework Features

Upgrade git-dogfood to use the latest git-vendored framework capabilities:
`$VENDOR_LIB` shell helpers, vendor support config, and Codex compatibility.

## Prerequisites

- git-vendored upgrade from 0.0.17 to a version that ships VENDOR_LIB,
  `--setup-hooks`, and the `support` config schema. This arrives through
  the normal dogfood loop (Bump & Release → PR).

## Tasks

### 1. Adopt `$VENDOR_LIB` in `install.sh`

Replace the hand-rolled `fetch_file` (install.sh:23-34) with the framework's
shared helper library using the inline-fallback pattern:

```bash
source "$VENDOR_LIB" 2>/dev/null || {
    fetch_file() {
        local src="$1" dst="$2"
        curl -fsSL "https://raw.githubusercontent.com/$VENDOR_REPO/$VENDOR_REF/$src" -o "$dst"
        [ "${3:-}" = "+x" ] && chmod +x "$dst"
        echo "$dst" >> "${VENDOR_MANIFEST:-/dev/null}"
    }
}
```

This drops the local auth/download logic and defers to the framework when
available. The fallback keeps install.sh working on older framework versions.

**Changes:** `install.sh` — remove lines 22-34 (custom `fetch_file` +
comment), replace with the `source` block above. Adjust the rest of the
script to use the new `fetch_file` signature (`+x` flag instead of separate
`chmod`).

### 2. Add `support` config to `git-dogfood.json`

Add the `support` key so `.vendored/feedback` surfaces useful info:

```json
{
  "_vendor": {
    "repo": "mangimangi/git-dogfood",
    "install_branch": "chore/install-git-dogfood",
    "protected": [
      ".dogfood/**",
      ".github/workflows/dogfood.yml"
    ]
  },
  "support": {
    "issues": "https://github.com/mangimangi/git-dogfood/issues",
    "instructions": "Include your .vendored/manifests/git-dogfood.version in bug reports.",
    "labels": ["vendored", "bug"]
  }
}
```

**Changes:** `.vendored/configs/git-dogfood.json`

### 3. Regenerate hooks via `--setup-hooks`

`.claude/settings.json` currently hard-codes `$CLAUDE_PROJECT_DIR` (lines 9,
19). After upgrading git-vendored, run:

```
python3 .vendored/install --setup-hooks
```

This regenerates `.claude/settings.json` (without `$CLAUDE_PROJECT_DIR`) and
creates `.codex/config.toml` for Codex compatibility.

**Changes:** `.claude/settings.json` (regenerated), `.codex/config.toml` (new)

### 4. Verify vendor hooks don't use `$CLAUDE_PROJECT_DIR`

The vendor hooks under `.vendored/pkg/` (pearls, madreperla) already use
`PROJECT_DIR` with a `CLAUDE_PROJECT_DIR` fallback. These are vendor-managed
files — no changes needed on our side, but verify after upgrade that the
fallback chain is `PROJECT_DIR → git rev-parse` (no `CLAUDE_PROJECT_DIR`).

## Sequencing

Tasks 1 and 2 can proceed independently and ahead of the git-vendored upgrade
(the VENDOR_LIB fallback ensures backward compatibility, and the `support`
key is ignored by older framework versions).

Tasks 3 and 4 are blocked on the git-vendored upgrade landing.

## Out of scope

- Implementing VENDOR_LIB, `--setup-hooks`, or the `support` schema (these
  are git-vendored framework features, not git-dogfood work).
- Upgrading git-vendored itself (arrives via the dogfood loop).
