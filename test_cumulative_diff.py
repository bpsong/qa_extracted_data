"""
Test cumulative diff functionality to ensure all changes are captured.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.diff_utils import calculate_diff, has_changes


def test_diff_includes_array_changes():
    """Test that diff calculation includes array changes."""
    original = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    modified = {
        "name": "John Doe",
        "items": ["item1", "item2", "item3"],  # Array changed
        "amount": 100.0
    }
    
    diff = calculate_diff(original, modified)
    
    # Should detect array changes
    assert has_changes(diff)
    assert 'iterable_item_added' in diff or 'values_changed' in diff


def test_diff_includes_scalar_field_changes():
    """Test that diff calculation includes scalar field changes."""
    original = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    modified = {
        "name": "Jane Doe",  # Scalar changed
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    diff = calculate_diff(original, modified)
    
    # Should detect scalar changes
    assert has_changes(diff)
    assert 'values_changed' in diff


def test_diff_includes_multiple_changes():
    """Test that diff calculation includes multiple sequential edits."""
    original = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    modified = {
        "name": "Jane Doe",  # Scalar changed
        "items": ["item1", "item2", "item3"],  # Array changed
        "amount": 150.0  # Another scalar changed
    }
    
    diff = calculate_diff(original, modified)
    
    # Should detect all changes
    assert has_changes(diff)
    assert 'values_changed' in diff
    # Check that multiple fields are captured
    if isinstance(diff.get('values_changed'), dict):
        # Should have at least 2 value changes (name and amount)
        assert len(diff['values_changed']) >= 2


def test_diff_with_empty_arrays():
    """Test diff calculation handles empty arrays correctly."""
    original = {
        "name": "John Doe",
        "items": []
    }
    
    modified = {
        "name": "John Doe",
        "items": ["item1"]
    }
    
    diff = calculate_diff(original, modified)
    
    # Should detect array addition
    assert has_changes(diff)


def test_diff_with_missing_keys():
    """Test diff calculation handles missing keys correctly."""
    original = {
        "name": "John Doe",
        "amount": 100.0
    }
    
    modified = {
        "name": "John Doe",
        "amount": 100.0,
        "items": ["item1"]  # New field added
    }
    
    diff = calculate_diff(original, modified)
    
    # Should detect new field
    assert has_changes(diff)
    assert 'dictionary_item_added' in diff


def test_collect_current_form_data_with_arrays():
    """Test that collect_current_form_data properly extracts array values."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    
    # Mock session state
    with patch.object(st, 'session_state', {
        'field_items': ['item1', 'item2', 'item3'],
        'field_name': 'John Doe',
        'field_amount': 100.0
    }):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        
        # Should extract all fields including arrays
        assert 'name' in form_data
        assert 'items' in form_data
        assert 'amount' in form_data
        assert form_data['items'] == ['item1', 'item2', 'item3']


def test_collect_current_form_data_with_object_arrays():
    """Test that collect_current_form_data properly extracts object array values from data_editor."""
    import streamlit as st
    import pandas as pd
    from utils.form_generator import FormGenerator
    
    # Create a mock DataFrame
    df = pd.DataFrame([
        {'name': 'Item 1', 'quantity': 5},
        {'name': 'Item 2', 'quantity': 10}
    ])
    
    # Mock session state with data_editor key
    with patch.object(st, 'session_state', {
        'data_editor_line_items': df,
        'field_customer': 'John Doe'
    }):
        schema = {
            'fields': {
                'customer': {'type': 'string'},
                'line_items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'quantity': {'type': 'integer'}
                        }
                    }
                }
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        
        # Should extract object array from data_editor
        assert 'line_items' in form_data
        assert isinstance(form_data['line_items'], list)
        assert len(form_data['line_items']) == 2
        assert form_data['line_items'][0]['name'] == 'Item 1'


