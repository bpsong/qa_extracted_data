# Documentation Review: Coverage, Accuracy, and Consolidation

## Scope reviewed

- `README.md`
- `CONFIGURATION.md`
- `SCHEMA_GUIDE.md`
- `DEPLOYMENT.md`
- `sandbox/README.md`

## Overall assessment

The codebase has **good breadth** of documentation, but information is split across files and has a few stale references that can confuse users.

## What matches the codebase well

- Core workflow (queue → edit → submit → audit) aligns with `streamlit_app.py` and view modules.
- Directory-based processing model is aligned with `utils/file_utils.py` and `utils/config_loader.py`.
- Schema-driven form approach aligns with `utils/schema_loader.py`, `utils/model_builder.py`, and `utils/form_generator.py`.

## Accuracy issues found

1. **Audit directory naming drift**
   - Some docs referred to `audit_logs/`, while runtime config and file utilities use `audits/`.

2. **Configuration key naming drift in deployment docs**
   - `max_file_size_mb` / `lock_timeout_minutes` appeared in examples, while code consumes `max_file_size` / `lock_timeout`.

3. **Non-existent template directory references**
   - `CONFIGURATION.md` referenced `config-templates/` files that are not present in the repository.

## Changes made in this review

- Standardized docs to use **`audits/`** naming.
- Updated deployment config examples to canonical processing keys:
  - `processing.max_file_size`
  - `processing.lock_timeout`
- Replaced `config-templates/` references with the existing `example-config.yaml` workflow.
- Added two consolidation docs:
  - `USER_GUIDE.md` (task-oriented, non-technical)
  - `TECHNICAL_GUIDE.md` (implementation-oriented)

## Consolidation model (recommended)

Use a persona-first doc set:

1. **`USER_GUIDE.md`** — operators, QA users, business reviewers.
2. **`README.md`** — project entrypoint and quick links.
3. **`TECHNICAL_GUIDE.md`** — architecture, canonical config keys, testing entry points.
4. **`SCHEMA_GUIDE.md`** — schema authoring deep dive.
5. **`DEPLOYMENT.md`** — deployment/runbook details.
6. **`CONFIGURATION.md`** — exhaustive configuration behavior and examples.

## Improvements for non-technical users

- Keep action-oriented language and screen-by-screen workflows.
- Prefer “what to do next” troubleshooting over internal implementation details.
- Maintain a single “common errors” table in `USER_GUIDE.md` and link from README.

## Improvements for technical users

- Add a short “source of truth” section listing canonical keys and path names.
- Add “docs versioning” note in release process to avoid stale examples.
- Keep environment-specific snippets limited to settings that are verified in code.

## Maintenance checklist (lightweight)

For any PR that changes config/runtime behavior:
- Update relevant guide(s).
- Verify names of directories and keys against `utils/config_loader.py` and `utils/file_utils.py`.
- Run at least targeted docs consistency checks (grep for deprecated key/path strings).
