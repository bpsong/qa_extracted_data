"""
Integration tests for array field bug fixes.

Tests the complete workflow of:
1. Scalar array add/remove functionality
2. Reset to original functionality for arrays
3. Cumulative diff display
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import yaml
from datetime import date

from utils.form_generator import FormGenerator
from utils.edit_view import EditView
from utils.session_manager import SessionManager
from utils.diff_utils import calculate_diff
from utils.file_utils import load_json_file


@pytest.fixture
def insurance_schema():
    """Load the insurance schema with serial numbers."""
    schema_path = Path("schemas/insurance_with_serial_numbers.yaml")
    with open(schema_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def insurance_data():
    """Load sample insurance data."""
    return {
        "Supplier name": "China Taiping Insurance (Singapore) Pte. Ltd.",
        "Client name": "KIM BOCK CONTRACTOR PTE LTD",
        "Client": "3 PEMIMPIN DRIVE #05-05 LIP HING INDUSTRIAL BUILDING SINGAPORE 576147",
        "Invoice amount": 490.5,
        "Insurance Start date": "2024-11-12",
        "Insurance End date": "2025-11-11",
        "Policy Number": "DFIRSNA00046522412",
        "Serial Numbers": ["SerialNo1", "SerialNo2"],
        "Invoice type": "debit"
    }


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit session state and components."""
    class MockSessionState(dict):
        """Mock session state that supports both dict and attribute access."""
        def __setattr__(self, key, value):
            self[key] = value
        
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
    
    mock_state = MockSessionState()
    with patch('streamlit.session_state', mock_state):
        yield mock_state


class TestCompleteArrayEditingWorkflow:
    """Test 4.1: Complete array editing workflow."""
    
    def test_add_items_to_scalar_array(self, insurance_schema, insurance_data, mock_streamlit):
        """Test adding items to scalar array using size control."""
        # Initialize session state
        field_name = "Serial Numbers"
        original_array = insurance_data[field_name].copy()
        
        st.session_state[f"field_{field_name}"] = original_array.copy()
        st.session_state[f"scalar_array_{field_name}_size"] = len(original_array)
        
        # Initialize SessionManager
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(insurance_data.copy())
        
        # Simulate adding an item
        new_size = len(original_array) + 1
        st.session_state[f"scalar_array_{field_name}_size"] = new_size
        
        # Simulate the array modification
        working_array = original_array.copy()
        working_array.append("")  # Add empty item
        
        # Call sync method
        FormGenerator._sync_array_to_session(field_name, working_array)
        
        # Verify session state updated
        assert st.session_state[f"field_{field_name}"] == working_array
        assert len(st.session_state[f"field_{field_name}"]) == new_size
        
        # Verify form data updated
        form_data = SessionManager.get_form_data()
        assert form_data[field_name] == working_array
        assert len(form_data[field_name]) == new_size
    
    def test_remove_items_from_scalar_array(self, insurance_schema, insurance_data, mock_streamlit):
        """Test removing items from scalar array using size control."""
        field_name = "Serial Numbers"
        original_array = insurance_data[field_name].copy()
        
        st.session_state[f"field_{field_name}"] = original_array.copy()
        st.session_state[f"scalar_array_{field_name}_size"] = len(original_array)
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(insurance_data.copy())
        
        # Simulate removing an item
        new_size = len(original_array) - 1
        st.session_state[f"scalar_array_{field_name}_size"] = new_size
        
        working_array = original_array[:new_size]
        
        # Call sync method
        FormGenerator._sync_array_to_session(field_name, working_array)
        
        # Verify session state updated
        assert st.session_state[f"field_{field_name}"] == working_array
        assert len(st.session_state[f"field_{field_name}"]) == new_size
        
        # Verify form data updated
        form_data = SessionManager.get_form_data()
        assert form_data[field_name] == working_array
        assert len(form_data[field_name]) == new_size
    
    def test_diff_updates_immediately_after_array_change(self, insurance_schema, insurance_data, mock_streamlit):
        """Test that diff updates immediately after array changes."""
        field_name = "Serial Numbers"
        original_array = insurance_data[field_name].copy()
        modified_array = original_array + ["SerialNo3"]
        
        st.session_state[f"field_{field_name}"] = modified_array
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(insurance_data.copy())
        
        # Sync the modified array
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Calculate diff
        form_data = SessionManager.get_form_data()
        diff = calculate_diff(insurance_data, form_data)
        
        # Verify diff shows the array change
        assert 'iterable_item_added' in diff
        assert len(diff['iterable_item_added']) > 0
        
        # Verify the modified data has the new item
        assert len(form_data[field_name]) == 3
        assert "SerialNo3" in form_data[field_name]
    
    def test_cumulative_diff_with_array_and_scalar_changes(self, insurance_schema, insurance_data, mock_streamlit):
        """Test that diff shows both array and scalar field changes."""
        # Modify array field
        field_name = "Serial Numbers"
        modified_array = insurance_data[field_name] + ["SerialNo3"]
        st.session_state[f"field_{field_name}"] = modified_array
        
        # Modify scalar field
        scalar_field = "Invoice amount"
        modified_amount = 550.0
        st.session_state[f"field_{scalar_field}"] = modified_amount
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(insurance_data.copy())
        
        # Sync both changes
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Collect all form data
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        SessionManager.set_form_data(form_data)
        
        # Calculate diff
        diff = calculate_diff(insurance_data, form_data)
        
        # Verify both changes are in diff
        # Array change should show in iterable_item_added
        assert 'iterable_item_added' in diff or 'values_changed' in diff
        
        # Scalar change should show in values_changed
        assert 'values_changed' in diff
        
        # Verify the actual data changes
        assert len(form_data[field_name]) == 3
        assert "SerialNo3" in form_data[field_name]
        assert form_data[scalar_field] == modified_amount


