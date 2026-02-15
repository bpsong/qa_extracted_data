from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import utils.edit_view as edit_view


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _SessionState:
    def __init__(self, initial=None):
        super().__setattr__("_data", dict(initial or {}))

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def _mock_st(session_state=None):
    if session_state is None:
        session_state = {}

    def _columns(spec, **_kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            count = len(spec)
        return tuple(_DummyContext() for _ in range(count))

    return SimpleNamespace(
        session_state=_SessionState(session_state),
        header=MagicMock(),
        divider=MagicMock(),
        subheader=MagicMock(),
        columns=MagicMock(side_effect=_columns),
        button=MagicMock(return_value=False),
        warning=MagicMock(),
        success=MagicMock(),
        markdown=MagicMock(),
        metric=MagicMock(),
        rerun=MagicMock(),
        expander=MagicMock(return_value=_DummyContext()),
        error=MagicMock(),
    )


def test_render_routes_to_no_file_selected(monkeypatch):
    st = _mock_st()
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_current_file", return_value=None), patch.object(
        edit_view.EditView, "_render_no_file_selected"
    ) as mock_no_file:
        edit_view.EditView.render()

    mock_no_file.assert_called_once()


def test_render_stops_when_initialization_fails(monkeypatch):
    st = _mock_st()
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_current_file", return_value="doc.json"), patch.object(
        edit_view.EditView, "_initialize_edit_data", return_value=False
    ), patch.object(edit_view.EditView, "_render_side_by_side_layout") as mock_layout:
        edit_view.EditView.render()

    mock_layout.assert_not_called()


def test_render_pdf_column_handles_none_current_file(monkeypatch):
    st = _mock_st()
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_current_file", return_value=None), patch.object(
        edit_view.PDFViewer, "render_pdf_preview"
    ) as mock_render:
        edit_view.EditView._render_pdf_column()

    mock_render.assert_called_once_with("")


def test_render_pdf_column_uses_selected_file(monkeypatch):
    st = _mock_st()
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_current_file", return_value="invoice.json"), patch.object(
        edit_view.PDFViewer, "render_pdf_preview"
    ) as mock_render:
        edit_view.EditView._render_pdf_column()

    mock_render.assert_called_once_with("invoice.json")


def test_render_form_column_warns_once_when_schema_missing(monkeypatch):
    st = _mock_st(session_state={})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_schema", return_value=None), patch(
        "utils.edit_view.Notify.warn"
    ) as mock_warn:
        edit_view.EditView._render_form_column()
        edit_view.EditView._render_form_column()

    assert st.session_state["edit_view_schema_required_warned"] is True
    mock_warn.assert_called_once()


def test_render_form_column_updates_session_form_data(monkeypatch):
    st = _mock_st(session_state={})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_schema", return_value={"fields": {"a": {"type": "string"}}}), patch.object(
        edit_view.SessionManager, "get_form_data", return_value={"a": "old"}
    ), patch.object(
        edit_view.FormGenerator, "render_dynamic_form", return_value={"a": "new"}
    ) as mock_form, patch.object(edit_view.SessionManager, "set_form_data") as mock_set:
        edit_view.EditView._render_form_column()

    mock_form.assert_called_once()
    mock_set.assert_called_once_with({"a": "new"})


def test_render_diff_section_no_data_shows_info(monkeypatch):
    st = _mock_st(session_state={})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "get_current_file", return_value="doc.json"), patch.object(
        edit_view.SessionManager, "get_schema", return_value=None
    ), patch.object(edit_view, "load_json_file", return_value=None), patch.object(
        edit_view.SessionManager, "get_form_data", return_value={"a": 1}
    ), patch("utils.edit_view.Notify.info") as mock_info:
        edit_view.EditView._render_diff_section()

    mock_info.assert_called_once()


def test_render_diff_section_with_changes_sets_current_diff(monkeypatch):
    st = _mock_st(session_state={})
    st.columns = MagicMock(return_value=(_DummyContext(), _DummyContext(), _DummyContext(), _DummyContext()))
    monkeypatch.setattr(edit_view, "st", st)

    original = {"a": 1}
    current = {"a": 2}
    diff = {"values_changed": {"root['a']": {"old_value": 1, "new_value": 2}}}

    with patch.object(edit_view.SessionManager, "get_current_file", return_value="doc.json"), patch.object(
        edit_view.SessionManager, "get_schema", return_value={"fields": {"a": {"type": "integer"}}}
    ), patch.object(edit_view, "load_json_file", return_value=original), patch(
        "utils.form_data_collector.collect_all_form_data", return_value=current
    ), patch.object(edit_view, "calculate_diff", return_value=diff), patch.object(
        edit_view, "has_changes", return_value=True
    ), patch(
        "utils.diff_utils.get_change_summary",
        return_value={"total": 1, "modified": 1, "added": 0, "removed": 0},
    ), patch.object(
        edit_view, "format_diff_for_display", return_value="formatted diff"
    ):
        edit_view.EditView._render_diff_section()

    assert st.session_state["current_diff"] == diff
    st.markdown.assert_called_once_with("formatted diff")


def test_render_action_buttons_status_branches(monkeypatch):
    st = _mock_st(session_state={})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.EditView, "_handle_reset") as mock_reset, patch.object(
        edit_view.SessionManager, "get_validation_errors", return_value=["err"]
    ), patch.object(edit_view.SessionManager, "has_unsaved_changes", return_value=False), patch(
        "utils.edit_view.Notify.warn"
    ) as mock_warn:
        st.button.side_effect = [True]
        edit_view.EditView._render_action_buttons()

    mock_reset.assert_called_once()
    mock_warn.assert_called_once()


def test_render_action_buttons_unsaved_and_clean_states(monkeypatch):
    st = _mock_st(session_state={})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.EditView, "_handle_reset"), patch.object(
        edit_view.SessionManager, "get_validation_errors", return_value=[]
    ), patch.object(
        edit_view.SessionManager, "has_unsaved_changes", side_effect=[True, False]
    ), patch(
        "utils.edit_view.Notify.success"
    ) as mock_success:
        st.button.side_effect = [False, False]
        edit_view.EditView._render_action_buttons()
        edit_view.EditView._render_action_buttons()

    st.warning.assert_called_once()
    mock_success.assert_called_once()


def test_render_cancel_confirmation_without_unsaved_changes_calls_callback(monkeypatch):
    st = _mock_st(session_state={"show_cancel_confirm": True})
    monkeypatch.setattr(edit_view, "st", st)
    callback = MagicMock()

    with patch.object(edit_view.SessionManager, "has_unsaved_changes", return_value=False):
        edit_view.EditView._render_cancel_confirmation(cancel_callback=callback)

    callback.assert_called_once()
    assert st.session_state["show_cancel_confirm"] is False


def test_handle_reset_increments_form_version_and_reruns(monkeypatch):
    st = _mock_st(session_state={"form_version": 2})
    monkeypatch.setattr(edit_view, "st", st)

    with patch.object(edit_view.SessionManager, "clear_validation_errors") as mock_clear, patch(
        "utils.edit_view.Notify.success"
    ) as mock_success:
        edit_view.EditView._handle_reset()

    assert st.session_state["form_version"] == 3
    mock_clear.assert_called_once()
    mock_success.assert_called_once()
    st.rerun.assert_called_once()
