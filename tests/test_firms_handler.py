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
    @patch('streamlit.warning')
    @patch('streamlit.error')
    def test_fetch_fire_data(self, mock_error, mock_warning, mock_write, mock_spinner, mock_get):
        """Test the fetch_fire_data method."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """latitude,longitude,brightness,frp,acq_date,acq_time
36.1,70.2,315.5,10.5,2023-01-01,1200
36.2,70.3,320.1,12.3,2023-01-01,1205
36.3,70.4,318.7,11.8,2023-01-01,1210"""
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Mock context managers
        mock_spinner.return_value.__enter__ = MagicMock(return_value=None)
        mock_spinner.return_value.__exit__ = MagicMock(return_value=None)
        
        # Mock clustering to avoid DBSCAN dependency
        with patch.object(self.handler, '_apply_dbscan', return_value=pd.read_csv(
            StringIO(mock_response.text)
        )):
            # Test fetch_fire_data with valid parameters
            result = self.handler.fetch_fire_data(
                country='Afghanistan',
                dataset='VIIRS_NOAA20_NRT',
                category='fires'
            )
            
            # Verify result
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 3)
            self.assertEqual(list(result.columns), ['latitude', 'longitude', 'brightness', 'frp', 'acq_date', 'acq_time'])
            
            # Verify API call
            mock_get.assert_called_once()
            self.assertIn(self.handler.api_key, mock_get.call_args[0][0])
            self.assertIn('Afghanistan', mock_get.call_args[0][0])
            
if __name__ == '__main__':
    unittest.main()