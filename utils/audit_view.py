"""
Audit view utilities for JSON QA webapp.
Handles audit log display, filtering, and detailed diff viewing.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from .file_utils import read_audit_logs
from .diff_utils import format_diff_for_display, get_change_summary
from utils.ui_feedback import Notify

logger = logging.getLogger(__name__)


class AuditView:
    """Manages the audit view interface for processed files and changes."""
    
    
    @staticmethod
    def render():
        """Render the complete audit view."""
        
        st.header("📊 Audit Log")
        st.markdown("Review processed files and changes:")
        
        try:
            # Render controls and filters
            filters = AuditView._render_controls()
            
            # Get and display audit entries
            entries = AuditView._get_filtered_entries(filters)
            
            if not entries:
                AuditView._render_empty_state()
                return
            
            # Render audit entries
            AuditView._render_audit_entries(entries)
            
        except Exception as e:
            Notify.error(f"Error loading audit log: {str(e)}")
            logger.error(f"Error in audit view: {e}", exc_info=True)
    
    @staticmethod
    def _render_controls():
        """Render audit view controls and filters."""
        def store_value(key):
            st.session_state[key] = st.session_state[f"_{key}"]
        
        def load_value(key):
            if key in st.session_state:
                st.session_state[f"_{key}"] = st.session_state[key]
        
        # Initialize permanent session state for dates if not present
        default_start = datetime.now().date() - timedelta(days=30)
        default_end = datetime.now().date()
        if 'audit_start_date' not in st.session_state:
            st.session_state.audit_start_date = default_start
        if 'audit_end_date' not in st.session_state:
            st.session_state.audit_end_date = default_end
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                # Date range filter
                date_options = {
                    'all': 'All Time',
                    'today': 'Today',
                    'week': 'Last 7 Days',
                    'month': 'Last 30 Days',
                    'custom': 'Custom Range'
                }
                
                date_filter = st.selectbox(
                    "Date Range:",
                    options=list(date_options.keys()),
                    format_func=lambda x: date_options[x],
                    index=2,  # Default to last 7 days
                    key="audit_date_filter"
                )
            
            with col2:
                # User filter
                all_entries = read_audit_logs()
                users = ['All'] + sorted(list(set(entry.get('user', 'Unknown') for entry in all_entries)))
                
                user_filter = st.selectbox(
                    "User:",
                    options=users,
                    index=0,
                    key="audit_user_filter"
                )
            
            with col3:
                # Action filter
                actions = ['All', 'corrected', 'reviewed', 'rejected']
                action_filter = st.selectbox(
                    "Action:",
                    options=actions,
                    index=0,
                    key="audit_action_filter"
                )
            
            with col4:
                # Refresh button
                if st.button("🔄 Refresh", help="Refresh audit log", key="audit_refresh_btn"):
                    st.rerun()
            
            # Custom date range (if selected)
            custom_start_date = None
            custom_end_date = None
            
            if date_filter == 'custom':
                # Load permanent state to temp keys before rendering widgets
                load_value("audit_start_date")
                load_value("audit_end_date")
                
                col_start, col_end = st.columns(2)
                with col_start:
                    custom_start_date = st.date_input(
                        "Start Date:",
                        key="_audit_start_date",
                        on_change=store_value,
                        args=["audit_start_date"]
                    )
                with col_end:
                    custom_end_date = st.date_input(
                        "End Date:",
                        key="_audit_end_date",
                        on_change=store_value,
                        args=["audit_end_date"]
                    )
            
            return {
                'date_filter': date_filter,
                'user_filter': user_filter,
                'action_filter': action_filter,
                'custom_start_date': custom_start_date,
                'custom_end_date': custom_end_date
            }
    
    @staticmethod
    def _get_filtered_entries(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get audit entries with applied filters."""
        logger.info(f"Getting filtered entries with filters: {filters}")
        try:
            entries = read_audit_logs()
            logger.info(f"Loaded {len(entries)} total entries from audit logs")
            
            if not entries:
                return []
            
            # Apply date filter
            if filters['date_filter'] != 'all':
                entries = AuditView._filter_by_date(entries, filters)
                logger.info(f"After date filter: {len(entries)} entries remaining")
            
            # Apply user filter
            if filters['user_filter'] != 'All':
                entries = [e for e in entries if e.get('user') == filters['user_filter']]
            
            # Apply action filter
            if filters['action_filter'] != 'All':
                entries = [e for e in entries if e.get('action') == filters['action_filter']]
            
            logger.info(f"Final filtered entries count: {len(entries)}")
            return entries
            
        except Exception as e:
            logger.error(f"Error filtering audit entries: {e}")
            return []
    
    @staticmethod
    def _filter_by_date(entries: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter entries by date range."""
        now = datetime.now()
        
        if filters['date_filter'] == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif filters['date_filter'] == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif filters['date_filter'] == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
        elif filters['date_filter'] == 'custom':
            if filters['custom_start_date'] and filters['custom_end_date']:
                start_date = datetime.combine(filters['custom_start_date'], datetime.min.time())
                end_date = datetime.combine(filters['custom_end_date'], datetime.max.time())
                logger.info(f"Filtering with custom range: {start_date} to {end_date}")
                if start_date > end_date:
                    Notify.error("Invalid date range: Start date must be before or equal to end date. Please adjust and try again.")
                    logger.warning(f"Date filter will match nothing due to invalid range: start {start_date} > end {end_date}")
                    return []
            else:
                logger.info("Custom filter skipped: missing dates")
                return entries  # No custom dates provided
        else:
            return entries
        
        filtered_entries = []
        match_count = 0
        for entry in entries:
            try:
                entry_timestamp = entry.get('timestamp')
                if entry_timestamp:
                    entry_date = datetime.fromisoformat(entry_timestamp.replace('Z', '+00:00'))
                    if start_date <= entry_date <= end_date:
                        filtered_entries.append(entry)
                        match_count += 1
                    else:
                        logger.debug(f"Entry {entry.get('filename', 'unknown')} at {entry_date} outside range {start_date} to {end_date}")
                else:
                    logger.debug(f"Skipping entry with no timestamp: {entry.get('filename', 'unknown')}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid timestamp for entry {entry.get('filename', 'unknown')}: {e}")
                # Include entries with invalid timestamps
                filtered_entries.append(entry)
        logger.info(f"Date filter matched {match_count} out of {len(entries)} entries")
        
        return filtered_entries
    
    @staticmethod
    def _render_empty_state():
        """Render empty state when no audit entries are found."""
        Notify.info("📝 No audit entries found matching the current filters")
        
        with st.expander("ℹ️ About the Audit Log"):
            st.markdown("""
            **The audit log tracks all file processing activities:**
            
            - **File Corrections**: When operators submit corrected JSON data
            - **Change Details**: Complete diff showing what was modified
            - **User Tracking**: Who made each change and when
            - **Validation Results**: Any validation errors or warnings
            
            **Audit entries are created when:**
            - Files are successfully submitted after editing
            - Validation errors are encountered
            - Files are processed through automated workflows
            
            **Try adjusting the filters above to see more entries, or process some files to generate audit data.**
            """)
    
    @staticmethod
    def _render_audit_entries(entries: List[Dict[str, Any]]):
        """Render the list of audit entries."""
        # Summary statistics
        AuditView._render_audit_summary(entries)
        
        st.divider()
        
        # Entries list with export option
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"📋 Audit Entries ({len(entries)})")
        
        with col2:
            # Export functionality with dialog
            if st.button(
                "📥 Export Data",
                help="Export audit data to CSV or JSON format",
                type="secondary",
                width='stretch',
                key="audit_export_btn"
            ):
                st.session_state.show_export_dialog = True
        
        # Show export dialog if requested
        if st.session_state.get('show_export_dialog', False):
            AuditView._render_export_dialog(entries)
        
        for i, entry in enumerate(entries):
            AuditView._render_audit_entry(entry, i)
    
    @staticmethod
    def _render_audit_summary(entries: List[Dict[str, Any]]):
        """Render audit summary statistics."""
        st.subheader("📈 Summary Statistics")
        
        # Calculate statistics
        total_entries = len(entries)
        unique_files = len(set(entry.get('filename', 'Unknown') for entry in entries))
        unique_users = len(set(entry.get('user', 'Unknown') for entry in entries))
        
        # Count changes
        total_changes = 0
        entries_with_changes = 0
        
        for entry in entries:
            if entry.get('change_summary', {}).get('total', 0) > 0:
                entries_with_changes += 1
                total_changes += entry['change_summary']['total']
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", total_entries)
        
        with col2:
            st.metric("Unique Files", unique_files)
        
        with col3:
            st.metric("Active Users", unique_users)
        
        with col4:
            st.metric("Total Changes", total_changes)
        
        # Additional statistics
        if entries:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Entries with Changes", entries_with_changes)
            
            with col2:
                avg_changes = total_changes / entries_with_changes if entries_with_changes > 0 else 0
                st.metric("Avg Changes per Entry", f"{avg_changes:.1f}")
            
            with col3:
                # Most recent entry
                latest_entry = entries[0] if entries else None
                if latest_entry:
                    timestamp = latest_entry.get('timestamp', '')
                    try:
                        latest_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_ago = datetime.now() - latest_date.replace(tzinfo=None)
                        
                        if time_ago.days > 0:
                            time_str = f"{time_ago.days}d ago"
                        elif time_ago.seconds > 3600:
                            time_str = f"{time_ago.seconds // 3600}h ago"
                        else:
                            time_str = f"{time_ago.seconds // 60}m ago"
                        
                        st.metric("Latest Entry", time_str)
                    except:
                        st.metric("Latest Entry", "Unknown")
    
    @staticmethod
    def _render_audit_entry(entry: Dict[str, Any], index: int):
        """Render a single audit entry."""
        filename = entry.get('filename', 'Unknown')
        timestamp = entry.get('timestamp', 'Unknown time')
        user = entry.get('user', 'Unknown')
        action = entry.get('action', 'unknown')
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            time_ago = datetime.now() - dt.replace(tzinfo=None)
            
            if time_ago.days > 0:
                time_ago_str = f"{time_ago.days}d ago"
            elif time_ago.seconds > 3600:
                time_ago_str = f"{time_ago.seconds // 3600}h ago"
            else:
                time_ago_str = f"{time_ago.seconds // 60}m ago"
        except:
            formatted_time = timestamp
            time_ago_str = ""
        
        # Entry header
        with st.expander(f"📄 {filename} - {formatted_time} ({time_ago_str})"):
            # Basic information
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**File:** {filename}")
                st.write(f"**User:** {user}")
                st.write(f"**Action:** {action.title()}")
                st.write(f"**Timestamp:** {formatted_time}")
            
            with col2:
                # Change summary
                change_summary = entry.get('change_summary', {})
                if change_summary:
                    total_changes = change_summary.get('total', 0)
                    st.write(f"**Total Changes:** {total_changes}")
                    
                    if total_changes > 0:
                        st.write(f"  • Modified: {change_summary.get('modified', 0)}")
                        st.write(f"  • Added: {change_summary.get('added', 0)}")
                        st.write(f"  • Removed: {change_summary.get('removed', 0)}")
                        st.write(f"  • Type Changed: {change_summary.get('type_changed', 0)}")
                else:
                    st.write("**Changes:** No change data available")
                
                # Additional metadata
                if 'submission_method' in entry:
                    st.write(f"**Method:** {entry['submission_method']}")
            
            # Show detailed diff if available
            if entry.get('has_changes') and 'detailed_diff' in entry:
                st.subheader("🔍 Detailed Changes")
                
                # Option to show/hide diff
                show_diff = st.checkbox(f"Show detailed diff", key=f"show_diff_{index}")
                
                if show_diff:
                    try:
                        # Pass original and modified data for better diff display
                        original_data = entry.get('original_data')
                        modified_data = entry.get('modified_data')
                        diff_display = format_diff_for_display(
                            entry['detailed_diff'], 
                            original_data, 
                            modified_data
                        )
                        st.markdown(diff_display)
                    except Exception as e:
                        Notify.error(f"Error displaying diff: {str(e)}")
            
            elif not entry.get('has_changes'):
                Notify.info("✅ No changes were made to this file (reviewed without modifications)")
            
            # Show original and modified data if available
            if 'original_data' in entry and 'modified_data' in entry:
                with st.expander("📋 View Raw Data"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Original Data")
                        st.json(entry['original_data'])
                    
                    with col2:
                        st.subheader("Modified Data")
                        st.json(entry['modified_data'])
    
    @staticmethod
    def render_audit_sidebar():
        """Render audit view sidebar information."""
        try:
            entries = read_audit_logs()
            
            if not entries:
                st.sidebar.info("No audit data available")
                return
            
            st.sidebar.subheader("📊 Audit Statistics")
            
            # Quick stats
            total_entries = len(entries)
            st.sidebar.metric("Total Entries", total_entries)
            
            # Recent activity (last 24 hours)
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            recent_entries = []
            for entry in entries:
                try:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', '').replace('Z', '+00:00'))
                    if entry_time.replace(tzinfo=None) > yesterday:
                        recent_entries.append(entry)
                except:
                    pass
            
            st.sidebar.metric("Last 24h", len(recent_entries))
            
            # Top users
            user_counts = {}
            for entry in entries[:50]:  # Last 50 entries
                user = entry.get('user', 'Unknown')
                user_counts[user] = user_counts.get(user, 0) + 1
            
            if user_counts:
                st.sidebar.subheader("👥 Top Users")
                for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.sidebar.write(f"• {user}: {count}")
            
            # File types processed
            file_types = {}
            for entry in entries[:50]:  # Last 50 entries
                filename = entry.get('filename', '')
                if 'invoice' in filename.lower():
                    file_types['Invoice'] = file_types.get('Invoice', 0) + 1
                elif 'receipt' in filename.lower():
                    file_types['Receipt'] = file_types.get('Receipt', 0) + 1
                elif 'contract' in filename.lower():
                    file_types['Contract'] = file_types.get('Contract', 0) + 1
                else:
                    file_types['Other'] = file_types.get('Other', 0) + 1
            
            if file_types:
                st.sidebar.subheader("📄 File Types")
                for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                    st.sidebar.write(f"• {file_type}: {count}")
        
        except Exception as e:
            st.sidebar.error("Error loading audit stats")
            logger.error(f"Error in audit sidebar: {e}", exc_info=True)
    
    @staticmethod
    @staticmethod
    def _render_export_dialog(entries: List[Dict[str, Any]]):
        """Render export dialog for audit data."""
        @st.dialog("📥 Export Audit Data")
        def export_dialog():
            if not entries:
                Notify.warn("⚠️ No data available to export. Apply different filters or process some files first.")
                if st.button("Close", type="primary", width='stretch'):
                    st.session_state.show_export_dialog = False
                    st.rerun()
                return
            
            # Export summary with better styling
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                <h4 style="margin: 0; color: #1f77b4;">📊 Ready to Export</h4>
                <p style="margin: 0.5rem 0 0 0; color: #666;">{len(entries)} audit entries selected for export</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Format selection
            st.subheader("📄 Choose Export Format")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_selected = st.button(
                    "📊 CSV Format\n\nBest for spreadsheet analysis\n(Excel, Google Sheets)",
                    key="csv_format",
                    width='stretch',
                    help="Export as comma-separated values for use in spreadsheet applications"
                )
            
            with col2:
                json_selected = st.button(
                    "📋 JSON Format\n\nComplete raw data\n(APIs, data analysis)",
                    key="json_format", 
                    width='stretch',
                    help="Export as JSON with all available data fields"
                )
            
            # Handle format selection
            export_format = None
            if csv_selected:
                export_format = 'csv'
            elif json_selected:
                export_format = 'json'
            
            if export_format:
                st.divider()
                
                # Generate export data
                with st.spinner(f"Generating {export_format.upper()} export..."):
                    try:
                        exported_data = AuditView.export_audit_data(entries, export_format)
                        
                        if exported_data:
                            filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
                            file_size_kb = len(exported_data) / 1024
                            
                            # Success message
                            Notify.success("✅ Export data prepared! Click the download button below to save the file.")
                            
                            # File info
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("File Size", f"{file_size_kb:.1f} KB")
                            with col2:
                                st.metric("Records", len(entries))
                            
                            # Download button
                            st.download_button(
                                label=f"⬇️ Download {filename}",
                                data=exported_data,
                                file_name=filename,
                                mime=f"text/{export_format}" if export_format == 'csv' else 'application/json',
                                type="primary",
                                width='stretch',
                                help=f"Click to download your {export_format.upper()} file"
                            )
                            
                            # Preview section
                            with st.expander("👁️ Preview Export Data", expanded=False):
                                if export_format == 'csv':
                                    lines = exported_data.split('\n')[:6]  # Header + 5 rows
                                    preview_data = '\n'.join(lines)
                                    st.code(preview_data, language='csv')
                                    if len(lines) < len(exported_data.split('\n')):
                                        st.caption(f"Showing first 5 rows of {len(exported_data.split('\n'))-1} total rows")
                                else:
                                    import json
                                    try:
                                        json_data = json.loads(exported_data)
                                        if isinstance(json_data, list) and len(json_data) > 0:
                                            st.json(json_data[0])
                                            if len(json_data) > 1:
                                                st.caption(f"Showing first entry of {len(json_data)} total entries")
                                        else:
                                            st.json(json_data)
                                    except:
                                        st.code(exported_data[:500] + "..." if len(exported_data) > 500 else exported_data)
                        else:
                            Notify.error("❌ Failed to generate export data. Please try again.")
                            
                    except Exception as e:
                        Notify.error(f"❌ Export error: {str(e)}")
                        logger.error(f"Export error: {e}", exc_info=True)
            
            # Dialog controls
            st.divider()
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🔄 Reset", help="Reset format selection", width='stretch'):
                    st.rerun()
            
            with col2:
                if st.button("❌ Close", type="secondary", width='stretch'):
                    st.session_state.show_export_dialog = False
                    st.rerun()
        
        # Call the dialog
        export_dialog()
    
    @staticmethod
    def export_audit_data(entries: List[Dict[str, Any]], format: str = 'csv') -> Optional[str]:
        """Export audit data in various formats."""
        try:
            if not entries:
                logger.warning("No entries provided for export")
                return None
            
            if format == 'csv':
                # Flatten entries for CSV export
                flattened_data = []
                
                for entry in entries:
                    # Safely extract change summary data
                    change_summary = entry.get('change_summary', {})
                    
                    flat_entry = {
                        'filename': entry.get('filename', ''),
                        'timestamp': entry.get('timestamp', ''),
                        'user': entry.get('user', ''),
                        'action': entry.get('action', ''),
                        'has_changes': entry.get('has_changes', False),
                        'total_changes': change_summary.get('total', 0) if isinstance(change_summary, dict) else 0,
                        'modified_fields': change_summary.get('modified', 0) if isinstance(change_summary, dict) else 0,
                        'added_fields': change_summary.get('added', 0) if isinstance(change_summary, dict) else 0,
                        'removed_fields': change_summary.get('removed', 0) if isinstance(change_summary, dict) else 0,
                        'type_changed_fields': change_summary.get('type_changed', 0) if isinstance(change_summary, dict) else 0,
                        'submission_method': entry.get('submission_method', '')
                    }
                    flattened_data.append(flat_entry)
                
                # Convert to DataFrame and then CSV
                if flattened_data:
                    df = pd.DataFrame(flattened_data)
                    csv_data = df.to_csv(index=False)
                    logger.info(f"Successfully generated CSV with {len(flattened_data)} rows")
                    return csv_data
                else:
                    logger.warning("No data to export after flattening")
                    return None
            
            elif format == 'json':
                import json
                # Clean up entries for JSON serialization
                clean_entries = []
                for entry in entries:
                    # Create a clean copy of the entry
                    clean_entry = {}
                    for key, value in entry.items():
                        try:
                            # Test if value is JSON serializable
                            json.dumps(value, default=str)
                            clean_entry[key] = value
                        except (TypeError, ValueError):
                            # Convert problematic values to strings
                            clean_entry[key] = str(value)
                    clean_entries.append(clean_entry)
                
                json_data = json.dumps(clean_entries, indent=2, default=str)
                logger.info(f"Successfully generated JSON with {len(clean_entries)} entries")
                return json_data
            
            else:
                logger.error(f"Unsupported export format: {format}")
                return None
        
        except Exception as e:
            logger.error(f"Error exporting audit data: {e}", exc_info=True)
            return None


# Convenience functions
def render_audit_view():
    """Render the audit view."""
    AuditView.render()


def render_audit_sidebar():
    """Render audit sidebar."""
    AuditView.render_audit_sidebar()