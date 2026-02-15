from datetime import datetime, date, timedelta
from unittest.mock import patch

import utils.queue_filter_state as qfs
from utils.queue_filter_state import (
    QueueFilterState,
    FilterStateValidator,
    get_filter_state_from_session,
    save_filter_state_to_session,
    get_validated_filter_state,
    ensure_filter_state_compatibility,
)


class _SessionState:
    def __init__(self, data=None):
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name)

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def test_queue_filter_state_sanitizes_invalid_values():
    state = QueueFilterState(sort_by="bad", sort_order="sideways", date_preset="bad-date")

    assert state.sort_by == "created_at"
    assert state.sort_order in {"asc", "desc"}
    assert state.date_preset == "all"
    assert state.date_start is None
    assert state.date_end is None


def test_from_session_dict_converts_date_types_and_invalid_values():
    state = QueueFilterState.from_session_dict(
        {
            "sort_by": "filename",
            "sort_order": "asc",
            "date_preset": "custom",
            "date_start": date(2026, 1, 2),
            "date_end": datetime(2026, 1, 3, 8, 0, 0),
        }
    )
    assert state.date_start == datetime(2026, 1, 2, 0, 0, 0)
    assert state.date_end == datetime(2026, 1, 3, 8, 0, 0)

    invalid = QueueFilterState.from_session_dict({"date_start": object(), "date_end": object()})
    assert invalid.date_start is None
    assert invalid.date_end is None


def test_to_session_dict_and_display_summary_custom_range():
    state = QueueFilterState(
        sort_by="filename",
        sort_order="asc",
        date_preset="custom",
        date_start=datetime(2026, 1, 1),
        date_end=datetime(2026, 1, 5),
    )
    as_dict = state.to_session_dict()
    summary = state.get_display_summary()

    assert as_dict["date_start"].startswith("2026-01-01")
    assert as_dict["date_end"].startswith("2026-01-05")
    assert "Sorted by" in summary
    assert "Date: 2026-01-01 to 2026-01-05" in summary


def test_update_sort_field_and_date_filter_behaviors():
    state = QueueFilterState.create_default()
    assert state.update_sort_field("bad") is state

    updated_sort = state.update_sort_field("filename")
    assert updated_sort.sort_by == "filename"

    updated_date_invalid = state.update_date_filter("bad-preset")
    assert updated_date_invalid is state

    invalid_range = state.update_date_filter(
        "custom",
        start_date=datetime(2026, 1, 5),
        end_date=datetime(2026, 1, 1),
    )
    assert invalid_range.date_start is None
    assert invalid_range.date_end is None

    non_custom = state.update_date_filter(
        "week",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 2),
    )
    assert non_custom.date_start is None
    assert non_custom.date_end is None


def test_detect_session_state_format_variants():
    assert FilterStateValidator.detect_session_state_format({}) == "empty"
    assert FilterStateValidator.detect_session_state_format({"queue_filters": {}}) == "consolidated"
    assert FilterStateValidator.detect_session_state_format({"queue_sort_by": "filename"}) == "individual_keys"
    assert (
        FilterStateValidator.detect_session_state_format(
            {"queue_filters": {}, "queue_sort_by": "filename"}
        )
        == "mixed"
    )


def test_migrate_session_state_format_individual_and_mixed():
    individual = {
        "queue_sort_by": "filename",
        "queue_sort_order": "asc",
        "queue_date_preset": "week",
    }
    state = FilterStateValidator.migrate_session_state_format(individual)
    assert state.sort_by == "filename"
    assert state.sort_order == "asc"
    assert state.date_preset == "week"

    mixed = {
        "queue_filters": {"sort_by": "created_at", "sort_order": "desc", "file_type": "ignored"},
        "queue_sort_order": "asc",
    }
    mixed_state = FilterStateValidator.migrate_session_state_format(mixed)
    assert mixed_state.sort_order == "asc"


def test_validate_filter_settings_comprehensive_clears_non_custom_dates():
    validated = FilterStateValidator.validate_filter_settings_comprehensive(
        {
            "sort_by": "filename",
            "sort_order": "asc",
            "date_preset": "week",
            "date_start": datetime(2026, 1, 1).isoformat(),
            "date_end": datetime(2026, 1, 2).isoformat(),
            "file_type": "legacy",
        }
    )

    assert validated["sort_by"] == "filename"
    assert validated["date_preset"] == "week"
    assert validated["date_start"] is None
    assert validated["date_end"] is None


def test_validate_state_consistency_failure_paths():
    mutated = QueueFilterState.create_default()
    mutated.sort_by = "bad"
    assert not FilterStateValidator.validate_state_consistency(mutated)

    non_custom_with_dates = QueueFilterState(sort_by="filename", sort_order="asc", date_preset="week")
    non_custom_with_dates.date_start = datetime.now()
    non_custom_with_dates.date_end = datetime.now()
    assert not FilterStateValidator.validate_state_consistency(non_custom_with_dates)

    custom_bad_range = QueueFilterState(sort_by="filename", sort_order="asc", date_preset="custom")
    custom_bad_range.date_start = datetime.now()
    custom_bad_range.date_end = datetime.now() - timedelta(days=1)
    assert not FilterStateValidator.validate_state_consistency(custom_bad_range)


def test_session_wrappers_get_and_save_filter_state():
    session_state = _SessionState({"queue_filters": {"sort_by": "filename", "sort_order": "asc"}})

    with patch("streamlit.session_state", session_state):
        state = get_filter_state_from_session()
        assert state.sort_by == "filename"
        save_filter_state_to_session(state)
        assert "queue_filters" in session_state


def test_get_validated_filter_state_exception_fallback():
    session_state = _SessionState({})
    with patch("streamlit.session_state", session_state), patch.object(
        FilterStateValidator, "migrate_session_state_format", side_effect=RuntimeError("boom")
    ):
        state = get_validated_filter_state()

    assert isinstance(state, QueueFilterState)
    assert state.is_default_state()


def test_ensure_filter_state_compatibility_exception_resets_defaults():
    session_state = _SessionState({})
    with patch("streamlit.session_state", session_state), patch(
        "utils.queue_filter_state.get_validated_filter_state", side_effect=RuntimeError("boom")
    ):
        ensure_filter_state_compatibility()

    assert "queue_filters" in session_state._data
