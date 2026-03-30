# vendor-config-validation: git-dogfood

> **Target repo:** mangimangi/git-dogfood
>
> **Parent epic:** mdci-0424 (vendor-config-validation)
>
> **Parent planning doc:** [vendor-config-validation.md](vendor-config-validation.md)
>
> **Session graph:** refine → [implement → eval]*
>
> **Blocked by:** git-vendored (schema framework must ship first)

## Context

git-dogfood is the self-update/bootstrap tool. It has minimal or no user-facing config fields. This work adds a schema file — likely trivial or empty — to participate in the validation framework.

## Scope

### 1. Create `templates/config.schema`

Declare the config fields that git-dogfood owns (if any). Even if the schema is empty, shipping one allows the audit command to validate that no misplaced fields from other vendors have leaked into git-dogfood's config.

**Acceptance criteria:**
- `templates/config.schema` exists and follows the schema format
- If git-dogfood has no user-facing config fields, ship an empty fields object:

```json
{
  "vendor": "git-dogfood",
  "fields": {}
}
```

## Cross-repo context

- git-vendored handles schema installation
- The schema format is defined by git-vendored (see vcv-git-vendored planning doc)
- This is the simplest repo in the epic — good smoke test for the framework's schema handling

## Not in scope

- Source layout alignment (separate follow-up epic)
