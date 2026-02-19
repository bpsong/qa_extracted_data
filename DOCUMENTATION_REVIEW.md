# Documentation Review: docs set vs source code

## Scope reviewed

Because this repository currently stores documentation files at the repository root (not in a `docs/` directory), this review covered:

- `README.md`
- `CONFIGURATION.md`
- `DEPLOYMENT.md`
- `TECHNICAL_GUIDE.md`
- `USER_GUIDE.md`
- `SCHEMA_GUIDE.md`

Source-of-truth code checked:

- `utils/config_loader.py`
- `utils/directory_config.py`
- `utils/file_utils.py`
- `streamlit_app.py`
- `requirements.txt`

## Overall result

Documentation is mostly aligned with runtime behavior, especially around:

- canonical directory keys under `directories.*`
- canonical processing keys under `processing.*`
- queue/edit/audit workflow and schema-driven forms

However, there are several documentation updates recommended below.

## Recommended documentation updates

### 1) `DEPLOYMENT.md`: application config snippet uses non-canonical keys

**Issue**

The "Application Config (`config.yaml`)" example currently uses legacy/unsupported keys such as:

- `data_directory`
- `pdf_directory`
- `schema_directory`
- `output_directory`
- `audit_directory`
- top-level `max_file_size`, `lock_timeout`

But runtime configuration is loaded from nested sections and canonical keys:

- `directories.json_docs`, `directories.pdf_docs`, `directories.corrected`, `directories.audits`, `directories.locks`
- `processing.max_file_size`, `processing.lock_timeout`

**Documentation update needed**

Replace this section with canonical nested config structure consistent with `utils/config_loader.py`.

---

### 2) `README.md`: dependency minimum versions are stale

**Issue**

`README.md` lists older minimum versions (for example, `streamlit>=1.31.0`) while `requirements.txt` now pins higher minimums (for example, `streamlit>=1.50.0`, `pydantic>=2.11.0`, etc.).

**Documentation update needed**

Update the dependency list in `README.md` to match `requirements.txt` exactly, or replace hardcoded versions with a short note: "See `requirements.txt` for canonical dependency versions."

---

### 3) Python version guidance should be normalized

**Issue**

`README.md` and `DEPLOYMENT.md` currently state Python `3.8+`, while current dependencies and deployment examples effectively target modern versions (e.g., Docker example uses Python 3.9).

**Documentation update needed**

Normalize Python guidance across docs to a single minimum that is guaranteed compatible with `requirements.txt` (recommended: `3.9+`).

---

### 4) Clarify docs location naming

**Issue**

Some workflows refer to "documentation in docs folder," but this repository stores primary docs in the root.

**Documentation update needed**

Add a short note in `README.md` under "Documentation by Audience" that docs live in the repository root.

## No update currently needed

The following are currently consistent with source code and can remain as-is:

- `CONFIGURATION.md` canonical key names (`processing.lock_timeout`, `processing.max_file_size`, `directories.*`)
- `TECHNICAL_GUIDE.md` key and directory conventions
- `USER_GUIDE.md` audit path reference (`audits/audit.jsonl`)

## Optional follow-up cleanup (non-documentation)

`setup.py` still creates `audit_logs/` during bootstrap, while runtime/config conventions use `audits/`. This is a **code** inconsistency rather than a docs inconsistency and should be fixed in source.