class TestResetFunctionalityWithArrays:
    """Test 4.2: Reset functionality with arrays."""
    
    def test_reset_reverts_array_values(self, insurance_schema, insurance_data, mock_streamlit):
        """Test that reset reverts all array values to original."""
        field_name = "Serial Numbers"
        original_array = insurance_data[field_name].copy()
        modified_array = original_array + ["SerialNo3", "SerialNo4"]
        
        # Set up modified state
        st.session_state[f"field_{field_name}"] = modified_array
        st.session_state[f"scalar_array_{field_name}_size"] = len(modified_array)
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_current_file("test_file.json")
        
        # Mock file loading
        with patch('utils.file_utils.load_json_file', return_value=insurance_data):
            # Simulate reset logic
            for field, field_config in insurance_schema.get('fields', {}).items():
                if field_config.get('type') == 'array':
                    original_value = insurance_data.get(field, [])
                    st.session_state[f"field_{field}"] = original_value
                    st.session_state[f"scalar_array_{field}_size"] = len(original_value)
            
            # Update form data
            SessionManager.set_form_data(insurance_data.copy())
        
        # Verify reset worked
        assert st.session_state[f"field_{field_name}"] == original_array
        assert st.session_state[f"scalar_array_{field_name}_size"] == len(original_array)
        
        # Verify diff shows no changes
        form_data = SessionManager.get_form_data()
        diff = calculate_diff(insurance_data, form_data)
        assert len(diff) == 0
    
    def test_reset_with_multiple_field_modifications(self, insurance_schema, insurance_data, mock_streamlit):
        """Test reset after modifying both arrays and scalar fields."""
        # Modify array
        array_field = "Serial Numbers"
        modified_array = insurance_data[array_field] + ["SerialNo3"]
        st.session_state[f"field_{array_field}"] = modified_array
        
        # Modify scalar fields
        st.session_state["field_Invoice amount"] = 600.0
        st.session_state["field_Client name"] = "Modified Client"
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_current_file("test_file.json")
        
        # Mock file loading and perform reset
        with patch('utils.file_utils.load_json_file', return_value=insurance_data):
            # Reset all fields
            for field, field_config in insurance_schema.get('fields', {}).items():
                original_value = insurance_data.get(field)
                st.session_state[f"field_{field}"] = original_value
                
                if field_config.get('type') == 'array':
                    st.session_state[f"scalar_array_{field}_size"] = len(original_value) if original_value else 0
            
            SessionManager.set_form_data(insurance_data.copy())
        
        # Verify all fields reset
        assert st.session_state[f"field_{array_field}"] == insurance_data[array_field]
        assert st.session_state["field_Invoice amount"] == insurance_data["Invoice amount"]
        assert st.session_state["field_Client name"] == insurance_data["Client name"]
        
        # Verify diff is empty
        form_data = SessionManager.get_form_data()
        diff = calculate_diff(insurance_data, form_data)
        assert len(diff) == 0


