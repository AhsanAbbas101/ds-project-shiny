# Introduction
This project was done as a part of ”Introduction to data science” course in Helsinki University. The focus of this project was to predict the electricity spot prices in Finland.

# Working
The webpage implementation is based on the Python library shiny. This allowed to create the web user interface purely through Python. The historical data is stored to a cloud database using sqlite
, and forecast data is accessed through the Forecast API methods. The prediction model is loaded from the stored joblib file.

To get started, create an `.env` file to store the following environement variables:
- `DB_CONNECTION_STRING`: connection string for sqlite database
- `FINGRID_CONSUMPTION_API_KEY`: api key for consumption
- `FINGRID_PRODUCTION_API_KEY`: api key for production

Install dependencies and run the app using:
```
pip install -r requirements.txt
shiny run app.py
```

