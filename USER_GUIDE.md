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

## Common operator issues

- **Cannot claim file**: another user may already hold the lock.
- **PDF not shown**: file may be missing or named differently.
- **Field validation errors**: value format likely violates schema rules.

## Where to go next

- For setup and configuration: `README.md` and `CONFIGURATION.md`.
- For schema authors: `SCHEMA_GUIDE.md`.
- For developers and deployment: `TECHNICAL_GUIDE.md` and `DEPLOYMENT.md`.
