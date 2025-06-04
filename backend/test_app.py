import unittest
from unittest.mock import patch, MagicMock
import json
import requests # For requests.exceptions
from backend.app import app # Import the Flask app instance

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.config['TESTING'] = True

    def tearDown(self):
        self.app_context.pop()

    @patch('backend.app.requests.get')
    def test_get_average_price_success_all_types(self, mock_get):
        # Mock the HMLR API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Example CSV content based on HMLR structure for /region/{name}.csv
        csv_content = (
            "Period,RegionName,AreaCode,AveragePrice,Index,AveragePriceDetached,IndexDetached,AveragePriceSemiDetached,IndexSemiDetached,AveragePriceTerraced,IndexTerraced,AveragePriceFlatMaisonette,IndexFlatMaisonette\n"
            "2023-10,England,E92000001,300000,150.0,500000,155.0,280000,145.0,220000,140.0,200000,135.0\n"
        )
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise for 200
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=england&property_type=all')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['average_price'], 300000)
        self.assertEqual(data['property_type'], 'all')
        self.assertEqual(data['location'], 'england')
        self.assertEqual(data['data_period'], '2023-10')

    @patch('backend.app.requests.get')
    def test_get_average_price_success_detached(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        csv_content = (
            "Period,RegionName,AreaCode,AveragePrice,Index,AveragePriceDetached,IndexDetached,AveragePriceSemiDetached,IndexSemiDetached,AveragePriceTerraced,IndexTerraced,AveragePriceFlatMaisonette,IndexFlatMaisonette\n"
            "2023-10,England,E92000001,300000,150.0,500000,155.0,280000,145.0,220000,140.0,200000,135.0\n"
        )
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=england&property_type=detached')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['average_price'], 500000)
        self.assertEqual(data['property_type'], 'detached')

    @patch('backend.app.requests.get')
    def test_get_average_price_api_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response) # Mock raise_for_status
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=nonexistent&property_type=all')
        self.assertEqual(response.status_code, 404) # Our app should return 404
        data = json.loads(response.data)
        self.assertIn('Data not found for location', data['error'])

    @patch('backend.app.requests.get')
    def test_get_average_price_api_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("API timed out")

        response = self.client.get('/api/average_price?location=england&property_type=all')
        self.assertEqual(response.status_code, 504) # Gateway Timeout
        data = json.loads(response.data)
        self.assertIn('HMLR API request timed out', data['error'])

    def test_get_average_price_missing_location(self):
        response = self.client.get('/api/average_price?property_type=all')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Location parameter is required')

    def test_get_average_price_invalid_property_type(self):
        response = self.client.get('/api/average_price?location=england&property_type=invalidtype')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invalid property type specified: invalidtype')

    @patch('backend.app.requests.get')
    def test_get_average_price_missing_column(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # CSV missing 'AveragePriceDetached'
        csv_content = (
            "Period,RegionName,AveragePrice\n"
            "2023-10,TestRegion,300000\n"
        )
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=testregion&property_type=detached')
        self.assertEqual(response.status_code, 404) # Should indicate data not found for that type
        data = json.loads(response.data)
        self.assertIn("Data column 'AveragePriceDetached' not found", data['error'])

    @patch('backend.app.requests.get')
    def test_get_average_price_unparseable_price(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        csv_content = (
            "Period,RegionName,AveragePrice\n"
            "2023-10,TestRegion,NotAPrice\n"
        )
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=testregion&property_type=all')
        self.assertEqual(response.status_code, 500) # Internal server error due to parsing
        data = json.loads(response.data)
        self.assertIn("Could not parse price value 'NotAPrice'", data['error'])

    @patch('backend.app.requests.get')
    def test_get_average_price_empty_csv(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        csv_content = "" # Empty or just headers with no data rows
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=testregion&property_type=all')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("No data rows found", data['error'])

    @patch('backend.app.requests.get')
    def test_get_average_price_headers_only_csv(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        csv_content = "Period,RegionName,AveragePrice\n" # Headers only
        mock_response.text = csv_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get('/api/average_price?location=testregion&property_type=all')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("No data rows found", data['error'])

if __name__ == '__main__':
    unittest.main()
