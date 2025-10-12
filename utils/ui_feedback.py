"""
UI feedback utilities for JSON QA webapp.
Provides loading indicators, progress bars, success messages, and user feedback.
"""

import streamlit as st
import time
from typing import Optional, Callable, Any, List, Dict
from contextlib import contextmanager
import logging

# Configure logging
logger = logging.getLogger(__name__)


class LoadingIndicator:
    """Loading indicator utilities."""
    
    @staticmethod
    @contextmanager
    def spinner(message: str = "Loading..."):
        """Context manager for spinner loading indicator."""
        with st.spinner(message):
            yield
    
    @staticmethod
    @contextmanager
    def progress_bar(total_steps: int, message: str = "Processing..."):
        """Context manager for progress bar."""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        class ProgressTracker:
            def __init__(self):
                self.current_step = 0
                self.total = total_steps
            
            def update(self, step: int, step_message: str = ""):
                self.current_step = step
                progress = min(step / total_steps, 1.0)
                progress_bar.progress(progress)
                
                if step_message:
                    status_text.text(f"{message}: {step_message}")
                else:
                    status_text.text(f"{message}: Step {step}/{total_steps}")
            
            def increment(self, step_message: str = ""):
                self.update(self.current_step + 1, step_message)
            
            def complete(self, completion_message: str = "Complete!"):
                progress_bar.progress(1.0)
                status_text.text(completion_message)
                time.sleep(0.5)  # Brief pause to show completion
                progress_bar.empty()
                status_text.empty()
        
        try:
            yield ProgressTracker()
        finally:
            progress_bar.empty()
            status_text.empty()
    
    @staticmethod
    def show_loading_message(message: str, duration: float = 2.0):
        """Show a temporary loading message."""
        placeholder = st.empty()
        placeholder.info(f"⏳ {message}")
        time.sleep(duration)
        placeholder.empty()


class UserFeedback:
    """User feedback and notification utilities."""
    
    @staticmethod
    def success(message: str, duration: Optional[float] = None, celebration: bool = False):
        """Show success message with optional celebration."""
        st.success(f"✅ {message}")
        
        if celebration:
            st.balloons()
        
        if duration:
            time.sleep(duration)
    
    @staticmethod
    def info(message: str, icon: str = "ℹ️"):
        """Show info message."""
        st.info(f"{icon} {message}")
    
    @staticmethod
    def warning(message: str, icon: str = "⚠️"):
        """Show warning message."""
        st.warning(f"{icon} {message}")
    
    @staticmethod
    def error(message: str, icon: str = "❌"):
        """Show error message."""
        st.error(f"{icon} {message}")
    
    @staticmethod
    def toast(message: str, type: str = "info"):
        """Show toast notification (if supported)."""
        # Streamlit doesn't have native toast, so we use temporary message
        placeholder = st.empty()
        
        if type == "success":
            placeholder.success(f"✅ {message}")
        elif type == "warning":
            placeholder.warning(f"⚠️ {message}")
        elif type == "error":
            placeholder.error(f"❌ {message}")
        else:
            placeholder.info(f"ℹ️ {message}")
        
        # Auto-dismiss after 3 seconds
        time.sleep(3)
        placeholder.empty()
    
    @staticmethod
    def confirmation_dialog(
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        danger: bool = False
    ) -> Optional[bool]:
        """Show confirmation dialog."""
        st.subheader(title)
        st.write(message)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if danger:
                confirmed = st.button(confirm_text, type="primary", key="confirm_danger")
            else:
                confirmed = st.button(confirm_text, type="primary", key="confirm_action")
        
        with col2:
            cancelled = st.button(cancel_text, key="cancel_action")
        
        if confirmed:
            return True
        elif cancelled:
            return False
        else:
            return None  # No action taken yet
    
    @staticmethod
    def show_validation_results(errors: List[str], warnings: Optional[List[str]] = None):
        """Show validation results with errors and warnings."""
        if warnings is None:
            warnings = []
        
        if errors:
            st.error("❌ **Validation Errors:**")
            for error in errors:
                st.error(f"  • {error}")
        
        if warnings:
            st.warning("⚠️ **Warnings:**")
            for warning in warnings:
                st.warning(f"  • {warning}")
        
        if not errors and not warnings:
            st.success("✅ **Validation Passed:** No issues found")
    
    @staticmethod
    def show_operation_status(
        operation: str,
        status: str,
        details: Optional[str] = None,
        progress: Optional[float] = None
    ):
        """Show operation status with optional progress."""
        status_icons = {
            'pending': '⏳',
            'running': '🔄',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'cancelled': '🚫'
        }
        
        icon = status_icons.get(status, '📋')
        message = f"{icon} **{operation}:** {status.title()}"
        
        if details:
            message += f" - {details}"
        
        if status == 'success':
            st.success(message)
        elif status == 'error':
            st.error(message)
        elif status == 'warning':
            st.warning(message)
        else:
            st.info(message)
        
        if progress is not None:
            st.progress(progress)


