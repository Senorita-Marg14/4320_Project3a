#imports and setup stuff
import pygal 
from pygal.style import *

import requests
from flask import Flask, render_template, request, flash, url_for, redirect
from datetime import datetime
import os
from dotenv import load_dotenv

#get the api key from .env files that are .gitignore (add the api code from README and put into your own .env folder)
load_dotenv()
API_KEY = os.getenv("API_KEY")

#used to generate the chart in the html page
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = 'your secret key'

#functions from Alpha Vantage Website 
TIME_SERIES_OPTIONS = {
    "1": ("TIME_SERIES_INTRADAY", "Time Series (60min)"),
    "2": ("TIME_SERIES_DAILY", "Time Series (Daily)"),
    "3": ("TIME_SERIES_WEEKLY", "Weekly Time Series"),
    "4": ("TIME_SERIES_MONTHLY", "Monthly Time Series")
}

#get the symbols from the stocks.csv file 
def get_symbols():
    symbols = []
    file = open ("stocks.csv", "r")
    lines = file.readlines()
    file.close()

    for line in lines[1:]:
        symbol = line.split(",")[0].strip()
        if symbol != "":
            symbols.append(symbol)
    symbols.sort()
    return symbols



#ask the user for the beginning date in YYYY-MM-DD format
#make sure the date is in the right format
def get_date_validate(user_date_input):
        try:
            validated_user_date = datetime.strptime(user_date_input, "%Y-%m-%d")
            return validated_user_date.date()
        except ValueError:
            flash("Please enter a valid date in the YYYY-MM-DD format.")
            return None
#ask the user for the end date in YYYY-MM-DD format 
def get_end_date(start_date, user_input):
    while True:
        end_date = get_date_validate(user_input)
        #the end date should not be before the begin date
        if end_date is None:
            return end_date
        if end_date >= start_date:
            return end_date
        else:
            flash("The end date cannot be before the start date.")

#api stuff 
#gets the data using API key from Alpha Vantage Website
def get_api_data(symbol_choice, time_series_choice):
    function_name, data_key = TIME_SERIES_OPTIONS[time_series_choice]

    url = f"https://www.alphavantage.co/query?function={function_name}&symbol={symbol_choice}&apikey={API_KEY}"
    if time_series_choice == "1":
        url += "&interval=60min"

    response = requests.get(url)
    data = response.json()

    if "Error Message" in data:
        flash(f"No data was found for the symbol {symbol_choice}. Please check your spelling.")
        return None
    if data_key not in data:
        flash("There was an error getting your data from Alpha Vantage. Please try again.")
        return None

    return data[data_key]

def sort_api_data(time_series_choice, start_date, end_date):
    dates = []
    open_values = []
    high_values = []
    low_values = []
    close_values = []

    all_dates = sorted(time_series_choice.keys())

    for date in all_dates:
        date_only = datetime.strptime(date[:10], "%Y-%m-%d").date()

        if date_only >= start_date and date_only <= end_date:
            prices = time_series_choice[date]

            dates.append(date)
            open_values.append(float(prices["1. open"]))
            high_values.append(float(prices["2. high"]))
            low_values.append(float(prices["3. low"]))
            close_values.append(float(prices["4. close"]))

    #data for chart 
    stock_data = {"open": open_values, "high": high_values, "low": low_values, "close": close_values }

    return dates, stock_data


#Generate a graph and open the user's default browser

def draw_graph(dates, stock_data, symbol_choice, start_date, end_date, chart_type):
    chart_colors = Style(colors=("#FF3B1A", "#0C83F2", "#1AFF6A", "#EDDF1F"))
    if chart_type == "bar":
        chart_object = pygal.Bar(x_label_rotation=45, height=400, style=chart_colors)
    else:
        chart_object = pygal.Line(x_label_rotation=45, height=400, style=chart_colors)

    chart_object.title = f"Stock Data for {symbol_choice}: {start_date} to {end_date}"
    chart_object.x_labels = dates
    chart_object.add("Open", stock_data["open"])
    chart_object.add("High", stock_data["high"])
    chart_object.add("Low", stock_data["low"])
    chart_object.add("Close", stock_data["close"])

    return chart_object.render_data_uri()


#send the chart to the base.html and iopen it in the user browser

#main function 
@app.route("/", methods=("GET", "POST"))
def index():
    symbols = get_symbols()
    chart = None

    if request.method == "POST":
        if not API_KEY:
            flash("Please check that the API key is valid")
            return render_template("index.html", symbols=symbols, chart=chart)

        symbol = request.form["symbol"]
        chart_type = request.form["chart_type"]
        time_series = request.form["time_series"]
        start_date = get_date_validate(request.form["start_date"])
        end_date = None
        if start_date:
            end_date = get_end_date(start_date, request.form["end_date"])

        if start_date and end_date:
            time_series = get_api_data(symbol, time_series)

            if time_series:
                dates, stock_data = sort_api_data(time_series, start_date, end_date)

                if dates: 
                    chart = draw_graph(dates, stock_data, symbol, start_date, end_date, chart_type)

                else:
                    flash("No data was found for that date range (possible limitation of free API key)")

    return render_template("index.html", symbols=symbols, chart=chart)


app.run(host="0.0.0.0", port=5005)