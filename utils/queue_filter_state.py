"""
Enhanced state management for queue view filters with backward compatibility.
Provides type-safe filter state with auto-adjusting sort orders and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging

from .queue_filter_config import QueueFilterConfig

logger = logging.getLogger(__name__)


@dataclass
class QueueFilterState:
    """Type-safe representation of queue filter state with enhanced UX features.
    
    This class provides:
    - Auto-adjusting sort orders based on field type for better UX
    - Date filter state properties and validation
    - Session state conversion methods for backward compatibility
    - Validation with graceful degradation for invalid settings
    """
    
    # Core filter properties
    sort_by: str = 'created_at'
    sort_order: str = 'desc'  # Will be auto-adjusted in __post_init__
    
    # Date filter properties
    date_preset: str = 'all'
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    
    # Internal validation flag
    _validated: bool = field(default=False, init=False)
    
    def __post_init__(self):
        """Auto-adjust sort order based on field type for better UX and validate settings."""
        # Auto-adjust sort order based on field type if not already validated
        if not self._validated:
            self._auto_adjust_sort_order()
            self._validate_and_sanitize()
            self._validated = True
    
    def _auto_adjust_sort_order(self):
        """Auto-adjust sort order based on field type for optimal UX."""
        if self.sort_by in QueueFilterConfig.SORT_FIELDS:
            default_order = QueueFilterConfig.get_default_sort_order(self.sort_by)
            
            # Only auto-adjust if current order is invalid or if we're using defaults
            if self.sort_order not in ['asc', 'desc']:
                self.sort_order = default_order
                logger.debug(f"Auto-adjusted sort order to '{default_order}' for field '{self.sort_by}'")
    
    def _validate_and_sanitize(self):
        """Validate and sanitize all filter settings with graceful degradation."""
        # Validate sort_by
        if not QueueFilterConfig.validate_sort_field(self.sort_by):
            logger.warning(f"Invalid sort field '{self.sort_by}', falling back to 'created_at'")
            self.sort_by = 'created_at'
            self.sort_order = QueueFilterConfig.get_default_sort_order(self.sort_by)
        
        # Validate sort_order
        if not QueueFilterConfig.validate_sort_order(self.sort_order):
            logger.warning(f"Invalid sort order '{self.sort_order}', using default for field '{self.sort_by}'")
            self.sort_order = QueueFilterConfig.get_default_sort_order(self.sort_by)
        
        # Validate date_preset
        if not QueueFilterConfig.validate_date_preset(self.date_preset):
            logger.warning(f"Invalid date preset '{self.date_preset}', falling back to 'all'")
            self.date_preset = 'all'
            self.date_start = None
            self.date_end = None
        
        # Validate date range consistency
        if self.date_preset == 'custom':
            if self.date_start and self.date_end and self.date_start > self.date_end:
                logger.warning("Invalid date range: start date is after end date, clearing custom dates")
                self.date_start = None
                self.date_end = None
        elif self.date_preset != 'all':
            # Clear custom dates if not using custom preset
            if self.date_start or self.date_end:
                logger.debug(f"Clearing custom dates for preset '{self.date_preset}'")
                self.date_start = None
                self.date_end = None
    
    def to_session_dict(self) -> Dict[str, Any]:
        """Convert to session state format for backward compatibility.
        
        Returns:
            Dictionary compatible with existing session state structure
        """
        result = {
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'date_preset': self.date_preset
        }
        
        # Include custom dates if present
        if self.date_start:
            result['date_start'] = self.date_start.isoformat()
        if self.date_end:
            result['date_end'] = self.date_end.isoformat()
        
        return result
    
    @classmethod
    def from_session_dict(cls, session_dict: Dict[str, Any]) -> 'QueueFilterState':
        """Create from session state with validation and smart defaults.
        
        Args:
            session_dict: Dictionary from session state (may contain legacy formats)
            
        Returns:
            Validated QueueFilterState instance with appropriate defaults
        """
        # Parse dates if present
        date_start = None
        date_end = None
        
        if session_dict.get('date_start'):
            try:
                date_start_value = session_dict['date_start']
                if isinstance(date_start_value, str):
                    date_start = datetime.fromisoformat(date_start_value)
                elif isinstance(date_start_value, datetime):
                    date_start = date_start_value
                elif isinstance(date_start_value, date):
                    # Convert date to datetime (start of day)
                    date_start = datetime.combine(date_start_value, datetime.min.time())
                else:
                    raise ValueError(f"Unsupported date_start type: {type(date_start_value)}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date_start format: {e}")
        
        if session_dict.get('date_end'):
            try:
                date_end_value = session_dict['date_end']
                if isinstance(date_end_value, str):
                    date_end = datetime.fromisoformat(date_end_value)
                elif isinstance(date_end_value, datetime):
                    date_end = date_end_value
                elif isinstance(date_end_value, date):
                    # Convert date to datetime (end of day)
                    date_end = datetime.combine(date_end_value, datetime.max.time())
                else:
                    raise ValueError(f"Unsupported date_end type: {type(date_end_value)}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date_end format: {e}")
        
        # Create instance with validation (ignoring any legacy file_type values)
        return cls(
            sort_by=session_dict.get('sort_by', 'created_at'),
            sort_order=session_dict.get('sort_order', 'desc'),  # Will be auto-adjusted in __post_init__
            date_preset=session_dict.get('date_preset', 'all'),
            date_start=date_start,
            date_end=date_end
        )
    
    @classmethod
    def create_default(cls) -> 'QueueFilterState':
        """Create a default filter state with optimal settings.
        
        Returns:
            QueueFilterState with sensible defaults
        """
        return cls(
            sort_by='created_at',
            sort_order='desc',  # Newest first by default
            date_preset='all'
        )
    
    def update_sort_field(self, new_sort_by: str) -> 'QueueFilterState':
        """Update sort field and auto-adjust sort order for optimal UX.
        
        Args:
            new_sort_by: New sort field name
            
        Returns:
            New QueueFilterState instance with updated sort settings
        """
        # Validate the new sort field
        if not QueueFilterConfig.validate_sort_field(new_sort_by):
            logger.warning(f"Invalid sort field '{new_sort_by}', keeping current field '{self.sort_by}'")
            return self
        
        # Create new instance with auto-adjusted sort order
        return QueueFilterState(
            sort_by=new_sort_by,
            sort_order=QueueFilterConfig.get_default_sort_order(new_sort_by),
            date_preset=self.date_preset,
            date_start=self.date_start,
            date_end=self.date_end
        )
    

    
    def update_date_filter(self, new_preset: str, start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> 'QueueFilterState':
        """Update date filter settings with validation.
        
        Args:
            new_preset: New date preset key
            start_date: Custom start date (used when preset is 'custom')
            end_date: Custom end date (used when preset is 'custom')
            
        Returns:
            New QueueFilterState instance with updated date filter
        """
        # Validate the new preset
        if not QueueFilterConfig.validate_date_preset(new_preset):
            logger.warning(f"Invalid date preset '{new_preset}', keeping current preset '{self.date_preset}'")
            return self
        
        # Handle custom date validation
        if new_preset == 'custom':
            if start_date and end_date and start_date > end_date:
                logger.warning("Invalid custom date range: start date is after end date")
                start_date = None
                end_date = None
        else:
            # Clear custom dates for non-custom presets
            start_date = None
            end_date = None
        
        return QueueFilterState(
            sort_by=self.sort_by,
            sort_order=self.sort_order,
            date_preset=new_preset,
            date_start=start_date,
            date_end=end_date
        )
    
    def get_display_summary(self) -> str:
        """Get a human-readable summary of current filter settings.
        
        Returns:
            String describing the current filter state
        """
        parts = []
        
        # Sort description
        sort_config = QueueFilterConfig.get_sort_field_config(self.sort_by)
        sort_label = sort_config['label']
        order_labels = sort_config['order_labels']
        order_label = order_labels[0] if self.sort_order == 'asc' else order_labels[1]
        parts.append(f"Sorted by {sort_label} ({order_label})")
        
        # Date description
        if self.date_preset != 'all':
            if self.date_preset == 'custom' and (self.date_start or self.date_end):
                if self.date_start and self.date_end:
                    parts.append(f"Date: {self.date_start.strftime('%Y-%m-%d')} to {self.date_end.strftime('%Y-%m-%d')}")
                elif self.date_start:
                    parts.append(f"Date: From {self.date_start.strftime('%Y-%m-%d')}")
                elif self.date_end:
                    parts.append(f"Date: Until {self.date_end.strftime('%Y-%m-%d')}")
            else:
                preset_config = QueueFilterConfig.get_date_preset_config(self.date_preset)
                parts.append(f"Date: {preset_config['label']}")
        
        return " • ".join(parts) if parts else "Default filters"
    
    def is_default_state(self) -> bool:
        """Check if this represents the default filter state.
        
        Returns:
            True if all settings are at their defaults
        """
        default_state = self.create_default()
        return (
            self.sort_by == default_state.sort_by and
            self.sort_order == default_state.sort_order and
            self.date_preset == default_state.date_preset and
            self.date_start is None and
            self.date_end is None
        )
    
    def reset_to_defaults(self) -> 'QueueFilterState':
        """Reset all filter settings to defaults.
        
        Returns:
            New QueueFilterState instance with default settings
        """
        return self.create_default()


def get_filter_state_from_session() -> QueueFilterState:
    """Extract filter state from Streamlit session state with validation.
    
    Returns:
        Validated QueueFilterState instance
    """
    import streamlit as st
    
    # Get existing filters from session state
    session_filters = st.session_state.get('queue_filters', {})
    
    # Create filter state from session data
    filter_state = QueueFilterState.from_session_dict(session_filters)
    
    return filter_state


def save_filter_state_to_session(filter_state: QueueFilterState):
    """Save filter state to Streamlit session state for backward compatibility.
    
    Args:
        filter_state: QueueFilterState instance to save
    """
    import streamlit as st
    
    # Convert to session format and save
    st.session_state.queue_filters = filter_state.to_session_dict()


def migrate_legacy_session_state() -> QueueFilterState:
    """Migrate legacy session state formats to new QueueFilterState.
    
    This function handles various legacy formats that might exist in session state
    and converts them to the new enhanced format.
    
    Returns:
        Migrated QueueFilterState instance
    """
    import streamlit as st
    
    # Check for various legacy session state keys
    legacy_keys = [
        'queue_sort_by',
        'queue_sort_order', 
        'queue_file_type_filter',  # Will be ignored but cleaned up
        'queue_date_preset',
        'queue_date_start',
        'queue_date_end'
    ]
    
    # Build session dict from individual keys if they exist
    session_dict = {}
    
    if 'queue_filters' in st.session_state:
        # Use existing consolidated filters (ignoring any file_type)
        session_dict = st.session_state.queue_filters.copy()
        # Remove file_type if it exists in the consolidated format
        session_dict.pop('file_type', None)
    else:
        # Migrate from individual keys (excluding file_type)
        if 'queue_sort_by' in st.session_state:
            session_dict['sort_by'] = st.session_state.queue_sort_by
        if 'queue_sort_order' in st.session_state:
            session_dict['sort_order'] = st.session_state.queue_sort_order
        # Skip queue_file_type_filter - no longer needed
        if 'queue_date_preset' in st.session_state:
            session_dict['date_preset'] = st.session_state.queue_date_preset
        if 'queue_date_start' in st.session_state:
            session_dict['date_start'] = st.session_state.queue_date_start
        if 'queue_date_end' in st.session_state:
            session_dict['date_end'] = st.session_state.queue_date_end
    
    # Create validated filter state
    filter_state = QueueFilterState.from_session_dict(session_dict)
    
    # Save back to session state in consolidated format
    save_filter_state_to_session(filter_state)
    
    # Clean up legacy individual keys
    for key in legacy_keys:
        if key in st.session_state:
            del st.session_state[key]
            logger.debug(f"Cleaned up legacy session key: {key}")
    
    return filter_state


class FilterStateValidator:
    """Advanced validation and migration logic for filter settings."""
    
    @staticmethod
    def validate_filter_settings_comprehensive(settings: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive validation with detailed error reporting and graceful degradation.
        
        Args:
            settings: Raw filter settings dictionary
            
        Returns:
            Validated and sanitized settings dictionary
        """
        validated = {}
        validation_errors = []
        
        # Validate sort_by with detailed error handling
        sort_by = settings.get('sort_by', 'created_at')
        if QueueFilterConfig.validate_sort_field(sort_by):
            validated['sort_by'] = sort_by
        else:
            validation_errors.append(f"Invalid sort field '{sort_by}', using 'created_at'")
            validated['sort_by'] = 'created_at'
        
        # Validate sort_order with field-specific defaults
        sort_order = settings.get('sort_order', 'desc')
        if QueueFilterConfig.validate_sort_order(sort_order):
            validated['sort_order'] = sort_order
        else:
            default_order = QueueFilterConfig.get_default_sort_order(validated['sort_by'])
            validation_errors.append(f"Invalid sort order '{sort_order}', using '{default_order}' for field '{validated['sort_by']}'")
            validated['sort_order'] = default_order
        
        # Skip file_type validation - no longer used in single schema workflow
        if 'file_type' in settings:
            logger.debug("Ignoring legacy file_type setting in single schema workflow")
        
        # Validate date_preset
        date_preset = settings.get('date_preset', 'all')
        if QueueFilterConfig.validate_date_preset(date_preset):
            validated['date_preset'] = date_preset
        else:
            validation_errors.append(f"Invalid date preset '{date_preset}', using 'all'")
            validated['date_preset'] = 'all'
        
        # Validate custom dates with comprehensive error handling
        date_start = None
        date_end = None
        
        if settings.get('date_start'):
            try:
                date_start_value = settings['date_start']
                if isinstance(date_start_value, str):
                    date_start = datetime.fromisoformat(date_start_value)
                elif isinstance(date_start_value, datetime):
                    date_start = date_start_value
                elif isinstance(date_start_value, date):
                    # Convert date to datetime (start of day)
                    date_start = datetime.combine(date_start_value, datetime.min.time())
                else:
                    raise ValueError(f"Unsupported date_start type: {type(date_start_value)}")
            except (ValueError, TypeError) as e:
                validation_errors.append(f"Invalid date_start format: {e}")
        
        if settings.get('date_end'):
            try:
                date_end_value = settings['date_end']
                if isinstance(date_end_value, str):
                    date_end = datetime.fromisoformat(date_end_value)
                elif isinstance(date_end_value, datetime):
                    date_end = date_end_value
                elif isinstance(date_end_value, date):
                    # Convert date to datetime (end of day)
                    date_end = datetime.combine(date_end_value, datetime.max.time())
                else:
                    raise ValueError(f"Unsupported date_end type: {type(date_end_value)}")
            except (ValueError, TypeError) as e:
                validation_errors.append(f"Invalid date_end format: {e}")
        
        # Validate date range consistency
        if date_start and date_end:
            if date_start > date_end:
                validation_errors.append("Invalid date range: start date is after end date, clearing dates")
                date_start = None
                date_end = None
        
        # Handle date preset and custom date consistency
        if validated['date_preset'] == 'custom':
            validated['date_start'] = date_start
            validated['date_end'] = date_end
        else:
            # Clear custom dates for non-custom presets
            validated['date_start'] = None
            validated['date_end'] = None
            if date_start or date_end:
                logger.debug(f"Cleared custom dates for preset '{validated['date_preset']}'")
        
        # Log validation errors if any
        if validation_errors:
            logger.warning(f"Filter validation errors: {'; '.join(validation_errors)}")
        
        return validated
    
    @staticmethod
    def detect_session_state_format(session_state: Dict[str, Any]) -> str:
        """Detect the format of session state data for appropriate migration.
        
        Args:
            session_state: Raw session state dictionary
            
        Returns:
            Format identifier ('consolidated', 'individual_keys', 'mixed', 'empty')
        """
        has_consolidated = 'queue_filters' in session_state
        
        individual_keys = [
            'queue_sort_by', 'queue_sort_order', 'queue_file_type_filter',  # file_type_filter will be ignored
            'queue_date_preset', 'queue_date_start', 'queue_date_end'
        ]
        has_individual = any(key in session_state for key in individual_keys)
        
        if has_consolidated and has_individual:
            return 'mixed'
        elif has_consolidated:
            return 'consolidated'
        elif has_individual:
            return 'individual_keys'
        else:
            return 'empty'
    
    @staticmethod
    def migrate_session_state_format(session_state: Dict[str, Any]) -> QueueFilterState:
        """Migrate session state from any format to QueueFilterState.
        
        Args:
            session_state: Raw session state dictionary
            
        Returns:
            Migrated and validated QueueFilterState
        """
        format_type = FilterStateValidator.detect_session_state_format(session_state)
        logger.debug(f"Detected session state format: {format_type}")
        
        session_dict = {}
        
        if format_type == 'consolidated':
            session_dict = session_state.get('queue_filters', {}).copy()
        
        elif format_type == 'individual_keys':
            # Migrate from individual keys (excluding file_type)
            key_mapping = {
                'queue_sort_by': 'sort_by',
                'queue_sort_order': 'sort_order',
                # Skip 'queue_file_type_filter' - no longer needed
                'queue_date_preset': 'date_preset',
                'queue_date_start': 'date_start',
                'queue_date_end': 'date_end'
            }
            
            for old_key, new_key in key_mapping.items():
                if old_key in session_state:
                    session_dict[new_key] = session_state[old_key]
        
        elif format_type == 'mixed':
            # Prefer consolidated format, but merge individual keys if they're newer
            session_dict = session_state.get('queue_filters', {}).copy()
            # Remove file_type if it exists in consolidated format
            session_dict.pop('file_type', None)
            
            # Override with individual keys (assuming they might be more recent, excluding file_type)
            key_mapping = {
                'queue_sort_by': 'sort_by',
                'queue_sort_order': 'sort_order', 
                # Skip 'queue_file_type_filter' - no longer needed
                'queue_date_preset': 'date_preset',
                'queue_date_start': 'date_start',
                'queue_date_end': 'date_end'
            }
            
            for old_key, new_key in key_mapping.items():
                if old_key in session_state:
                    session_dict[new_key] = session_state[old_key]
                    logger.debug(f"Merged individual key '{old_key}' into consolidated format")
        
        else:  # empty
            logger.debug("No existing filter state found, using defaults")
        
        # Validate and create filter state
        validated_dict = FilterStateValidator.validate_filter_settings_comprehensive(session_dict)
        filter_state = QueueFilterState.from_session_dict(validated_dict)
        
        return filter_state
    
    @staticmethod
    def create_fallback_state(error_context: str = "") -> QueueFilterState:
        """Create a safe fallback filter state when all else fails.
        
        Args:
            error_context: Context information about what caused the fallback
            
        Returns:
            Safe default QueueFilterState
        """
        logger.warning(f"Creating fallback filter state due to: {error_context}")
        return QueueFilterState.create_default()
    
    @staticmethod
    def validate_state_consistency(filter_state: QueueFilterState) -> bool:
        """Validate that a filter state is internally consistent.
        
        Args:
            filter_state: QueueFilterState to validate
            
        Returns:
            True if state is consistent, False otherwise
        """
        try:
            # Check that all fields are valid
            if not QueueFilterConfig.validate_sort_field(filter_state.sort_by):
                return False
            
            if not QueueFilterConfig.validate_sort_order(filter_state.sort_order):
                return False
            
            # Skip file_type validation - no longer used
            
            if not QueueFilterConfig.validate_date_preset(filter_state.date_preset):
                return False
            
            # Check date consistency
            if filter_state.date_preset == 'custom':
                if filter_state.date_start and filter_state.date_end:
                    if filter_state.date_start > filter_state.date_end:
                        return False
            else:
                # Non-custom presets should not have custom dates
                if filter_state.date_start or filter_state.date_end:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating filter state consistency: {e}")
            return False


