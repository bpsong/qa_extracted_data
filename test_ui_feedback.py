"""
Unit tests for ui_feedback module.
"""

import time
from unittest.mock import patch, MagicMock, call
import pytest

# Import the module to test
from utils.ui_feedback import (
    LoadingIndicator,
    UserFeedback,
    InteractiveElements,
    StatusIndicators,
    AnimatedElements,
    show_loading,
    show_progress,
    show_success,
    show_error,
    show_warning,
    show_info
)


class TestLoadingIndicator:
    """Test class for loading indicators."""
    
    @patch('streamlit.spinner')
    def test_spinner_context_manager(self, mock_spinner):
        """Test spinner context manager."""
        mock_context = MagicMock()
        mock_spinner.return_value = mock_context
        
        with LoadingIndicator.spinner("Loading..."):
            pass
        
        mock_spinner.assert_called_once_with("Loading...")
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
    
    @patch('streamlit.progress')
    @patch('streamlit.empty')
    def test_progress_bar_context_manager(self, mock_empty, mock_progress):
        """Test progress bar context manager."""
        mock_progress_bar = MagicMock()
        mock_status_text = MagicMock()
        mock_progress.return_value = mock_progress_bar
        mock_empty.return_value = mock_status_text
        
        with LoadingIndicator.progress_bar(5, "Processing...") as progress:
            progress.update(1, "Step 1")
            progress.increment("Step 2")
            progress.complete("Done!")
        
        mock_progress.assert_called_once_with(0)
        mock_progress_bar.progress.assert_called()
        mock_status_text.text.assert_called()
    
    @patch('streamlit.empty')
    @patch('time.sleep')
    def test_show_loading_message(self, mock_sleep, mock_empty):
        """Test loading message display."""
        mock_placeholder = MagicMock()
        mock_empty.return_value = mock_placeholder
        
        LoadingIndicator.show_loading_message("Loading...", duration=1.0)
        
        mock_placeholder.info.assert_called_once_with("⏳ Loading...")
        mock_sleep.assert_called_once_with(1.0)
        mock_placeholder.empty.assert_called_once()


