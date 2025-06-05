from flask import Flask, jsonify, request, render_template
import requests # We'll need this later
import csv
import io
import sys
import re # For postcode validation

app = Flask(__name__, template_folder='templates', static_folder='../frontend')

# Updated HMLR Data Endpoint to the full CSV file
HMLR_DATA_ENDPOINT = "https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data/UK-HPI-full-file-2025-03.csv"

# Regex for basic London postcode validation (simplified)
# Covers E, EC, N, NW, S, SE, SW, W, WC. Allows for optional letter in outward code district.
LONDON_POSTCODE_REGEX = re.compile(r"^(E|EC|N|NW|S|SE|SW|W|WC)\d{1,2}[A-Z]?\s*\d[A-Z]{2}$", re.IGNORECASE)

def is_london_postcode(postcode):
    """
    Validates if the given string is a likely London postcode.
    This is a simplified check and might need refinement for production use.
    """
    if not postcode:
        return False
    return bool(LONDON_POSTCODE_REGEX.match(postcode.strip()))

@app.route('/')
def index():
    return render_template('index.html') # We'll create this basic HTML file next

@app.route('/api/average_price', methods=['GET'])
def get_average_price():
    postcode_query = request.args.get('postcode')
    property_type_query = request.args.get('property_type', 'all') # Default to 'all'

    if not postcode_query:
        return jsonify({"error": "Postcode parameter is required"}), 400

    if not is_london_postcode(postcode_query):
        return jsonify({"error": "Invalid or non-London postcode format provided. Postcode must be a valid London postcode."}), 400

    # Normalize postcode for comparison (uppercase, remove spaces)
    normalised_postcode_query = postcode_query.upper().replace(' ', '')

    property_type_to_column = {
        'all': 'AveragePrice',
        'detached': 'AveragePriceDetached',
        'semi-detached': 'AveragePriceSemiDetached',
        'terraced': 'AveragePriceTerraced',
        'flat-maisonette': 'AveragePriceFlatMaisonette',
    }

    requested_col_name = property_type_to_column.get(property_type_query.lower())

    if not requested_col_name:
        return jsonify({"error": f"Invalid property type specified: {property_type_query}"}), 400

    # The API URL is now the direct link to the full CSV
    api_url = HMLR_DATA_ENDPOINT
    headers = {
        'User-Agent': 'PropertyPriceApp/1.0' # Good practice to set a User-Agent
    }

    try:
        # Download the full CSV
        response = requests.get(api_url, headers=headers, timeout=30) # Increased timeout for larger file
        response.raise_for_status()

        csv_data = response.text
        csvfile = io.StringIO(csv_data)
        reader = csv.DictReader(csvfile)

        matching_rows = []
        # Assume 'Postcode' and 'RegionName' are the correct column names.
        # This might need verification by inspecting the CSV.
        postcode_col_name = 'Postcode' # Adjust if CSV uses a different name
        region_col_name = 'RegionName' # Adjust if CSV uses a different name

        for row_raw in reader:
            row = {k.strip(): v for k, v in row_raw.items()} # Clean keys

            # Normalize postcode from CSV for comparison
            csv_postcode = row.get(postcode_col_name, '').upper().replace(' ', '')
            csv_region = row.get(region_col_name, '')

            if csv_postcode == normalised_postcode_query and csv_region.lower() == 'london':
                matching_rows.append(row)

        if not matching_rows:
            return jsonify({"error": "Postcode not found or not within London in the dataset."}), 404

        # For simplicity, we'll use the first matching row.
        # If multiple property types exist for the same postcode, this logic might need enhancement
        # or rely on the property_type_query to select the correct data.
        # The current HMLR full file structure seems to be one row per area/date/property_type combination.
        # So, if a postcode appears multiple times, it's likely for different dates or pre-aggregated property types.
        # We need to find the row that matches the property_type_query, if specified.

        data_row = None
        if property_type_query == 'all': # 'AveragePrice' is usually for all types
            # Find a row that ideally has 'AveragePrice' and matches the postcode.
            # The CSV structure might have specific rows for 'all property types' or just individual ones.
            # Let's assume for now that if 'AveragePrice' is requested, we find *any* relevant row for the postcode
            # and extract that. This part might need refinement based on actual CSV structure.
            for r in matching_rows:
                if requested_col_name in r and r[requested_col_name]:
                    data_row = r
                    break
            if not data_row: # Fallback if specific 'AveragePrice' row not found but others exist
                data_row = matching_rows[0] if matching_rows else None

        else: # Specific property type requested
            for r in matching_rows:
                # The CSV might have columns like 'DetachedPrice', 'SemiDetachedPrice' etc.
                # Or it might have a 'PropertyType' column and a generic 'Price' column.
                # Assuming the former, based on `property_type_to_column`
                # Select row if column name exists, even if value is empty (handled later)
                if requested_col_name in r:
                    data_row = r
                    break

        if not data_row:
             return jsonify({"error": f"Data for property type '{property_type_query}' not found for the given London postcode."}), 404

        if requested_col_name in data_row:
            price_str = data_row[requested_col_name]
            # Assuming 'Date' column for period, adjust if different
            data_period = data_row.get("Date", data_row.get("Period", "N/A"))

            if not price_str or price_str.isspace():
                return jsonify({
                    "error": f"Price data is missing or empty for {requested_col_name} in period {data_period}",
                    "postcode": postcode_query,
                    "property_type": property_type_query,
                    "data_period": data_period
                }), 404

            try:
                cleaned_price_str = price_str.replace(',', '')
                if not cleaned_price_str: # Check if empty after stripping commas
                    return jsonify({
                        "error": f"Price data is empty for {requested_col_name} in period {data_period} after cleaning.",
                        "postcode": postcode_query,
                        "property_type": property_type_query,
                        "data_period": data_period
                    }), 404

                price = float(cleaned_price_str)
                return jsonify({
                    "average_price": price,
                    "postcode": postcode_query,
                    "property_type": property_type_query,
                    "data_period": data_period,
                    "source_url": api_url # This is now the URL of the CSV file
                })
            except ValueError:
                return jsonify({
                    "error": f"Could not parse price value '{price_str}' for {requested_col_name} in period {data_period}",
                    "postcode": postcode_query,
                    "property_type": property_type_query,
                    "data_period": data_period
                }), 500
        else:
            # This case means the requested_col_name (e.g. 'AveragePriceDetached') was not in the found data_row
            print(f"DEBUG: Requested column '{requested_col_name}' not found in data_row. Available columns: {list(data_row.keys()) if data_row else 'No data row'}", file=sys.stderr)
            return jsonify({
                "error": f"Data column '{requested_col_name}' not found for the specified postcode and property type.",
                "available_columns": list(data_row.keys()) if data_row else [],
                "postcode": postcode_query,
                "property_type": property_type_query
            }), 404

    except requests.exceptions.HTTPError as e:
        # This error is for the CSV download itself
        return jsonify({"error": f"Failed to download HMLR data CSV with status {e.response.status_code}: {str(e)}. (Source: {api_url})"}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": f"HMLR data CSV download timed out. (Source: {api_url})"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to download HMLR data CSV: {str(e)}. (Source: {api_url})"}), 502
    except Exception as e: # Catch-all for other processing errors
        print(f"ERROR: An unexpected error occurred: {str(e)}", file=sys.stderr) # Log detailed error
        return jsonify({"error": f"An unexpected error occurred while processing data. Please check server logs."}), 500

if __name__ == '__main__':
    app.run(debug=True)
