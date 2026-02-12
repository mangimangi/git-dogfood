# Git-dogfood: Vendor V2 Compliance

Changes needed to make git-dogfood compliant with the git-vendored v2 contract.

## Summary

| Area | Status | Work needed |
|------|--------|-------------|
| `install.sh` env vars | non-compliant | Use `VENDOR_REF`/`VENDOR_REPO` instead of `$1`/`$2` |
| `install.sh` install dir | non-compliant | Use `VENDOR_INSTALL_DIR` with `.dogfood/` fallback |
| `install.sh` manifest | non-compliant | Write all paths to `$VENDOR_MANIFEST` |
| `install.sh` version file | non-compliant | Remove `.dogfood/.version` write |
| `install.sh` self-registration | non-compliant | Remove `.vendored/config.json` write |
| `dogfood/resolve` config loading | **compliant** | No changes needed |

## install.sh changes

### 1. Environment variables

Replace positional args with env vars (keep positional as fallback for old framework):

```bash
# Before
VERSION="${1:?Usage: install.sh <version> [<repo>]}"
DOGFOOD_REPO="${2:-mangimangi/git-dogfood}"

# After
VERSION="${VENDOR_REF:-${1:?Usage: install.sh <version> [<repo>]}}"
DOGFOOD_REPO="${VENDOR_REPO:-${2:-mangimangi/git-dogfood}}"
```

### 2. VENDOR_INSTALL_DIR

Add install dir resolution. The `resolve` script installs under `$INSTALL_DIR`.

```bash
INSTALL_DIR="${VENDOR_INSTALL_DIR:-.dogfood}"
```

Dogfood note: when git-dogfood is installed in its own repo, the framework infers dogfood from key/repo name matching and does not set `VENDOR_INSTALL_DIR`. The fallback to `.dogfood/` kicks in automatically.

### 3. File placement

| File | Before | After | Notes |
|------|--------|-------|-------|
| `resolve` | `.dogfood/resolve` | `$INSTALL_DIR/resolve` | Code |
| `dogfood.yml` | `.github/workflows/dogfood.yml` | `.github/workflows/dogfood.yml` | Workflow — fixed path |

Update the `mkdir` and `fetch_file` calls:

```bash
# Before
mkdir -p .dogfood .github/workflows
fetch_file "dogfood/resolve" ".dogfood/resolve"
chmod +x .dogfood/resolve

# After
mkdir -p "$INSTALL_DIR" .github/workflows
fetch_file "dogfood/resolve" "$INSTALL_DIR/resolve"
chmod +x "$INSTALL_DIR/resolve"
```

### 4. Remove version file write

Delete this line — the framework writes version to `.vendored/manifests/git-dogfood.version`:

```bash
# DELETE THIS LINE
echo "$VERSION" > .dogfood/.version
```

### 5. Remove self-registration

Delete the entire `.vendored/config.json` registration block:

```bash
# DELETE THIS ENTIRE BLOCK
if [ -f .vendored/config.json ]; then
    python3 -c "
import json
with open('.vendored/config.json') as f:
    config = json.load(f)
config.setdefault('vendors', {})
config['vendors']['git-dogfood'] = {
    'repo': '$DOGFOOD_REPO',
    'install_branch': 'chore/install-git-dogfood',
    'protected': ['.dogfood/**', '.github/workflows/dogfood.yml'],
    'allowed': ['.dogfood/.version']
}
with open('.vendored/config.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"
    echo "Registered git-dogfood in .vendored/config.json"
fi
```

### 6. Manifest emission

Track every installed file and write to `$VENDOR_MANIFEST`:

```bash
INSTALLED_FILES=()

mkdir -p "$INSTALL_DIR" .github/workflows

fetch_file "dogfood/resolve" "$INSTALL_DIR/resolve"
chmod +x "$INSTALL_DIR/resolve"
INSTALLED_FILES+=("$INSTALL_DIR/resolve")

# Workflow (first-install only, add to manifest if installed)
if [ ! -f ".github/workflows/dogfood.yml" ]; then
    if fetch_file "templates/github/workflows/dogfood.yml" ".github/workflows/dogfood.yml" 2>/dev/null; then
        INSTALLED_FILES+=(".github/workflows/dogfood.yml")
    fi
fi

# Write manifest
if [ -n "${VENDOR_MANIFEST:-}" ]; then
    printf '%s\n' "${INSTALLED_FILES[@]}" > "$VENDOR_MANIFEST"
fi
```

