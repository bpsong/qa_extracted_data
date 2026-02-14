# Unit Test Edge-Case Gap Assessment

## Scope and method
I reviewed:
1. Product/business documentation to infer user workflows and business intent.
2. The current test suite composition and unit/integration distribution.
3. Utility modules in `utils/` to spot untested or under-tested branches.
4. Current test execution health.

Commands used:
- `pytest -q`
- `python -m py_compile utils/*.py`
- `python` scripts to map `utils/*` modules to `test_*.py` imports

---

## Business-intent baseline from docs
The app is intended for QA correction workflows with:
- queue/claim/lock behavior for multi-user editing,
- PDF + form side-by-side correction,
- schema-driven validation,
- audit logging/export,
- configurable directories with graceful fallback.

These intentions come from the primary workflow and feature descriptions in README and schema/config docs.

---

## Critical finding before expanding edge-case tests
### 1) Test collection is currently blocked by a syntax error
`pytest -q` fails at collection because `utils/audit_view.py` contains an f-string expression that includes a backslash in `split('\n')` inside the expression.

Impact:
- Full suite cannot run to completion.
- Any additional unit tests cannot be validated in CI until this parse error is fixed.

Recommendation:
- Fix this parser error first, then rerun the full suite and only then add new edge-case tests.

---

## Coverage-gap summary (unit tests vs codebase)
### A) High-risk modules with **no direct tests**
- `utils/pdf_viewer.py`
- `utils/form_data_collector.py`

Why this matters:
- `pdf_viewer` is directly tied to a core workflow (reviewing source PDF during correction).
- `form_data_collector` controls final payload assembly and type normalization before submission.

### B) Modules with limited or fragile coverage signals
- `utils/audit_view.py` is only indirectly covered by `test_export.py`, which is script-like and not assert-heavy.
- `test_runner.py`’s maintained test list is stale relative to the number of test files currently in repo, so it may not represent real suite health.

### C) Existing strong areas
- Arrays and form behavior have substantial tests (`test_form_generator_arrays.py`, `test_enhanced_validation_integration.py`, `test_cumulative_diff.py`).
- Queue filtering/date logic has focused tests (`test_queue_filter_*`).
- Directory/config handling is broadly tested (`test_directory_*`, `test_config_loader.py`, integration tests).

---

## Edge cases that should be added
Prioritized by production impact and alignment to documented user workflows.

### Priority 0 (must add immediately after syntax fix)
1. **PDF resolution and failure paths** (`pdf_viewer`)
   - Missing PDF directory vs empty directory vs unreadable file.
   - `streamlit_pdf_viewer` ImportError fallback to iframe.
   - iframe/base64 generation failure fallback to download/info path.
   - metadata extraction when `PyPDF2` unavailable/corrupt PDF.

2. **Form payload assembly correctness** (`form_data_collector`)
   - Missing versioned widget keys defaults per type (array/object/scalar/date/datetime).
   - Object-array `_current` DataFrame path vs fallback `field_*` list path.
   - Handling malformed session values (non-list array, non-dict object).
   - NaN/NumPy normalization and schema-property completion in `_clean_object_array`.

3. **Audit export regression safety** (`audit_view` / export path)
   - Assert-based tests for CSV/JSON content shape, encoding, line endings, and empty-entry handling.
   - Large payload preview truncation behavior.

### Priority 1 (important)
4. **Locking and concurrency edge behavior** (`file_utils`, queue flow)
   - stale lock cleanup boundary (exact timeout minute).
   - malformed lock files / race-like read/write failures.
   - claiming already-locked file by same vs different user.

5. **Schema-validation negative coverage**
   - invalid regex patterns, invalid enum defaults, mixed-type arrays, deeply nested unsupported object arrays.
   - required-field behavior for empty strings vs null for different scalar types.

### Priority 2 (nice-to-have hardening)
6. **Config + path portability edges**
   - relative path traversal, Windows-style separators on non-Windows CI mocks.
   - partially invalid config with graceful fallback for only failing section.

---

## Suggested AI prompt to generate new unit tests
Use the following prompt with your coding assistant after fixing the syntax error in `utils/audit_view.py`:

```text
You are working in /workspace/qa_extracted_data.

Goal: add high-value pytest unit tests for edge cases without changing production behavior.

Constraints:
- Do not refactor production code unless absolutely required for testability.
- Use mocks/patching for streamlit, filesystem, and optional deps (PyPDF2, streamlit_pdf_viewer).
- Prefer assert-focused tests; avoid print-only test scripts.
- Keep tests deterministic and CI-safe (no network, no real browser).

Add tests for:
1) utils/pdf_viewer.py
   - render_pdf_preview: no filename, missing PDF, found PDF, get_pdf_path exception.
   - _display_pdf fallback chain:
     a) _try_streamlit_pdf_viewer success
     b) ImportError in streamlit_pdf_viewer -> iframe fallback
     c) iframe failure -> _display_pdf_fallback
   - get_pdf_metadata with PyPDF2 available/unavailable/corrupt PDF.

2) utils/form_data_collector.py
   - collect_all_form_data with missing versioned keys for each type.
   - object-array from _current DataFrame and fallback list path.
   - malformed session values (array not list, object not dict).
   - date/datetime conversion from Python objects and strings.
   - _clean_object_array NaN, numpy scalar conversion, missing property defaulting.

3) Replace/augment test_export.py behavior with real assertions:
   - CSV export has header + expected rows.
   - JSON export is valid JSON and contains expected keys.
   - empty audit entries return expected output shape.

Also:
- Add parametrized tests where suitable.
- Ensure new tests pass with `pytest -q`.
- Print a concise summary of added test cases and rationale.
```

---

## Overall verdict
Yes — **more edge cases are needed**.

The suite has good depth in array/form paths, but important business-critical surfaces (PDF rendering fallbacks, final form-data collection, and robust export assertions) are under-tested or untested, and current suite execution is blocked by a syntax error that should be fixed first.
