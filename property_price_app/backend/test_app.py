import unittest
from unittest.mock import patch, MagicMock
import json
import requests # For requests.exceptions
from property_price_app.backend.app import app # Import the Flask app instance

# New HMLR Data Endpoint (though not directly used in mock setup, good to note)
# HMLR_DATA_ENDPOINT = "https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data/UK-HPI-full-file-2025-03.csv"

MOCK_CSV_HEADER = "Date,RegionName,AreaCode,AveragePrice,Index,IndexSA,AveragePriceDetached,AveragePriceSemiDetached,AveragePriceTerraced,AveragePriceFlatMaisonette,Postcode"
MOCK_CSV_DATA = (
    MOCK_CSV_HEADER + "\n"
    # Valid London Postcode SW1A 0AA
    "2023-03-01,London,E92000001,500000,120,121,700000,600000,500000,400000,SW1A 0AA\n"
    # Valid London Postcode WC2N 5DU - different property types
    "2023-03-01,London,E92000001,550000,125,126,750000,650000,550000,450000,WC2N 5DU\n"
    # Non-London Postcode M1 1AA
    "2023-03-01,North West,E12000002,200000,110,111,300000,250000,200000,150000,M1 1AA\n"
    # London Postcode W1A 0AX with missing AveragePrice and some property types (e.g. Flat)
    "2023-03-01,London,E92000001,,115,116,650000,580000,480000,,W1A 0AX\n"
    # London Postcode E1 6AN with a non-numeric price for a specific type
    "2023-03-01,London,E92000001,470000,118,119,NotAPrice,620000,510000,420000,E1 6AN\n"
    # London Postcode N1 9GU - for testing 'all' when AveragePrice is present
    "2023-03-01,London,E92000001,520000,122,123,720000,620000,520000,420000,N1 9GU\n"
)

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.config['TESTING'] = True

    def tearDown(self):
        self.app_context.pop()

    def _configure_mock_csv_response(self, mock_get, csv_data=MOCK_CSV_DATA, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        if status_code == 200:
            mock_response.text = csv_data
            mock_response.raise_for_status = MagicMock()
        else:
            mock_response.text = "Simulated HTTP Error"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

    # --- Modified Existing Tests ---
    @patch('property_price_app.backend.app.requests.get')
    def test_get_average_price_success_london_postcode_all_types(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=all')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['average_price'], 500000)
        self.assertEqual(data['property_type'], 'all')
        self.assertEqual(data['postcode'], 'SW1A0AA')
        self.assertEqual(data['data_period'], '2023-03-01')

    @patch('property_price_app.backend.app.requests.get')
    def test_get_average_price_success_london_postcode_detached(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=detached')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['average_price'], 700000)
        self.assertEqual(data['property_type'], 'detached')
        self.assertEqual(data['postcode'], 'SW1A0AA')

    def test_get_average_price_missing_postcode_parameter(self):
        response = self.client.get('/api/average_price?property_type=all')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Postcode parameter is required')

    def test_get_average_price_invalid_property_type_with_valid_postcode(self):
        # No mock needed as it's a parameter validation before API call
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=invalidtype')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invalid property type specified: invalidtype')

    # --- New Test Cases ---

    @patch('property_price_app.backend.app.requests.get')
    def test_postcode_not_found_in_csv(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        response = self.client.get('/api/average_price?postcode=SE19SG&property_type=all') # Valid London format, not in MOCK_CSV_DATA
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Postcode not found or not within London", data['error'])

    def test_non_london_postcode_format(self):
        # No mock needed, validation happens before API call
        response = self.client.get('/api/average_price?postcode=M11AA&property_type=all') # Manchester postcode
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid or non-London postcode format", data['error'])

    def test_invalid_postcode_format(self):
        # No mock needed
        response = self.client.get('/api/average_price?postcode=INVALIDCODE&property_type=all')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid or non-London postcode format", data['error'])

    @patch('property_price_app.backend.app.requests.get')
    def test_correct_property_type_extraction_flat(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        response = self.client.get('/api/average_price?postcode=WC2N5DU&property_type=flat-maisonette')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['average_price'], 450000)
        self.assertEqual(data['property_type'], 'flat-maisonette')
        self.assertEqual(data['postcode'], 'WC2N5DU')

    @patch('property_price_app.backend.app.requests.get')
    def test_missing_price_data_for_postcode_all_types(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        # W1A 0AX has an empty AveragePrice in MOCK_CSV_DATA
        response = self.client.get('/api/average_price?postcode=W1A0AX&property_type=all')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Price data is missing or empty", data['error'])
        self.assertEqual(data['postcode'], 'W1A0AX')

    @patch('property_price_app.backend.app.requests.get')
    def test_missing_price_data_for_postcode_specific_type(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        # W1A 0AX has an empty AveragePriceFlatMaisonette in MOCK_CSV_DATA
        response = self.client.get('/api/average_price?postcode=W1A0AX&property_type=flat-maisonette')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Price data is missing or empty", data['error'])
        self.assertEqual(data['postcode'], 'W1A0AX')
        self.assertEqual(data['property_type'], 'flat-maisonette')

    @patch('property_price_app.backend.app.requests.get')
    def test_unparseable_price_for_specific_type(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        # E1 6AN has "NotAPrice" for AveragePriceDetached
        response = self.client.get('/api/average_price?postcode=E16AN&property_type=detached')
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("Could not parse price value 'NotAPrice'", data['error'])

    @patch('property_price_app.backend.app.requests.get')
    def test_case_insensitivity_and_space_postcode_search(self, mock_get):
        self._configure_mock_csv_response(mock_get)
        postcodes_to_test = ["sw1a 0aa", "SW1A0AA", " sw1a  0aa ", "sW1a 0Aa"]
        for pc in postcodes_to_test:
            with self.subTest(postcode=pc):
                response = self.client.get(f'/api/average_price?postcode={pc}&property_type=all')
                self.assertEqual(response.status_code, 200, msg=f"Failed for postcode: {pc}")
                data = json.loads(response.data)
                self.assertEqual(data['average_price'], 500000)
                self.assertEqual(data['postcode'], pc) # The returned postcode should be what user queried

    @patch('property_price_app.backend.app.requests.get')
    def test_download_csv_failed_http_error(self, mock_get):
        self._configure_mock_csv_response(mock_get, status_code=503) # Service Unavailable
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=all')
        self.assertEqual(response.status_code, 502) # Bad Gateway, as our app failed to get data
        data = json.loads(response.data)
        self.assertIn("Failed to download HMLR data CSV with status 503", data['error'])

    @patch('property_price_app.backend.app.requests.get')
    def test_download_csv_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("CSV Download timed out")
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=all')
        self.assertEqual(response.status_code, 504) # Gateway Timeout
        data = json.loads(response.data)
        self.assertIn("HMLR data CSV download timed out", data['error'])

    @patch('property_price_app.backend.app.requests.get')
    def test_empty_csv_downloaded(self, mock_get):
        self._configure_mock_csv_response(mock_get, csv_data="")
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=all')
        self.assertEqual(response.status_code, 404) # No data rows found effectively
        data = json.loads(response.data)
        # This error comes from csv.DictReader not finding headers, leading to no rows.
        # The application's current error for this situation is "Postcode not found or not within London..."
        # because the loop over `reader` will yield nothing.
        self.assertIn("Postcode not found or not within London", data['error'])


    @patch('property_price_app.backend.app.requests.get')
    def test_csv_headers_only_downloaded(self, mock_get):
        self._configure_mock_csv_response(mock_get, csv_data=MOCK_CSV_HEADER + "\n")
        response = self.client.get('/api/average_price?postcode=SW1A0AA&property_type=all')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Postcode not found or not within London", data['error'])

    @patch('property_price_app.backend.app.requests.get')
    def test_postcode_present_but_not_london_in_csv(self, mock_get):
        # This test ensures that even if a postcode (e.g. M1 1AA) is in the CSV,
        # if its RegionName is not 'London', it's treated as not found for our purposes.
        self._configure_mock_csv_response(mock_get)
        # M1 1AA is in mock CSV but RegionName is "North West"
        # The is_london_postcode() check in app.py should catch M1 1AA before CSV processing.
        # This test is more about ensuring the CSV filtering for 'RegionName' == 'london' works
        # if a non-London postcode somehow bypassed the initial regex check (e.g. if regex was broader).
        # For this, we'll use a London-formatted postcode that we'll imagine has a non-London region in CSV.

        custom_csv_data = (
            MOCK_CSV_HEADER + "\n"
            "2023-03-01,NotLondon,E92000001,500000,120,121,700000,600000,500000,400000,SW1A0BB\n" # SW1A0BB with RegionName "NotLondon"
            "2023-03-01,London,E92000001,550000,125,126,750000,650000,550000,450000,WC2N5DU\n"
        )
        self._configure_mock_csv_response(mock_get, csv_data=custom_csv_data)

        response = self.client.get('/api/average_price?postcode=SW1A0BB&property_type=all')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Postcode not found or not within London", data['error'])


if __name__ == '__main__':
    unittest.main()
