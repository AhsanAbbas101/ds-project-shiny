import sqlitecloud
import pandas as pd
from keys import DB_CONNECTION_STRING

from datetime import datetime
from dateutil.relativedelta import relativedelta

columns = [
    'Aika',                        # Timestamp
    'Hinta_snt_per_kWh',            # Price in cents per kWh
    'Keskituulen_nopeus_m_per_s',   # Average wind speed in m/s
    'Lampotilan_keskiarvo_C',       # Average temperature in Celsius
    'Kulutus_kWh_per_h',            # Energy consumption in kWh per hour
    'Tuotanto_kW',                  # Production in kW
    'is_holiday'                    # Holiday flag (1 if holiday, 0 if not)
]

def get_last_n_rows(n):

    conn = sqlitecloud.connect(DB_CONNECTION_STRING)

    query = f'SELECT * FROM PRICES ORDER BY Aika DESC LIMIT {n};'
    
    print(query)

    cursor = conn.execute(query)
    result = cursor.fetchall()

    df = pd.DataFrame(result,columns=columns)
    df['Aika'] = pd.to_datetime(df['Aika'])
    conn.close()
    return df

def get_all_data_from_db():

    conn = sqlitecloud.connect(DB_CONNECTION_STRING)

    cursor = conn.execute("SELECT * FROM PRICES")
    result = cursor.fetchall()

    df = pd.DataFrame(result,columns=columns)

    conn.close()
    return df

def get_rows_between(startDate, endDate):

    query = f"SELECT * FROM PRICES WHERE Aika BETWEEN '{str(startDate)}' AND '{str(endDate)}';"

    conn = sqlitecloud.connect(DB_CONNECTION_STRING)

    cursor = conn.execute(query)
    result = cursor.fetchall()

    df = pd.DataFrame(result,columns=columns)

    conn.close()
    return df
def get_data():

    df = get_last_n_rows(1)
    df['Aika'] = pd.to_datetime(df['Aika'])
    last_datetime = df.iloc[0]['Aika'] 
    print(df.iloc[0])
    yesterday = datetime.now().date() - relativedelta(days=1)
    print(yesterday)

    if last_datetime.date() == yesterday: 
        print('Date available')
    else:
        pass        

#get_data()

#print(get_rows_between(datetime(2024,9,21),datetime(2024,10,25,0,0,0)))

"""
data = pd.read_csv('./.data/data.csv')
data = data.rename(columns={
    'Aika': 'Aika',  # Keep the same
    'Hinta (snt/kWh)': 'Hinta_snt_per_kWh',
    'Keskituulen nopeus [m/s]': 'Keskituulen_nopeus_m_per_s',
    'Lämpötilan keskiarvo [°C]': 'Lampotilan_keskiarvo_C',
    'Kulutus (kWh/h)': 'Kulutus_kWh_per_h',
    'Tuotanto (kW)': 'Tuotanto_kW',
    'is_holiday': 'is_holiday'  
})

data['Aika'] = pd.to_datetime(data['Aika'])
data = data[data['Aika'] >= '2024-01-01']
conn = sqlitecloud.connect(DB_CONNECTION_STRING)
data.to_sql('PRICES', conn, if_exists='append', index=False)
conn.close()
"""