class Notify:
    """
    Toast-first notification helper.
    Prefers st.toast for non-blocking notifications when available (Streamlit 1.36+).
    Falls back to ephemeral placeholders with auto-dismiss for older versions.
    
    The API includes: success, info, warn, error, once.
    
    Usage:
    Notify.success("Operation successful!")
    Notify.error("Something went wrong.")
    Notify.once("Unique message", notification_type="info", key="my_once_key")  # Shows only once per session
    """

    @staticmethod
    def _display_notification(message: str, notification_type: str = 'info') -> None:
        """Internal method to display notification based on type."""
        icons = {
            'success': '✅',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌'
        }
        icon = icons.get(notification_type, 'ℹ️')
        full_message = f"{icon} {message}"

        # Debug: Check if st.toast is available
        toast_available = hasattr(st, 'toast')
        logger.debug(f"Notify: st.toast available: {toast_available}, Streamlit version: {st.__version__ if hasattr(st, '__version__') else 'unknown'}")
        
        try:
            if hasattr(st, 'toast'):
                # Map notification types to emoji icons for st.toast
                icon_map = {
                    'success': '✅',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌'
                }
                toast_icon = icon_map.get(notification_type, 'ℹ️')
                st.toast(message, icon=toast_icon)
            else:
                # Fallback to ephemeral placeholder
                placeholder = st.empty()
                if notification_type == 'success':
                    placeholder.success(full_message)
                elif notification_type == 'warning':
                    placeholder.warning(full_message)
                elif notification_type == 'error':
                    placeholder.error(full_message)
                else:
                    placeholder.info(full_message)
                time.sleep(3)  # Auto-dismiss after 3 seconds
                placeholder.empty()
        except Exception as e:
            # Log any exceptions when using toast
            logger.error(f"Error using st.toast: {e}", exc_info=True)
            # Ultimate fallback: use standard st methods
            if notification_type == 'success':
                st.success(full_message)
            elif notification_type == 'warning':
                st.warning(full_message)
            elif notification_type == 'error':
                st.error(full_message)
            else:
                st.info(full_message)

    @staticmethod
    def success(message: str) -> None:
        """Show success notification."""
        Notify._display_notification(message, 'success')

    @staticmethod
    def info(message: str) -> None:
        """Show info notification."""
        Notify._display_notification(message, 'info')

    @staticmethod
    def warn(message: str) -> None:
        """Show warning notification."""
        Notify._display_notification(message, 'warning')

    @staticmethod
    def error(message: str) -> None:
        """Show error notification."""
        Notify._display_notification(message, 'error')

    @staticmethod
    def once(message: str, notification_type: str = 'info', key: str = 'default_once') -> bool:
        """
        Show notification only once per session for the given key.
        Returns True if shown, False if already shown.
        """
        if key not in st.session_state:
            st.session_state[key] = False
        if not st.session_state[key]:
            Notify._display_notification(message, notification_type)
            st.session_state[key] = True
            return True
        return False


