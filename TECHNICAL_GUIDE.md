# Technical Guide

This guide consolidates implementation-facing details for engineers, maintainers, and DevOps.

## Architecture summary

- `streamlit_app.py` is the entry point and route/controller for views (`queue`, `edit`, `audit`, `schema_editor`).
- Most behavior lives in `utils/` modules:
  - file lifecycle and locking: `utils/file_utils.py`
  - schema loading and config lookup: `utils/schema_loader.py`
  - configuration validation and defaults: `utils/config_loader.py`
  - UI view modules: `utils/queue_view.py`, `utils/edit_view.py`, `utils/audit_view.py`, `utils/schema_editor_view.py`

## Runtime directories (canonical)

Configured under `directories` in `config.yaml`:
- `json_docs`
- `corrected`
- `audits`
- `pdf_docs`
- `locks`

Audit entries are stored in `audits/audit.jsonl`.

## Configuration keys used by code

Canonical processing keys consumed by app/config code:
- `processing.lock_timeout`
- `processing.max_file_size`

If alternative keys are added in future (`*_minutes`, `*_mb`), add explicit translation logic in `config_loader.py` before documenting them.

## Source of truth

Use these files as the canonical implementation references before changing docs:
- Runtime directory names and audit path behavior: `utils/file_utils.py`
- Default configuration shape and key validation: `utils/config_loader.py`
- Runtime lock timeout wiring in UI/session flow: `streamlit_app.py`

When docs and code differ, update docs to match these sources unless a code change is part of the same PR.

## Testing

Run full tests:

```bash
python -m pytest
```

Targeted regression checks:

```bash
python -m pytest test_config_loader.py test_file_utils.py test_schema_loader.py
```

Coverage policy helper:

```bash
python tools/coverage_policy.py --coverage-xml coverage.xml --policy-file coverage_policy.json
```

## Documentation map

- Product overview and day-to-day setup: `README.md`
- Non-technical operators: `USER_GUIDE.md`
- Schema design: `SCHEMA_GUIDE.md`
- Deployment options: `DEPLOYMENT.md`
- Configuration deep dive: `CONFIGURATION.md`

## Docs versioning in releases

For any PR that changes runtime behavior, config keys, directory names, or operational workflow:
- Update the affected docs in the same PR.
- Run a targeted consistency check for deprecated names before merging.
- Add a short note in the release summary calling out doc updates.

Suggested checks:

```bash
rg "audit[_]logs|max_file_size[_]mb|lock_timeout[_]minutes|data[_]directory|audit[_]directory" README.md USER_GUIDE.md DEPLOYMENT.md CONFIGURATION.md
```
