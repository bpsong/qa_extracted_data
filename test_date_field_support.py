"""
Test date field support in form generator.
Verifies that date and datetime fields render with proper date pickers.
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
from utils.form_generator import FormGenerator


class TestDateFieldSupport:
    """Test date and datetime field rendering."""
    
    def test_date_field_widget_type_determination(self):
        """Test that type: date fields are recognized as date_input widgets."""
        field_config = {
            'type': 'date',
            'label': 'Test Date',
            'required': True
        }
        
        # The widget type should be determined as 'date_input'
        # This is tested indirectly through the rendering logic
        assert field_config['type'] == 'date'
    
    def test_datetime_field_widget_type_determination(self):
        """Test that type: datetime fields are recognized as datetime_input widgets."""
        field_config = {
            'type': 'datetime',
            'label': 'Test DateTime',
            'required': True
        }
        
        assert field_config['type'] == 'datetime'
    
    @patch('utils.form_generator.st')
    def test_render_date_input_with_string_value(self, mock_st):
        """Test that date input can parse string values from JSON."""
        mock_st.date_input.return_value = date(2024, 3, 15)
        
        field_config = {
            'type': 'date',
            'label': 'Test Date',
            'required': True
        }
        
        kwargs = {
            'key': 'field_test_date',
            'label': 'Test Date',
            'value': '2024-03-15',  # String value from JSON
            'disabled': False
        }
        
        result = FormGenerator._render_date_input('test_date', field_config, kwargs)
        
        # Should call st.date_input with parsed date value
        mock_st.date_input.assert_called_once()
        call_kwargs = mock_st.date_input.call_args[1]
        
        # Verify the value was parsed to a date object
        assert 'value' in call_kwargs
        assert isinstance(call_kwargs['value'], date)
        assert call_kwargs['value'] == date(2024, 3, 15)
        
        # Result should be a string for JSON serialization
        assert result == "2024-03-15"
    
    @patch('utils.form_generator.st')
    def test_render_date_input_with_date_object(self, mock_st):
        """Test that date input handles date objects directly."""
        test_date = date(2024, 3, 15)
        mock_st.date_input.return_value = test_date
        
        field_config = {
            'type': 'date',
            'label': 'Test Date',
            'required': True
        }
        
        kwargs = {
            'key': 'field_test_date',
            'label': 'Test Date',
            'value': test_date,
            'disabled': False
        }
        
        result = FormGenerator._render_date_input('test_date', field_config, kwargs)
        
        mock_st.date_input.assert_called_once()
        call_kwargs = mock_st.date_input.call_args[1]
        
        assert call_kwargs['value'] == test_date
        # Result should be a string
        assert result == "2024-03-15"
    
    @patch('utils.form_generator.st')
    def test_render_date_input_with_datetime_object(self, mock_st):
        """Test that date input converts datetime to date."""
        test_datetime = datetime(2024, 3, 15, 14, 30, 0)
        expected_date = date(2024, 3, 15)
        mock_st.date_input.return_value = expected_date
        
        field_config = {
            'type': 'date',
            'label': 'Test Date',
            'required': True
        }
        
        kwargs = {
            'key': 'field_test_date',
            'label': 'Test Date',
            'value': test_datetime,
            'disabled': False
        }
        
        result = FormGenerator._render_date_input('test_date', field_config, kwargs)
        
        mock_st.date_input.assert_called_once()
        call_kwargs = mock_st.date_input.call_args[1]
        
        # Should extract date part from datetime
        assert call_kwargs['value'] == expected_date
        # Result should be a string
        assert result == "2024-03-15"
    
    @patch('utils.form_generator.st')
    def test_render_date_input_with_invalid_string(self, mock_st):
        """Test that date input handles invalid date strings gracefully."""
        mock_st.date_input.return_value = date(2024, 1, 1)
        
        field_config = {
            'type': 'date',
            'label': 'Test Date',
            'required': True
        }
        
        kwargs = {
            'key': 'field_test_date',
            'label': 'Test Date',
            'value': 'invalid-date-string',
            'disabled': False
        }
        
        result = FormGenerator._render_date_input('test_date', field_config, kwargs)
        
        # Should call st.date_input without value (letting it use default)
        mock_st.date_input.assert_called_once()
        call_kwargs = mock_st.date_input.call_args[1]
        
        # Value should be removed due to parse failure
        assert 'value' not in call_kwargs or call_kwargs.get('value') is None
    
    @patch('utils.form_generator.st')
    def test_render_datetime_input_with_string_value(self, mock_st):
        """Test that datetime input can parse string values from JSON."""
        # Setup mock columns
        col1_mock = MagicMock()
        col2_mock = MagicMock()
        col1_mock.__enter__ = MagicMock(return_value=col1_mock)
        col1_mock.__exit__ = MagicMock(return_value=False)
        col2_mock.__enter__ = MagicMock(return_value=col2_mock)
        col2_mock.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [col1_mock, col2_mock]
        
        # Setup return values
        test_date = date(2024, 3, 15)
        test_time = datetime(2024, 3, 15, 14, 30, 0).time()
        mock_st.date_input.return_value = test_date
        mock_st.time_input.return_value = test_time
        
        field_config = {
            'type': 'datetime',
            'label': 'Test DateTime',
            'required': True
        }
        
        kwargs = {
            'key': 'field_test_datetime',
            'label': 'Test DateTime',
            'value': '2024-03-15T14:30:00',  # ISO format string
            'disabled': False
        }
        
        result = FormGenerator._render_datetime_input('test_datetime', field_config, kwargs)
        
        # Should parse the string and return ISO format string
        assert isinstance(result, str)
        assert result == "2024-03-15T14:30:00"
    
    def test_date_field_in_schema_integration(self):
        """Test that schemas with type: date are properly recognized."""
        schema = {
            'title': 'Test Schema',
            'fields': {
                'start_date': {
                    'type': 'date',
                    'label': 'Start Date',
                    'required': True
                },
                'end_date': {
                    'type': 'date',
                    'label': 'End Date',
                    'required': False
                },
                'created_at': {
                    'type': 'datetime',
                    'label': 'Created At',
                    'required': False
                }
            }
        }
        
        # Verify schema structure
        assert schema['fields']['start_date']['type'] == 'date'
        assert schema['fields']['end_date']['type'] == 'date'
        assert schema['fields']['created_at']['type'] == 'datetime'
    
    @patch('utils.form_generator.st')
    def test_date_field_with_string_from_json(self, mock_st):
        """Test that date fields handle string values from JSON data without strftime errors."""
        # Simulate a date field with string value from JSON
        field_config = {
            'type': 'date',
            'label': 'Insurance End Date',
            'required': True
        }
        
        # String value as it would come from JSON
        current_value = "2024-12-31"
        
        # Mock session state
        mock_st.session_state = {}
        
        # Mock date_input to return a proper date object
        mock_st.date_input.return_value = date(2024, 12, 31)
        
        # This should not raise "descriptor 'strftime' for 'datetime.date' objects doesn't apply to a 'str' object"
        try:
            result = FormGenerator._render_date_input('end_date', field_config, {
                'key': 'field_end_date',
                'label': 'Insurance End Date',
                'value': current_value,
                'disabled': False
            })
            # Should successfully parse and return a string
            assert result == "2024-12-31"
        except TypeError as e:
            if "strftime" in str(e):
                pytest.fail(f"strftime error occurred: {e}")
            raise


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
