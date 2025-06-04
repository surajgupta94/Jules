from flask import Flask, jsonify, request, render_template
import requests # We'll need this later
import csv
import io

app = Flask(__name__, template_folder='templates', static_folder='../frontend')

# More specific for the CSVs we need:
HMLR_DATA_ENDPOINT = "http://landregistry.data.gov.uk/data/ukhpi/region"

@app.route('/')
def index():
    return render_template('index.html') # We'll create this basic HTML file next

@app.route('/api/average_price', methods=['GET'])
def get_average_price():
    # Placeholder for filter parameters
    location_query = request.args.get('location')
    property_type_query = request.args.get('property_type', 'all') # Default to 'all'

    if not location_query:
        return jsonify({"error": "Location parameter is required"}), 400

    # Basic slugification for location (lowercase, replace spaces with hyphens)
    location_slug = location_query.lower().replace(' ', '-')

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

    api_url = f"{HMLR_DATA_ENDPOINT}/{location_slug}.csv"
    headers = {
        'User-Agent': 'PropertyPriceApp/1.0'
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()

        csv_data = response.text
        csvfile = io.StringIO(csv_data)
        reader = csv.DictReader(csvfile)

        data_row = None
        for row in reader:
            if row:
                data_row = {k.strip(): v for k, v in row.items()}
                break

        if not data_row:
             return jsonify({"error": "No data rows found in HMLR API response for the location"}), 404

        if requested_col_name in data_row:
            price_str = data_row[requested_col_name]
            data_period = data_row.get("Period", "N/A")

            if not price_str or price_str.isspace():
                 return jsonify({
                    "error": f"Price data is missing or empty for {requested_col_name} in period {data_period}",
                    "location": location_query,
                    "property_type": property_type_query,
                    "data_period": data_period
                }), 404

            try:
                cleaned_price_str = price_str.replace(',', '')
                if not cleaned_price_str:
                    return jsonify({
                        "error": f"Price data is empty for {requested_col_name} in period {data_period} after cleaning.",
                        "location": location_query,
                        "property_type": property_type_query,
                        "data_period": data_period
                    }), 404

                price = float(cleaned_price_str)
                return jsonify({
                    "average_price": price,
                    "location": location_query,
                    "property_type": property_type_query,
                    "data_period": data_period,
                    "source_url": api_url
                })
            except ValueError:
                return jsonify({
                    "error": f"Could not parse price value '{price_str}' for {requested_col_name} in period {data_period}",
                    "location": location_query,
                    "property_type": property_type_query,
                    "data_period": data_period
                }), 500
        else:
            return jsonify({
                "error": f"Data column '{requested_col_name}' not found in API response.",
                "available_columns": list(data_row.keys()) if data_row else [],
                "location": location_query,
                "property_type": property_type_query,
                "source_url": api_url
            }), 404

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": f"Data not found for location '{location_query}'. Please check the location name. (Source: {api_url})"}), 404
        return jsonify({"error": f"HMLR API request failed with status {e.response.status_code}: {str(e)}. (Source: {api_url})"}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": f"HMLR API request timed out. (Source: {api_url})"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to retrieve data from HMLR API: {str(e)}. (Source: {api_url})"}), 502
    except Exception as e:
        return jsonify({"error": f"An error occurred while processing data: {str(e)}. (Source: {api_url})"}), 500

if __name__ == '__main__':
    app.run(debug=True)
