from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import utils.pdf_viewer as pdf_viewer


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def mock_st(monkeypatch):
    st = SimpleNamespace(
        subheader=MagicMock(),
        info=MagicMock(),
        warning=MagicMock(),
        error=MagicMock(),
    )
    monkeypatch.setattr(pdf_viewer, "st", st)
    return st


def test_render_pdf_preview_no_filename(mock_st):
    with patch.object(pdf_viewer.PDFViewer, "_display_pdf") as mock_display, patch.object(
        pdf_viewer.PDFViewer, "_display_pdf_not_found"
    ) as mock_not_found:
        pdf_viewer.PDFViewer.render_pdf_preview("")

    mock_st.subheader.assert_called_once()
    mock_st.info.assert_called_once_with("No file selected")
    mock_display.assert_not_called()
    mock_not_found.assert_not_called()


def test_render_pdf_preview_missing_pdf(mock_st):
    with patch("utils.file_utils.get_pdf_path", return_value=None), patch.object(
        pdf_viewer.PDFViewer, "_display_pdf_not_found"
    ) as mock_not_found, patch.object(pdf_viewer.PDFViewer, "_display_pdf") as mock_display:
        pdf_viewer.PDFViewer.render_pdf_preview("invoice.json")

    mock_not_found.assert_called_once_with("invoice.json")
    mock_display.assert_not_called()


def test_render_pdf_preview_found_pdf(mock_st, tmp_path):
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("utils.file_utils.get_pdf_path", return_value=pdf_path), patch.object(
        pdf_viewer.PDFViewer, "_display_pdf"
    ) as mock_display, patch.object(pdf_viewer.PDFViewer, "_display_pdf_not_found") as mock_not_found:
        pdf_viewer.PDFViewer.render_pdf_preview("invoice.json")

    mock_display.assert_called_once_with(pdf_path)
    mock_not_found.assert_not_called()


def test_render_pdf_preview_get_pdf_path_exception(mock_st):
    with patch("utils.file_utils.get_pdf_path", side_effect=RuntimeError("boom")), patch.object(
        pdf_viewer.PDFViewer, "_display_pdf"
    ) as mock_display, patch.object(pdf_viewer.PDFViewer, "_display_pdf_not_found") as mock_not_found:
        pdf_viewer.PDFViewer.render_pdf_preview("invoice.json")

    mock_display.assert_not_called()
    mock_not_found.assert_not_called()
    mock_st.error.assert_called_once()
    assert "Error loading PDF preview" in mock_st.error.call_args[0][0]


def test_display_pdf_stops_on_streamlit_pdf_viewer_success():
    with patch.object(
        pdf_viewer.PDFViewer, "_try_streamlit_pdf_viewer", return_value=True
    ) as mock_try_streamlit, patch.object(
        pdf_viewer.PDFViewer, "_try_iframe_embed"
    ) as mock_try_iframe, patch.object(
        pdf_viewer.PDFViewer, "_display_pdf_fallback"
    ) as mock_fallback:
        pdf_viewer.PDFViewer._display_pdf(Path("doc.pdf"))

    mock_try_streamlit.assert_called_once_with(Path("doc.pdf"))
    mock_try_iframe.assert_not_called()
    mock_fallback.assert_not_called()


def test_display_pdf_importerror_in_streamlit_pdf_viewer_falls_back_to_iframe():
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "streamlit_pdf_viewer":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import), patch.object(
        pdf_viewer.PDFViewer, "_try_iframe_embed", return_value=True
    ) as mock_try_iframe, patch.object(pdf_viewer.PDFViewer, "_display_pdf_fallback") as mock_fallback:
        pdf_viewer.PDFViewer._display_pdf(Path("doc.pdf"))

    mock_try_iframe.assert_called_once_with(Path("doc.pdf"))
    mock_fallback.assert_not_called()


def test_display_pdf_iframe_failure_uses_fallback():
    with patch.object(
        pdf_viewer.PDFViewer, "_try_streamlit_pdf_viewer", return_value=False
    ) as mock_try_streamlit, patch.object(
        pdf_viewer.PDFViewer, "_try_iframe_embed", return_value=False
    ) as mock_try_iframe, patch.object(
        pdf_viewer.PDFViewer, "_display_pdf_fallback"
    ) as mock_fallback:
        pdf_viewer.PDFViewer._display_pdf(Path("doc.pdf"))

    mock_try_streamlit.assert_called_once_with(Path("doc.pdf"))
    mock_try_iframe.assert_called_once_with(Path("doc.pdf"))
    mock_fallback.assert_called_once_with(Path("doc.pdf"))


