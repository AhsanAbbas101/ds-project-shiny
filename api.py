import os
from pathlib import Path

import requests
import pandas as pd

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from keys import FINGRID_CONSUMPTION_API_KEY, FINGRID_PRODUCTION_API_KEY
from shared import holidays

WEATHER_API_ENDPOINT = 'https://api.open-meteo.com/v1/forecast'

FINGRID_CONSUMPTION_FORECAST_ENDPOINT = 'https://data.fingrid.fi/api/datasets/165/data'
FINGRID_PRODUCTION_FORECAST_ENDPOINT= 'https://data.fingrid.fi/api/datasets/242/data'
PRICE_API_FORECAST_ENDPOINT = 'https://api.porssisahko.net/v1/latest-prices.json'

PRICE_API_ENDPOINT = 'https://api.porssisahko.net/v1/price.json'
FINGRID_CONSUMPTION_ENDPOINT = 'https://data.fingrid.fi/api/datasets/124/data'
FINGRID_PRODUCTION_ENDPOINT= 'https://data.fingrid.fi/api/datasets/192/data'


"""
'Aika',                        # Timestamp
'Hinta_snt_per_kWh',            # Price in cents per kWh
'Keskituulen_nopeus_m_per_s',   # Average wind speed in m/s
'Lampotilan_keskiarvo_C',       # Average temperature in Celsius
'Kulutus_kWh_per_h',            # Energy consumption in kWh per hour
'Tuotanto_kW',                  # Production in kW
'is_holiday'                    # Holiday flag (1 if holiday, 0 if not)
"""

def process_fingrid_data(ec_pred_df, col):

    # Let's drop the first column
    ec_pred_df = ec_pred_df.drop(['datasetId'], axis=1)

    # Changing the names of the columns
    ec_pred_columns = ['Aika', f'{col} (MW)']
    if ec_pred_df.columns.tolist() != ec_pred_columns:
        ec_pred_df.columns = ['Ylimääräinen', 'Aika', f'{col} (MW)']

    ec_pred_df = ec_pred_df[ec_pred_columns]

    # Changing MW to kW
    ec_pred_df[f'{col} (MW)'] = ec_pred_df[f'{col} (MW)'] * 1000
    ec_pred_df.rename(columns={f'{col} (MW)': f'{col} (kW)'}, inplace=True)

    # Replacing unnecessary letters and numbers
    ec_pred_df['Aika'] = ec_pred_df['Aika'].str.replace('T', ' ').str.replace('Z', '').str.replace('.000', '')

    ec_pred_df['Aika'] = ec_pred_df['Aika'].values[::-1]
    ec_pred_df[f'{col} (kW)'] = ec_pred_df[f'{col} (kW)'].values[::-1]

    # Making sure that all time values are datetime objects
    ec_pred_df['Aika'] = pd.to_datetime(ec_pred_df['Aika'])

    # Taking the hourly mean of electricity production
    ec_pred_df.set_index('Aika', inplace=True)
    ec_pred_df = ec_pred_df.resample('1H').mean().interpolate(method='linear').reset_index()

    # Restoring the columns
    ec_pred_df = ec_pred_df[['Aika', f'{col} (kW)']]

    # Removing the duplicates
    ec_pred_df = ec_pred_df.loc[~ec_pred_df['Aika'].duplicated(keep='first')]

    return ec_pred_df

