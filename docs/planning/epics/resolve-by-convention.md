# Epic: Replace `dogfood: true` flag with convention-based resolve

## Problem

The `.dogfood/resolve` script finds which vendor to auto-update by scanning
`.vendored/config.json` for a vendor with `"dogfood": true`. This is
redundant — the vendor key is always `"git-dogfood"`, and `install.sh`
doesn't even set the flag when registering in consumer repos:

```python
# install.sh — note: no "dogfood": true
config['vendors']['git-dogfood'] = {
    'repo': '$DOGFOOD_REPO',
    'install_branch': 'chore/install-git-dogfood',
    'protected': ['.dogfood/**', '.github/workflows/dogfood.yml'],
    'allowed': ['.dogfood/.version']
}
```

This means the resolve script silently fails in freshly-installed consumer
repos — the dogfood workflow fires but finds no vendor and does nothing.

## Proposal

Replace the `"dogfood": true` lookup with a convention: resolve looks for
the vendor key `"git-dogfood"` directly.

### Why this works

- The vendor key `"git-dogfood"` is already set by `install.sh` — it's the
  canonical name, not configurable
- `dogfood.yml` and `.dogfood/resolve` are installed by git-dogfood's own
  `install.sh` — they only exist because git-dogfood is vendored
- There's no realistic scenario where a different vendor would be the
  dogfood target — the workflow and resolve script are tightly coupled to
  the git-dogfood tool

### What changes

| File | Change |
|------|--------|
| `dogfood/resolve` | Look up `vendors["git-dogfood"]` instead of scanning for `dogfood: true` |
| `.vendored/config.json` | Remove `"dogfood": true` from the git-dogfood entry |
| `tests/test_resolve.py` | Update tests to match convention-based lookup |
| `install.sh` | No change needed (already registers as `"git-dogfood"`) |
| `.github/workflows/dogfood.yml` | Update comment (cosmetic) |
| `templates/github/workflows/dogfood.yml` | Update comment (cosmetic) |

## Detailed design

### `dogfood/resolve` — new logic

```python
VENDOR_KEY = "git-dogfood"

def find_dogfood_vendor(config):
    """Find the git-dogfood vendor entry. Returns key or None."""
    vendors = config.get("vendors", {})
    if VENDOR_KEY in vendors:
        return VENDOR_KEY
    return None
```

Simpler, no iteration, no flag to forget.

### `.vendored/config.json` — remove flag

```diff
  "git-dogfood": {
    "repo": "mangimangi/git-dogfood",
    "install_branch": "chore/install-git-dogfood",
-   "dogfood": true,
    "protected": [".dogfood/**", ".github/workflows/dogfood.yml"]
  },
```

### `tests/test_resolve.py` — updated tests

Key test changes:
- `test_finds_dogfood_vendor` — config has a `"git-dogfood"` key, assert it's found
- `test_returns_none_when_no_dogfood` — config has vendors but none named `"git-dogfood"`
- Remove `test_returns_none_when_dogfood_false` — flag no longer exists
- Remove `test_first_dogfood_wins` — no ambiguity with convention
- Add `test_finds_by_key_ignoring_other_vendors` — other vendors present, still finds git-dogfood
- Keep `test_empty_vendors` and `test_no_vendors_key` — edge cases still valid

## Risks and trade-offs

### What we lose
- **Theoretical flexibility**: You can't point dogfood at a different vendor
  by flipping a flag. In practice this was never done and the workflow +
  resolve script are git-dogfood-specific anyway.

### What we gain
- **Consumer repos work out of the box** — no missing flag bug
- **Simpler config** — one less field to document and explain
- **Convention over configuration** — the vendor key IS the identity

## Semver impact

This changes `dogfood/resolve` (tracked in `.semver/config.json` under
`"files": ["dogfood/*", ...]`), so a version bump will be triggered
automatically on merge to main.

The resolve output format (`vendor=git-dogfood`) is unchanged, so the
`dogfood.yml` workflow and `install-vendored.yml` need no changes beyond
their trigger. This is a **patch** bump — behavior is identical for any
repo that had the flag set correctly.

## Out of scope

- Changing `install-vendored.yml` or the install flow itself
- Adding new features to the resolve script
- Changing how the dogfood workflow triggers
