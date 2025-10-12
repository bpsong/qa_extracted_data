"""
Centralized filter configuration system for queue view.
Provides enhanced sort field configurations, document type filters, and date presets.
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta


@dataclass
class QueueFilterConfig:
    """Centralized configuration for queue filters and sorting with enhanced UX."""
    
    # Enhanced sort configurations with context-aware labels and smart defaults
    SORT_FIELDS = {
        'created_at': {
            'label': 'Creation Date',
            'key_func': lambda x: x['created_at'],
            'default_order': 'desc',  # Newest first for dates
            'order_labels': ('Oldest First', 'Newest First')
        },
        'filename': {
            'label': 'File Name',
            'key_func': lambda x: x['filename'],
            'default_order': 'asc',  # A→Z for filenames
            'order_labels': ('A → Z', 'Z → A')
        },
        'size': {
            'label': 'File Size',
            'key_func': lambda x: x['size'],
            'default_order': 'desc',  # Largest first for size
            'order_labels': ('Smallest First', 'Largest First')
        },
        'modified_at': {
            'label': 'Modified Date',
            'key_func': lambda x: x['modified_at'],
            'default_order': 'desc',  # Newest first for dates
            'order_labels': ('Oldest First', 'Newest First')
        }
    }
    

    
    # Date filter presets for UI components
    DATE_FILTER_PRESETS = {
        'all': {
            'label': 'All Time',
            'days': None,
            'description': 'Show files from any date'
        },
        'today': {
            'label': 'Today',
            'days': 0,
            'description': 'Show files created or modified today'
        },
        'week': {
            'label': 'Last 7 days',
            'days': 7,
            'description': 'Show files created or modified in the past 7 days'
        },
        'month': {
            'label': 'Last 30 days',
            'days': 30,
            'description': 'Show files created or modified in the past 30 days'
        },
        'quarter': {
            'label': 'Last 90 days',
            'days': 90,
            'description': 'Show files created or modified in the past 90 days'
        },
        'custom': {
            'label': 'Custom Range',
            'days': None,
            'description': 'Specify a custom date range (creation or modification date)'
        }
    }
    
    @classmethod
    def get_sort_field_config(cls, field_name: str) -> Dict[str, Any]:
        """Get configuration for a specific sort field with fallback to default."""
        return cls.SORT_FIELDS.get(field_name, cls.SORT_FIELDS['created_at'])
    

    
    @classmethod
    def get_date_preset_config(cls, preset_key: str) -> Dict[str, Any]:
        """Get configuration for a specific date preset with fallback to 'all'."""
        return cls.DATE_FILTER_PRESETS.get(preset_key, cls.DATE_FILTER_PRESETS['all'])
    
    @classmethod
    def get_default_sort_order(cls, field_name: str) -> str:
        """Get the default sort order for a given field."""
        config = cls.get_sort_field_config(field_name)
        return config['default_order']
    
    @classmethod
    def get_sort_order_labels(cls, field_name: str) -> tuple:
        """Get the context-aware sort order labels for a given field."""
        config = cls.get_sort_field_config(field_name)
        return config['order_labels']
    
    @classmethod
    def get_sort_key_function(cls, field_name: str) -> Callable:
        """Get the sort key function for a given field."""
        config = cls.get_sort_field_config(field_name)
        return config['key_func']
    
    @classmethod
    def get_available_sort_fields(cls) -> List[str]:
        """Get list of available sort field keys."""
        return list(cls.SORT_FIELDS.keys())
    

    
    @classmethod
    def get_available_date_presets(cls) -> List[str]:
        """Get list of available date preset keys."""
        return list(cls.DATE_FILTER_PRESETS.keys())
    

    
    @classmethod
    def calculate_date_range(cls, preset_key: str, custom_start: Optional[datetime] = None, 
                           custom_end: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
        """Calculate the actual date range for a given preset or custom range."""
        config = cls.get_date_preset_config(preset_key)
        
        if preset_key == 'custom':
            return custom_start, custom_end
        
        if preset_key == 'all':
            return None, None
        
        days = config.get('days')
        if days is None:
            return None, None
        
        end_date = datetime.now()
        
        if days == 0:  # Today
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    @classmethod
    def validate_sort_field(cls, field_name: str) -> bool:
        """Validate if a sort field is supported."""
        return field_name in cls.SORT_FIELDS
    

    
    @classmethod
    def validate_date_preset(cls, preset_key: str) -> bool:
        """Validate if a date preset is supported."""
        return preset_key in cls.DATE_FILTER_PRESETS
    
    @classmethod
    def validate_sort_order(cls, sort_order: str) -> bool:
        """Validate if a sort order is supported."""
        return sort_order in ['asc', 'desc']


# Dictionary-based sort key functions for lookup-based sorting
# This replaces the if/elif chains in the original implementation
SORT_KEY_FUNCTIONS = {
    field_name: config['key_func'] 
    for field_name, config in QueueFilterConfig.SORT_FIELDS.items()
}


def get_sort_key_function(field_name: str) -> Callable:
    """Get sort key function with fallback to default."""
    return SORT_KEY_FUNCTIONS.get(field_name, SORT_KEY_FUNCTIONS['created_at'])


