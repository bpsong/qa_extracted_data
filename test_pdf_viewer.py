from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import utils.pdf_viewer as pdf_viewer


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
