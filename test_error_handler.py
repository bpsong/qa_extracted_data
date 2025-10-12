"""
Unit tests for error_handler module.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import json

# Import the module to test
from utils.error_handler import (
    ErrorHandler,
    ErrorType,
    SafeOperations,
    handle_error,
    with_error_handling
)


class TestErrorHandler:
    """Test class for error handler."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_get_user_friendly_message_file_system(self):
        """Test user-friendly messages for file system errors."""
        # FileNotFoundError
        error = FileNotFoundError("File not found")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.FILE_SYSTEM)
        assert "file could not be found" in message.lower()
        assert "📁" in message
        
        # PermissionError
        error = PermissionError("Permission denied")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.FILE_SYSTEM)
        assert "permission denied" in message.lower()
        assert "🔒" in message
        
        # Default file system error
        error = OSError("Generic OS error")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.FILE_SYSTEM)
        assert "file system error" in message.lower()
    
    def test_get_user_friendly_message_schema(self):
        """Test user-friendly messages for schema errors."""
        # JSON decode error
        error = json.JSONDecodeError("Invalid JSON", "doc", 0)
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.SCHEMA)
        assert "invalid json" in message.lower()
        assert "📋" in message
        
        # KeyError
        error = KeyError("missing_field")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.SCHEMA)
        assert "required schema field" in message.lower()
        
        # Default schema error
        error = ValueError("Schema validation failed")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.SCHEMA)
        assert "schema contains invalid values" in message.lower()
    
    def test_get_user_friendly_message_validation(self):
        """Test user-friendly messages for validation errors."""
        error = ValueError("Validation failed")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.VALIDATION)
        assert "validation failed" in message.lower()
        assert "✅" in message
    
    def test_get_user_friendly_message_concurrency(self):
        """Test user-friendly messages for concurrency errors."""
        error = Exception("Lock conflict")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.CONCURRENCY)
        assert "being edited by another user" in message.lower()
        assert "🔒" in message
    
    def test_get_user_friendly_message_pdf(self):
        """Test user-friendly messages for PDF errors."""
        error = FileNotFoundError("PDF not found")
        message = ErrorHandler._get_user_friendly_message(error, ErrorType.PDF)
        assert "pdf file not found" in message.lower()
        assert "📄" in message
    
    @patch('streamlit.error')
    @patch('streamlit.subheader')
    @patch('streamlit.write')
    def test_display_error_basic(self, mock_write, mock_subheader, mock_error):
        """Test basic error display."""
        error = ValueError("Test error")
        user_message = "Test user message"
        context = "test context"
        
        ErrorHandler._display_error(user_message, error, context)
        
        mock_error.assert_called_once_with(user_message)
    
    @patch('streamlit.error')
    @patch('streamlit.subheader')
    @patch('streamlit.write')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_display_error_with_recovery_options(self, mock_columns, mock_button, mock_write, mock_subheader, mock_error):
        """Test error display with recovery options."""
        error = ValueError("Test error")
        user_message = "Test user message"
        context = "test context"
        recovery_options = [
            {
                'title': 'Retry',
                'description': 'Try the operation again',
                'button_text': 'Retry',
                'action': lambda: None
            }
        ]
        
        # Mock columns to return mock objects
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_columns.return_value = [mock_col1, mock_col2]
        
        ErrorHandler._display_error(user_message, error, context, recovery_options)
        
        mock_error.assert_called_once_with(user_message)
        mock_subheader.assert_called_once()
    
    def test_log_error_analytics(self):
        """Test error analytics logging."""
        error = ValueError("Test error")
        context = "test context"
        error_type = ErrorType.VALIDATION
        
        ErrorHandler._log_error_analytics(error, context, error_type)
        
        # Check that log file was created
        log_file = Path("logs/error_analytics.jsonl")
        assert log_file.exists()
        
        # Check log entry content
        with open(log_file, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert log_entry['error_type'] == error_type
        assert log_entry['exception_type'] == 'ValueError'
        assert log_entry['context'] == context
        assert log_entry['message'] == 'Test error'
        assert 'timestamp' in log_entry
    
    def test_with_error_handling_success(self):
        """Test error handling wrapper with successful operation."""
        def successful_operation():
            return "success"
        
        result = ErrorHandler.with_error_handling(
            successful_operation,
            "test context",
            default_return="default"
        )
        
        assert result == "success"
    
    @patch('utils.error_handler.ErrorHandler.handle_error')
    def test_with_error_handling_failure(self, mock_handle_error):
        """Test error handling wrapper with failed operation."""
        def failing_operation():
            raise ValueError("Test error")
        
        result = ErrorHandler.with_error_handling(
            failing_operation,
            "test context",
            default_return="default"
        )
        
        assert result == "default"
        mock_handle_error.assert_called_once()
    
    def test_create_recovery_options_file_context(self):
        """Test recovery options creation for file context."""
        options = ErrorHandler.create_recovery_options("file operation")
        
        assert len(options) > 0
        
        # Check for file-specific options
        titles = [opt['title'] for opt in options]
        assert any('Refresh File List' in title for title in titles)
        assert any('Check File Permissions' in title for title in titles)
        
        # Check for general options
        assert any('Restart Session' in title for title in titles)
        assert any('Contact Support' in title for title in titles)
    
    def test_create_recovery_options_schema_context(self):
        """Test recovery options creation for schema context."""
        options = ErrorHandler.create_recovery_options("schema loading")
        
        titles = [opt['title'] for opt in options]
        assert any('Reload Schema' in title for title in titles)
        assert any('Use Default Schema' in title for title in titles)
    
    def test_create_recovery_options_validation_context(self):
        """Test recovery options creation for validation context."""
        options = ErrorHandler.create_recovery_options("validation error")
        
        titles = [opt['title'] for opt in options]
        assert any('Review Input Data' in title for title in titles)
        assert any('Reset Form' in title for title in titles)
    
    def test_create_recovery_options_pdf_context(self):
        """Test recovery options creation for PDF context."""
        options = ErrorHandler.create_recovery_options("pdf processing")
        
        titles = [opt['title'] for opt in options]
        assert any('Check PDF Location' in title for title in titles)
        assert any('Continue Without PDF' in title for title in titles)
    
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.warning')
    @patch('streamlit.error')
    def test_check_file_system(self, mock_error, mock_warning, mock_success, mock_info):
        """Test file system check functionality."""
        # Create some test directories
        Path("json_docs").mkdir()
        Path("corrected").mkdir()
        
        ErrorHandler._check_file_system()
        
        # Should have called info to start check
        mock_info.assert_called()
        
        # Should have called success for existing directories
        assert mock_success.call_count > 0
    
    @patch('streamlit.info')
    @patch('streamlit.success')
    def test_use_default_schema(self, mock_success, mock_info):
        """Test default schema usage."""
        ErrorHandler._use_default_schema()
        
        mock_info.assert_called_once()
        mock_success.assert_called_once()
    
    @patch('utils.error_handler.SessionManager')
    @patch('streamlit.success')
    @patch('streamlit.warning')
    @patch('streamlit.rerun')
    def test_reset_form(self, mock_rerun, mock_warning, mock_success, mock_session_manager):
        """Test form reset functionality."""
        # Test with original data available
        mock_session_manager.get_original_data.return_value = {"name": "John"}
        
        ErrorHandler._reset_form()
        
        mock_session_manager.set_form_data.assert_called_once()
        mock_success.assert_called_once()
        mock_rerun.assert_called_once()
        
        # Test with no original data
        mock_session_manager.reset_mock()
        mock_session_manager.get_original_data.return_value = None
        
        ErrorHandler._reset_form()
        
        mock_warning.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.warning')
    @patch('streamlit.error')
    def test_check_pdf_files(self, mock_error, mock_warning, mock_success, mock_info):
        """Test PDF files check functionality."""
        # Test with no PDF directory
        ErrorHandler._check_pdf_files()
        mock_error.assert_called_once()
        
        # Test with PDF directory but no files
        mock_error.reset_mock()
        Path("pdf_docs").mkdir()
        
        ErrorHandler._check_pdf_files()
        mock_warning.assert_called_once()
        
        # Test with PDF files
        mock_warning.reset_mock()
        (Path("pdf_docs") / "test.pdf").write_text("fake pdf")
        
        ErrorHandler._check_pdf_files()
        mock_success.assert_called_once()
    
    @patch('utils.error_handler.SessionManager')
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_restart_session(self, mock_rerun, mock_success, mock_session_manager):
        """Test session restart functionality."""
        ErrorHandler._restart_session()
        
        mock_session_manager.reset_session.assert_called_once()
        mock_success.assert_called_once()
        mock_rerun.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.markdown')
    def test_show_support_info(self, mock_markdown, mock_info):
        """Test support information display."""
        ErrorHandler._show_support_info()
        
        mock_info.assert_called_once()
        mock_markdown.assert_called_once()


class TestSafeOperations:
    """Test class for safe operations."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_safe_file_read_success(self):
        """Test successful safe file read."""
        test_file = Path("test.txt")
        test_content = "test content"
        test_file.write_text(test_content)
        
        result = SafeOperations.safe_file_read(str(test_file))
        assert result == test_content
    
    @patch('utils.error_handler.ErrorHandler.with_error_handling')
    def test_safe_file_read_failure(self, mock_with_error_handling):
        """Test safe file read with failure."""
        mock_with_error_handling.return_value = "default"
        
        result = SafeOperations.safe_file_read("nonexistent.txt", default="default")
        
        assert result == "default"
        mock_with_error_handling.assert_called_once()
    
    def test_safe_json_load_success(self):
        """Test successful safe JSON load."""
        test_file = Path("test.json")
        test_data = {"key": "value"}
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        result = SafeOperations.safe_json_load(str(test_file))
        assert result == test_data
    
    @patch('utils.error_handler.ErrorHandler.with_error_handling')
    def test_safe_json_load_failure(self, mock_with_error_handling):
        """Test safe JSON load with failure."""
        mock_with_error_handling.return_value = {}
        
        result = SafeOperations.safe_json_load("nonexistent.json")
        
        assert result == {}
        mock_with_error_handling.assert_called_once()
    
    @patch('utils.error_handler.ErrorHandler.with_error_handling')
    @patch('utils.schema_loader.load_schema')
    def test_safe_schema_load(self, mock_load_schema, mock_with_error_handling):
        """Test safe schema load."""
        mock_with_error_handling.return_value = None
        
        result = SafeOperations.safe_schema_load("test_schema.yaml")
        
        assert result is None
        mock_with_error_handling.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('utils.error_handler.ErrorHandler.handle_error')
    def test_handle_error_convenience(self, mock_handle_error):
        """Test handle_error convenience function."""
        error = ValueError("test")
        context = "test context"
        
        handle_error(error, context)
        
        mock_handle_error.assert_called_once_with(error, context, ErrorType.SYSTEM)
    
    @patch('utils.error_handler.ErrorHandler.with_error_handling')
    def test_with_error_handling_convenience(self, mock_with_error_handling):
        """Test with_error_handling convenience function."""
        func = lambda: "result"
        context = "test context"
        
        with_error_handling(func, context)
        
        mock_with_error_handling.assert_called_once_with(func, context)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])

# Import os for the test setup
import os