def test_diff_shows_array_changes_after_scalar_field_edits():
    """Test that diff shows array changes after scalar field edits (Requirement 3.2)."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    from utils.edit_view import EditView
    from utils.session_manager import SessionManager
    from utils.file_utils import load_json_file
    
    # Mock original data
    original_data = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    # Mock session state with scalar field edit first, then array edit
    with patch.object(st, 'session_state', {
        'field_name': 'Jane Doe',  # Scalar field changed first
        'field_items': ['item1', 'item2', 'item3'],  # Array changed second
        'field_amount': 100.0
    }):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        # Collect current form data (simulating what _render_diff_section does)
        form_data = FormGenerator.collect_current_form_data(schema)
        
        # Calculate diff
        diff = calculate_diff(original_data, form_data)
        
        # Should show both scalar and array changes
        assert has_changes(diff)
        
        # Check for scalar field change (name)
        has_name_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'name' in str(change_path):
                    has_name_change = True
                    break
        
        # Check for array change (items)
        has_items_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        if 'iterable_item_added' in diff:
            for change_path in diff['iterable_item_added']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        
        assert has_name_change, "Name field change should be detected"
        assert has_items_change, "Items array change should be detected"


def test_diff_shows_scalar_field_changes_after_array_edits():
    """Test that diff shows scalar field changes after array edits (Requirement 3.3)."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    
    original_data = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    # Mock session state with array edit first, then scalar field edit
    with patch.object(st, 'session_state', {
        'field_name': 'John Doe',
        'field_items': ['item1', 'item2', 'item3'],  # Array changed first
        'field_amount': 150.0  # Scalar field changed second
    }):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        diff = calculate_diff(original_data, form_data)
        
        # Should show both array and scalar changes
        assert has_changes(diff)
        
        # Check for scalar field change (amount)
        has_amount_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'amount' in str(change_path):
                    has_amount_change = True
                    break
        
        # Check for array change (items)
        has_items_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        if 'iterable_item_added' in diff:
            for change_path in diff['iterable_item_added']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        
        assert has_amount_change, "Amount field change should be detected"
        assert has_items_change, "Items array change should be detected"


def test_diff_shows_multiple_array_field_changes():
    """Test that diff shows multiple array field changes (Requirement 3.1, 3.5)."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    
    original_data = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "tags": ["tag1"],
        "amount": 100.0
    }
    
    # Mock session state with multiple array changes
    with patch.object(st, 'session_state', {
        'field_name': 'John Doe',
        'field_items': ['item1', 'item2', 'item3'],  # First array changed
        'field_tags': ['tag1', 'tag2', 'tag3'],  # Second array changed
        'field_amount': 100.0
    }):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'tags': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        diff = calculate_diff(original_data, form_data)
        
        # Should show changes to both arrays
        assert has_changes(diff)
        
        # Check for items array change
        has_items_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        if not has_items_change and 'iterable_item_added' in diff:
            for change_path in diff['iterable_item_added']:
                if 'items' in str(change_path):
                    has_items_change = True
                    break
        
        # Check for tags array change
        has_tags_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'tags' in str(change_path):
                    has_tags_change = True
                    break
        if not has_tags_change and 'iterable_item_added' in diff:
            for change_path in diff['iterable_item_added']:
                if 'tags' in str(change_path):
                    has_tags_change = True
                    break
        
        assert has_items_change, "Items array change should be detected"
        assert has_tags_change, "Tags array change should be detected"


def test_diff_persists_across_validate_button_clicks():
    """Test that diff persists across validate button clicks (Requirement 3.4)."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    from utils.session_manager import SessionManager
    
    original_data = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    # Mock session state with changes
    session_state = {
        'field_name': 'Jane Doe',  # Changed
        'field_items': ['item1', 'item2', 'item3'],  # Changed
        'field_amount': 150.0  # Changed
    }
    
    with patch.object(st, 'session_state', session_state):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        # First diff calculation (before validate)
        form_data_1 = FormGenerator.collect_current_form_data(schema)
        diff_1 = calculate_diff(original_data, form_data_1)
        
        # Simulate validate button click by updating SessionManager
        with patch.object(SessionManager, 'set_form_data') as mock_set_form_data:
            SessionManager.set_form_data(form_data_1)
            mock_set_form_data.assert_called_once_with(form_data_1)
        
        # Second diff calculation (after validate)
        form_data_2 = FormGenerator.collect_current_form_data(schema)
        diff_2 = calculate_diff(original_data, form_data_2)
        
        # Both diffs should show the same changes
        assert has_changes(diff_1)
        assert has_changes(diff_2)
        
        # Verify that the same types of changes are present in both diffs
        # (We can't compare diff objects directly due to internal DeepDiff object differences)
        assert set(diff_1.keys()) == set(diff_2.keys()), "Both diffs should have the same change types"
        
        # Verify specific changes are preserved
        if 'values_changed' in diff_1 and 'values_changed' in diff_2:
            # Check that the same number of value changes are present
            assert len(diff_1['values_changed']) == len(diff_2['values_changed']), "Same number of value changes should persist"


