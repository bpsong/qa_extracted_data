# User Guide (Non-Technical)

This guide is for QA operators and business users who review extracted JSON against source PDFs.

## What this app does

The app helps you:
- pick unprocessed JSON files from a queue,
- compare extracted data with the original PDF,
- correct values in a form,
- submit corrections with a full audit history.

## Basic workflow

1. **Queue View**
   - Open available files.
   - Claim one file so other users cannot edit it at the same time.

2. **Edit View**
   - Left side: PDF preview.
   - Right side: editable form generated from the schema.
   - Diff panel shows what changed while you edit.

3. **Submit**
   - When complete, submit corrections.
   - Corrected JSON is saved and an audit entry is recorded.

4. **Audit View**
   - Review who changed what and when.

## File naming expectations

- Input JSON lives in `json_docs/`.
- Related PDF lives in `pdf_docs/`.
- Names should match: `invoice_001.json` ↔ `invoice_001.pdf`.

## Key terms

- **Schema**: rules that define which fields appear and what values are valid.
- **Lock**: temporary reservation of a file while someone edits it.
- **Audit log**: permanent change history in `audits/audit.jsonl`.

## Common errors

| What you see | What it usually means | What to do next |
|---|---|---|
| Cannot claim file | Another user already holds the lock, or the lock has not expired yet. | Wait briefly and try again. If it still fails, ask an admin to check stale locks in `locks/`. |
| PDF not shown | Matching PDF is missing or named differently than the JSON file. | Confirm matching names in `pdf_docs/` and `json_docs/` (example: `invoice_001.pdf` and `invoice_001.json`). |
| Field validation error on submit | One or more values do not match schema rules (type, format, required field, range). | Read the field error text, correct the value, and submit again. |
| Submitted changes but cannot find history | Audit view is filtered or you are checking the wrong file. | Open Audit View, clear filters, then search by filename and recent timestamp. |

## Where to go next

- For setup and configuration: `README.md` and `CONFIGURATION.md`.
- For schema authors: `SCHEMA_GUIDE.md`.
- For developers and deployment: `TECHNICAL_GUIDE.md` and `DEPLOYMENT.md`.
