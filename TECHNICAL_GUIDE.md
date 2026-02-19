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
- Documentation quality review and action plan: `DOCUMENTATION_REVIEW.md`
