from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import utils.queue_view as queue_view
from utils.queue_view import QueueView


class _SessionState:
    def __init__(self, data=None):
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name)

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def _mock_st(session_state=None):
    return SimpleNamespace(
        session_state=_SessionState(session_state),
        error=MagicMock(),
        success=MagicMock(),
        rerun=MagicMock(),
        cache_data=SimpleNamespace(clear=MagicMock()),
    )


def test_get_filter_settings_validates_and_applies_defaults(monkeypatch):
    st = _mock_st(
        {
            "queue_filters": {
                "sort_by": "not-valid",
                "sort_order": "sideways",
                "date_preset": "not-valid",
                "custom_start": datetime(2026, 1, 1),
                "custom_end": datetime(2026, 1, 2),
            }
        }
    )
    monkeypatch.setattr(queue_view, "st", st)

    settings = QueueView._get_filter_settings()

    assert settings["sort_by"] == "created_at"
    assert settings["sort_order"] == "desc"
    assert settings["date_preset"] == "all"


def test_get_filtered_files_uses_validated_state_pipeline():
    files = [{"filename": "a.json"}]
    processed = [{"filename": "processed.json"}]
    state = SimpleNamespace(
        sort_by="filename",
        sort_order="asc",
        date_preset="all",
        date_start=None,
        date_end=None,
    )

    with patch("utils.queue_view.list_unverified_files", return_value=files), patch(
        "utils.queue_filter_state.get_validated_filter_state", return_value=state
    ), patch.object(QueueView, "_apply_filter_pipeline", return_value=processed) as mock_pipeline:
        result = QueueView._get_filtered_files()

    assert result == processed
    mock_pipeline.assert_called_once()


def test_get_filtered_files_falls_back_when_enhanced_pipeline_errors():
    with patch("utils.queue_view.list_unverified_files", side_effect=RuntimeError("boom")), patch.object(
        QueueView, "_get_filtered_files_fallback", return_value=[{"filename": "fallback.json"}]
    ) as mock_fallback:
        result = QueueView._get_filtered_files()

    assert result == [{"filename": "fallback.json"}]
    mock_fallback.assert_called_once()


def test_get_filtered_files_fallback_returns_empty_on_error():
    with patch("utils.queue_view.list_unverified_files", side_effect=RuntimeError("boom")):
        assert QueueView._get_filtered_files_fallback() == []


def test_get_file_type_purchase_order_and_default_detection():
    assert QueueView._get_file_type("purchase_order_123.json") == "Purchase Order"
    assert QueueView._get_file_type("po_12345.json") == "Purchase Order"
    assert QueueView._get_file_type("random_document.json") == "Document"


def test_get_type_color_returns_default_for_unknown_type():
    assert QueueView._get_type_color("UnknownType") == "#f5f5f5"


def test_get_file_type_counts_includes_all_bucket():
    files = [
        {"filename": "invoice_a.json"},
        {"filename": "receipt_a.json"},
        {"filename": "other.json"},
    ]
    counts = QueueView.get_file_type_counts(files)

    assert counts["all"] == 3
    assert counts["Invoice"] == 1
    assert counts["Receipt"] == 1
    assert counts["Document"] == 1


def test_force_release_file_success_path(monkeypatch):
    st = _mock_st({})
    monkeypatch.setattr(queue_view, "st", st)

    with patch("utils.file_utils.release_file", return_value=True), patch.object(
        queue_view.SessionManager, "get_lock_timeout", return_value=5
    ), patch.object(queue_view, "cleanup_stale_locks") as mock_cleanup:
        QueueView._force_release_file("doc.json")

    st.success.assert_called_once()
    st.cache_data.clear.assert_called_once()
    mock_cleanup.assert_called_once_with(5)
    st.rerun.assert_called_once()


def test_force_release_file_failure_path(monkeypatch):
    st = _mock_st({})
    monkeypatch.setattr(queue_view, "st", st)

    with patch("utils.file_utils.release_file", return_value=False):
        QueueView._force_release_file("doc.json")

    st.error.assert_called_once()


def test_resume_file_sets_session_and_reruns(monkeypatch):
    st = _mock_st({})
    monkeypatch.setattr(queue_view, "st", st)

    with patch.object(queue_view.SessionManager, "set_current_file") as mock_file, patch.object(
        queue_view.SessionManager, "set_current_page"
    ) as mock_page:
        QueueView._resume_file("doc.json")

    mock_file.assert_called_once_with("doc.json")
    mock_page.assert_called_once_with("edit")
    st.success.assert_called_once()
    st.rerun.assert_called_once()
