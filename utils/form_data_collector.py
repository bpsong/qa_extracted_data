"""
Simplified form data collection for JSON QA webapp.
Collects current values from ALL widgets in session state.
"""

import streamlit as st
import logging
from typing import Dict, Any
from datetime import date, datetime

logger = logging.getLogger(__name__)


def collect_all_form_data(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect current form values from ALL widgets in session state.
    
    SIMPLE RULE: Every widget stores its value in field_{field_name}_v{form_version}.
    We just read those values directly.
    
    Args:
        schema: Schema definition containing field configurations
        
    Returns:
        Dictionary of current form data with all field values
    """
    form_data = {}
    fields = schema.get('fields', {})
    
    # Get current form version
    form_version = st.session_state.get('form_version', 0)
    
    logger.info("[SIMPLIFIED COLLECTOR] === COLLECTING ALL FORM DATA ===")
    logger.info(f"[SIMPLIFIED COLLECTOR] Form version: {form_version}")
    
    for field_name, field_config in fields.items():
        field_type = field_config.get('type', 'string')
        field_key = f"field_{field_name}_v{form_version}"
        
        # Check if widget value exists
        if field_key not in st.session_state:
            logger.warning(f"[SIMPLIFIED COLLECTOR] Missing widget value for: {field_name}")
            # Use default based on type
            if field_type == 'array':
                form_data[field_name] = []
            elif field_type == 'object':
                form_data[field_name] = {}
            else:
                form_data[field_name] = None
            continue
        
        value = st.session_state[field_key]
        
        # Handle arrays (both scalar and object)
        if field_type == 'array':
            items_config = field_config.get('items', {})
            item_type = items_config.get('type', 'string')
            
            # For object arrays, read from the _current key (edited DataFrame)
            if item_type == 'object':
                array_key = f'array_{field_name}_v{form_version}'
                current_key = f'{array_key}_current'
                
                if current_key in st.session_state:
                    # Use the edited DataFrame stored during rendering
                    edited_df = st.session_state[current_key]
                    if hasattr(edited_df, 'to_dict'):
                        records = edited_df.to_dict('records')
                        properties = items_config.get("properties", {})
                        cleaned = _clean_object_array(records, properties)
                        logger.info(f"[SIMPLIFIED COLLECTOR] Object array {field_name}: {len(cleaned)} objects from _current")
                        if cleaned:
                            logger.info(f"[SIMPLIFIED COLLECTOR]   First: {cleaned[0]}")
                        form_data[field_name] = cleaned
                    else:
                        logger.warning(f"[SIMPLIFIED COLLECTOR] {current_key} is not a DataFrame: {type(edited_df)}")
                        form_data[field_name] = []
                elif field_key in st.session_state and isinstance(st.session_state[field_key], list):
                    # Fallback to field key if _current not available
                    value = st.session_state[field_key]
                    properties = items_config.get("properties", {})
                    cleaned = _clean_object_array(value, properties)
                    logger.info(f"[SIMPLIFIED COLLECTOR] Object array {field_name}: {len(cleaned)} objects from field_key")
                    form_data[field_name] = cleaned
                else:
                    logger.warning(f"[SIMPLIFIED COLLECTOR] No data found for object array {field_name}")
                    form_data[field_name] = []
                continue
            
            # For scalar arrays, use the field_key directly
            if not isinstance(value, list):
                logger.warning(f"[SIMPLIFIED COLLECTOR] Scalar array {field_name} has non-list value: {type(value)}")
                form_data[field_name] = []
                continue
            
            logger.info(f"[SIMPLIFIED COLLECTOR] Scalar array {field_name}: {len(value)} items")
            form_data[field_name] = value
        
        # Handle objects
        elif field_type == 'object':
            if isinstance(value, dict):
                form_data[field_name] = value
            else:
                logger.warning(f"[SIMPLIFIED COLLECTOR] Object {field_name} has non-dict value: {type(value)}")
                form_data[field_name] = {}
        
        # Handle dates - convert to strings for JSON serialization
        elif field_type == 'date':
            if isinstance(value, date):
                form_data[field_name] = value.strftime("%Y-%m-%d")
            elif isinstance(value, str):
                form_data[field_name] = value
            else:
                form_data[field_name] = None
        
        # Handle datetimes - convert to ISO strings
        elif field_type == 'datetime':
            if isinstance(value, datetime):
                form_data[field_name] = value.isoformat()
            elif isinstance(value, str):
                form_data[field_name] = value
            else:
                form_data[field_name] = None
        
        # Handle all other scalar types
        else:
            logger.debug(f"[SIMPLIFIED COLLECTOR] Scalar {field_name}: {value}")
            form_data[field_name] = value
    
    logger.info(f"[SIMPLIFIED COLLECTOR] Collected {len(form_data)} fields")
    return form_data


def _clean_object_array(array: list, properties: Dict[str, Dict[str, Any]]) -> list:
    """Clean object array by removing NaN values and normalizing types."""
    import pandas as pd
    import numpy as np
    
    cleaned_array = []
    for obj in array:
        if not isinstance(obj, dict):
            continue
            
        cleaned_obj = {}
        for key, value in obj.items():
            # Handle pandas NaN values
            if pd.isna(value):
                cleaned_obj[key] = None
            else:
                # Normalize numpy types to Python types
                if isinstance(value, np.bool_):
                    cleaned_obj[key] = bool(value)
                elif isinstance(value, np.integer):
                    cleaned_obj[key] = int(value)
                elif isinstance(value, np.floating):
                    cleaned_obj[key] = float(value)
                else:
                    cleaned_obj[key] = value
        
        # Ensure all schema properties are present
        for prop_name in properties.keys():
            cleaned_obj.setdefault(prop_name, None)
        
        cleaned_array.append(cleaned_obj)
    
    return cleaned_array
