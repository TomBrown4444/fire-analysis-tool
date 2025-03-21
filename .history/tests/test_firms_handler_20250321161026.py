"""
Tests for the FIRMSHandler class.
"""
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from io import StringIO

from app.core.firms_handler import FIRMSHandler

class TestFIRMSHandler(unittest.TestCase):
    """Test the FIRMSHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = FIRMSHandler('test_user', 'test_password', 'test_api_key')
        
    def test_get_country_bbox(self):
        """Test the get_country_bbox method."""
        # Test a known country
        self.assertEqual(self.handler.get_country_bbox('Afghanistan'), '60.52,29.31,75.15,38.48')
        
        # Test an unknown country
        self.assertIsNone(self.handler.get_country_bbox('Narnia'))
    
    @patch('requests.Session.get')
    @patch('streamlit.spinner')
    @patch('streamlit.write')
    @patch('stream