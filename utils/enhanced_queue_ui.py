"""
Enhanced UI components for queue view with improved user experience.
Provides context-aware sort controls, pill-style filters, and collapsible date filters.
"""

import streamlit as st
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import logging

from .queue_filter_config import QueueFilterConfig

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedQueueUI:
    """Enhanced UI components for queue view filtering and sorting."""
    
    @staticmethod
    def render_enhanced_sort_controls() -> Dict[str, Any]:
        """
        Render improved sort controls with context-aware labels and auto-defaulting.
        
        Returns:
            Dict containing sort_by and sort_order values
        """
        col1, col2 = st.columns(2)
        
        with col1:
            # Sort field selection with enhanced labels
            sort_by = st.selectbox(
                "Sort by:",
                options=QueueFilterConfig.get_available_sort_fields(),
                format_func=lambda x: QueueFilterConfig.get_sort_field_config(x)['label'],
                key="queue_sort_by",
                help="Choose how to organize the file list"
            )
            st.caption("Choose how to order the file list")
        
        with col2:
            # Context-aware sort order labels based on selected field
            order_labels = QueueFilterConfig.get_sort_order_labels(sort_by)
            default_order = QueueFilterConfig.get_default_sort_order(sort_by)
            
            # Set default index based on field type
            default_index = 0 if default_order == 'asc' else 1
            
            sort_order = st.selectbox(
                "Sort order:",
                options=['asc', 'desc'],
                format_func=lambda x: order_labels[0] if x == 'asc' else order_labels[1],
                index=default_index,
                key="queue_sort_order",
                help=f"Choose between {order_labels[0]} or {order_labels[1]}"
            )
            st.caption("Choose ascending or descending order")
        
        return {
            'sort_by': sort_by,
            'sort_order': sort_order
        }
    

    
    @staticmethod
    def render_collapsible_date_filter() -> Dict[str, Any]:
        """
        Render collapsible date filter with presets and custom range options.
        
        Returns:
            Dict containing date filter settings
        """
        with st.expander("📅 Date Filter", expanded=False):
            # Date preset selection
            preset = st.selectbox(
                "Filter by date (creation or modification):",
                options=QueueFilterConfig.get_available_date_presets(),
                format_func=lambda x: QueueFilterConfig.get_date_preset_config(x)['label'],
                key="queue_date_preset",
                help="Filter files by creation or modification date (uses the most recent date)"
            )
            
            # Show description for selected preset
            preset_config = QueueFilterConfig.get_date_preset_config(preset)
            description = preset_config.get('description', 'Filter files by date')
            st.caption(f"{description} (uses creation or modification date, whichever is more recent)")
            
            # Custom date range inputs (only shown for custom preset)
            start_date = None
            end_date = None
            
            if preset == 'custom':
                st.write("**Custom Date Range:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    start_date_input = st.date_input(
                        "From:",
                        key="queue_date_start",
                        help="Start date for filtering (inclusive)"
                    )
                
                with col2:
                    end_date_input = st.date_input(
                        "To:",
                        key="queue_date_end",
                        value=date.today(),
                        help="End date for filtering (inclusive)"
                    )
                
                # Convert date objects to datetime objects for filtering
                if start_date_input:
                    start_date = datetime.combine(start_date_input, datetime.min.time())
                else:
                    start_date = None
                
                if end_date_input:
                    end_date = datetime.combine(end_date_input, datetime.max.time())
                else:
                    end_date = None
                
                # Validate date range
                if start_date and end_date and start_date > end_date:
                    st.error("Start date must be before or equal to end date")
                    start_date = None
                    end_date = None
                
                # Show helpful information for custom range
                if start_date or end_date:
                    range_info = []
                    if start_date:
                        range_info.append(f"From: {start_date.strftime('%Y-%m-%d')}")
                    if end_date:
                        range_info.append(f"To: {end_date.strftime('%Y-%m-%d')}")
                    st.caption(f"Active range: {' | '.join(range_info)}")
            
            return {
                'preset': preset,
                'start_date': start_date,
                'end_date': end_date
            }
    

    
    @staticmethod
    def render_enhanced_controls(files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Render all enhanced UI controls in a coordinated layout.
        
        Args:
            files: List of file information (not used for file type counting anymore)
            
        Returns:
            Dictionary containing all filter and sort settings
        """
        # Render sort controls
        sort_settings = EnhancedQueueUI.render_enhanced_sort_controls()
        
        # Add some spacing
        st.markdown("---")
        
        # Render date filter
        date_settings = EnhancedQueueUI.render_collapsible_date_filter()
        
        # Add refresh button in a separate row
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col4:
            if st.button("🔄 Refresh", help="Refresh file list and cleanup stale locks", key="queue_refresh_btn"):
                from .file_utils import cleanup_stale_locks
                from .session_manager import SessionManager
                cleanup_stale_locks(SessionManager.get_lock_timeout())
                st.rerun()
        
        # Combine all settings (no file_type anymore)
        return {
            'sort_by': sort_settings['sort_by'],
            'sort_order': sort_settings['sort_order'],
            'date_preset': date_settings['preset'],
            'date_start': date_settings['start_date'],
            'date_end': date_settings['end_date']
        }
    
    @staticmethod
    def validate_and_normalize_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize filter settings with fallbacks.
        
        Args:
            settings: Raw filter settings dictionary
            
        Returns:
            Validated and normalized settings dictionary
        """
        normalized = {}
        
        # Validate sort field
        sort_by = settings.get('sort_by', 'created_at')
        if not QueueFilterConfig.validate_sort_field(sort_by):
            sort_by = 'created_at'
        normalized['sort_by'] = sort_by
        
        # Validate sort order with auto-default based on field
        sort_order = settings.get('sort_order')
        if not QueueFilterConfig.validate_sort_order(sort_order):
            sort_order = QueueFilterConfig.get_default_sort_order(sort_by)
        normalized['sort_order'] = sort_order
        

        
        # Validate date preset
        date_preset = settings.get('date_preset', 'all')
        if not QueueFilterConfig.validate_date_preset(date_preset):
            date_preset = 'all'
        normalized['date_preset'] = date_preset
        
        # Pass through date values (validation handled in render method)
        normalized['date_start'] = settings.get('date_start')
        normalized['date_end'] = settings.get('date_end')
        
        return normalized