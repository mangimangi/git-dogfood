# Initial consumer self-install on first dogfood setup

## Problem

When git-dogfood is first installed in a consumer repo, the dogfood infrastructure
(resolve + workflow) is in place but the consumer's first self-install doesn't happen
until the next Bump & Release. This means there's a gap between "dogfood is installed"
and "the dogfood loop is actually working."

## Idea

After installing the dogfood infrastructure, `install.sh` triggers `install-vendored`
for the consumer repo itself:

```bash
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    CONSUMER="${GITHUB_REPOSITORY##*/}"
    gh workflow run install-vendored.yml \
        -f vendor="$CONSUMER" \
        -f version=latest
fi
```

## Open questions

- Does `install-vendored.yml` accept `workflow_dispatch`, or is it `workflow_call` only?
- Should this be a separate workflow step rather than inline in install.sh?
- Error handling: what if the consumer doesn't have an install.sh yet? (Fail loudly
  in install-vendored — probably fine.)

## Status

Out of scope for now. The dogfood loop works on next Bump & Release. This would
eliminate the gap for first-time setup.
