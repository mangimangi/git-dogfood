# install.sh `_vendor` self-registration

## Problem

When `install.sh` runs in a new repo, it does not create a `.vendored/configs/git-dogfood.json` config file with `_vendor` metadata (`repo`, `install_branch`, `protected`). The git-vendored framework expects vendors to self-register these fields.

This only surfaces when adding git-dogfood to a **new** repo — existing repos already have the `_vendor` block from prior installs. Discovered during madreperla extraction (bootstrapping a fresh repo).

## What needs to change

In `install.sh`, add a config creation block (similar to git-semver's pattern):

```bash
if [ ! -f .vendored/configs/git-dogfood.json ]; then
    mkdir -p .vendored/configs
    cat > .vendored/configs/git-dogfood.json << 'CONF'
{
  "_vendor": {
    "repo": "mangimangi/git-dogfood",
    "install_branch": "chore/install-git-dogfood",
    "protected": [
      ".dogfood/**",
      ".github/workflows/dogfood.yml"
    ]
  }
}
CONF
fi
```

The `_vendor.repo` field should use `$DOGFOOD_REPO` (or equivalent env var) so it works with forks.

## Scope

Small change — add config file creation to `install.sh`. No behavior change for existing consumers.
