import csv
import io
import json

import pytest

from utils.audit_view import AuditView


@pytest.fixture
def sample_entries():
    return [
        {
            "filename": "invoice_001.json",
            "timestamp": "2026-02-14T10:00:00",
            "user": "alice",
            "action": "corrected",
            "has_changes": True,
            "change_summary": {"total": 2, "modified": 1, "added": 1, "removed": 0, "type_changed": 0},
            "submission_method": "manual",
        },
        {
            "filename": "receipt_001.json",
            "timestamp": "2026-02-14T10:05:00",
            "user": "bob",
            "action": "reviewed",
            "has_changes": False,
            "change_summary": {"total": 0, "modified": 0, "added": 0, "removed": 0, "type_changed": 0},
            "submission_method": "automated",
        },
    ]


def test_export_audit_data_csv_has_header_and_rows(sample_entries):
    csv_data = AuditView.export_audit_data(sample_entries, "csv")

    assert csv_data is not None
    rows = list(csv.DictReader(io.StringIO(csv_data)))
    assert len(rows) == 2
    assert rows[0]["filename"] == "invoice_001.json"
    assert rows[0]["total_changes"] == "2"
    assert rows[1]["filename"] == "receipt_001.json"
    assert rows[1]["has_changes"] == "False"

    header = next(csv.reader([csv_data.splitlines()[0]]))
    assert header == [
        "filename",
        "timestamp",
        "user",
        "action",
        "has_changes",
        "total_changes",
        "modified_fields",
        "added_fields",
        "removed_fields",
        "type_changed_fields",
        "submission_method",
    ]


def test_export_audit_data_json_is_valid_and_contains_expected_keys(sample_entries):
    json_data = AuditView.export_audit_data(sample_entries, "json")

    assert json_data is not None
    payload = json.loads(json_data)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert {"filename", "timestamp", "user", "action", "change_summary"}.issubset(payload[0].keys())
    assert payload[0]["filename"] == "invoice_001.json"
    assert payload[1]["change_summary"]["total"] == 0


@pytest.mark.parametrize("export_format", ["csv", "json"])
def test_export_audit_data_empty_entries_returns_none(export_format):
    assert AuditView.export_audit_data([], export_format) is None
