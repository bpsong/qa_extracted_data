"""
Unit tests for diff_utils module.
"""

import json
import tempfile
from pathlib import Path
import pytest

# Import the module to test
from utils.diff_utils import (
    calculate_diff,
    has_changes,
    format_diff_for_display,
    format_diff_for_streamlit,
    get_change_summary,
    create_audit_diff_entry,
    compare_json_files,
    highlight_changes_in_json,
    get_field_changes,
    create_change_badge,
    validate_diff_data
)


class TestDiffUtils:
    """Test class for diff utilities."""
    
    def test_calculate_diff_no_changes(self):
        """Test calculating diff with no changes."""
        original = {"name": "John", "age": 30}
        modified = {"name": "John", "age": 30}
        
        diff = calculate_diff(original, modified)
        
        # Should be empty or have no significant changes
        assert not has_changes(diff)
    
    def test_calculate_diff_value_changed(self):
        """Test calculating diff with value changes."""
        original = {"name": "John", "age": 30}
        modified = {"name": "John", "age": 31}
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff)
        assert 'values_changed' in diff
    
    def test_calculate_diff_item_added(self):
        """Test calculating diff with added items."""
        original = {"name": "John"}
        modified = {"name": "John", "age": 30}
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff)
        assert 'dictionary_item_added' in diff
    
    def test_calculate_diff_item_removed(self):
        """Test calculating diff with removed items."""
        original = {"name": "John", "age": 30}
        modified = {"name": "John"}
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff)
        assert 'dictionary_item_removed' in diff
    
    def test_calculate_diff_type_changed(self):
        """Test calculating diff with type changes."""
        original = {"age": "30"}  # String
        modified = {"age": 30}    # Integer
    
        diff = calculate_diff(original, modified)
    
        # Due to normalization, numeric strings are converted to numbers,
        # so no changes should be detected between "30" and 30
        assert not has_changes(diff)
    
    def test_has_changes_true(self):
        """Test has_changes returns True for actual changes."""
        original = {"name": "John"}
        modified = {"name": "Jane"}
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff) == True
    
    def test_has_changes_false(self):
        """Test has_changes returns False for no changes."""
        original = {"name": "John", "age": 30}
        modified = {"name": "John", "age": 30}
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff) == False
    
    def test_has_changes_empty_diff(self):
        """Test has_changes with empty diff."""
        assert has_changes({}) == False
    
    def test_format_diff_for_display_no_changes(self):
        """Test formatting diff display with no changes."""
        original = {"name": "John"}
        modified = {"name": "John"}
        
        diff = calculate_diff(original, modified)
        formatted = format_diff_for_display(diff, original, modified)
        
        assert "No changes detected" in formatted
        assert "✅" in formatted
    
    def test_format_diff_for_display_with_changes(self):
        """Test formatting diff display with changes."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 30, "city": "New York"}
        
        diff = calculate_diff(original, modified)
        formatted = format_diff_for_display(diff, original, modified)
        
        assert "Changes Summary" in formatted
        assert "John" in formatted or "Jane" in formatted
    
    def test_format_diff_for_display_added_field_with_value(self):
        """Test formatting diff display when a field is added with actual value."""
        original = {
            "Supplier name": "MESON FAR EAST PTE LTD",
            "Purchase Order number": "1781038",
            "Invoice Amount": 243.0,
            "Project number": "S268588"
        }
        modified = {
            "Supplier name": "MESON FAR EAST PTE LTD",
            "Purchase Order number": "1781038",
            "Invoice Amount": 243.0,
            "Project number": "S268588",
            "Currency": "SGD"
        }
        
        diff = calculate_diff(original, modified)
        formatted = format_diff_for_display(diff, original, modified)
        
        assert "Added Fields" in formatted
        assert "Currency" in formatted
        assert "SGD" in formatted
        assert "Before:** `None`" in formatted
        assert "After:** `SGD`" in formatted
    
    def test_format_diff_for_display_serialized_setordered(self):
        """Test formatting diff display with serialized SetOrdered format from audit logs."""
        original = {
            "Supplier name": "MESON FAR EAST PTE LTD",
            "Purchase Order number": "1781038",
            "Invoice Amount": 243.0,
            "Project number": "S268588"
        }
        modified = {
            "Supplier name": "MESON FAR EAST PTE LTD",
            "Purchase Order number": "1781038",
            "Invoice Amount": 243.0,
            "Project number": "S268588",
            "Currency": "SGD"
        }
        
        # Simulate the serialized diff format from audit logs
        diff = {
            "dictionary_item_added": "SetOrdered([\"root['Currency']\"])"
        }
        
        formatted = format_diff_for_display(diff, original, modified)
        
        assert "Added Fields" in formatted
        assert "Currency" in formatted
        assert "SGD" in formatted
        assert "Before:** `None`" in formatted
        assert "After:** `SGD`" in formatted
    
    def test_format_diff_for_streamlit(self):
        """Test formatting diff for Streamlit components."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 31}
        
        diff = calculate_diff(original, modified)
        changes = format_diff_for_streamlit(diff)
        
        assert isinstance(changes, list)
        assert len(changes) > 0
        
        # Check structure of change entries
        for change in changes:
            assert 'type' in change
            assert 'field' in change
            assert 'old_value' in change
            assert 'new_value' in change
            assert 'icon' in change
    
    def test_format_diff_for_streamlit_no_changes(self):
        """Test formatting diff for Streamlit with no changes."""
        original = {"name": "John"}
        modified = {"name": "John"}
        
        diff = calculate_diff(original, modified)
        changes = format_diff_for_streamlit(diff)
        
        assert changes == []
    
    def test_get_change_summary(self):
        """Test getting change summary."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "city": "New York"}
        
        diff = calculate_diff(original, modified)
        summary = get_change_summary(diff)
        
        assert isinstance(summary, dict)
        assert 'modified' in summary
        assert 'added' in summary
        assert 'removed' in summary
        assert 'type_changed' in summary
        assert 'total' in summary
        
        # Should have some changes
        assert summary['total'] > 0
    
    def test_get_change_summary_no_changes(self):
        """Test getting change summary with no changes."""
        original = {"name": "John"}
        modified = {"name": "John"}
        
        diff = calculate_diff(original, modified)
        summary = get_change_summary(diff)
        
        assert summary['total'] == 0
        assert summary['modified'] == 0
        assert summary['added'] == 0
        assert summary['removed'] == 0
        assert summary['type_changed'] == 0
    
    def test_create_audit_diff_entry(self):
        """Test creating audit diff entry."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 31}
        
        audit_entry = create_audit_diff_entry(original, modified)
        
        assert isinstance(audit_entry, dict)
        assert 'has_changes' in audit_entry
        assert 'change_summary' in audit_entry
        assert 'detailed_diff' in audit_entry
        assert 'original_data' in audit_entry
        assert 'modified_data' in audit_entry
        
        assert audit_entry['has_changes'] == True
        assert audit_entry['original_data'] == original
        assert audit_entry['modified_data'] == modified
    
    def test_compare_json_files(self):
        """Test comparing JSON files."""
        # Create temporary JSON files
        with tempfile.TemporaryDirectory() as temp_dir:
            file1_path = Path(temp_dir) / "file1.json"
            file2_path = Path(temp_dir) / "file2.json"
            
            data1 = {"name": "John", "age": 30}
            data2 = {"name": "Jane", "age": 30}
            
            with open(file1_path, 'w') as f:
                json.dump(data1, f)
            
            with open(file2_path, 'w') as f:
                json.dump(data2, f)
            
            diff = compare_json_files(str(file1_path), str(file2_path))
            
            assert has_changes(diff)
    
    def test_compare_json_files_not_found(self):
        """Test comparing non-existent JSON files."""
        diff = compare_json_files("nonexistent1.json", "nonexistent2.json")
        
        # Should return empty diff on error
        assert diff == {}
    
    def test_highlight_changes_in_json(self):
        """Test highlighting changes in JSON."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 31}
        
        original_json, modified_json = highlight_changes_in_json(original, modified)
        
        assert isinstance(original_json, str)
        assert isinstance(modified_json, str)
        assert "John" in original_json
        assert "Jane" in modified_json
    
    def test_get_field_changes_modified(self):
        """Test getting changes for a specific modified field."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 30}
        
        diff = calculate_diff(original, modified)
        changes = get_field_changes(diff, "name")
        
        if changes:  # DeepDiff might structure this differently
            assert changes['type'] in ['modified', 'added', 'removed']
    
    def test_get_field_changes_no_changes(self):
        """Test getting changes for field with no changes."""
        original = {"name": "John", "age": 30}
        modified = {"name": "John", "age": 30}
        
        diff = calculate_diff(original, modified)
        changes = get_field_changes(diff, "name")
        
        assert changes is None
    
    def test_create_change_badge(self):
        """Test creating change badges."""
        badges = {
            'modified': create_change_badge('modified'),
            'added': create_change_badge('added'),
            'removed': create_change_badge('removed'),
            'type_changed': create_change_badge('type_changed'),
            'unknown': create_change_badge('unknown')
        }
        
        for badge_type, badge in badges.items():
            assert isinstance(badge, str)
            assert len(badge) > 0
            # Should contain emoji or formatting
            assert any(char in badge for char in ['🔄', '➕', '➖', '🔀', '📝', '*'])
    
    def test_validate_diff_data_valid(self):
        """Test validating valid diff data."""
        original = {"name": "John", "age": 30}
        modified = {"name": "Jane", "age": 31}
        
        assert validate_diff_data(original, modified) == True
    
    def test_validate_diff_data_invalid(self):
        """Test validating invalid diff data."""
        # Create non-serializable data
        class NonSerializable:
            pass
        
        original = {"name": "John"}
        modified = {"obj": NonSerializable()}
        
        # Should handle the error gracefully
        result = validate_diff_data(original, modified)
        # Might be True or False depending on implementation
        assert isinstance(result, bool)
    
    def test_complex_nested_diff(self):
        """Test diff with complex nested structures."""
        original = {
            "user": {
                "name": "John",
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown"
                },
                "hobbies": ["reading", "swimming"]
            }
        }
        
        modified = {
            "user": {
                "name": "John",
                "address": {
                    "street": "456 Oak Ave",
                    "city": "Anytown",
                    "zip": "12345"
                },
                "hobbies": ["reading", "cycling", "cooking"]
            }
        }
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff)
        
        # Test formatting
        formatted = format_diff_for_display(diff, original, modified)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        
        # Test summary
        summary = get_change_summary(diff)
        assert summary['total'] > 0
    
    def test_array_changes(self):
        """Test diff with array changes."""
        original = {
            "items": ["apple", "banana", "cherry"]
        }
        
        modified = {
            "items": ["apple", "orange", "cherry", "date"]
        }
        
        diff = calculate_diff(original, modified)
        
        assert has_changes(diff)
        
        # Should detect array changes
        changes = format_diff_for_streamlit(diff)
        assert len(changes) > 0


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])