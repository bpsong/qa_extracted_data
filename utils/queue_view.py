"""
Queue view utilities for JSON QA webapp.
Handles file listing, sorting, filtering, and display.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from .file_utils import list_unverified_files, cleanup_stale_locks
from .session_manager import SessionManager
from .queue_filter_config import QueueFilterConfig, get_sort_key_function

# Configure logging
logger = logging.getLogger(__name__)


class QueueView:
    """Manages the queue view interface for unverified files."""
    
    @staticmethod
    def _add_keyboard_shortcuts():
        pass
    
    @staticmethod
    def render():
        """Render the complete queue view."""
        
        # Use subheader instead of header for smaller size
        st.subheader("📋 File Queue")
        st.markdown("Select a file to claim and begin validation:")
        
        
        try:
            # Render controls
            QueueView._render_controls()
            
            # Get and display files
            files = QueueView._get_filtered_files()
            
            if not files:
                QueueView._render_empty_state()
                return
            
            # Render file list
            QueueView._render_file_list(files)
            
        except Exception as e:
            st.error(f"Error loading file queue: {str(e)}")
            logger.error(f"Error in queue view: {e}", exc_info=True)
    
    @staticmethod
    def _render_controls():
        """Render enhanced queue view controls using new UI components."""
        try:
            # Get current files (no longer needed for type counting)
            files = list_unverified_files()
            
            # Import enhanced UI components
            from .enhanced_queue_ui import EnhancedQueueUI
            
            # Render enhanced controls and get settings
            filter_settings = EnhancedQueueUI.render_enhanced_controls(files)
            
            # Convert datetime objects to ISO format strings for session state
            date_start = filter_settings.get('date_start')
            date_end = filter_settings.get('date_end')
            
            st.session_state.queue_filters = {
                'sort_by': filter_settings['sort_by'],
                'sort_order': filter_settings['sort_order'],
                'date_preset': filter_settings.get('date_preset', 'all'),
                'date_start': date_start.isoformat() if date_start else None,
                'date_end': date_end.isoformat() if date_end else None
            }
            
        except Exception as e:
            logger.error(f"Error rendering enhanced controls: {e}")
            # Fallback to basic controls if enhanced UI fails
            QueueView._render_basic_controls_fallback()
    
    @staticmethod
    def _render_basic_controls_fallback():
        """Fallback to basic controls if enhanced UI fails."""
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Sort options
            sort_options = {
                'created_at': 'Creation Date',
                'filename': 'File Name',
                'size': 'File Size',
                'modified_at': 'Modified Date'
            }
            
            sort_by = st.selectbox(
                "Sort by:",
                options=list(sort_options.keys()),
                format_func=lambda x: sort_options[x],
                index=0,
                key="queue_sort_by"
            )
        
        with col2:
            # Sort order
            sort_order = st.selectbox(
                "Order:",
                options=['asc', 'desc'],
                format_func=lambda x: 'Oldest First' if x == 'asc' else 'Newest First',
                index=0 if sort_by == 'created_at' else 1,
                key="queue_sort_order"
            )
        
        with col3:
            # Refresh button
            if st.button("🔄 Refresh", help="Refresh file list and cleanup stale locks (Ctrl+R)", key="queue_refresh_btn"):
                # Clear any potential caches
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
                # More aggressive cleanup - remove all stale locks
                cleanup_stale_locks(1)  # Clean locks older than 1 minute
                st.rerun()
        
        # Store filter settings in session state
        st.session_state.queue_filters = {
            'sort_by': sort_by,
            'sort_order': sort_order,
            'date_preset': 'all'
        }
    


    @staticmethod
    def _apply_date_filter(files: List[Dict[str, Any]], date_preset: str, 
                          custom_start: Optional[datetime] = None, 
                          custom_end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Apply date filtering based on preset or custom range.
        
        Args:
            files: List of file dictionaries to filter
            date_preset: Date preset key from QueueFilterConfig.DATE_FILTER_PRESETS
            custom_start: Custom start date (used when preset is 'custom')
            custom_end: Custom end date (used when preset is 'custom')
            
        Returns:
            Filtered list of files within the specified date range
        """
        if date_preset == 'all':
            return files
        
        # Calculate the actual date range
        start_date, end_date = QueueFilterConfig.calculate_date_range(
            date_preset, custom_start, custom_end
        )
        
        if start_date is None and end_date is None:
            return files
        
        filtered_files = []
        for file_info in files:
            # Check both creation and modification dates
            created_at = file_info.get('created_at')
            modified_at = file_info.get('modified_at')
            
            # Handle edge cases where dates might be missing
            if not created_at and not modified_at:
                continue
            
            # Use the most recent date for filtering
            file_date = max(
                d for d in [created_at, modified_at] 
                if d is not None
            )
            
            # Apply date range filter
            include_file = True
            
            if start_date is not None and file_date < start_date:
                include_file = False
            
            if end_date is not None and file_date > end_date:
                include_file = False
            
            if include_file:
                filtered_files.append(file_info)
        
        return filtered_files

    @staticmethod
    def _apply_sort(files: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Apply sorting using dictionary-based sort key lookup.
        
        Args:
            files: List of file dictionaries to sort
            sort_by: Sort field name from QueueFilterConfig.SORT_FIELDS
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Sorted list of files
        """
        if not files:
            return files
        
        # Validate sort configuration
        if not QueueFilterConfig.validate_sort_field(sort_by):
            logger.warning(f"Invalid sort field '{sort_by}', falling back to 'created_at'")
            sort_by = 'created_at'
        
        if not QueueFilterConfig.validate_sort_order(sort_order):
            logger.warning(f"Invalid sort order '{sort_order}', falling back to default for field '{sort_by}'")
            sort_order = QueueFilterConfig.get_default_sort_order(sort_by)
        
        # Get sort key function using lookup
        sort_key_func = get_sort_key_function(sort_by)
        
        # Apply sorting with reverse flag based on sort order
        reverse = sort_order == 'desc'
        
        try:
            sorted_files = sorted(files, key=sort_key_func, reverse=reverse)
            return sorted_files
        except (KeyError, TypeError, AttributeError) as e:
            # Handle cases where sort key is missing or invalid
            logger.warning(f"Error sorting by '{sort_by}': {e}, falling back to filename sort")
            fallback_key_func = get_sort_key_function('filename')
            return sorted(files, key=fallback_key_func, reverse=False)

    @staticmethod
    def _get_filter_settings() -> Dict[str, Any]:
        """Extract and validate filter settings from session state.
        
        Returns:
            Dictionary containing validated filter settings with defaults
        """
        filters = st.session_state.get('queue_filters', {})
        
        # Extract and validate settings with fallbacks (no file_type anymore)
        settings = {
            'sort_by': filters.get('sort_by', 'created_at'),
            'sort_order': filters.get('sort_order', 'desc'),
            'date_preset': filters.get('date_preset', 'all'),
            'custom_start': filters.get('custom_start'),
            'custom_end': filters.get('custom_end')
        }
        
        # Validate settings and apply defaults if invalid
        if not QueueFilterConfig.validate_sort_field(settings['sort_by']):
            settings['sort_by'] = 'created_at'
        
        if not QueueFilterConfig.validate_sort_order(settings['sort_order']):
            settings['sort_order'] = QueueFilterConfig.get_default_sort_order(settings['sort_by'])
        
        if not QueueFilterConfig.validate_date_preset(settings['date_preset']):
            settings['date_preset'] = 'all'
        
        return settings

    @staticmethod
    def _apply_filter_pipeline(files: List[Dict[str, Any]], filter_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Main coordinator function that composes individual filter steps.
        
        Args:
            files: Raw list of files to process
            filter_settings: Dictionary of filter settings from _get_filter_settings()
            
        Returns:
            Filtered and sorted list of files
        """
        if not files:
            return files
        
        # Step 1: Apply date filtering
        filtered_files = QueueView._apply_date_filter(
            files,
            filter_settings['date_preset'],
            filter_settings.get('custom_start'),
            filter_settings.get('custom_end')
        )
        
        # Step 2: Apply sorting
        sorted_files = QueueView._apply_sort(
            filtered_files,
            filter_settings['sort_by'],
            filter_settings['sort_order']
        )
        
        return sorted_files

    @staticmethod
    def _get_filtered_files() -> List[Dict[str, Any]]:
        """Get files with applied filters and sorting using the enhanced filter pipeline."""
        try:
            # Step 1: Get raw file list
            files = list_unverified_files()
            
            if not files:
                return []
            
            # Step 2: Get validated filter state using enhanced state management
            from .queue_filter_state import get_validated_filter_state
            filter_state = get_validated_filter_state()
            
            # Step 3: Convert filter state to settings format for pipeline
            filter_settings = {
                'sort_by': filter_state.sort_by,
                'sort_order': filter_state.sort_order,
                'date_preset': filter_state.date_preset,
                'custom_start': filter_state.date_start,
                'custom_end': filter_state.date_end
            }
            
            # Step 4: Apply enhanced filter pipeline
            processed_files = QueueView._apply_filter_pipeline(files, filter_settings)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Error filtering files with enhanced pipeline: {e}")
            # Fallback to basic filtering if enhanced pipeline fails
            return QueueView._get_filtered_files_fallback()
    
    @staticmethod
    def _get_filtered_files_fallback() -> List[Dict[str, Any]]:
        """Fallback filtering method using basic logic."""
        try:
            # Step 1: Get raw file list
            files = list_unverified_files()
            
            if not files:
                return []
            
            # Step 2: Extract and validate filter settings using basic method
            filter_settings = QueueView._get_filter_settings()
            
            # Step 3: Apply filter pipeline with basic settings
            processed_files = QueueView._apply_filter_pipeline(files, filter_settings)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Error in fallback filtering: {e}")
            return []
    
    @staticmethod
    def _render_empty_state():
        """Render empty state when no files are available."""
        st.info("🎉 No unverified files found! All files have been processed.")
        
        with st.expander("ℹ️ What to do next"):
            st.markdown("""
            **No files to process right now. Here are some options:**
            
            1. **Add new files**: Place JSON files in the `json_docs/` directory
            2. **Check processed files**: Go to the Audit View to see completed work
            3. **Wait for new files**: Files may be added by automated extraction processes
            
            **File Requirements:**
            - Files must be in JSON format
            - Files should not already exist in the `corrected/` directory
            - Files should have corresponding PDF documents in `pdf_docs/` (optional but recommended)
            """)
    
    @staticmethod
    def _render_file_list(files: List[Dict[str, Any]]):
        """Render the list of files with claim buttons."""
        # Compact summary stats
        total_files = len(files)
        locked_files = sum(1 for f in files if f['is_locked'])
        available_files = total_files - locked_files
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", total_files)
        with col2:
            st.metric("Available", available_files)
        with col3:
            st.metric("Locked", locked_files)
        
        # Render files
        for i, file_info in enumerate(files):
            QueueView._render_file_item(file_info, i)
    
    @staticmethod
    def _render_file_item(file_info: Dict[str, Any], index: int):
        """Render a single file item."""
        filename = file_info['filename']
        
        with st.container():
            # Create columns for file information and actions
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            
            with col1:
                # File name and basic info
                st.write(f"**{filename}**")
                
                # File type badge
                file_type = QueueView._get_file_type(filename)
                type_color = QueueView._get_type_color(file_type)
                st.markdown(f"<span style='background-color: {type_color}; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;'>{file_type}</span>", unsafe_allow_html=True)
                
                # File size
                size_mb = file_info['size'] / (1024 * 1024)
                if size_mb >= 1:
                    st.caption(f"📄 {size_mb:.1f} MB")
                else:
                    st.caption(f"📄 {file_info['size']:,} bytes")
            
            with col2:
                # Creation date
                created = file_info['created_at']
                st.write("**Created:**")
                st.write(created.strftime('%Y-%m-%d'))
                st.caption(created.strftime('%H:%M:%S'))
            
            with col3:
                # Modified date
                modified = file_info['modified_at']
                st.write("**Modified:**")
                st.write(modified.strftime('%Y-%m-%d'))
                st.caption(modified.strftime('%H:%M:%S'))
            
            with col4:
                # Lock status
                if file_info['is_locked']:
                    st.write("**Status:**")
                    st.warning(f"🔒 Locked")
                    st.caption(f"By: {file_info['locked_by']}")
                    
                    if file_info['lock_expires']:
                        expires = file_info['lock_expires']
                        time_left = expires - datetime.now()
                        if time_left.total_seconds() > 0:
                            minutes_left = int(time_left.total_seconds() / 60)
                            st.caption(f"Expires in: {minutes_left}m")
                        else:
                            st.caption("⚠️ Expired")
                else:
                    st.write("**Status:**")
                    st.success("🔓 Available")
                    
                    # Show PDF availability
                    from .file_utils import get_pdf_path
                    pdf_path = get_pdf_path(filename)
                    if pdf_path and pdf_path.exists():
                        st.caption("📄 PDF available")
                    else:
                        st.caption("⚠️ No PDF")
            
            with col5:
                # Action button
                if not file_info['is_locked']:
                    if st.button(
                        "Claim",
                        key=f"claim_{index}",
                        help=f"Claim {filename} for editing",
                        type="primary"
                    ):
                        QueueView._claim_file(filename)
                else:
                    # Show locked button or force release option
                    if file_info['locked_by'] == SessionManager.get_current_user():
                        if st.button(
                            "Resume",
                            key=f"resume_{index}",
                            help=f"Resume editing {filename}",
                            type="secondary"
                        ):
                            QueueView._resume_file(filename)
                    else:
                        st.button(
                            "🔒 Locked",
                            key=f"locked_{index}",
                            disabled=True,
                            help=f"Locked by {file_info['locked_by']}"
                        )
                        
                        # Admin option to force release (if needed)
                        if st.session_state.get('show_admin_options', False):
                            if st.button(
                                "🔓 Force Release",
                                key=f"force_{index}",
                                help="Force release this lock (admin only)"
                            ):
                                QueueView._force_release_file(filename)
            
            # Additional file details in expander
            with st.expander(f"📋 Details for {filename}"):
                QueueView._render_file_details(file_info)
            
            st.divider()
    
    @staticmethod
    def _render_file_details(file_info: Dict[str, Any]):
        """Render detailed file information."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**File Information:**")
            st.write(f"• Full path: `{file_info['filepath']}`")
            st.write(f"• Size: {file_info['size']:,} bytes")
            st.write(f"• Created: {file_info['created_at']}")
            st.write(f"• Modified: {file_info['modified_at']}")
        
        with col2:
            st.write("**Processing Information:**")
            
            # Check for corresponding PDF
            from .file_utils import get_pdf_path
            pdf_path = get_pdf_path(file_info['filename'])
            if pdf_path and pdf_path.exists():
                st.write(f"• PDF: ✅ Available ({pdf_path.name})")
                st.write(f"• PDF size: {pdf_path.stat().st_size:,} bytes")
            else:
                st.write("• PDF: ❌ Not found")
            
            # Check for schema
            from .schema_loader import get_schema_for_file
            try:
                schema = get_schema_for_file(file_info['filename'])
                schema_title = schema.get('title', 'Unknown Schema')
                st.write(f"• Schema: ✅ {schema_title}")
            except Exception:
                st.write("• Schema: ❌ Error loading")
            
            # Lock information
            if file_info['is_locked']:
                st.write(f"• Locked by: {file_info['locked_by']}")
                if file_info['lock_expires']:
                    st.write(f"• Lock expires: {file_info['lock_expires']}")
    
    @staticmethod
    def _get_file_type(filename: str) -> str:
        """Determine file type from filename."""
        filename_lower = filename.lower()
        
        if 'invoice' in filename_lower:
            return 'Invoice'
        elif 'receipt' in filename_lower:
            return 'Receipt'
        elif 'contract' in filename_lower:
            return 'Contract'
        elif any(term in filename_lower for term in [
            'purchase_order', 'po_number', 'purchaseorder', 'purchase-order'
        ]) or ('po_' in filename_lower and any(char.isdigit() for char in filename.split('_')[1] if '_' in filename and len(filename.split('_')) > 1)):
            return 'Purchase Order'
        else:
            return 'Document'
    

    
    @staticmethod
    def _get_type_color(file_type: str) -> str:
        """Get color for file type badge."""
        colors = {
            'Invoice': '#e3f2fd',
            'Receipt': '#f3e5f5',
            'Contract': '#e8f5e8',
            'Purchase Order': '#fff3e0',
            'Document': '#f5f5f5'
        }
        return colors.get(file_type, '#f5f5f5')
    
    @staticmethod
    def _claim_file(filename: str):
        """Claim a file for editing."""
        from .error_handler import ErrorHandler, ErrorType
        from .ui_feedback import show_loading, show_success, show_error
        
        def claim_operation():
            from .file_utils import claim_file
            
            user = SessionManager.get_current_user()
            timeout = SessionManager.get_lock_timeout()
            
            if claim_file(filename, user, timeout):
                SessionManager.set_current_file(filename)
                # Preload schema before navigating to edit view so EditView sees latest schema
                try:
                    from .schema_loader import load_active_schema, get_config_value
                    schema_path = get_config_value('schema', 'primary_schema', 'default_schema.yaml')
                    load_active_schema(schema_path)
                except Exception as schema_exc:
                    logger.warning(f"Failed to preload schema for {filename}: {schema_exc}")
                SessionManager.set_current_page('edit')
                return True
            else:
                raise Exception("File may have been claimed by another user")
        
        try:
            with show_loading(f"Claiming {filename}..."):
                success = claim_operation()
            
            if success:
                show_success(f"Successfully claimed {filename}")
                st.rerun()
                
        except Exception as e:
            ErrorHandler.handle_error(
                e,
                f"claiming file {filename}",
                ErrorType.CONCURRENCY,
                recovery_options=[
                    {
                        'title': 'Refresh File List',
                        'description': 'Check if the file is still available',
                        'button_text': '🔄 Refresh',
                        'action': lambda: st.rerun()
                    },
                    {
                        'title': 'Try Another File',
                        'description': 'Select a different file to work on',
                        'button_text': '📋 Browse Files',
                        'action': lambda: None
                    }
                ]
            )
    
    @staticmethod
    def _resume_file(filename: str):
        """Resume editing a file that's already claimed by current user."""
        try:
            SessionManager.set_current_file(filename)
            SessionManager.set_current_page('edit')
            st.success(f"✅ Resuming work on {filename}")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error resuming file: {str(e)}")
            logger.error(f"Error resuming file {filename}: {e}", exc_info=True)
    
    @staticmethod
    def _force_release_file(filename: str):
        """Force release a locked file (admin function)."""
        try:
            from .file_utils import release_file
            
            if release_file(filename):
                st.success(f"✅ Force released {filename}")
                # Clear any potential caches
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
                # Force cleanup of stale locks
                cleanup_stale_locks(SessionManager.get_lock_timeout())
                st.rerun()
            else:
                st.error(f"❌ Failed to force release {filename}")
                
        except Exception as e:
            st.error(f"Error force releasing file: {str(e)}")
            logger.error(f"Error force releasing file {filename}: {e}", exc_info=True)
    
    @staticmethod
    def get_file_type_counts(files: List[Dict[str, Any]], use_optimized: bool = True) -> Dict[str, int]:
        """
        Get counts of files by type.
        
        Args:
            files: List of file information dictionaries
            use_optimized: Whether to use optimized counting (unused, for compatibility)
            
        Returns:
            Dictionary mapping file type keys to counts
        """
        counts = {'all': len(files)}
        
        for file_info in files:
            filename = file_info.get('filename', '')
            file_type = QueueView._get_file_type(filename)
            
            if file_type not in counts:
                counts[file_type] = 0
            counts[file_type] += 1
        
        return counts
    
    @staticmethod
    def render_queue_stats():
        """Render queue statistics sidebar."""
        try:
            files = list_unverified_files()
            
            if not files:
                st.sidebar.info("No files in queue")
                return
            
            # Calculate stats
            total_files = len(files)
            locked_files = sum(1 for f in files if f['is_locked'])
            available_files = total_files - locked_files
            
            # File type breakdown using centralized counting
            filter_counts = QueueView.get_file_type_counts(files, use_optimized=False)
            
            # Convert filter keys to display names for backward compatibility
            type_display_names = {
                'json': 'JSON Files',
                'pdf': 'PDF Files',
                'image': 'Image Files',
                'text': 'Text Files',
                'other': 'Other Files'
            }
            
            type_counts = {}
            for filter_key, count in filter_counts.items():
                if filter_key == 'all':
                    continue
                display_name = type_display_names.get(filter_key, filter_key.title())
                if count > 0:  # Only show types that have files
                    type_counts[display_name] = count
            
            # Size stats
            total_size = sum(f['size'] for f in files)
            avg_size = total_size / total_files if total_files > 0 else 0
            
            # Display stats
            st.sidebar.subheader("📊 Queue Statistics")
            
            st.sidebar.metric("Total Files", total_files)
            st.sidebar.metric("Available", available_files)
            st.sidebar.metric("Locked", locked_files)
            
            if total_size > 1024 * 1024:
                st.sidebar.metric("Total Size", f"{total_size / (1024 * 1024):.1f} MB")
            else:
                st.sidebar.metric("Total Size", f"{total_size / 1024:.1f} KB")
            
            # File type breakdown
            if type_counts:
                st.sidebar.subheader("📋 File Types")
                for file_type, count in sorted(type_counts.items()):
                    st.sidebar.write(f"• {file_type}: {count}")
            
        except Exception as e:
            st.sidebar.error("Error loading queue stats")
            logger.error(f"Error in queue stats: {e}", exc_info=True)