def test_get_pdf_metadata_with_pypdf2_available(tmp_path):
    class FakeReader:
        def __init__(self, _):
            self.pages = [object(), object(), object()]
            self.metadata = {
                "/Title": "Invoice",
                "/Author": "QA",
                "/Subject": "Testing",
                "/Creator": "Generator",
                "/Producer": "Tool",
                "/CreationDate": "D:20260101000000",
                "/ModDate": "D:20260102000000",
            }

    fake_module = SimpleNamespace(PdfReader=FakeReader)
    pdf_path = tmp_path / "meta.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch.dict("sys.modules", {"PyPDF2": fake_module}):
        metadata = pdf_viewer.PDFViewer.get_pdf_metadata(pdf_path)

    assert metadata["page_count"] == 3
    assert metadata["title"] == "Invoice"
    assert metadata["author"] == "QA"
    assert metadata["subject"] == "Testing"
    assert metadata["creator"] == "Generator"
    assert metadata["producer"] == "Tool"
    assert metadata["creation_date"] == "D:20260101000000"
    assert metadata["modification_date"] == "D:20260102000000"


def test_get_pdf_metadata_with_pypdf2_unavailable():
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "PyPDF2":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        metadata = pdf_viewer.PDFViewer.get_pdf_metadata(Path("missing.pdf"))

    assert metadata == {
        "title": None,
        "author": None,
        "subject": None,
        "creator": None,
        "producer": None,
        "creation_date": None,
        "modification_date": None,
        "page_count": None,
    }


def test_get_pdf_metadata_with_corrupt_pdf(tmp_path):
    class BrokenReader:
        def __init__(self, _):
            raise ValueError("bad pdf")

    fake_module = SimpleNamespace(PdfReader=BrokenReader)
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not-a-real-pdf")

    with patch.dict("sys.modules", {"PyPDF2": fake_module}):
        metadata = pdf_viewer.PDFViewer.get_pdf_metadata(pdf_path)

    assert metadata["page_count"] is None
    assert metadata["title"] is None


def test_display_pdf_exception_path_uses_fallback():
    with patch.object(
        pdf_viewer.PDFViewer, "_try_streamlit_pdf_viewer", side_effect=RuntimeError("boom")
    ), patch.object(pdf_viewer.PDFViewer, "_display_pdf_fallback") as mock_fallback:
        pdf_viewer.PDFViewer._display_pdf(Path("doc.pdf"))

    mock_fallback.assert_called_once_with(Path("doc.pdf"))


def test_try_streamlit_pdf_viewer_success_invokes_pdf_viewer_and_info():
    called = {}

    def fake_pdf_viewer(path, width, height):
        called["args"] = (path, width, height)

    fake_module = SimpleNamespace(pdf_viewer=fake_pdf_viewer)
    with patch.dict("sys.modules", {"streamlit_pdf_viewer": fake_module}), patch.object(
        pdf_viewer.PDFViewer, "_display_pdf_info"
    ) as mock_info:
        result = pdf_viewer.PDFViewer._try_streamlit_pdf_viewer(Path("doc.pdf"))

    assert result is True
    assert called["args"] == ("doc.pdf", 700, 600)
    mock_info.assert_called_once_with(Path("doc.pdf"))


def test_try_streamlit_pdf_viewer_runtime_failure_returns_false():
    def fake_pdf_viewer(*_args, **_kwargs):
        raise ValueError("render failed")

    fake_module = SimpleNamespace(pdf_viewer=fake_pdf_viewer)
    with patch.dict("sys.modules", {"streamlit_pdf_viewer": fake_module}):
        assert pdf_viewer.PDFViewer._try_streamlit_pdf_viewer(Path("doc.pdf")) is False