class TestUserFeedback:
    """Test class for user feedback."""
    
    @patch('streamlit.success')
    @patch('streamlit.balloons')
    def test_success_with_celebration(self, mock_balloons, mock_success):
        """Test success message with celebration."""
        UserFeedback.success("Operation completed!", celebration=True)
        
        mock_success.assert_called_once_with("✅ Operation completed!")
        mock_balloons.assert_called_once()
    
    @patch('streamlit.success')
    @patch('time.sleep')
    def test_success_with_duration(self, mock_sleep, mock_success):
        """Test success message with duration."""
        UserFeedback.success("Success!", duration=2.0)
        
        mock_success.assert_called_once_with("✅ Success!")
        mock_sleep.assert_called_once_with(2.0)
    
    @patch('streamlit.info')
    def test_info_message(self, mock_info):
        """Test info message."""
        UserFeedback.info("Information message")
        
        mock_info.assert_called_once_with("ℹ️ Information message")
    
    @patch('streamlit.warning')
    def test_warning_message(self, mock_warning):
        """Test warning message."""
        UserFeedback.warning("Warning message")
        
        mock_warning.assert_called_once_with("⚠️ Warning message")
    
    @patch('streamlit.error')
    def test_error_message(self, mock_error):
        """Test error message."""
        UserFeedback.error("Error message")
        
        mock_error.assert_called_once_with("❌ Error message")
    
    @patch('streamlit.empty')
    @patch('time.sleep')
    def test_toast_notification(self, mock_sleep, mock_empty):
        """Test toast notification."""
        mock_placeholder = MagicMock()
        mock_empty.return_value = mock_placeholder
        
        UserFeedback.toast("Toast message", type="success")
        
        mock_placeholder.success.assert_called_once_with("✅ Toast message")
        mock_sleep.assert_called_once_with(3)
        mock_placeholder.empty.assert_called_once()
    
    @patch('streamlit.subheader')
    @patch('streamlit.write')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_confirmation_dialog(self, mock_columns, mock_button, mock_write, mock_subheader):
        """Test confirmation dialog."""
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_columns.return_value = [mock_col1, mock_col2]
        mock_button.side_effect = [True, False]  # Confirmed
        
        result = UserFeedback.confirmation_dialog(
            "Confirm Action",
            "Are you sure?",
            confirm_text="Yes",
            cancel_text="No"
        )
        
        assert result == True
        mock_subheader.assert_called_once_with("Confirm Action")
        mock_write.assert_called_once_with("Are you sure?")
    
    @patch('streamlit.error')
    @patch('streamlit.warning')
    @patch('streamlit.success')
    def test_show_validation_results(self, mock_success, mock_warning, mock_error):
        """Test validation results display."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        
        UserFeedback.show_validation_results(errors, warnings)
        
        mock_error.assert_called()  # Called multiple times
        mock_warning.assert_called()  # Called multiple times
        
        # Test with no errors or warnings
        mock_success.reset_mock()
        UserFeedback.show_validation_results([], [])
        
        mock_success.assert_called_once()
    
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    @patch('streamlit.info')
    @patch('streamlit.progress')
    def test_show_operation_status(self, mock_progress, mock_info, mock_warning, mock_error, mock_success):
        """Test operation status display."""
        # Test success status
        UserFeedback.show_operation_status("Upload", "success", "File uploaded", 1.0)
        mock_success.assert_called_once()
        mock_progress.assert_called_once_with(1.0)
        
        # Test error status
        UserFeedback.show_operation_status("Upload", "error", "Upload failed")
        mock_error.assert_called_once()
        
        # Test warning status
        UserFeedback.show_operation_status("Upload", "warning", "Partial upload")
        mock_warning.assert_called_once()
        
        # Test info status
        UserFeedback.show_operation_status("Upload", "pending", "Waiting")
        mock_info.assert_called_once()


class TestInteractiveElements:
    """Test class for interactive elements."""
    
    @patch('streamlit.button')
    @patch('utils.ui_feedback.UserFeedback.success')
    @patch('utils.ui_feedback.LoadingIndicator.spinner')
    def test_action_button_success(self, mock_spinner, mock_success, mock_button):
        """Test successful action button."""
        mock_button.return_value = True
        mock_action = MagicMock(return_value="result")
        mock_spinner.return_value.__enter__ = MagicMock()
        mock_spinner.return_value.__exit__ = MagicMock()
        
        result = InteractiveElements.action_button(
            "Test Action",
            mock_action,
            success_message="Action completed",
            loading_message="Processing..."
        )
        
        assert result == True
        mock_button.assert_called_once()
        mock_action.assert_called_once()
        mock_success.assert_called_once_with("Action completed")
    
    @patch('streamlit.button')
    @patch('utils.ui_feedback.UserFeedback.confirmation_dialog')
    @patch('utils.ui_feedback.UserFeedback.info')
    def test_action_button_with_confirmation_cancelled(self, mock_info, mock_confirmation, mock_button):
        """Test action button with confirmation cancelled."""
        mock_button.return_value = True
        mock_confirmation.return_value = False  # User cancelled
        
        result = InteractiveElements.action_button(
            "Delete",
            lambda: None,
            confirmation_required=True,
            confirmation_message="Are you sure?"
        )
        
        assert result == False
        mock_confirmation.assert_called_once()
        mock_info.assert_called_once_with("Action cancelled")
    
    @patch('streamlit.file_uploader')
    @patch('utils.ui_feedback.UserFeedback.success')
    @patch('utils.ui_feedback.UserFeedback.error')
    def test_file_upload_with_feedback(self, mock_error, mock_success, mock_file_uploader):
        """Test file upload with feedback."""
        # Mock uploaded file
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        mock_file.getvalue.return_value = b"x" * (5 * 1024 * 1024)  # 5MB file
        mock_file_uploader.return_value = mock_file
        
        result = InteractiveElements.file_upload_with_feedback(
            "Upload File",
            ["pdf"],
            max_size_mb=10
        )
        
        assert result == mock_file
        mock_success.assert_called_once()
        
        # Test file too large
        mock_file.getvalue.return_value = b"x" * (15 * 1024 * 1024)  # 15MB file
        mock_success.reset_mock()
        
        result = InteractiveElements.file_upload_with_feedback(
            "Upload File",
            ["pdf"],
            max_size_mb=10
        )
        
        assert result is None
        mock_error.assert_called_once()
    
    @patch('streamlit.form')
    @patch('streamlit.text_input')
    @patch('streamlit.number_input')
    @patch('streamlit.selectbox')
    @patch('streamlit.checkbox')
    @patch('streamlit.form_submit_button')
    @patch('utils.ui_feedback.UserFeedback.show_validation_results')
    @patch('utils.ui_feedback.UserFeedback.success')
    def test_form_with_validation(self, mock_success, mock_validation, mock_submit, 
                                 mock_checkbox, mock_selectbox, mock_number, mock_text, mock_form):
        """Test form with validation."""
        # Mock form context
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        
        # Mock form inputs
        mock_text.return_value = "John Doe"
        mock_number.return_value = 30
        mock_selectbox.return_value = "Option 1"
        mock_checkbox.return_value = True
        mock_submit.return_value = True
        
        fields = {
            "name": {"type": "text", "label": "Name", "required": True},
            "age": {"type": "number", "label": "Age", "required": True},
            "option": {"type": "select", "label": "Option", "options": ["Option 1", "Option 2"]},
            "agree": {"type": "checkbox", "label": "Agree"}
        }
        
        result = InteractiveElements.form_with_validation("test_form", fields)
        
        assert result is not None
        assert result["name"] == "John Doe"
        assert result["age"] == 30
        mock_success.assert_called_once()


class TestStatusIndicators:
    """Test class for status indicators."""
    
    def test_status_badge(self):
        """Test status badge creation."""
        badge = StatusIndicators.status_badge("success", "Completed")
        
        assert "✅" in badge
        assert "Completed" in badge
        assert "#28a745" in badge  # Success color
        assert "span" in badge
    
    def test_progress_indicator(self):
        """Test progress indicator creation."""
        indicator = StatusIndicators.progress_indicator(3, 5, "Tasks")
        
        assert "3/5" in indicator
        assert "Tasks" in indicator
        assert "60%" in indicator
        assert "span" in indicator
    
    def test_health_indicator(self):
        """Test health indicator creation."""
        # Healthy status
        indicator = StatusIndicators.health_indicator("healthy", "All systems operational")
        assert "🟢" in indicator
        assert "Healthy" in indicator
        assert "All systems operational" in indicator
        
        # Warning status
        indicator = StatusIndicators.health_indicator("warning", "Minor issues")
        assert "🟡" in indicator
        assert "Warning" in indicator
        
        # Error status
        indicator = StatusIndicators.health_indicator("error", "System down")
        assert "🔴" in indicator
        assert "Error" in indicator
        
        # Unknown status
        indicator = StatusIndicators.health_indicator("unknown", "Status unclear")
        assert "⚪" in indicator
        assert "Unknown" in indicator


class TestAnimatedElements:
    """Test class for animated elements."""
    
    @patch('streamlit.empty')
    @patch('time.sleep')
    def test_typing_effect(self, mock_sleep, mock_empty):
        """Test typing effect animation."""
        mock_placeholder = MagicMock()
        mock_empty.return_value = mock_placeholder
        
        AnimatedElements.typing_effect("Hello", delay=0.01)
        
        # Should call text multiple times (once for each character + cursor)
        assert mock_placeholder.text.call_count > 1
        mock_sleep.assert_called()
    
    @patch('streamlit.empty')
    @patch('time.sleep')
    def test_countdown_timer(self, mock_sleep, mock_empty):
        """Test countdown timer."""
        mock_placeholder = MagicMock()
        mock_empty.return_value = mock_placeholder
        
        AnimatedElements.countdown_timer(2, "Countdown")
        
        # Should show countdown and completion
        assert mock_placeholder.info.call_count >= 2
        mock_placeholder.success.assert_called_once()
        mock_placeholder.empty.assert_called_once()
    
    @patch('streamlit.empty')
    @patch('time.sleep')
    @patch('time.time')
    def test_pulse_message(self, mock_time, mock_sleep, mock_empty):
        """Test pulse message animation."""
        mock_placeholder = MagicMock()
        mock_empty.return_value = mock_placeholder
        
        # Mock time to control the loop
        mock_time.side_effect = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5]  # End after 3 seconds
        
        AnimatedElements.pulse_message("Pulsing...", duration=3.0, interval=0.5)
        
        mock_placeholder.info.assert_called()
        mock_placeholder.empty.assert_called()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('utils.ui_feedback.LoadingIndicator.spinner')
    def test_show_loading(self, mock_spinner):
        """Test show_loading convenience function."""
        show_loading("Loading...")
        mock_spinner.assert_called_once_with("Loading...")
    
    @patch('utils.ui_feedback.LoadingIndicator.progress_bar')
    def test_show_progress(self, mock_progress_bar):
        """Test show_progress convenience function."""
        show_progress(5, "Processing...")
        mock_progress_bar.assert_called_once_with(5, "Processing...")
    
    @patch('utils.ui_feedback.UserFeedback.success')
    def test_show_success(self, mock_success):
        """Test show_success convenience function."""
        show_success("Success!", celebration=True)
        mock_success.assert_called_once_with("Success!", celebration=True)
    
    @patch('utils.ui_feedback.UserFeedback.error')
    def test_show_error(self, mock_error):
        """Test show_error convenience function."""
        show_error("Error!")
        mock_error.assert_called_once_with("Error!")
    
    @patch('utils.ui_feedback.UserFeedback.warning')
    def test_show_warning(self, mock_warning):
        """Test show_warning convenience function."""
        show_warning("Warning!")
        mock_warning.assert_called_once_with("Warning!")
    
    @patch('utils.ui_feedback.UserFeedback.info')
    def test_show_info(self, mock_info):
        """Test show_info convenience function."""
        show_info("Info!")
        mock_info.assert_called_once_with("Info!")


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])