---

## dogfood/resolve — no changes needed

The resolve script reads `.vendored/config.json` (the framework's vendor registry) to find the git-dogfood entry. This is framework-level config, not project-specific config, so no migration to `.vendored/configs/` is needed. The resolve script is already compliant.

---

## Complete install.sh (after changes)

For reference, the full v2-compliant `install.sh`:

```bash
#!/bin/bash
# git-dogfood/install.sh - Install or update git-dogfood in a project
#
# Environment (v2 contract):
#   VENDOR_REF        - Version/ref to install
#   VENDOR_REPO       - GitHub repo (owner/name)
#   VENDOR_MANIFEST   - Path to write file manifest
#   VENDOR_INSTALL_DIR - Base directory for installed files
#   GH_TOKEN          - Auth token for private repos
#
# Fallback (v1 compat):
#   install.sh <version> [<repo>]
#
set -euo pipefail

VERSION="${VENDOR_REF:-${1:?Usage: install.sh <version> [<repo>]}}"
DOGFOOD_REPO="${VENDOR_REPO:-${2:-mangimangi/git-dogfood}}"
INSTALL_DIR="${VENDOR_INSTALL_DIR:-.dogfood}"
INSTALLED_FILES=()

# File download helper
fetch_file() {
    local repo_path="$1"
    local dest="$2"
    local ref="${3:-v$VERSION}"

    if [ -n "${GH_TOKEN:-}" ] && command -v gh &>/dev/null; then
        gh api "repos/$DOGFOOD_REPO/contents/$repo_path?ref=$ref" \
            --jq '.content' | base64 -d > "$dest"
    else
        local base="https://raw.githubusercontent.com/$DOGFOOD_REPO"
        curl -fsSL "$base/$ref/$repo_path" -o "$dest"
    fi
}

echo "Installing git-dogfood v$VERSION from $DOGFOOD_REPO"

# Create directories
mkdir -p "$INSTALL_DIR" .github/workflows

# Download resolve script
echo "Downloading resolve..."
fetch_file "dogfood/resolve" "$INSTALL_DIR/resolve"
chmod +x "$INSTALL_DIR/resolve"
INSTALLED_FILES+=("$INSTALL_DIR/resolve")

# Install workflow (first install only)
if [ ! -f ".github/workflows/dogfood.yml" ]; then
    if fetch_file "templates/github/workflows/dogfood.yml" \
                  ".github/workflows/dogfood.yml" 2>/dev/null; then
        echo "Installed .github/workflows/dogfood.yml"
        INSTALLED_FILES+=(".github/workflows/dogfood.yml")
    fi
else
    echo "Workflow .github/workflows/dogfood.yml already exists, skipping"
fi

# Write manifest
if [ -n "${VENDOR_MANIFEST:-}" ]; then
    printf '%s\n' "${INSTALLED_FILES[@]}" > "$VENDOR_MANIFEST"
fi

echo ""
echo "Done! git-dogfood v$VERSION installed."
```

## Backwards compatibility

| Scenario | Behavior |
|----------|----------|
| New framework | `VENDOR_INSTALL_DIR` set → resolve goes to `.vendored/pkg/git-dogfood/` |
| Old framework | Env vars unset → falls back to `.dogfood/`, no manifest written |
| Dogfood (self-install) | `VENDOR_INSTALL_DIR` not set → falls back to `.dogfood/` |

## Checklist

- [ ] `install.sh`: Use `VENDOR_REF`/`VENDOR_REPO` with positional fallback
- [ ] `install.sh`: Use `VENDOR_INSTALL_DIR` with `.dogfood/` fallback
- [ ] `install.sh`: Track all files in `INSTALLED_FILES` array
- [ ] `install.sh`: Write `$VENDOR_MANIFEST` when set
- [ ] `install.sh`: Remove `.dogfood/.version` write
- [ ] `install.sh`: Remove `.vendored/config.json` self-registration block
- [ ] Tests: Update for new file paths and env var contract
- [ ] Release: Tag new version