def test_try_iframe_embed_success(monkeypatch, tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    st = SimpleNamespace(markdown=MagicMock(), caption=MagicMock())
    monkeypatch.setattr(pdf_viewer, "st", st)

    with patch.object(pdf_viewer.PDFViewer, "_display_pdf_info") as mock_info:
        result = pdf_viewer.PDFViewer._try_iframe_embed(pdf_path)

    assert result is True
    st.markdown.assert_called_once()
    st.caption.assert_called_once()
    mock_info.assert_called_once_with(pdf_path)


def test_try_iframe_embed_failure_returns_false(monkeypatch):
    st = SimpleNamespace(markdown=MagicMock(), caption=MagicMock())
    monkeypatch.setattr(pdf_viewer, "st", st)

    with patch("builtins.open", side_effect=OSError("cannot read")):
        assert pdf_viewer.PDFViewer._try_iframe_embed(Path("doc.pdf")) is False


def test_display_pdf_fallback_download_failure_still_shows_text_preview(monkeypatch):
    st = SimpleNamespace(info=MagicMock(), error=MagicMock(), download_button=MagicMock())
    monkeypatch.setattr(pdf_viewer, "st", st)

    with patch.object(pdf_viewer.PDFViewer, "_display_pdf_info") as mock_info, patch.object(
        pdf_viewer.PDFViewer, "_try_display_pdf_text_preview"
    ) as mock_preview, patch("builtins.open", side_effect=OSError("cannot read")):
        pdf_viewer.PDFViewer._display_pdf_fallback(Path("doc.pdf"))

    st.info.assert_called_once()
    st.error.assert_called_once()
    mock_info.assert_called_once_with(Path("doc.pdf"))
    mock_preview.assert_called_once_with(Path("doc.pdf"))


def test_try_display_pdf_text_preview_image_based_pdf(monkeypatch, tmp_path):
    class FakePage:
        def extract_text(self):
            return ""

    class FakeReader:
        def __init__(self, _):
            self.pages = [FakePage()]

    st = SimpleNamespace(
        expander=MagicMock(return_value=_DummyContext()),
        text_area=MagicMock(),
        info=MagicMock(),
    )
    monkeypatch.setattr(pdf_viewer, "st", st)

    pdf_path = tmp_path / "image.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    fake_module = SimpleNamespace(PdfReader=FakeReader)

    with patch.dict("sys.modules", {"PyPDF2": fake_module}):
        pdf_viewer.PDFViewer._try_display_pdf_text_preview(pdf_path)

    st.info.assert_called_once()
    st.text_area.assert_not_called()


def test_display_pdf_not_found_lists_available_files(monkeypatch, tmp_path):
    st = SimpleNamespace(
        warning=MagicMock(),
        info=MagicMock(),
        markdown=MagicMock(),
        container=MagicMock(return_value=_DummyContext()),
        expander=MagicMock(return_value=_DummyContext()),
        write=MagicMock(),
        error=MagicMock(),
    )
    monkeypatch.setattr(pdf_viewer, "st", st)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pdf_docs").mkdir()
    (tmp_path / "pdf_docs" / "a.pdf").write_bytes(b"x")
    (tmp_path / "pdf_docs" / "b.pdf").write_bytes(b"x")

    pdf_viewer.PDFViewer._display_pdf_not_found("invoice.json")

    assert st.warning.called
    assert st.markdown.called
    assert any("a.pdf" in str(call.args[0]) for call in st.write.call_args_list if call.args)
    assert any("b.pdf" in str(call.args[0]) for call in st.write.call_args_list if call.args)


def test_render_pdf_metadata_writes_present_fields(monkeypatch):
    st = SimpleNamespace(
        expander=MagicMock(return_value=_DummyContext()),
        columns=MagicMock(return_value=(_DummyContext(), _DummyContext())),
        write=MagicMock(),
    )
    monkeypatch.setattr(pdf_viewer, "st", st)

    metadata = {
        "title": "Doc",
        "author": None,
        "subject": "Subj",
        "creator": "Creator",
        "producer": None,
        "creation_date": "2026-01-01",
        "modification_date": None,
        "page_count": 2,
    }
    with patch.object(pdf_viewer.PDFViewer, "get_pdf_metadata", return_value=metadata):
        pdf_viewer.PDFViewer.render_pdf_metadata(Path("doc.pdf"))

    writes = [str(c.args[0]) for c in st.write.call_args_list if c.args]
    assert any("Title" in w for w in writes)
    assert any("Subject" in w for w in writes)
    assert any("Pages" in w for w in writes)
    assert any("Creator" in w for w in writes)
    assert any("Created" in w for w in writes)
    assert not any("Author" in w for w in writes)
    assert not any("Producer" in w for w in writes)


def test_convenience_render_pdf_preview_calls_classmethod():
    with patch.object(pdf_viewer.PDFViewer, "render_pdf_preview") as mock_render:
        pdf_viewer.render_pdf_preview("invoice.json")
    mock_render.assert_called_once_with("invoice.json")


def test_convenience_display_pdf_not_found_calls_classmethod():
    with patch.object(pdf_viewer.PDFViewer, "_display_pdf_not_found") as mock_display:
        pdf_viewer.display_pdf_not_found("invoice.json")
    mock_display.assert_called_once_with("invoice.json")
