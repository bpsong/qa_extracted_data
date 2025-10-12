"""
Unit tests for individual queue filter functions.
Tests _apply_file_type_filter, _apply_sort, and _apply_date_filter with various configurations and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

# Import the functions to test
from utils.queue_view import QueueView
from utils.queue_filter_config import QueueFilterConfig



class TestApplySort:
    """Test cases for _apply_sort function."""
    
    @pytest.fixture
    def sample_files_for_sorting(self) -> List[Dict[str, Any]]:
        """Sample file data with varied values for testing sorting."""
        return [
            {
                'filename': 'zebra.json',
                'size': 1000,
                'created_at': datetime(2024, 1, 3),
                'modified_at': datetime(2024, 1, 6),
            },
            {
                'filename': 'alpha.json',
                'size': 3000,
                'created_at': datetime(2024, 1, 1),
                'modified_at': datetime(2024, 1, 4),
            },
            {
                'filename': 'beta.json',
                'size': 2000,
                'created_at': datetime(2024, 1, 2),
                'modified_at': datetime(2024, 1, 5),
            }
        ]
    
    def test_sort_by_filename_ascending(self, sample_files_for_sorting):
        """Test sorting by filename in ascending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'filename', 'asc')
        
        filenames = [f['filename'] for f in result]
        assert filenames == ['alpha.json', 'beta.json', 'zebra.json']
    
    def test_sort_by_filename_descending(self, sample_files_for_sorting):
        """Test sorting by filename in descending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'filename', 'desc')
        
        filenames = [f['filename'] for f in result]
        assert filenames == ['zebra.json', 'beta.json', 'alpha.json']
    
    def test_sort_by_size_ascending(self, sample_files_for_sorting):
        """Test sorting by size in ascending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'size', 'asc')
        
        sizes = [f['size'] for f in result]
        assert sizes == [1000, 2000, 3000]
    
    def test_sort_by_size_descending(self, sample_files_for_sorting):
        """Test sorting by size in descending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'size', 'desc')
        
        sizes = [f['size'] for f in result]
        assert sizes == [3000, 2000, 1000]
    
    def test_sort_by_created_at_ascending(self, sample_files_for_sorting):
        """Test sorting by creation date in ascending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'created_at', 'asc')
        
        dates = [f['created_at'] for f in result]
        assert dates == [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3)
        ]
    
    def test_sort_by_created_at_descending(self, sample_files_for_sorting):
        """Test sorting by creation date in descending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'created_at', 'desc')
        
        dates = [f['created_at'] for f in result]
        assert dates == [
            datetime(2024, 1, 3),
            datetime(2024, 1, 2),
            datetime(2024, 1, 1)
        ]
    
    def test_sort_by_modified_at_ascending(self, sample_files_for_sorting):
        """Test sorting by modification date in ascending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'modified_at', 'asc')
        
        dates = [f['modified_at'] for f in result]
        assert dates == [
            datetime(2024, 1, 4),
            datetime(2024, 1, 5),
            datetime(2024, 1, 6)
        ]
    
    def test_sort_by_modified_at_descending(self, sample_files_for_sorting):
        """Test sorting by modification date in descending order."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'modified_at', 'desc')
        
        dates = [f['modified_at'] for f in result]
        assert dates == [
            datetime(2024, 1, 6),
            datetime(2024, 1, 5),
            datetime(2024, 1, 4)
        ]
    
    def test_sort_empty_list_returns_empty_list(self):
        """Test that sorting an empty list returns an empty list."""
        result = QueueView._apply_sort([], 'filename', 'asc')
        assert result == []
    
    def test_sort_invalid_field_falls_back_to_default(self, sample_files_for_sorting):
        """Test that invalid sort field falls back to default (created_at)."""
        with patch('utils.queue_view.logger') as mock_logger:
            result = QueueView._apply_sort(sample_files_for_sorting, 'invalid_field', 'asc')
            
            # Should fall back to created_at sorting
            dates = [f['created_at'] for f in result]
            assert dates == [
                datetime(2024, 1, 1),
                datetime(2024, 1, 2),
                datetime(2024, 1, 3)
            ]
            
            # Should log a warning
            mock_logger.warning.assert_called()
    
    def test_sort_invalid_order_falls_back_to_default(self, sample_files_for_sorting):
        """Test that invalid sort order falls back to field default."""
        with patch('utils.queue_view.logger') as mock_logger:
            result = QueueView._apply_sort(sample_files_for_sorting, 'filename', 'invalid_order')
            
            # Should fall back to default order for filename (asc)
            filenames = [f['filename'] for f in result]
            assert filenames == ['alpha.json', 'beta.json', 'zebra.json']
            
            # Should log a warning
            mock_logger.warning.assert_called()
    
    def test_sort_missing_field_falls_back_gracefully(self):
        """Test that missing sort field in files falls back gracefully."""
        files_missing_field = [
            {'filename': 'test1.json'},
            {'filename': 'test2.json'}
        ]
        
        with patch('utils.queue_view.logger') as mock_logger:
            result = QueueView._apply_sort(files_missing_field, 'created_at', 'asc')
            
            # Should fall back to filename sorting
            assert len(result) == 2
            mock_logger.warning.assert_called()
    
    def test_sort_preserves_file_structure(self, sample_files_for_sorting):
        """Test that sorting preserves the original file structure."""
        result = QueueView._apply_sort(sample_files_for_sorting, 'filename', 'asc')
        
        # Check that all original fields are preserved
        for file_info in result:
            assert 'filename' in file_info
            assert 'size' in file_info
            assert 'created_at' in file_info
            assert 'modified_at' in file_info


class TestApplyDateFilter:
    """Test cases for _apply_date_filter function."""
    
    @pytest.fixture
    def sample_files_with_dates(self) -> List[Dict[str, Any]]:
        """Sample file data with varied dates for testing date filtering."""
        now = datetime.now()
        return [
            {
                'filename': 'today.json',
                'created_at': now,
                'modified_at': now,
            },
            {
                'filename': 'yesterday.json',
                'created_at': now - timedelta(days=1),
                'modified_at': now - timedelta(days=1),
            },
            {
                'filename': 'last_week.json',
                'created_at': now - timedelta(days=7),
                'modified_at': now - timedelta(days=7),
            },
            {
                'filename': 'last_month.json',
                'created_at': now - timedelta(days=30),
                'modified_at': now - timedelta(days=30),
            },
            {
                'filename': 'very_old.json',
                'created_at': now - timedelta(days=365),
                'modified_at': now - timedelta(days=365),
            }
        ]
    
    def test_filter_all_returns_all_files(self, sample_files_with_dates):
        """Test that 'all' date filter returns all files."""
        result = QueueView._apply_date_filter(sample_files_with_dates, 'all')
        assert len(result) == 5
        assert result == sample_files_with_dates
    
    def test_filter_today_returns_today_files(self, sample_files_with_dates):
        """Test that 'today' filter returns only today's files."""
        result = QueueView._apply_date_filter(sample_files_with_dates, 'today')
        
        # Should return only the file from today
        assert len(result) == 1
        assert result[0]['filename'] == 'today.json'
    
    def test_filter_week_returns_last_7_days(self, sample_files_with_dates):
        """Test that 'week' filter returns files from last 7 days."""
        result = QueueView._apply_date_filter(sample_files_with_dates, 'week')
        
        # Should return today and yesterday files (last_week is exactly 7 days ago, might be excluded)
        filenames = {f['filename'] for f in result}
        # The exact boundary depends on timing, so we check for at least today and yesterday
        assert 'today.json' in filenames
        assert 'yesterday.json' in filenames
        # last_week.json may or may not be included depending on exact timing
        assert len(filenames) >= 2
    
    def test_filter_month_returns_last_30_days(self, sample_files_with_dates):
        """Test that 'month' filter returns files from last 30 days."""
        result = QueueView._apply_date_filter(sample_files_with_dates, 'month')
        
        # Should return recent files but exclude very_old
        filenames = {f['filename'] for f in result}
        # Definitely should include today, yesterday, and last_week
        assert 'today.json' in filenames
        assert 'yesterday.json' in filenames
        assert 'last_week.json' in filenames
        # last_month.json may or may not be included depending on exact timing
        # very_old.json should definitely be excluded
        assert 'very_old.json' not in filenames
        assert len(filenames) >= 3
    
    def test_filter_custom_range_with_both_dates(self, sample_files_with_dates):
        """Test custom date range with both start and end dates."""
        now = datetime.now()
        start_date = now - timedelta(days=8)
        end_date = now - timedelta(days=2)
        
        result = QueueView._apply_date_filter(
            sample_files_with_dates, 'custom', start_date, end_date
        )
        
        # Should return only last_week file (7 days ago, within range)
        assert len(result) == 1
        assert result[0]['filename'] == 'last_week.json'
    
    def test_filter_custom_range_with_start_date_only(self, sample_files_with_dates):
        """Test custom date range with only start date."""
        now = datetime.now()
        start_date = now - timedelta(days=2)
        
        result = QueueView._apply_date_filter(
            sample_files_with_dates, 'custom', start_date, None
        )
        
        # Should return today and yesterday files
        filenames = {f['filename'] for f in result}
        expected = {'today.json', 'yesterday.json'}
        assert filenames == expected
    
    def test_filter_custom_range_with_end_date_only(self, sample_files_with_dates):
        """Test custom date range with only end date."""
        now = datetime.now()
        end_date = now - timedelta(days=8)
        
        result = QueueView._apply_date_filter(
            sample_files_with_dates, 'custom', None, end_date
        )
        
        # Should return last_month and very_old files
        filenames = {f['filename'] for f in result}
        expected = {'last_month.json', 'very_old.json'}
        assert filenames == expected
    
    def test_filter_custom_range_with_no_dates_returns_all(self, sample_files_with_dates):
        """Test custom date range with no dates returns all files."""
        result = QueueView._apply_date_filter(
            sample_files_with_dates, 'custom', None, None
        )
        
        assert len(result) == 5
        assert result == sample_files_with_dates
    
    def test_filter_empty_list_returns_empty_list(self):
        """Test that filtering an empty list returns an empty list."""
        result = QueueView._apply_date_filter([], 'today')
        assert result == []
    
    def test_filter_files_missing_dates_are_excluded(self):
        """Test that files missing date fields are excluded from results."""
        files_missing_dates = [
            {'filename': 'no_dates.json'},
            {'filename': 'partial_dates.json', 'created_at': datetime.now()}
        ]
        
        result = QueueView._apply_date_filter(files_missing_dates, 'today')
        
        # Should return only the file with a date
        assert len(result) == 1
        assert result[0]['filename'] == 'partial_dates.json'
    
    def test_filter_uses_most_recent_date(self):
        """Test that filtering uses the most recent of created_at or modified_at."""
        now = datetime.now()
        files_with_different_dates = [
            {
                'filename': 'recent_modified.json',
                'created_at': now - timedelta(days=10),
                'modified_at': now,  # More recent
            },
            {
                'filename': 'recent_created.json',
                'created_at': now,  # More recent
                'modified_at': now - timedelta(days=10),
            }
        ]
        
        result = QueueView._apply_date_filter(files_with_different_dates, 'today')
        
        # Both files should be included because they have recent dates
        assert len(result) == 2
        filenames = {f['filename'] for f in result}
        assert filenames == {'recent_modified.json', 'recent_created.json'}
    
    def test_filter_preserves_file_structure(self, sample_files_with_dates):
        """Test that date filtering preserves the original file structure."""
        result = QueueView._apply_date_filter(sample_files_with_dates, 'week')
        
        # Check that all original fields are preserved
        for file_info in result:
            assert 'filename' in file_info
            assert 'created_at' in file_info
            assert 'modified_at' in file_info
    
    def test_filter_week_with_precise_timing(self):
        """Test week filter with precise date calculations."""
        now = datetime.now()
        
        # Create files with precise timing relative to the filter logic
        files_with_precise_dates = [
            {
                'filename': 'within_week.json',
                'created_at': now - timedelta(days=6),  # Definitely within 7 days
                'modified_at': now - timedelta(days=6),
            },
            {
                'filename': 'outside_week.json',
                'created_at': now - timedelta(days=8),  # Definitely outside 7 days
                'modified_at': now - timedelta(days=8),
            }
        ]
        
        result = QueueView._apply_date_filter(files_with_precise_dates, 'week')
        
        # Should include only the file within the week
        assert len(result) == 1
        assert result[0]['filename'] == 'within_week.json'
    
    def test_filter_month_with_precise_timing(self):
        """Test month filter with precise date calculations."""
        now = datetime.now()
        
        # Create files with precise timing relative to the filter logic
        files_with_precise_dates = [
            {
                'filename': 'within_month.json',
                'created_at': now - timedelta(days=29),  # Definitely within 30 days
                'modified_at': now - timedelta(days=29),
            },
            {
                'filename': 'outside_month.json',
                'created_at': now - timedelta(days=31),  # Definitely outside 30 days
                'modified_at': now - timedelta(days=31),
            }
        ]
        
        result = QueueView._apply_date_filter(files_with_precise_dates, 'month')
        
        # Should include only the file within the month
        assert len(result) == 1
        assert result[0]['filename'] == 'within_month.json'