def test_diff_clears_after_reset():
    """Test that diff clears after reset (Requirement 3.6)."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    from utils.edit_view import EditView
    from utils.session_manager import SessionManager
    
    original_data = {
        "name": "John Doe",
        "items": ["item1", "item2"],
        "amount": 100.0
    }
    
    schema = {
        'fields': {
            'name': {'type': 'string'},
            'items': {'type': 'array', 'items': {'type': 'string'}},
            'amount': {'type': 'number'}
        }
    }
    
    # Mock session state with changes
    session_state_with_changes = {
        'field_name': 'Jane Doe',  # Changed
        'field_items': ['item1', 'item2', 'item3'],  # Changed
        'field_amount': 150.0  # Changed
    }
    
    with patch.object(st, 'session_state', session_state_with_changes):
        # Calculate diff with changes
        form_data_with_changes = FormGenerator.collect_current_form_data(schema)
        diff_with_changes = calculate_diff(original_data, form_data_with_changes)
        
        # Should have changes
        assert has_changes(diff_with_changes)
    
    # Mock session state after reset (values back to original)
    session_state_after_reset = {
        'field_name': 'John Doe',  # Reset to original
        'field_items': ['item1', 'item2'],  # Reset to original
        'field_amount': 100.0  # Reset to original
    }
    
    with patch.object(st, 'session_state', session_state_after_reset):
        # Calculate diff after reset
        form_data_after_reset = FormGenerator.collect_current_form_data(schema)
        diff_after_reset = calculate_diff(original_data, form_data_after_reset)
        
        # Should have no changes
        assert not has_changes(diff_after_reset), "Diff should show no changes after reset"


def test_diff_with_object_array_changes():
    """Test that diff properly handles object array changes in cumulative diff."""
    import streamlit as st
    import pandas as pd
    from utils.form_generator import FormGenerator
    
    original_data = {
        "customer": "John Doe",
        "line_items": [
            {"name": "Item 1", "quantity": 5},
            {"name": "Item 2", "quantity": 10}
        ]
    }
    
    # Create modified DataFrame for object array
    modified_df = pd.DataFrame([
        {"name": "Item 1", "quantity": 5},
        {"name": "Item 2", "quantity": 15},  # Changed quantity
        {"name": "Item 3", "quantity": 3}   # Added item
    ])
    
    # Mock session state with object array changes
    with patch.object(st, 'session_state', {
        'field_customer': 'Jane Doe',  # Scalar field changed
        'data_editor_line_items': modified_df  # Object array changed
    }):
        schema = {
            'fields': {
                'customer': {'type': 'string'},
                'line_items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'quantity': {'type': 'integer'}
                        }
                    }
                }
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        diff = calculate_diff(original_data, form_data)
        
        # Should show both scalar and object array changes
        assert has_changes(diff)
        
        # Check for customer name change
        has_customer_change = False
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'customer' in str(change_path):
                    has_customer_change = True
                    break
        
        # Check for object array changes
        has_array_changes = False
        
        # Check in values_changed
        if 'values_changed' in diff:
            for change_path in diff['values_changed']:
                if 'line_items' in str(change_path):
                    has_array_changes = True
                    break
        
        # Check in iterable_item_added
        if not has_array_changes and 'iterable_item_added' in diff:
            for change_path in diff['iterable_item_added']:
                if 'line_items' in str(change_path):
                    has_array_changes = True
                    break
        
        # Check in iterable_item_removed
        if not has_array_changes and 'iterable_item_removed' in diff:
            for change_path in diff['iterable_item_removed']:
                if 'line_items' in str(change_path):
                    has_array_changes = True
                    break
        
        assert has_customer_change, "Customer field change should be detected"
        assert has_array_changes, "Object array changes should be detected in cumulative diff"


def test_collect_current_form_data_handles_edge_cases():
    """Test that collect_current_form_data handles edge cases properly."""
    import streamlit as st
    from utils.form_generator import FormGenerator
    
    # Test with missing keys and None values
    with patch.object(st, 'session_state', {
        'field_name': None,  # None value
        'field_items': [],   # Empty array
        # field_amount missing entirely
    }):
        schema = {
            'fields': {
                'name': {'type': 'string'},
                'items': {'type': 'array', 'items': {'type': 'string'}},
                'amount': {'type': 'number'}
            }
        }
        
        form_data = FormGenerator.collect_current_form_data(schema)
        
        # Should handle missing and None values gracefully
        assert 'items' in form_data
        assert form_data['items'] == []  # Empty array should be preserved
        assert 'amount' not in form_data  # Missing field should not be included
        # None values for scalar fields should not be included


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