class InteractiveElements:
    """Interactive UI elements with feedback."""
    
    @staticmethod
    def action_button(
        label: str,
        action: Callable,
        confirmation_required: bool = False,
        confirmation_message: str = "",
        success_message: str = "",
        loading_message: str = "",
        **button_kwargs
    ) -> bool:
        """Action button with loading and confirmation."""
        if st.button(label, **button_kwargs):
            # Show confirmation if required
            if confirmation_required:
                if not confirmation_message:
                    confirmation_message = f"Are you sure you want to {label.lower()}?"
                
                confirmed = UserFeedback.confirmation_dialog(
                    "Confirm Action",
                    confirmation_message
                )
                
                if confirmed is None:
                    return False  # Still waiting for confirmation
                elif not confirmed:
                    UserFeedback.info("Action cancelled")
                    return False
        
            # Execute action with loading indicator
            try:
                if loading_message:
                    with LoadingIndicator.spinner(loading_message):
                        result = action()
                else:
                    result = action()
                
                # Show success message
                if success_message:
                    UserFeedback.success(success_message)
                
                return True
                
            except Exception as e:
                UserFeedback.error(f"Action failed: {str(e)}")
                logger.error(f"Action button error: {e}", exc_info=True)
                return False
        
        return False
    
    @staticmethod
    def file_upload_with_feedback(
        label: str,
        accepted_types: List[str],
        max_size_mb: int = 10,
        **upload_kwargs
    ):
        """File upload with validation and feedback."""
        uploaded_file = st.file_uploader(
            label,
            type=accepted_types,
            **upload_kwargs
        )
        
        if uploaded_file is not None:
            # Validate file size
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            
            if file_size_mb > max_size_mb:
                UserFeedback.error(f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)")
                return None
            
            # Show file info
            UserFeedback.success(f"File uploaded: {uploaded_file.name} ({file_size_mb:.1f}MB)")
            
            return uploaded_file
        
        return None
    
    @staticmethod
    def form_with_validation(
        form_key: str,
        fields: Dict[str, Dict[str, Any]],
        submit_label: str = "Submit",
        validation_func: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Form with built-in validation and feedback."""
        with st.form(form_key):
            form_data = {}
            
            # Render form fields
            for field_name, field_config in fields.items():
                field_type = field_config.get('type', 'text')
                label = field_config.get('label', field_name)
                required = field_config.get('required', False)
                
                if field_type == 'text':
                    value = st.text_input(label, key=f"{form_key}_{field_name}")
                elif field_type == 'number':
                    value = st.number_input(label, key=f"{form_key}_{field_name}")
                elif field_type == 'select':
                    options = field_config.get('options', [])
                    value = st.selectbox(label, options, key=f"{form_key}_{field_name}")
                elif field_type == 'checkbox':
                    value = st.checkbox(label, key=f"{form_key}_{field_name}")
                else:
                    value = st.text_input(label, key=f"{form_key}_{field_name}")
                
                form_data[field_name] = value
            
            # Submit button
            submitted = st.form_submit_button(submit_label, type="primary")
            
            if submitted:
                # Validate required fields
                errors = []
                for field_name, field_config in fields.items():
                    if field_config.get('required', False):
                        if not form_data.get(field_name):
                            label = field_config.get('label', field_name)
                            errors.append(f"{label} is required")
                
                # Custom validation
                if validation_func and not errors:
                    custom_errors = validation_func(form_data)
                    if custom_errors:
                        errors.extend(custom_errors)
                
                # Show validation results
                if errors:
                    UserFeedback.show_validation_results(errors)
                    return None
                else:
                    UserFeedback.success("Form submitted successfully!")
                    return form_data
        
        return None


class StatusIndicators:
    """Status indicators and badges."""
    
    @staticmethod
    def status_badge(status: str, label: str = "") -> str:
        """Create a status badge."""
        status_colors = {
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'info': '#17a2b8',
            'pending': '#6c757d',
            'processing': '#007bff'
        }
        
        status_icons = {
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'info': 'ℹ️',
            'pending': '⏳',
            'processing': '🔄'
        }
        
        color = status_colors.get(status, '#6c757d')
        icon = status_icons.get(status, '📋')
        display_text = label or status.title()
        
        return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{icon} {display_text}</span>'
    
    @staticmethod
    def progress_indicator(current: int, total: int, label: str = "") -> str:
        """Create a progress indicator."""
        percentage = (current / total) * 100 if total > 0 else 0
        
        if percentage == 100:
            color = '#28a745'  # Green
            icon = '✅'
        elif percentage >= 50:
            color = '#ffc107'  # Yellow
            icon = '🔄'
        else:
            color = '#6c757d'  # Gray
            icon = '⏳'
        
        display_text = f"{current}/{total}"
        if label:
            display_text = f"{label}: {display_text}"
        
        return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{icon} {display_text} ({percentage:.0f}%)</span>'
    
    @staticmethod
    def health_indicator(status: str, details: str = "") -> str:
        """Create a system health indicator."""
        if status == 'healthy':
            return f'<span style="color: #28a745;">🟢 Healthy {details}</span>'
        elif status == 'warning':
            return f'<span style="color: #ffc107;">🟡 Warning {details}</span>'
        elif status == 'error':
            return f'<span style="color: #dc3545;">🔴 Error {details}</span>'
        else:
            return f'<span style="color: #6c757d;">⚪ Unknown {details}</span>'


class AnimatedElements:
    """Animated UI elements for better user experience."""
    
    @staticmethod
    def typing_effect(text: str, delay: float = 0.05):
        """Show text with typing effect."""
        placeholder = st.empty()
        
        for i in range(len(text) + 1):
            placeholder.text(text[:i] + "▌")
            time.sleep(delay)
        
        placeholder.text(text)
    
    @staticmethod
    def countdown_timer(seconds: int, message: str = "Time remaining"):
        """Show countdown timer."""
        placeholder = st.empty()
        
        for i in range(seconds, 0, -1):
            placeholder.info(f"⏰ {message}: {i} seconds")
            time.sleep(1)
        
        placeholder.success("✅ Timer completed!")
        time.sleep(1)
        placeholder.empty()
    
    @staticmethod
    def pulse_message(message: str, duration: float = 3.0, interval: float = 0.5):
        """Show pulsing message."""
        placeholder = st.empty()
        end_time = time.time() + duration
        
        while time.time() < end_time:
            placeholder.info(f"🔄 {message}")
            time.sleep(interval / 2)
            placeholder.empty()
            time.sleep(interval / 2)
        
        placeholder.empty()


# Convenience functions
def show_loading(message: str = "Loading..."):
    """Show loading spinner."""
    return LoadingIndicator.spinner(message)


def show_progress(total_steps: int, message: str = "Processing..."):
    """Show progress bar."""
    return LoadingIndicator.progress_bar(total_steps, message)


def show_success(message: str, celebration: bool = False):
    """Show success message."""
    UserFeedback.success(message, celebration=celebration)


def show_error(message: str):
    """Show error message."""
    UserFeedback.error(message)


def show_warning(message: str):
    """Show warning message."""
    UserFeedback.warning(message)


def show_info(message: str):
    """Show info message."""
    UserFeedback.info(message)


def notify_schema_mismatch_ignored(extras: list[str]):
    """
    Notify the user that deprecated schema fields were ignored.

    - Uses st.toast when available for non-blocking notification, otherwise falls back to Notify.info.
    - Debounces repeated notifications using st.session_state to avoid spamming the user.
    """
    # Build message according to spec
    display_extras = ", ".join(extras[:5])
    ellipsis = "..." if len(extras) > 5 else ""
    message = f"Ignored {len(extras)} deprecated field(s): {display_extras}{ellipsis}"

    # Session-state key to debounce repeated notifications within a session
    session_key = "schema_mismatch_ignored_notified"

    # If already notified this session, do not notify again
    if st.session_state.get(session_key):
        logger.debug("notify_schema_mismatch_ignored: notification suppressed (already shown in session)")
        return

    # Try to use st.toast (preferred non-blocking). Preserve existing patterns.
    try:
        if hasattr(st, "toast"):
            try:
                st.toast(message, icon="ℹ️")
            except Exception as e:
                logger.debug(f"st.toast failed, falling back to Notify.info: {e}", exc_info=True)
                Notify.info(message)
        else:
            Notify.info(message)
    except Exception as e:
        # As a final fallback, log the error and use st.info
        logger.error(f"Failed to show schema mismatch ignored notification: {e}", exc_info=True)
        try:
            st.info(message)
        except Exception:
            # Nothing more to do
            pass

    # Mark as shown for this session to debounce
    st.session_state[session_key] = True