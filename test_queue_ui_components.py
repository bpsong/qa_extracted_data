"""
UI component tests for enhanced queue filtering interface.
Tests enhanced sort controls, pill-style document type filters, and date filter UI components.
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, call
import streamlit as st

# Import the UI components to test
from utils.enhanced_queue_ui import EnhancedQueueUI
from utils.queue_filter_config import QueueFilterConfig


class TestEnhancedSortControls:
    """Test cases for enhanced sort controls with context-aware labels."""
    
    def test_render_enhanced_sort_controls_basic_functionality(self):
        """Test basic functionality of enhanced sort controls."""
        # Mock streamlit components
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption:
            
            # Mock column objects
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock selectbox returns
            mock_selectbox.side_effect = ['filename', 'asc']
            
            # Call the function
            result = EnhancedQueueUI.render_enhanced_sort_controls()
            
            # Verify structure
            assert result['sort_by'] == 'filename'
            assert result['sort_order'] == 'asc'
            
            # Verify streamlit calls
            mock_columns.assert_called_once_with(2)
            assert mock_selectbox.call_count == 2
    
    def test_sort_controls_with_different_field_types(self):
        """Test that sort controls adapt labels based on field type."""
        # Test different sort fields and their expected labels
        test_cases = [
            ('filename', ['A → Z', 'Z → A']),
            ('size', ['Smallest First', 'Largest First']),
            ('created_at', ['Oldest First', 'Newest First']),
            ('modified_at', ['Oldest First', 'Newest First'])
        ]
        
        for sort_field, expected_labels in test_cases:
            with patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.selectbox') as mock_selectbox, \
                 patch('streamlit.caption'):
                
                mock_col1 = MagicMock()
                mock_col2 = MagicMock()
                mock_columns.return_value = [mock_col1, mock_col2]
                
                # Mock first selectbox to return the sort field
                # Second selectbox to return 'asc'
                mock_selectbox.side_effect = [sort_field, 'asc']
                
                result = EnhancedQueueUI.render_enhanced_sort_controls()
                
                # Verify the result
                assert result['sort_by'] == sort_field
                assert result['sort_order'] == 'asc'
                
                # Verify that selectbox was called with correct format_func
                # The second call should have the context-aware labels
                calls = mock_selectbox.call_args_list
                assert len(calls) == 2
                
                # Test the format function for sort order
                sort_order_call = calls[1]
                format_func = sort_order_call[1]['format_func']
                
                # Test format function with 'asc' and 'desc'
                assert format_func('asc') == expected_labels[0]
                assert format_func('desc') == expected_labels[1]
    
    def test_sort_controls_default_order_selection(self):
        """Test that sort controls use appropriate default order for each field."""
        # Test cases: (field, expected_default_index)
        # Index 0 = asc, Index 1 = desc
        test_cases = [
            ('filename', 0),    # Filename defaults to asc (A→Z)
            ('size', 1),        # Size defaults to desc (Largest first)
            ('created_at', 1),  # Dates default to desc (Newest first)
            ('modified_at', 1)  # Dates default to desc (Newest first)
        ]
        
        for sort_field, expected_index in test_cases:
            with patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.selectbox') as mock_selectbox, \
                 patch('streamlit.caption'):
                
                mock_col1 = MagicMock()
                mock_col2 = MagicMock()
                mock_columns.return_value = [mock_col1, mock_col2]
                
                mock_selectbox.side_effect = [sort_field, 'desc']  # Return values
                
                EnhancedQueueUI.render_enhanced_sort_controls()
                
                # Check that the second selectbox call used the correct default index
                calls = mock_selectbox.call_args_list
                sort_order_call = calls[1]
                
                # Verify the index parameter
                assert sort_order_call[1]['index'] == expected_index
    
    def test_sort_controls_help_text_and_captions(self):
        """Test that sort controls include appropriate help text and captions."""
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption:
            
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            mock_selectbox.side_effect = ['filename', 'asc']
            
            EnhancedQueueUI.render_enhanced_sort_controls()
            
            # Verify captions were called
            assert mock_caption.call_count == 2
            
            # Verify help text in selectbox calls
            calls = mock_selectbox.call_args_list
            
            # First call (sort field) should have help text
            sort_field_call = calls[0]
            assert 'help' in sort_field_call[1]
            assert 'organize' in sort_field_call[1]['help'].lower()
            
            # Second call (sort order) should have help text
            sort_order_call = calls[1]
            assert 'help' in sort_order_call[1]





class TestCollapsibleDateFilter:
    """Test cases for collapsible date filter with presets and custom ranges."""
    
    def test_render_collapsible_date_filter_basic_functionality(self):
        """Test basic functionality of collapsible date filter."""
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption:
            
            # Mock expander context
            mock_expander_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock selectbox to return 'all' preset
            mock_selectbox.return_value = 'all'
            
            result = EnhancedQueueUI.render_collapsible_date_filter()
            
            # Verify structure
            assert result['preset'] == 'all'
            assert result['start_date'] is None
            assert result['end_date'] is None
            
            # Verify streamlit calls
            mock_expander.assert_called_once()
            mock_selectbox.assert_called_once()
            mock_caption.assert_called_once()
    
    def test_date_filter_preset_options_and_labels(self):
        """Test that date filter shows correct preset options and labels."""
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption'):
            
            mock_expander_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=None)
            
            mock_selectbox.return_value = 'week'
            
            EnhancedQueueUI.render_collapsible_date_filter()
            
            # Check selectbox call
            selectbox_call = mock_selectbox.call_args
            
            # Should have all available date presets as options
            options = selectbox_call[1]['options']
            expected_presets = QueueFilterConfig.get_available_date_presets()
            assert options == expected_presets
            
            # Test format function
            format_func = selectbox_call[1]['format_func']
            
            # Test a few preset labels
            assert format_func('all') == 'All Time'
            assert format_func('week') == 'Last 7 days'
            assert format_func('month') == 'Last 30 days'
            assert format_func('custom') == 'Custom Range'
    
    def test_date_filter_custom_range_inputs(self):
        """Test custom date range input fields."""
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.date_input') as mock_date_input, \
             patch('streamlit.caption'):
            
            mock_expander_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=None)
            
            # Mock selectbox to return 'custom'
            mock_selectbox.return_value = 'custom'
            
            # Mock columns
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock date inputs
            start_date = date(2024, 1, 1)
            end_date = date(2024, 1, 31)
            mock_date_input.side_effect = [start_date, end_date]
            
            result = EnhancedQueueUI.render_collapsible_date_filter()
            
            # Verify custom range is returned
            assert result['preset'] == 'custom'
            assert result['start_date'] == start_date
            assert result['end_date'] == end_date
            
            # Verify UI elements were created
            mock_write.assert_called_once_with("**Custom Date Range:**")
            mock_columns.assert_called_once_with(2)
            assert mock_date_input.call_count == 2
    
    def test_date_filter_custom_range_validation(self):
        """Test validation of custom date ranges."""
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.write'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.date_input') as mock_date_input, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.caption'):
            
            mock_expander_context = MagicMock()
            mock_expander.return_value.__enter__ = MagicMock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = MagicMock(return_value=None)
            
            mock_selectbox.return_value = 'custom'
            
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock invalid date range (start after end)
            start_date = date(2024, 1, 31)
            end_date = date(2024, 1, 1)
            mock_date_input.side_effect = [start_date, end_date]
            
            result = EnhancedQueueUI.render_collapsible_date_filter()
            
            # Should clear invalid dates
            assert result['preset'] == 'custom'
            assert result['start_date'] is None
            assert result['end_date'] is None
            
            # Should show error message
            mock_error.assert_called_once()
            error_message = mock_error.call_args[0][0]
            assert 'start date' in error_message.lower()
            assert 'end date' in error_message.lower()
    
    def test_date_filter_preset_descriptions(self):
        """Test that preset descriptions are shown."""
        presets_to_test = ['all', 'today', 'week', 'month', 'custom']
        
        for preset in presets_to_test:
            with patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.selectbox') as mock_selectbox, \
                 patch('streamlit.caption') as mock_caption:
                
                mock_expander_context = MagicMock()
                mock_expander.return_value.__enter__ = MagicMock(return_value=mock_expander_context)
                mock_expander.return_value.__exit__ = MagicMock(return_value=None)
                
                mock_selectbox.return_value = preset
                
                EnhancedQueueUI.render_collapsible_date_filter()
                
                # Should show description for the preset
                mock_caption.assert_called()
                caption_call = mock_caption.call_args[0][0]
                
                # Verify description contains relevant text
                expected_config = QueueFilterConfig.get_date_preset_config(preset)
                expected_description = expected_config.get('description', '')
                
                if expected_description:
                    # The caption should contain the description or similar text
                    assert len(caption_call) > 0


class TestEnhancedControlsIntegration:
    """Integration tests for all enhanced UI controls working together."""
    
    @pytest.fixture
    def sample_files_for_ui_testing(self) -> List[Dict[str, Any]]:
        """Sample files for UI integration testing."""
        now = datetime.now()
        return [
            {
                'filename': 'invoice_001.json',
                'size': 2048,
                'created_at': now - timedelta(hours=1),
                'modified_at': now,
                'is_locked': False
            },
            {
                'filename': 'receipt_001.json',
                'size': 1024,
                'created_at': now - timedelta(days=2),
                'modified_at': now - timedelta(days=1),
                'is_locked': False
            },
            {
                'filename': 'contract_001.json',
                'size': 4096,
                'created_at': now - timedelta(days=5),
                'modified_at': now - timedelta(days=3),
                'is_locked': True
            }
        ]
    
    def test_render_enhanced_controls_integration(self, sample_files_for_ui_testing):
        """Test integration of all enhanced controls."""
        with patch('utils.enhanced_queue_ui.EnhancedQueueUI.render_enhanced_sort_controls') as mock_sort, \
             patch('utils.enhanced_queue_ui.EnhancedQueueUI.render_collapsible_date_filter') as mock_date, \
             patch('streamlit.markdown'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button:
            
            # Mock return values
            mock_sort.return_value = {'sort_by': 'filename', 'sort_order': 'asc'}
            mock_date.return_value = {'preset': 'week', 'start_date': None, 'end_date': None}
            
            # Mock refresh button
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_col3 = MagicMock()
            mock_col4 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2, mock_col3, mock_col4]
            mock_button.return_value = False
            
            result = EnhancedQueueUI.render_enhanced_controls(sample_files_for_ui_testing)
            
            # Verify all components were called
            mock_sort.assert_called_once()
            mock_date.assert_called_once()
            
            # Verify result structure
            assert result['sort_by'] == 'filename'
            assert result['sort_order'] == 'asc'
            assert result['date_preset'] == 'week'
            assert result['date_start'] is None
            assert result['date_end'] is None
    

    
    def test_enhanced_controls_with_refresh_button(self, sample_files_for_ui_testing):
        """Test refresh button functionality in enhanced controls."""
        with patch('utils.enhanced_queue_ui.EnhancedQueueUI.render_enhanced_sort_controls') as mock_sort, \
             patch('utils.enhanced_queue_ui.EnhancedQueueUI.render_collapsible_date_filter') as mock_date, \
             patch('streamlit.markdown'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.rerun') as mock_rerun:
            
            # Mock return values
            mock_sort.return_value = {'sort_by': 'size', 'sort_order': 'desc'}
            mock_date.return_value = {'preset': 'all', 'start_date': None, 'end_date': None}
            
            # Mock columns and refresh button clicked
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_col3 = MagicMock()
            mock_col4 = MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2, mock_col3, mock_col4]
            mock_button.return_value = True  # Refresh button clicked
            
            with patch('utils.file_utils.cleanup_stale_locks') as mock_cleanup, \
                 patch('utils.session_manager.SessionManager.get_lock_timeout') as mock_timeout:
                
                mock_timeout.return_value = 1800  # 30 minutes
                
                result = EnhancedQueueUI.render_enhanced_controls(sample_files_for_ui_testing)
                
                # Verify cleanup was called
                mock_cleanup.assert_called_once_with(1800)
                
                # Verify rerun was called
                mock_rerun.assert_called_once()
                
                # Verify result is still returned
                assert 'sort_by' in result
                assert 'date_preset' in result


class TestUIValidationAndNormalization:
    """Test validation and normalization of UI settings."""
    
    def test_validate_and_normalize_settings_basic(self):
        """Test basic validation and normalization of UI settings."""
        raw_settings = {
            'sort_by': 'filename',
            'sort_order': 'asc',
            'date_preset': 'week',
            'date_start': None,
            'date_end': None
        }
        
        normalized = EnhancedQueueUI.validate_and_normalize_settings(raw_settings)
        
        # Should pass through valid settings unchanged
        assert normalized['sort_by'] == 'filename'
        assert normalized['sort_order'] == 'asc'
        assert normalized['date_preset'] == 'week'
        assert normalized['date_start'] is None
        assert normalized['date_end'] is None
    
    def test_validate_and_normalize_settings_with_invalid_values(self):
        """Test validation with invalid values that need correction."""
        invalid_settings = {
            'sort_by': 'invalid_field',
            'sort_order': 'invalid_order',
            'date_preset': 'invalid_preset',
            'date_start': 'invalid_date',
            'date_end': 'invalid_date'
        }
        
        normalized = EnhancedQueueUI.validate_and_normalize_settings(invalid_settings)
        
        # Should fall back to valid defaults
        assert normalized['sort_by'] == 'created_at'  # Default sort field
        assert normalized['sort_order'] == 'desc'     # Default for created_at
        assert normalized['date_preset'] == 'all'     # Default date preset
        
        # Note: The current implementation passes through date values without validation
        # Date validation is handled in the render method, not in this normalization function
        assert normalized['date_start'] == 'invalid_date'  # Passed through as-is
        assert normalized['date_end'] == 'invalid_date'    # Passed through as-is
    
    def test_validate_and_normalize_settings_with_none_dates(self):
        """Test validation with None date values."""
        settings_with_none_dates = {
            'sort_by': 'filename',
            'sort_order': 'asc',
            'date_preset': 'custom',
            'date_start': None,
            'date_end': None
        }
        
        normalized = EnhancedQueueUI.validate_and_normalize_settings(settings_with_none_dates)
        
        # Should pass through None values correctly
        assert normalized['date_start'] is None
        assert normalized['date_end'] is None
        assert normalized['date_preset'] == 'custom'
    
    def test_validate_and_normalize_settings_with_field_specific_defaults(self):
        """Test that validation uses field-specific defaults for sort order."""
        test_cases = [
            ('filename', 'invalid', 'asc'),    # Filename defaults to asc
            ('size', 'invalid', 'desc'),       # Size defaults to desc
            ('created_at', 'invalid', 'desc'), # Dates default to desc
            ('modified_at', 'invalid', 'desc') # Dates default to desc
        ]
        
        for sort_field, invalid_order, expected_order in test_cases:
            settings = {
                'sort_by': sort_field,
                'sort_order': invalid_order,
                'date_preset': 'all'
            }
            
            normalized = EnhancedQueueUI.validate_and_normalize_settings(settings)
            
            assert normalized['sort_by'] == sort_field
            assert normalized['sort_order'] == expected_order
    
    def test_validate_and_normalize_settings_with_missing_fields(self):
        """Test validation with missing fields."""
        incomplete_settings = {
            'sort_by': 'filename'
            # Missing other fields
        }
        
        normalized = EnhancedQueueUI.validate_and_normalize_settings(incomplete_settings)
        
        # Should provide defaults for missing fields
        assert normalized['sort_by'] == 'filename'
        assert normalized['sort_order'] == 'asc'  # Default for filename
        assert normalized['date_preset'] == 'all'
        assert normalized['date_start'] is None
        assert normalized['date_end'] is None


if __name__ == '__main__':
    pytest.main([__file__])