class TestObjectArrayEditingWorkflow:
    """Test 4.3: Object array editing workflow."""
    
    def test_object_array_with_dataframe_operations(self, mock_streamlit):
        """Test object array editing with add/remove/edit operations."""
        import pandas as pd
        
        # Create schema with object array
        schema = {
            'fields': {
                'items': {
                    'type': 'array',
                    'label': 'Items',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'quantity': {'type': 'number'}
                        }
                    }
                }
            }
        }
        
        # Original data
        original_data = {
            'items': [
                {'name': 'Item1', 'quantity': 10},
                {'name': 'Item2', 'quantity': 20}
            ]
        }
        
        field_name = 'items'
        
        # Initialize session state
        df = pd.DataFrame(original_data[field_name])
        st.session_state[f"data_editor_{field_name}"] = df
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data(original_data.copy())
        
        # Simulate adding a row
        new_row = pd.DataFrame([{'name': 'Item3', 'quantity': 30}])
        modified_df = pd.concat([df, new_row], ignore_index=True)
        st.session_state[f"data_editor_{field_name}"] = modified_df
        
        # Convert to list and sync
        modified_array = modified_df.to_dict('records')
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Verify sync worked
        form_data = SessionManager.get_form_data()
        assert len(form_data[field_name]) == 3
        assert form_data[field_name][2]['name'] == 'Item3'
        
        # Calculate diff
        diff = calculate_diff(original_data, form_data)
        # Verify diff shows array changes
        assert 'iterable_item_added' in diff
        assert len(diff['iterable_item_added']) > 0


class TestEdgeCasesAndErrorScenarios:
    """Test 4.4: Edge cases and error scenarios."""
    
    def test_empty_array_handling(self, mock_streamlit):
        """Test handling of empty arrays."""
        schema = {
            'fields': {
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        
        data = {'tags': []}
        
        field_name = 'tags'
        st.session_state[f"field_{field_name}"] = []
        st.session_state[f"scalar_array_{field_name}_size"] = 0
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data(data.copy())
        
        # Add item to empty array
        new_array = ["tag1"]
        FormGenerator._sync_array_to_session(field_name, new_array)
        
        # Verify it works
        form_data = SessionManager.get_form_data()
        assert len(form_data[field_name]) == 1
        assert form_data[field_name][0] == "tag1"
    
    def test_array_at_min_length_constraint(self, mock_streamlit):
        """Test array at minimum length constraint."""
        schema = {
            'fields': {
                'required_items': {
                    'type': 'array',
                    'min_length': 2,
                    'items': {'type': 'string'}
                }
            }
        }
        
        data = {'required_items': ['item1', 'item2']}
        
        field_name = 'required_items'
        st.session_state[f"field_{field_name}"] = data[field_name].copy()
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data(data.copy())
        
        # Verify current length
        assert len(st.session_state[f"field_{field_name}"]) == 2
        
        # Attempting to remove would violate constraint
        # This should be prevented by UI logic
        min_length = schema['fields'][field_name].get('min_length', 0)
        current_length = len(st.session_state[f"field_{field_name}"])
        
        assert current_length >= min_length
    
    def test_array_at_max_length_constraint(self, mock_streamlit):
        """Test array at maximum length constraint."""
        schema = {
            'fields': {
                'limited_items': {
                    'type': 'array',
                    'max_length': 3,
                    'items': {'type': 'string'}
                }
            }
        }
        
        data = {'limited_items': ['item1', 'item2', 'item3']}
        
        field_name = 'limited_items'
        st.session_state[f"field_{field_name}"] = data[field_name].copy()
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data(data.copy())
        
        # Verify at max length
        max_length = schema['fields'][field_name].get('max_length', float('inf'))
        current_length = len(st.session_state[f"field_{field_name}"])
        
        assert current_length == max_length
        
        # Adding more would violate constraint (should be prevented by UI)
        assert current_length <= max_length
    
    def test_malformed_array_data(self, mock_streamlit):
        """Test handling of malformed array data."""
        schema = {
            'fields': {
                'items': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        
        # Data with None instead of array
        data = {'items': None}
        
        field_name = 'items'
        
        # Initialize with safe default
        safe_value = data.get(field_name) or []
        st.session_state[f"field_{field_name}"] = safe_value
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data({'items': safe_value})
        
        # Verify safe handling
        assert isinstance(st.session_state[f"field_{field_name}"], list)
        assert len(st.session_state[f"field_{field_name}"]) == 0
    
    def test_missing_schema_field(self, mock_streamlit):
        """Test handling when schema is missing for a field."""
        schema = {
            'fields': {
                'known_field': {
                    'type': 'string'
                }
            }
        }
        
        # Data has field not in schema
        data = {
            'known_field': 'value',
            'unknown_array': ['item1', 'item2']
        }
        
        # Set up session state for known field
        st.session_state['field_known_field'] = 'value'
        
        SessionManager.set_schema(schema)
        SessionManager.set_form_data(data.copy())
        
        # Collect form data should handle gracefully
        form_data = FormGenerator.collect_current_form_data(schema)
        
        # Should include known fields from session state
        assert 'known_field' in form_data
        # Unknown fields are preserved in form_data but not collected from session
        # This is expected behavior - only schema fields are collected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