class TestFilterFunctionIntegration:
    """Integration tests for filter functions working together."""
    
    @pytest.fixture
    def comprehensive_sample_files(self) -> List[Dict[str, Any]]:
        """Comprehensive sample data for integration testing."""
        now = datetime.now()
        return [
            {
                'filename': 'invoice_recent.json',
                'size': 1000,
                'created_at': now,
                'modified_at': now,
                'is_locked': False
            },
            {
                'filename': 'invoice_old.json',
                'size': 2000,
                'created_at': now - timedelta(days=60),
                'modified_at': now - timedelta(days=60),
                'is_locked': False
            },
            {
                'filename': 'receipt_recent.json',
                'size': 1500,
                'created_at': now - timedelta(days=1),
                'modified_at': now - timedelta(days=1),
                'is_locked': True
            },
            {
                'filename': 'contract_medium.json',
                'size': 3000,
                'created_at': now - timedelta(days=15),
                'modified_at': now - timedelta(days=15),
                'is_locked': False
            }
        ]
    
    def test_filter_functions_can_be_chained(self, comprehensive_sample_files):
        """Test that filter functions can be chained together."""
        # Chain filters: date -> sort (no file type filtering)
        files_after_date = QueueView._apply_date_filter(
            comprehensive_sample_files, 'month'
        )
        final_files = QueueView._apply_sort(
            files_after_date, 'size', 'desc'
        )
        
        # Should have recent files sorted by size descending
        assert len(final_files) > 0
        
        # Check that results are sorted by size descending
        sizes = [f['size'] for f in final_files]
        assert sizes == sorted(sizes, reverse=True)
    
    def test_filter_functions_handle_empty_intermediate_results(self, comprehensive_sample_files):
        """Test that filter functions handle empty intermediate results gracefully."""
        # Create a date filter that returns no results
        now = datetime.now()
        very_old_start = now - timedelta(days=365)
        very_old_end = now - timedelta(days=300)
        
        # First filter should return empty list (no files in that old range)
        files_after_date = QueueView._apply_date_filter(
            comprehensive_sample_files, 'custom', very_old_start, very_old_end
        )
        assert files_after_date == []
        
        # Subsequent filters should handle empty list gracefully
        final_files = QueueView._apply_sort(
            files_after_date, 'filename', 'asc'
        )
        assert final_files == []


if __name__ == '__main__':
    pytest.main([__file__])