def get_validated_filter_state() -> QueueFilterState:
    """Get a validated filter state from session with comprehensive error handling.
    
    This is the main entry point for getting filter state with full validation,
    migration, and fallback support.
    
    Returns:
        Validated QueueFilterState instance
    """
    import streamlit as st
    
    try:
        # Attempt to migrate and validate session state
        filter_state = FilterStateValidator.migrate_session_state_format(st.session_state)
        
        # Double-check consistency
        if not FilterStateValidator.validate_state_consistency(filter_state):
            logger.warning("Filter state failed consistency check, creating fallback")
            filter_state = FilterStateValidator.create_fallback_state("consistency check failed")
        
        # Save validated state back to session
        save_filter_state_to_session(filter_state)
        
        return filter_state
        
    except Exception as e:
        logger.error(f"Error getting validated filter state: {e}")
        return FilterStateValidator.create_fallback_state(f"exception: {e}")


def ensure_filter_state_compatibility():
    """Ensure filter state is compatible with current system requirements.
    
    This function should be called during application startup or when
    filter configuration changes to ensure existing session state remains valid.
    """
    import streamlit as st
    
    try:
        # Get current filter state
        current_state = get_validated_filter_state()
        
        # Check if current sort field is still supported
        if not QueueFilterConfig.validate_sort_field(current_state.sort_by):
            logger.info(f"Sort field '{current_state.sort_by}' no longer supported, resetting to default")
            current_state = current_state.update_sort_field('created_at')
            save_filter_state_to_session(current_state)
        
        # File type filtering removed in single schema workflow - no compatibility check needed
        
        # Check if current date preset is still supported
        if not QueueFilterConfig.validate_date_preset(current_state.date_preset):
            logger.info(f"Date preset '{current_state.date_preset}' no longer supported, resetting to 'all'")
            current_state = current_state.update_date_filter('all')
            save_filter_state_to_session(current_state)
        
        logger.debug("Filter state compatibility check completed successfully")
        
    except Exception as e:
        logger.error(f"Error ensuring filter state compatibility: {e}")
        # Reset to defaults if there's any issue
        default_state = QueueFilterState.create_default()
        save_filter_state_to_session(default_state)