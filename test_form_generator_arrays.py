import copy
import sys
import types
from datetime import date, datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


class _MockSessionState(dict):
    """Minimal session_state stand-in supporting attribute access."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _context_manager_mock(*args, **kwargs):
    ctx = MagicMock()
    ctx.__enter__.return_value = MagicMock()
    ctx.__exit__.return_value = False
    return ctx


if "streamlit" not in sys.modules:
    def _pass_through_cache(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    mock_streamlit = types.SimpleNamespace(
        session_state=_MockSessionState(),
        container=MagicMock(side_effect=_context_manager_mock),
        expander=MagicMock(side_effect=_context_manager_mock),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        button=MagicMock(return_value=False),
        selectbox=MagicMock(return_value="none"),
        form_submit_button=MagicMock(return_value=False),
        markdown=MagicMock(),
        caption=MagicMock(),
        info=MagicMock(),
        warning=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        rerun=MagicMock(),
        write=MagicMock(),
        data_editor=MagicMock(),
        date_input=MagicMock(return_value=datetime.now().date()),
        time_input=MagicMock(return_value=datetime.now().time()),
        column_config=types.SimpleNamespace(
            TextColumn=MagicMock(return_value=MagicMock()),
            NumberColumn=MagicMock(return_value=MagicMock()),
            CheckboxColumn=MagicMock(return_value=MagicMock()),
            DateColumn=MagicMock(return_value=MagicMock()),
            SelectboxColumn=MagicMock(return_value=MagicMock()),
        ),
        cache_data=_pass_through_cache,
        cache_resource=types.SimpleNamespace(clear=MagicMock()),
    )
    sys.modules["streamlit"] = mock_streamlit

from utils.edit_view import EditView
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager


@pytest.fixture
def session_state():
    """Provide an isolated Streamlit session_state for each test."""
    mock_state: Dict[str, Any] = {}
    patcher = patch("streamlit.session_state", mock_state)
    patcher.start()
    try:
        yield mock_state
    finally:
        patcher.stop()


def test_sync_array_to_session_updates_state_and_manager(session_state):
    form_data = {"other": "value"}

    with patch.object(SessionManager, "get_form_data", return_value=form_data), patch.object(
        SessionManager, "set_form_data"
    ) as set_form_data:
        FormGenerator._sync_array_to_session("serials", ["A", "B"])

    assert session_state["field_serials"] == ["A", "B"]
    assert session_state["scalar_array_serials_size"] == 2

    set_form_data.assert_called_once()
    updated_payload = set_form_data.call_args[0][0]
    assert updated_payload["serials"] == ["A", "B"]
    assert updated_payload["other"] == "value"


def test_sync_array_to_session_overwrites_existing_values(session_state):
    session_state["field_tags"] = ["old"]
    session_state["scalar_array_tags_size"] = 1
    form_data = {"tags": ["old"], "other": 1}

    with patch.object(SessionManager, "get_form_data", return_value=form_data), patch.object(
        SessionManager, "set_form_data"
    ) as set_form_data:
        FormGenerator._sync_array_to_session("tags", ["new1", "new2"])

    assert session_state["field_tags"] == ["new1", "new2"]
    assert session_state["scalar_array_tags_size"] == 2

    updated_payload = set_form_data.call_args[0][0]
    assert updated_payload["tags"] == ["new1", "new2"]
    assert updated_payload["other"] == 1


def test_collect_array_data_from_widgets_uses_scalar_item_keys(session_state):
    schema = {
        "fields": {
            "Tags": {
                "type": "array",
                "items": {"type": "string"},
            }
        }
    }
    session_state["scalar_array_Tags_size"] = 3
    session_state["scalar_array_Tags_item_0"] = "first"
    session_state["scalar_array_Tags_item_1"] = "second"
    session_state["scalar_array_Tags_item_2"] = "third"

    original_form_data = {"Tags": ["stale"], "Other": "keep"}

    with patch.object(FormGenerator, "_sync_array_to_session") as sync_mock:
        updated = FormGenerator._collect_array_data_from_widgets(schema, copy.deepcopy(original_form_data))

    assert updated["Tags"] == ["first", "second", "third"]
    assert updated["Other"] == "keep"
    sync_mock.assert_called_once_with("Tags", ["first", "second", "third"])


def test_collect_array_data_from_widgets_falls_back_to_field_value(session_state):
    schema = {
        "fields": {
            "Tags": {
                "type": "array",
                "items": {"type": "string"},
            }
        }
    }
    session_state["scalar_array_Tags_size"] = 2
    session_state["field_Tags"] = ["alpha", "beta"]

    original_form_data = {"Tags": ["stale"], "Other": 5}

    with patch.object(FormGenerator, "_sync_array_to_session") as sync_mock:
        updated = FormGenerator._collect_array_data_from_widgets(schema, copy.deepcopy(original_form_data))

    assert updated["Tags"] == ["alpha", "beta"]
    assert updated["Other"] == 5
    sync_mock.assert_called_once_with("Tags", ["alpha", "beta"])


def test_render_array_editor_delegates_to_scalar_editor(session_state):
    field_config = {
        "type": "array",
        "items": {"type": "string"},
    }

    with patch.object(
        FormGenerator, "_render_scalar_array_editor", return_value=["ok"]
    ) as scalar_editor, patch.object(FormGenerator, "_render_object_array_editor") as object_editor:
        result = FormGenerator._render_array_editor("tags", field_config, ["existing"])

    assert result == ["ok"]
    scalar_editor.assert_called_once()
    object_editor.assert_not_called()


def test_render_array_editor_delegates_to_object_editor(session_state):
    field_config = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
        },
    }

    with patch.object(
        FormGenerator, "_render_object_array_editor", return_value=[{"code": "A"}]
    ) as object_editor, patch.object(FormGenerator, "_render_scalar_array_editor") as scalar_editor:
        result = FormGenerator._render_array_editor("line_items", field_config, [{"code": "B"}])

    assert result == [{"code": "A"}]
    object_editor.assert_called_once()
    scalar_editor.assert_not_called()


def test_validate_scalar_array_enforces_constraints():
    items_config = {"type": "number", "min_value": 1, "max_value": 5}
    errors = FormGenerator._validate_scalar_array("numbers", [0, 3, 6], items_config)

    assert len(errors) == 2
    assert "numbers[0]" in errors[0]
    assert "numbers[2]" in errors[1]


def test_validate_object_array_enforces_required_fields():
    items_config = {
        "properties": {
            "name": {"type": "string", "required": True},
            "quantity": {"type": "integer", "required": True, "min_value": 1},
        }
    }

    data = [
        {"name": "", "quantity": 1},
        {"name": "Widget", "quantity": 0},
    ]

    errors = FormGenerator._validate_object_array("line_items", data, items_config)
    assert len(errors) >= 2
    combined = " ".join(errors)
    assert "line_items[0].name" in combined
    assert "line_items[1].quantity" in combined


def test_clean_object_array_normalizes_nan_values():
    import numpy as np
    import pandas as pd

    dirty = [
        {"name": "Widget", "quantity": np.int64(5), "price": np.float64(9.5), "notes": pd.NA},
        {"name": "Empty", "quantity": np.nan, "price": None},
    ]

    cleaned = FormGenerator._clean_object_array(dirty)

    assert cleaned[0]["quantity"] == 5
    assert cleaned[0]["price"] == pytest.approx(9.5)
    assert cleaned[0]["notes"] is None
    assert cleaned[1]["quantity"] is None


def test_edit_view_handle_reset_restores_array_state(session_state, tmp_path):
    schema = {
        "fields": {
            "Numbers": {
                "type": "array",
                "items": {"type": "string"},
            },
            "Line Items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"description": {"type": "string", "required": True}},
                },
            },
            "Submitted At": {"type": "date"},
        }
    }

    original_data = {
        "Numbers": ["one", "two"],
        "Line Items": [{"description": "Row"}],
        "Submitted At": datetime(2024, 1, 1).date().isoformat(),
    }

    # Populate session_state with stale values and editor artifacts
    session_state.update(
        {
            "field_Numbers": ["stale"],
            "scalar_array_Numbers_size": 1,
            "scalar_array_Numbers_item_0": "stale",
            "data_editor_Line Items": [{"description": "stale"}],
            "array_Numbers": ["legacy"],
            "json_array_Numbers": ["legacy"],
            "field_Submitted At": "bad",
        }
    )

    with patch("utils.edit_view.SessionManager.get_schema", return_value=schema), patch(
        "utils.edit_view.SessionManager.get_current_file", return_value=str(tmp_path / "doc.json")
    ), patch(
        "utils.edit_view.load_json_file", return_value=original_data
    ) as load_file, patch(
        "utils.edit_view.SessionManager.set_original_data"
    ) as set_original, patch(
        "utils.edit_view.SessionManager.set_form_data"
    ) as set_form_data, patch(
        "utils.edit_view.SessionManager.clear_validation_errors"
    ) as clear_errors, patch(
        "utils.edit_view.Notify.success"
    ) as notify_success, patch(
        "streamlit.rerun"
    ):
        EditView._handle_reset()

    load_file.assert_called_once()
    set_original.assert_called_once_with(original_data)
    set_form_data.assert_any_call(original_data.copy())
    clear_errors.assert_called_once()
    notify_success.assert_called_once()

    assert session_state["field_Numbers"] == ["one", "two"]
    assert session_state["scalar_array_Numbers_size"] == 2
    assert "scalar_array_Numbers_item_0" not in session_state
    assert "array_Numbers" not in session_state
    assert "json_array_Numbers" not in session_state
    assert session_state["data_editor_Line Items"] == original_data["Line Items"]
    assert isinstance(session_state["field_Submitted At"], date)
