from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

import utils.form_data_collector as form_data_collector


def test_collect_all_form_data_missing_versioned_keys_defaults(monkeypatch):
    schema = {
        "fields": {
            "tags": {"type": "array", "items": {"type": "string"}},
            "line_items": {
                "type": "array",
                "items": {"type": "object", "properties": {"name": {"type": "string"}}},
            },
            "metadata": {"type": "object"},
            "invoice_date": {"type": "date"},
            "processed_at": {"type": "datetime"},
            "title": {"type": "string"},
        }
    }
    monkeypatch.setattr(form_data_collector.st, "session_state", {"form_version": 7})

    result = form_data_collector.collect_all_form_data(schema)

    assert result == {
        "tags": [],
        "line_items": [],
        "metadata": {},
        "invoice_date": None,
        "processed_at": None,
        "title": None,
    }


@pytest.mark.parametrize("source", ["current_dataframe", "fallback_list"])
def test_collect_all_form_data_object_array_current_and_fallback(monkeypatch, source):
    schema = {
        "fields": {
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "qty": {"type": "integer"}},
                },
            }
        }
    }
    session_state = {"form_version": 0, "field_line_items_v0": []}

    if source == "current_dataframe":
        session_state["array_line_items_v0_current"] = pd.DataFrame([{"name": "widget"}])
    else:
        session_state["field_line_items_v0"] = [{"name": "widget"}]

    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)
    result = form_data_collector.collect_all_form_data(schema)

    assert result["line_items"] == [{"name": "widget", "qty": None}]


def test_collect_all_form_data_malformed_session_values(monkeypatch):
    schema = {
        "fields": {
            "tags": {"type": "array", "items": {"type": "string"}},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "qty": {"type": "integer"}},
                },
            },
            "metadata": {"type": "object"},
        }
    }
    session_state = {
        "form_version": 0,
        "field_tags_v0": "not-a-list",
        "field_line_items_v0": "not-a-list",
        "field_metadata_v0": "not-a-dict",
    }
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["tags"] == []
    assert result["line_items"] == []
    assert result["metadata"] == {}


def test_collect_all_form_data_object_array_current_not_dataframe(monkeypatch):
    schema = {
        "fields": {
            "line_items": {
                "type": "array",
                "items": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        }
    }
    session_state = {
        "form_version": 1,
        "field_line_items_v1": [],
        "array_line_items_v1_current": "not-a-dataframe",
    }
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["line_items"] == []


def test_collect_all_form_data_scalar_array_list_path(monkeypatch):
    schema = {"fields": {"tags": {"type": "array", "items": {"type": "string"}}}}
    session_state = {"form_version": 0, "field_tags_v0": ["a", "b", "c"]}
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["tags"] == ["a", "b", "c"]


def test_collect_all_form_data_object_dict_value_kept(monkeypatch):
    schema = {"fields": {"metadata": {"type": "object"}}}
    session_state = {"form_version": 0, "field_metadata_v0": {"source": "ocr"}}
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["metadata"] == {"source": "ocr"}


@pytest.mark.parametrize(
    ("field_type", "value"),
    [
        ("date", 123),
        ("datetime", 123),
    ],
)
def test_collect_all_form_data_date_datetime_invalid_values(monkeypatch, field_type, value):
    schema = {"fields": {"field_value": {"type": field_type}}}
    session_state = {"form_version": 0, "field_field_value_v0": value}
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["field_value"] is None


def test_collect_all_form_data_other_scalar_passthrough(monkeypatch):
    schema = {"fields": {"priority": {"type": "integer"}}}
    session_state = {"form_version": 0, "field_priority_v0": 5}
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["priority"] == 5


@pytest.mark.parametrize(
    ("field_type", "value", "expected"),
    [
        ("date", date(2026, 1, 2), "2026-01-02"),
        ("date", "2026-01-03", "2026-01-03"),
        ("datetime", datetime(2026, 1, 2, 3, 4, 5), "2026-01-02T03:04:05"),
        ("datetime", "2026-01-03T04:05:06", "2026-01-03T04:05:06"),
    ],
)
def test_collect_all_form_data_date_datetime_conversion(monkeypatch, field_type, value, expected):
    schema = {"fields": {"field_value": {"type": field_type}}}
    session_state = {"form_version": 0, "field_field_value_v0": value}
    monkeypatch.setattr(form_data_collector.st, "session_state", session_state)

    result = form_data_collector.collect_all_form_data(schema)

    assert result["field_value"] == expected


def test_clean_object_array_normalizes_nan_numpy_and_defaults():
    array = [
        {
            "qty": np.int64(5),
            "price": np.float64(1.25),
            "active": np.bool_(True),
            "description": np.nan,
        },
        "skip-me",
    ]
    properties = {
        "qty": {},
        "price": {},
        "active": {},
        "description": {},
        "sku": {},
    }

    cleaned = form_data_collector._clean_object_array(array, properties)

    assert cleaned == [
        {
            "qty": 5,
            "price": 1.25,
            "active": True,
            "description": None,
            "sku": None,
        }
    ]
    assert isinstance(cleaned[0]["qty"], int)
    assert isinstance(cleaned[0]["price"], float)
    assert isinstance(cleaned[0]["active"], bool)
