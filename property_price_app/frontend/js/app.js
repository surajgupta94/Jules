document.addEventListener('DOMContentLoaded', () => {
    const searchButton = document.getElementById('search_button');
    const loadingMessageDiv = document.getElementById('loading_message'); // New

    // Filter inputs
    const postcodeNnput = document.getElementById('postcode'); // Changed from locationInput
    const propertyTypeSelect = document.getElementById('property_type');
    const minPriceInput = document.getElementById('min_price');
    const maxPriceInput = document.getElementById('max_price');

    // Result display elements
    const errorMessageDiv = document.getElementById('error_message');
    const resultLocationSpan = document.getElementById('res_location');
    const resultPropertyTypeSpan = document.getElementById('res_property_type');
    const resultAvgPriceSpan = document.getElementById('res_avg_price');
    const resultDataPeriodSpan = document.getElementById('res_data_period');

    searchButton.addEventListener('click', async () => {
        // Clear previous results and errors
        errorMessageDiv.textContent = '';
        resultLocationSpan.textContent = 'N/A';
        resultPropertyTypeSpan.textContent = 'N/A';
        resultAvgPriceSpan.textContent = 'N/A';
        resultDataPeriodSpan.textContent = 'N/A';

        const postcode = postcodeNnput.value.trim(); // Changed from location
        const propertyType = propertyTypeSelect.value;
        const minPrice = minPriceInput.value;
        const maxPrice = maxPriceInput.value;

        if (!postcode) { // Changed from location
            errorMessageDiv.textContent = 'Postcode is required.'; // Changed message
            return;
        }

        const params = new URLSearchParams();
        params.append('postcode', postcode); // Changed from location to postcode
        params.append('property_type', propertyType);

        if (minPrice) {
            params.append('min_price', minPrice);
        }
        if (maxPrice) {
            params.append('max_price', maxPrice);
        }

        // Show loading message and disable button
        loadingMessageDiv.style.display = 'block';
        searchButton.disabled = true;

        try {
            const response = await fetch(`/api/average_price?${params.toString()}`);
            const data = await response.json();

            if (!response.ok) {
                errorMessageDiv.textContent = data.error || `Error: ${response.status} ${response.statusText}`;
            } else {
                resultLocationSpan.textContent = data.postcode || 'N/A'; // Changed from data.location to data.postcode
                resultPropertyTypeSpan.textContent = data.property_type || 'N/A';
                resultAvgPriceSpan.textContent = data.average_price ? `£${data.average_price.toLocaleString()}` : 'N/A';
                resultDataPeriodSpan.textContent = data.data_period || 'N/A';
            }
        } catch (error) {
            console.error('Frontend error fetching average price:', error);
            errorMessageDiv.textContent = 'A network error occurred. Please try again.';
        } finally {
            // Hide loading message and re-enable button
            loadingMessageDiv.style.display = 'none';
            searchButton.disabled = false;
        }
    });
});
