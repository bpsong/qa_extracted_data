"""
PDF viewer component for JSON QA webapp.
Handles PDF display with error handling and fallback options.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Any
import base64
import logging

# Configure logging
logger = logging.getLogger(__name__)


class PDFViewer:
    """Handles PDF preview functionality."""
    
    @staticmethod
    def render_pdf_preview(filename: str):
        """
        Render PDF preview for a given JSON filename.
        
        Args:
            filename: JSON filename (will look for corresponding PDF)
        """
        st.subheader("📄 PDF Document")
        
        if not filename:
            st.info("No file selected")
            return
        
        try:
            from .file_utils import get_pdf_path
            pdf_path = get_pdf_path(filename)
            
            if pdf_path and pdf_path.exists():
                PDFViewer._display_pdf(pdf_path)
            else:
                PDFViewer._display_pdf_not_found(filename)
                
        except Exception as e:
            st.error(f"Error loading PDF preview: {str(e)}")
            logger.error(f"Error in PDF preview for {filename}: {e}", exc_info=True)
    
    @staticmethod
    def _display_pdf(pdf_path: Path):
        """Display PDF using available methods."""
        try:
            # Method 1: Try streamlit-pdf-viewer if available
            if PDFViewer._try_streamlit_pdf_viewer(pdf_path):
                return
            
            # Method 2: Try iframe embed
            if PDFViewer._try_iframe_embed(pdf_path):
                return
            
            # Method 3: Fallback to file info and download
            PDFViewer._display_pdf_fallback(pdf_path)
            
        except Exception as e:
            logger.error(f"Error displaying PDF {pdf_path}: {e}")
            PDFViewer._display_pdf_fallback(pdf_path)
    
    @staticmethod
    def _try_streamlit_pdf_viewer(pdf_path: Path) -> bool:
        """Try to use streamlit-pdf-viewer package."""
        try:
            # Try to import and use streamlit-pdf-viewer
            from streamlit_pdf_viewer import pdf_viewer
            
            # Display PDF with viewer
            pdf_viewer(str(pdf_path), width=700, height=600)
            
            # Add PDF info below
            PDFViewer._display_pdf_info(pdf_path)
            return True
            
        except ImportError:
            logger.info("streamlit-pdf-viewer not available, trying alternative methods")
            return False
        except Exception as e:
            logger.error(f"Error with streamlit-pdf-viewer: {e}")
            return False
    
    @staticmethod
    def _try_iframe_embed(pdf_path: Path) -> bool:
        """Try to embed PDF using iframe."""
        try:
            # Read PDF file and encode as base64
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            # Create base64 encoded data URL
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"
            
            # Display using iframe
            iframe_html = f"""
            <iframe 
                src="{pdf_data_url}" 
                width="100%" 
                height="600px" 
                style="border: 1px solid #ccc; border-radius: 5px;">
                <p>Your browser does not support PDFs. 
                <a href="{pdf_data_url}">Download the PDF</a>.</p>
            </iframe>
            """
            
            st.markdown(iframe_html, unsafe_allow_html=True)

            # Inform users that browser-embedded previews may not support programmatic zoom.
            st.caption("Note: Browser-embedded PDF preview may not support programmatic zoom. Use the toolbar above or download the PDF to view with zoom controls.")
            
            # Add PDF info below
            PDFViewer._display_pdf_info(pdf_path)
            return True
            
        except Exception as e:
            logger.error(f"Error with iframe embed: {e}")
            return False
    
    @staticmethod
    def _display_pdf_fallback(pdf_path: Path):
        """Fallback PDF display with file info and download."""
        st.info("📄 PDF Preview Available")
        
        # Display PDF information
        PDFViewer._display_pdf_info(pdf_path)
        
        # Provide download button
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                help="Download the PDF to view it in your default PDF viewer"
            )
            
        except Exception as e:
            st.error(f"Error creating download button: {str(e)}")
        
        # Show first few lines of PDF content as text (if possible)
        PDFViewer._try_display_pdf_text_preview(pdf_path)
    
    @staticmethod
    def _display_pdf_info(pdf_path: Path):
        """Display PDF file information."""
        try:
            stat = pdf_path.stat()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("File Name", pdf_path.name)
                size_mb = stat.st_size / (1024 * 1024)
                if size_mb >= 1:
                    st.metric("File Size", f"{size_mb:.1f} MB")
                else:
                    st.metric("File Size", f"{stat.st_size / 1024:.1f} KB")
            
            with col2:
                from datetime import datetime
                modified_time = datetime.fromtimestamp(stat.st_mtime)
                st.metric("Modified", modified_time.strftime("%Y-%m-%d %H:%M"))
                st.metric("Path", f".../{pdf_path.parent.name}/{pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Error displaying PDF info: {e}")
    
    @staticmethod
    def _try_display_pdf_text_preview(pdf_path: Path):
        """Try to display a text preview of the PDF content."""
        try:
            # Try to extract text using PyPDF2 if available
            try:
                import PyPDF2
                
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    
                    if len(pdf_reader.pages) > 0:
                        # Extract text from first page
                        first_page = pdf_reader.pages[0]
                        text = first_page.extract_text()
                        
                        if text and text.strip():
                            with st.expander("📝 Text Preview (First Page)"):
                                # Show first 500 characters
                                preview_text = text[:500]
                                if len(text) > 500:
                                    preview_text += "..."
                                
                                st.text_area(
                                    "Extracted Text:",
                                    value=preview_text,
                                    height=150,
                                    disabled=True
                                )
                        else:
                            st.info("📄 PDF appears to be image-based (no extractable text)")
                
            except ImportError:
                logger.info("PyPDF2 not available for text extraction")
            except Exception as e:
                logger.error(f"Error extracting PDF text: {e}")
                
        except Exception as e:
            logger.error(f"Error in PDF text preview: {e}")
    
    @staticmethod
    def _display_pdf_not_found(filename: str):
        """Display message when PDF is not found."""
        expected_pdf = filename.replace('.json', '.pdf')
        
        st.warning("⚠️ Corresponding PDF file not found")
        
        with st.container():
            st.info(f"**Expected PDF:** `{expected_pdf}`")
            st.markdown("""
            **To add the PDF:**
            1. Place the PDF file in the `pdf_docs/` directory
            2. Ensure the filename matches the JSON file (e.g., `invoice_001.json` → `invoice_001.pdf`)
            3. Refresh the page to see the PDF preview
            """)
        
        # Show directory contents for debugging
        with st.expander("🔍 Debug: Available PDF files"):
            try:
                from pathlib import Path
                pdf_dir = Path("pdf_docs")
                
                if pdf_dir.exists():
                    pdf_files = list(pdf_dir.glob("*.pdf"))
                    
                    if pdf_files:
                        st.write("**Available PDF files:**")
                        for pdf_file in sorted(pdf_files):
                            st.write(f"• {pdf_file.name}")
                    else:
                        st.write("No PDF files found in pdf_docs/ directory")
                else:
                    st.write("pdf_docs/ directory does not exist")
                    
            except Exception as e:
                st.error(f"Error listing PDF files: {str(e)}")
    

    
    @staticmethod
    def get_pdf_metadata(pdf_path: Path) -> dict:
        """Extract PDF metadata if possible."""
        from typing import Optional
        # Explicitly type metadata to allow storing strings, ints or None.
        metadata: dict[str, Optional[Any]] = {
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None,
            'page_count': None
        }
        
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Get page count
                metadata['page_count'] = len(pdf_reader.pages)
                
                # Get document info
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    metadata['title'] = info.get('/Title')
                    metadata['author'] = info.get('/Author')
                    metadata['subject'] = info.get('/Subject')
                    metadata['creator'] = info.get('/Creator')
                    metadata['producer'] = info.get('/Producer')
                    metadata['creation_date'] = info.get('/CreationDate')
                    metadata['modification_date'] = info.get('/ModDate')
        
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
        
        return metadata
    
    @staticmethod
    def render_pdf_metadata(pdf_path: Path):
        """Render PDF metadata in an expander."""
        with st.expander("📋 PDF Metadata"):
            metadata = PDFViewer.get_pdf_metadata(pdf_path)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if metadata['title']:
                    st.write(f"**Title:** {metadata['title']}")
                if metadata['author']:
                    st.write(f"**Author:** {metadata['author']}")
                if metadata['subject']:
                    st.write(f"**Subject:** {metadata['subject']}")
                if metadata['page_count']:
                    st.write(f"**Pages:** {metadata['page_count']}")
            
            with col2:
                if metadata['creator']:
                    st.write(f"**Creator:** {metadata['creator']}")
                if metadata['producer']:
                    st.write(f"**Producer:** {metadata['producer']}")
                if metadata['creation_date']:
                    st.write(f"**Created:** {metadata['creation_date']}")
                if metadata['modification_date']:
                    st.write(f"**Modified:** {metadata['modification_date']}")
 

# Convenience functions
def render_pdf_preview(filename: str):
    """Render PDF preview for a filename."""
    PDFViewer.render_pdf_preview(filename)


def display_pdf_not_found(filename: str):
    """Display PDF not found message."""
    PDFViewer._display_pdf_not_found(filename)