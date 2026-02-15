# Test Edge-Case Gap Report

## Baseline and current state
- Baseline run (`2026-02-15`, before this pass):
  - `537` tests passing
  - `utils` total coverage: `41%`
- Current run (`2026-02-15`, after this pass):
  - `633` tests passing
  - `utils` total coverage: `47%`
  - Commands used:
    - `python -m pytest -q`
    - `python -m pytest --cov=utils --cov-report=term-missing --cov-report=xml`
    - `python tools/coverage_policy.py --coverage-xml coverage.xml --policy-file coverage_policy.json`

## Module coverage deltas
- `utils/pdf_viewer.py`: `39.6% -> 80.2%` (`+40.6`)
- `utils/form_data_collector.py`: `90.9% -> 100.0%` (`+9.1`)
- `utils/file_utils.py`: `70.7% -> 94.2%` (`+23.5`)
- `utils/schema_loader.py`: `73.2% -> 98.2%` (`+25.0`)
- `utils/submission_handler.py`: `64.4% -> 71.0%` (`+6.6`)
- `utils/audit_view.py`: `15.7% -> 28.3%` (`+12.6`)
- `utils/edit_view.py`: `16.6% -> 38.2%` (`+21.6`)
- `utils/queue_view.py`: `26.7% -> 43.0%` (`+16.3`)
- `utils/queue_filter_state.py`: `53.4% -> 81.7%` (`+28.3`)
- `utils/form_generator.py`: `36.9% -> 37.6%` (`+0.7`)
- `utils/schema_editor_view.py`: `6.7% -> 7.1%` (`+0.4`)

## What was added

### Phase 1: high-ROI module expansion
- Expanded `test_pdf_viewer.py` for:
  - fallback chain behavior
  - iframe/embed failure handling
  - download fallback errors
  - metadata rendering and convenience wrappers
- Expanded `test_form_data_collector.py` to close uncovered lines:
  - `76-77, 96-97, 102, 114, 123-128`
- Expanded focused logic tests in:
  - `test_file_utils.py`
  - `test_schema_loader.py`
  - `test_submission_handler.py`

### Phase 2: UI-heavy hardening with mocks
- Added `test_audit_view.py` for export and filter branches.
- Added `test_edit_view.py` for interaction paths and state transitions.
- Added `test_queue_view_branches.py` for queue/state branch behavior.
- Added `test_queue_filter_state_branches.py` for validation, migration, and fallback paths.

### Phase 3: extract-testable-helper updates (no behavior change)
- `utils/form_generator.py`:
  - extracted `_parse_editor_row_index`
  - extracted `_delete_row_sort_index`
  - added helper coverage in `test_form_generator_arrays.py`
- `utils/schema_editor_view.py`:
  - extracted `_validate_single_field_name`
  - integrated into `validate_field_names`
  - added helper coverage in `test_schema_editor_field_validation.py`

### Phase 4: CI policy and guardrails
- Added `coverage_policy.json`:
  - core logic modules require `>=85%`
  - UI-heavy modules tracked with non-decreasing baseline
- Added `tools/coverage_policy.py`:
  - enforces core threshold
  - enforces UI non-regression vs baseline
  - supports `--update-ui-baseline`

## Core logic gate status
- Current gate: `PASS`
- Core modules configured in `coverage_policy.json`:
  - `utils/config_loader.py`
  - `utils/directory_config.py`
  - `utils/directory_creator.py`
  - `utils/directory_validator.py`
  - `utils/file_utils.py`
  - `utils/form_data_collector.py`
  - `utils/schema_loader.py`

## Remaining backlog (next increments)
- Raise `utils/submission_handler.py` from `71.0%` to `>=85%` using targeted validation-path and error-path tests.
- Push UI-heavy coverage further:
  - `utils/audit_view.py`
  - `utils/edit_view.py`
  - `utils/queue_view.py`
- Continue helper extraction and pure-function testing in:
  - `utils/form_generator.py`
  - `utils/schema_editor_view.py`
