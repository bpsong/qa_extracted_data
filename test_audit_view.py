from datetime import datetime, timedelta, date
from unittest.mock import patch

from utils.audit_view import AuditView


def test_filter_by_date_custom_invalid_range_returns_empty_and_notifies():
    entries = [{"filename": "a.json", "timestamp": datetime.now().isoformat()}]
    filters = {
        "date_filter": "custom",
        "custom_start_date": date(2026, 1, 10),
        "custom_end_date": date(2026, 1, 1),
    }

    with patch("utils.audit_view.Notify.error") as mock_notify:
        result = AuditView._filter_by_date(entries, filters)

    assert result == []
    mock_notify.assert_called_once()


def test_filter_by_date_custom_missing_dates_returns_original_entries():
    entries = [{"filename": "a.json", "timestamp": datetime.now().isoformat()}]
    filters = {
        "date_filter": "custom",
        "custom_start_date": None,
        "custom_end_date": None,
    }

    result = AuditView._filter_by_date(entries, filters)

    assert result == entries


def test_filter_by_date_includes_entries_with_invalid_timestamp():
    entries = [
        {"filename": "bad.json", "timestamp": "not-a-date"},
        {"filename": "good.json", "timestamp": (datetime.now() - timedelta(days=1)).isoformat()},
    ]
    filters = {"date_filter": "week", "custom_start_date": None, "custom_end_date": None}

    result = AuditView._filter_by_date(entries, filters)
    filenames = {entry["filename"] for entry in result}

    assert "bad.json" in filenames
    assert "good.json" in filenames


def test_get_filtered_entries_applies_date_user_and_action_filters():
    filters = {"date_filter": "week", "user_filter": "alice", "action_filter": "corrected"}
    entries = [
        {"filename": "a.json", "user": "alice", "action": "corrected"},
        {"filename": "b.json", "user": "alice", "action": "reviewed"},
        {"filename": "c.json", "user": "bob", "action": "corrected"},
    ]

    with patch("utils.audit_view.read_audit_logs", return_value=entries), patch.object(
        AuditView, "_filter_by_date", return_value=entries
    ):
        result = AuditView._get_filtered_entries(filters)

    assert result == [{"filename": "a.json", "user": "alice", "action": "corrected"}]


def test_get_filtered_entries_returns_empty_on_exception():
    filters = {"date_filter": "all", "user_filter": "All", "action_filter": "All"}
    with patch("utils.audit_view.read_audit_logs", side_effect=RuntimeError("boom")):
        assert AuditView._get_filtered_entries(filters) == []


def test_export_audit_data_csv_flattens_entries():
    entries = [
        {
            "filename": "a.json",
            "timestamp": "2026-01-01T10:00:00",
            "user": "alice",
            "action": "corrected",
            "has_changes": True,
            "change_summary": {"total": 3, "modified": 1, "added": 1, "removed": 1, "type_changed": 0},
            "submission_method": "ui",
        },
        {
            "filename": "b.json",
            "timestamp": "2026-01-02T10:00:00",
            "user": "bob",
            "action": "reviewed",
            "has_changes": False,
            "change_summary": "bad-summary-type",
        },
    ]

    csv_data = AuditView.export_audit_data(entries, "csv")

    assert csv_data is not None
    assert "filename,timestamp,user,action" in csv_data
    assert "a.json" in csv_data
    assert "b.json" in csv_data


def test_export_audit_data_json_handles_non_serializable_values():
    entries = [{"filename": "a.json", "bad": {1, 2, 3}}]

    json_data = AuditView.export_audit_data(entries, "json")

    assert json_data is not None
    assert "a.json" in json_data
    assert "bad" in json_data


def test_export_audit_data_handles_empty_and_unsupported_format():
    assert AuditView.export_audit_data([], "csv") is None
    assert AuditView.export_audit_data([{"filename": "a.json"}], "xml") is None
