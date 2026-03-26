# install.sh `_vendor` self-registration

## Problem

When `install.sh` runs in a new consumer repo, the dogfood loop is broken:

1. Bump & Release tags a new version
2. `dogfood.yml` triggers
3. `resolve` derives vendor name from `GITHUB_REPOSITORY` (e.g. `acme/my-tool` → `my-tool`)
4. `resolve` checks for `.vendored/configs/my-tool.json` — **file doesn't exist**
5. Resolve outputs nothing, dogfood silently does nothing

The resolve convention (vendor name = repo name, config filename must match) means the
**consumer repo** needs a self-referencing config file. Nobody creates it today.

Discovered during madreperla extraction (bootstrapping a fresh repo).

## What needs to change

In `install.sh`, after installing files, create `.vendored/configs/<repo-name>.json`
if it doesn't exist. The repo name is derived from `GITHUB_REPOSITORY`.

```bash
# Self-registration: ensure consumer has a vendor config for the dogfood loop.
# The config filename must match the repo name (resolve convention).
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    CONSUMER_NAME="${GITHUB_REPOSITORY##*/}"
    CONFIG_FILE=".vendored/configs/${CONSUMER_NAME}.json"
    if [ ! -f "$CONFIG_FILE" ]; then
        mkdir -p .vendored/configs
        cat > "$CONFIG_FILE" << EOF
{
  "_vendor": {
    "repo": "${GITHUB_REPOSITORY}",
    "install_branch": "chore/install-${CONSUMER_NAME}",
    "protected": [
      "${INSTALL_DIR}/**",
      ".github/workflows/dogfood.yml"
    ]
  }
}
EOF
        echo "Registered ${CONSUMER_NAME} in ${CONFIG_FILE}"
        INSTALLED_FILES+=("$CONFIG_FILE")
    fi
fi
```

### Key design decisions

- **Config named after consumer, not git-dogfood**: resolve derives vendor from
  `GITHUB_REPOSITORY` and checks for `<repo-name>.json`. The config is self-referencing.
- **`GITHUB_REPOSITORY` required**: Only runs in CI where this is set. Skip silently
  otherwise (install still works, just no dogfood loop).
- **First-install only**: `[ ! -f "$CONFIG_FILE" ]` guard. Consumer can overwrite
  defaults after initial creation.
- **`protected` uses `$INSTALL_DIR`**: Correct when framework sets `VENDOR_INSTALL_DIR`.
- **Added to manifest**: Config file appended to `INSTALLED_FILES` so the framework
  tracks it.

## Scope

Small change to `install.sh` + tests. No change to `resolve` (convention already landed).
Filed as `gdf-744b.4`.
