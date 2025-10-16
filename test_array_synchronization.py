"""
Unit tests for array synchronization functionality in FormGenerator.
Tests the _sync_array_to_session method and its integration with array modifications.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date
import json

# Import the module to test
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager


class TestArraySynchronization:
    """Test class for array synchronization functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear session state before each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
        
        # Initialize SessionManager
        SessionManager.initialize()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear session state after each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def test_sync_array_to_session_updates_session_state(self):
        """Test that _sync_array_to_session updates session state correctly."""
        field_name = "test_array"
        array_value = ["item1", "item2", "item3"]
        
        # Call the synchronization method
        FormGenerator._sync_array_to_session(field_name, array_value)