def get_electricity_consumption_forecast():
    
    today = datetime.today().date()
    next_day = today + relativedelta(days=1)
    start = today.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = next_day.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers ={'x-api-key': FINGRID_CONSUMPTION_API_KEY}
    params={'startTime': start, 'endTime': end, 'pageSize': 2000}

    try:
        response = requests.get(FINGRID_CONSUMPTION_FORECAST_ENDPOINT, headers=headers,params=params)

        if response.status_code == 200:

            x = response.json()
            ec_pred_df = pd.DataFrame(x['data'])
            print(ec_pred_df)    

            ec_pred_df = process_fingrid_data(ec_pred_df,col='Kulutus')

            ec_pred_df.rename(columns={'Kulutus (kW)': 'Kulutus_kWh_per_h'}, inplace=True)

            return ec_pred_df
        else:
            print(f'get_electricity_consumption_forecast: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_electricity_consumption_forecast: An exception occurred:", e)
        return None

def get_electricity_production_forecast():
    
    today = datetime.today().date()
    next_day = today + relativedelta(days=1)
    start = today.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = next_day.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers ={'x-api-key': FINGRID_PRODUCTION_API_KEY}
    params={'startTime': start, 'endTime': end, 'pageSize': 2000}

    try:
        response = requests.get(FINGRID_PRODUCTION_FORECAST_ENDPOINT, headers=headers,params=params)

        if response.status_code == 200:

            x = response.json()
            ec_pred_df = pd.DataFrame(x['data'])
            print(ec_pred_df)    

            ec_pred_df = process_fingrid_data(ec_pred_df,col='Tuotanto')

            ec_pred_df.rename(columns={'Tuotanto (kW)': 'Tuotanto_kW'}, inplace=True)

            return ec_pred_df
        else:
            print(f'get_electricity_consumption_forecast: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_electricity_consumption_forecast: An exception occurred:", e)
        return None

def get_weather_forecast(latitude:float=60.192059,
                        longitude:float=24.945831,
                        forecast_days:int=7,
                        past_days:int=0) -> pd.DataFrame|None:
    """Get weather forecast data from open-meteo api

    Args:
        latitude (float, optional): Latitude of location. Defaults to 60.192059 latitude of helsinki finland.
        longitude (float, optional): Longitude of location. Defaults to 24.945831 longitude of helsinki finland.
        forecast_days (int, optional): Number of days to forecast. Defaults to 7. Accepted Range 0-16
        past_days (int, optional): Number of past days to include in data. Defaults to 0. Accepted Range 0-92

    Returns:
        pd.DataFrame|None: dataframe containing weather forecast on success. dataframe has columns : time, temperature, wind_speed. Returns None on failure.
        
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": forecast_days,
        "past_days": past_days,
        "temperature_unit": 'celsius',
        "wind_speed_unit": 'ms',
        "hourly": ['temperature_2m','wind_speed_10m']
    }

    try:
        response = requests.get(WEATHER_API_ENDPOINT, params=params)

        if response.status_code == 200:
            data = response.json()

            columns = {'time':'Aika','temperature_2m':'Lampotilan_keskiarvo_C','wind_speed_10m':'Keskituulen_nopeus_m_per_s'}
            forecast = pd.DataFrame(data['hourly']).rename(columns=columns)
            forecast['Aika'] = pd.to_datetime(forecast['Aika'])
            return forecast
        else:
            print(f'get_weather_forecast: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_weather_forecast: An exception occurred:", e)
        return None

def get_price_forecast():
    try:
        response = requests.get(PRICE_API_FORECAST_ENDPOINT)

        if response.status_code == 200:
            data = response.json()

            columns = {'price':'Hinta_snt_per_kWh','startDate':'Aika'}
            forecast = pd.DataFrame(data['prices']).rename(columns=columns)
            forecast['Aika'] =  forecast['Aika'].str.replace('T', ' ').str.replace('Z', '').str.replace('.000', '')
            forecast['Aika'] = pd.to_datetime(forecast['Aika'])
            forecast.drop(columns=['endDate'],inplace=True)

            return forecast
        else:
            print(f'get_weather_forecast: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_weather_forecast: An exception occurred:", e)
        return None

def get_price_past_data(date:datetime):
    try:
        params = {'date':str(date.date()),'hour':0}
        data = pd.DataFrame(columns=['Aika','Hinta_snt_per_kWh'])
        prices = []

        for hour in range(24):
            params['hour'] = hour
            response = requests.get(PRICE_API_ENDPOINT,params=params)

            if response.status_code == 200:
                res = response.json()
                prices.append(res['price'])
            else:
                print(f'get_price_past_data: Error getting data. Response code: {response.status_code}')
                return None
        if len(prices):
            data = pd.DataFrame({
                'Aika': [date.replace(hour=hour) for hour in range(24)],
                'Hinta_snt_per_kWh': prices
            })

        return data
        
    except Exception as e:
        print("get_price_past_data: An exception occurred:", e)
        return None    

def get_electricity_consumption(startDate, endDate):

    start = startDate.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = endDate.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers ={'x-api-key': FINGRID_CONSUMPTION_API_KEY}
    params={'startTime': start, 'endTime': end, 'pageSize': 20000-1}

    try:
        response = requests.get(FINGRID_CONSUMPTION_ENDPOINT, headers=headers,params=params)

        if response.status_code == 200:

            x = response.json()
            ec_pred_df = pd.DataFrame(x['data'])
            print(ec_pred_df)    

            ec_pred_df = process_fingrid_data(ec_pred_df,col='Kulutus')

            ec_pred_df.rename(columns={'Kulutus (kW)': 'Kulutus_kWh_per_h'}, inplace=True)

            return ec_pred_df
        else:
            print(f'get_electricity_consumption: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_electricity_consumption: An exception occurred:", e)
        return None

def get_electricity_production(startDate,endDate):

    start = startDate.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = endDate.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers ={'x-api-key': FINGRID_PRODUCTION_API_KEY}
    params={'startTime': start, 'endTime': end, 'pageSize': 20000-1}

    try:
        response = requests.get(FINGRID_PRODUCTION_ENDPOINT, headers=headers,params=params)

        if response.status_code == 200:

            x = response.json()
            ec_pred_df = pd.DataFrame(x['data'])
            print(ec_pred_df)    

            ec_pred_df = process_fingrid_data(ec_pred_df,col='Tuotanto')

            ec_pred_df.rename(columns={'Tuotanto (kW)': 'Tuotanto_kW'}, inplace=True)

            return ec_pred_df
        else:
            print(f'get_electricity_production: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_electricity_production: An exception occurred:", e)
        return None

def get_weather(startDate:datetime,
                        endDate:datetime,
                        latitude:float=60.192059,
                        longitude:float=24.945831) -> pd.DataFrame|None:
    """Get weather forecast data from open-meteo api

    Args:
        latitude (float, optional): Latitude of location. Defaults to 60.192059 latitude of helsinki finland.
        longitude (float, optional): Longitude of location. Defaults to 24.945831 longitude of helsinki finland.

    Returns:
        pd.DataFrame|None: dataframe containing weather forecast on success. dataframe has columns : time, temperature, wind_speed. Returns None on failure.
        
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": str(startDate.date()),
        "end_date": str(endDate.date()),
        "temperature_unit": 'celsius',
        "wind_speed_unit": 'ms',
        "hourly": ['temperature_2m','wind_speed_10m']
    }

    try:
        response = requests.get(WEATHER_API_ENDPOINT, params=params)

        if response.status_code == 200:
            data = response.json()

            columns = {'time':'Aika','temperature_2m':'Lampotilan_keskiarvo_C','wind_speed_10m':'Keskituulen_nopeus_m_per_s'}
            forecast = pd.DataFrame(data['hourly']).rename(columns=columns)
            forecast['Aika'] = pd.to_datetime(forecast['Aika'])
            return forecast
        else:
            print(f'get_weather_forecast: Error getting data. Response code: {response.status_code}')
            return None
        
    except Exception as e:
        print("get_weather_forecast: An exception occurred:", e)
        return None

def get_forecast():

    app_dir = Path(__file__).parent
    if os.path.exists(app_dir / "forecast.csv"):
        print('forecast available')
        forecast = pd.read_csv(app_dir / "forecast.csv")
        forecast['Aika'] = pd.to_datetime(forecast['Aika'])

        if forecast.iloc[0]['Aika'].date() == datetime.now().date():    # same date
             return forecast

    consumption = get_electricity_consumption_forecast()
    time_wind = get_weather_forecast(forecast_days=1)
    production = get_electricity_production_forecast()
    price = get_price_forecast()

    print('time_wind shape: ',time_wind.shape)
    print('consumption shape: ',consumption.shape)
    print('production shape: ',production.shape)
    print('price shape: ',price.shape)

    forecast = pd.merge(consumption, production, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast = pd.merge(forecast, time_wind, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast = pd.merge(forecast, price, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast['date'] = forecast['Aika'].dt.date
    forecast['is_holiday'] = forecast['date'].isin(holidays['Holidays'].dt.date)

    forecast['is_holiday'] = forecast['is_holiday'].replace({True: 1, False: 0})
    forecast.drop(columns=['date'],inplace=True)

    columns = ['Aika','Hinta_snt_per_kWh','Keskituulen_nopeus_m_per_s','Lampotilan_keskiarvo_C','Kulutus_kWh_per_h','Tuotanto_kW','is_holiday']
    forecast = forecast[columns]
    forecast.to_csv(app_dir / "forecast.csv", mode='w', index=False)

    return forecast

def get_old_data(startDate,endDate):

    app_dir = Path(__file__).parent
    def daterange(start_date: date, end_date: date):
        days = int((end_date - start_date).days) + 1    #inclusive
        for n in range(days):
            yield start_date + timedelta(n)

    consumption = get_electricity_consumption(startDate,endDate)
    time_wind = get_weather(startDate,endDate)
    production = get_electricity_production(startDate,endDate)
    price = pd.DataFrame(columns=['Aika','Hinta_snt_per_kWh'])
    for single_date in daterange(startDate, endDate):
        price = pd.concat([price,get_price_past_data(single_date)],ignore_index=False)
        
    print('time_wind shape: ',time_wind.shape)
    print('consumption shape: ',consumption.shape)
    print('production shape: ',production.shape)
    print('price shape: ',price.shape)

    forecast = pd.merge(consumption, production, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast = pd.merge(forecast, time_wind, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast = pd.merge(forecast, price, on='Aika', how='inner')
    print('forecast shape: ',forecast.shape)

    forecast['date'] = forecast['Aika'].dt.date
    forecast['is_holiday'] = forecast['date'].isin(holidays['Holidays'].dt.date)

    forecast['is_holiday'] = forecast['is_holiday'].replace({True: 1, False: 0})
    forecast.drop(columns=['date'],inplace=True)

    columns = ['Aika','Hinta_snt_per_kWh','Keskituulen_nopeus_m_per_s','Lampotilan_keskiarvo_C','Kulutus_kWh_per_h','Tuotanto_kW','is_holiday']
    forecast = forecast[columns]
    forecast.to_csv(app_dir / "old_data.csv", mode='w', index=False)


#get_old_data(datetime(2024,9,21),datetime(2024,10,24))

