# UK Property Price Viewer

This web application allows users to view the average property prices in various regions of the UK, based on data from HM Land Registry. Users can filter by location and property type to get specific average price information.

## Features

-   Fetches live data from the HM Land Registry UK House Price Index (UKHPI).
-   Filter by location (e.g., England, Scotland, East Midlands).
-   Filter by property type (All, Detached, Semi-Detached, Terraced, Flat/Maisonette).
-   Displays the latest average price and the corresponding data period.
-   Simple, user-friendly web interface.
-   Includes backend unit tests.

## Data Source

The application uses data published by [HM Land Registry](https://landregistry.data.gov.uk/). It specifically queries the UK House Price Index (UKHPI) data for regions.

## Prerequisites

-   Python 3.7+
-   Pip (Python package installer)
-   Git (for cloning, optional if downloading the source code directly)

## Setup and Running the Application

1.  **Clone the Repository (or Download Source)**:
    ```bash
    git clone <repository_url>
    cd property_price_app
    ```
    (If you downloaded the source, navigate to the `property_price_app` directory).

2.  **Create and Activate a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies**:
    Make sure you are in the `property_price_app` root directory where `requirements.txt` is located.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Flask Application**:
    ```bash
    python backend/app.py
    ```

5.  **Access the Website**:
    Open your web browser and navigate to:
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Running Unit Tests

To run the backend unit tests:

1.  Ensure your virtual environment is activated and dependencies are installed.
2.  Navigate to the project root directory (`property_price_app`).
3.  Execute the following command:
    ```bash
    python -m unittest backend.test_app -v
    ```

## Project Structure

-   `property_price_app/`: Root directory.
    -   `backend/`: Contains the Flask backend application.
        -   `app.py`: The main Flask application file.
        -   `test_app.py`: Unit tests for the backend.
        -   `templates/`: HTML templates (e.g., `index.html`).
        -   `__init__.py`: Makes `backend` a Python package.
    -   `frontend/`: Contains static frontend files.
        -   `css/style.css`: CSS stylesheets.
        -   `js/app.js`: JavaScript files.
    -   `requirements.txt`: Python dependencies for the project.
    -   `README.md`: This file.
    -   `venv/`: Virtual environment directory (if created).
