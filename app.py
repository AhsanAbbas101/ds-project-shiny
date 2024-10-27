print('Logging...')
import faicons as fa
import plotly.express as px

# Load data and compute static values
from shared import app_dir
from shinywidgets import render_plotly

from shiny import reactive, render
from shiny.express import input, ui

from datetime import datetime, time

import pandas as pd

from pathlib import Path
import os

from db import get_rows_between
from api import get_forecast

FORECAST_DATA = None#get_forecast()

import joblib

model = joblib.load(app_dir / 'model/model.joblib')
#FORECAST_DATA['predictions'] = model.predict(FORECAST_DATA.drop(columns=['Aika','Hinta_snt_per_kWh']))

date_rng = (datetime(2024,1,1).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'))

selected_date_range = reactive.value((datetime.now().date(),datetime.now().date()))

# Add page title and sidebar
ui.page_opts(title="Electricity Spot Price Prediction", fillable=True)

with ui.sidebar(open="desktop"):

    ui.input_date("startDate", "Start Date", min=date_rng[0],max=date_rng[1], value=date_rng[1])  
    ui.input_date("endDate", "End Date", min=date_rng[0],max=date_rng[1], value=date_rng[1])  
    ui.input_action_button("filter", "Show")

    ui.hr()

    ui.input_radio_buttons(  
        "plot_type",  
        "Type of Plot",  
        {"1": "Line Plot", "2": "Bar Plot"},  
    ) 

    ui.input_checkbox("add_y_true", "Show recorded price", False) 

    ui.input_action_button("reset", "Reset")

# Add main content
ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "currency-dollar": fa.icon_svg("dollar-sign"),
    "ellipsis": fa.icon_svg("ellipsis"),
    "calender":fa.icon_svg("calendar-days"),
    "temp": fa.icon_svg("temperature-low"),
    "production" : fa.icon_svg("plug-circle-plus"),
    "consumption" : fa.icon_svg("plug-circle-minus"),
}

with ui.layout_columns(col_widths=[12]):

    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Electricity Spot Price"
            
        @render_plotly
        def plot_data():

            plot_type = input.plot_type()
            y = ['predictions','Hinta_snt_per_kWh'] if input.add_y_true() else ['predictions']
            labels={'x': 'Time', 'y':'Price (cent/KWh)'}
            
            if plot_type == '1':
                fig = px.line(
                    price_data(),
                    x="Aika",
                    y=y,
                    markers=True,
                )
            else:
                fig = px.bar(
                    price_data(),
                    x="Aika",
                    y=y,
                    barmode='group',
                )
            fig.update_layout(xaxis_title='Time', yaxis_title='Price (cent/KWh)')
            return fig

with ui.layout_columns(fill=False):

    with ui.value_box(showcase=ICONS["calender"]):
        "Today"

        @render.express
        def date_today():
            datetime.today().strftime('%b %d, %Y')

    with ui.value_box(showcase=ICONS["temp"]):
        "Average Temperature [C]"

        @render.express
        def avg_temp():
            '{0:.2f}'.format(FORECAST_DATA['Lampotilan_keskiarvo_C'].mean()) if FORECAST_DATA is not None else ''

    with ui.value_box(showcase=ICONS["production"]):
        "Average Production [MW]"

        @render.express
        def avg_prod():
            '{0:.2f}'.format(FORECAST_DATA['Tuotanto_kW'].mean() / 1000) if FORECAST_DATA is not None else ''

    with ui.value_box(showcase=ICONS["consumption"]):
        "Average Consumption [MWh]"

        @render.express
        def avg_consumption():
            '{0:.2f}'.format(FORECAST_DATA['Kulutus_kWh_per_h'].mean() / 1000) if FORECAST_DATA is not None else ''

    with ui.value_box(showcase=ICONS["currency-dollar"]):
        "Average Price [ckWh]"

        @render.express
        def avg_price():
            '{0:.2f}'.format(FORECAST_DATA['Hinta_snt_per_kWh'].mean()) if FORECAST_DATA is not None else ''



ui.include_css(app_dir / "styles.css")

# --------------------------------------------------------
# Reactive calculations and effects
# --------------------------------------------------------

def forecast_data():

    global FORECAST_DATA

    def download_and_prepare_forecast():
        FORECAST_DATA = get_forecast()
        FORECAST_DATA['predictions'] = model.predict(FORECAST_DATA.drop(columns=['Aika','Hinta_snt_per_kWh']))
        FORECAST_DATA.to_csv(app_dir / "forecast.csv", mode='w', index=False)
        FORECAST_DATA['Aika'] = pd.to_datetime(FORECAST_DATA['Aika'])
        return FORECAST_DATA
    
    if FORECAST_DATA is not None:

        if FORECAST_DATA.iloc[0]['Aika'].date() == datetime.now().date():
            return FORECAST_DATA
        
        return download_and_prepare_forecast()
    print('Path: ', app_dir / "forecast.csv")
    # FORECAST_DATA doesn't exists in memory
    if os.path.exists(app_dir / "forecast.csv"):

        FORECAST_DATA = pd.read_csv(app_dir / "forecast.csv")
        FORECAST_DATA['Aika'] = pd.to_datetime(FORECAST_DATA['Aika'])

        if FORECAST_DATA.iloc[0]['Aika'].date() == datetime.now().date():    # same date
             return FORECAST_DATA

    return  download_and_prepare_forecast()

@reactive.calc
def price_data():


    ui.notification_show(
            f"Calculating",
            type="default",
            duration=2,
        )  
    
    startDate, endDate = selected_date_range()

    if startDate == endDate == datetime.now().date():
        return forecast_data()
    
    try:
        DATA = get_rows_between(datetime.combine(startDate,time(0,0,0)),datetime.combine(endDate,time(23,59,59))) 
        if len(DATA):
            DATA['predictions'] = model.predict(DATA.drop(columns=['Aika','Hinta_snt_per_kWh']))
        else:
            DATA['predictions'] = pd.Series()

        if endDate == datetime.now().date():    # append forecast data
            return pd.concat([DATA,forecast_data()],ignore_index=False)
        
        return DATA
    except Exception as e:
        print('error getting data from database.',e)
        ui.notification_show(f"Failed to get data from database.",type="error",duration=3)
        return forecast_data()
    



@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_radio_buttons("plot_type",selected='1')
    ui.update_checkbox("add_y_true",value=False)
    ui.update_date('startDate',value=date_rng[1])
    ui.update_date('endDate',value=date_rng[1])


@reactive.effect
@reactive.event(input.filter)
def _():
    
    start = input.startDate()
    end = input.endDate()

    if end < start:
        ui.notification_show(
            f"Invalid start date selected.",
            type="error",
            duration=2,
        )        
        ui.update_date('startDate',value=date_rng[1])
        ui.update_date('endDate',value=date_rng[1])
        return 

    selected_date_range.set((start,end))
