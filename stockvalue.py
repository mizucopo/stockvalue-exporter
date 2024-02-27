import datetime
import json
import os
import time

from flask import Flask, Response
import click
import pandas as pd
import yfinance as yf


def load_config(app: Flask, config_filepath: str = None):
    """
    Load configuration from a JSON file and update the app's configuration.

    Parameters:
    - app (Flask): The Flask application object to update the configuration for.
    - config_filepath (str, optional):
        The filepath of the JSON configuration file.
        If None, it defaults to 'config.json'.

    Returns:
    None

    Raises:
    - RuntimeError: If the configuration file cannot be read or if it's not valid JSON.
    """
    if config_filepath is None:
        config_filepath = os.environ.get('CONFIG_FILEPATH', 'config.json')

    try:
        with open(config_filepath, 'r') as config_file:
            config = json.load(config_file)
            app.config.update({
                'TICKER_SYMBOLS': config.get('TICKER_SYMBOLS', []),
                'SERVER_PORT': config.get('SERVER_PORT', 9100),
                'CACHE_FILE': config.get('CACHE_FILE', '/tmp/cache.pkl'),
                'CACHE_SECONDS': config.get('CACHE_SECONDS', 300)
            })
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read '{config_filepath}'. "
                           f"Ensure the file exists and is readable.")
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse '{config_filepath}'. "
                           f"Ensure it is a valid JSON file.")


def get_stock_data(ticker_symbol: str,
                   period: str = "10d",
                   cache_file: str = None,
                   cache_seconds: int = 0):
    """
    Retrieve historical stock data for a given ticker symbol.

    Parameters:
    ticker_symbol (str): The ticker symbol of the stock.
    period (str, optional): The time period for which to retrieve the data.
                            Defaults to "10d".
    cache_file (str, optional): The file path to cache the data.
                                Defaults to None.
    cache_seconds (int, optional): The number of seconds to consider
                                   the cache valid.
                                   Defaults to 0.

    Returns:
    pandas.DataFrame: The historical stock data.
    """
    if cache_file and os.path.exists(cache_file):
        file_modified_time = os.path.getmtime(cache_file)
        elapsed_time = time.time() - file_modified_time
        if elapsed_time < cache_seconds:
            return pd.read_pickle(cache_file)

    stock = yf.Ticker(ticker_symbol)
    data = stock.history(period=period)

    if cache_file:
        data.to_pickle(cache_file)

    return data


def get_current_price(data: pd.DataFrame) -> int:
    """
    Get the current price from the given DataFrame.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the stock data.

    Returns:
    int: The current price.
    """
    price = int(data.loc[data.dropna().index[-1]]['Close'])
    return price


def get_last_trading_day_data(data: pd.DataFrame) -> tuple:
    """
    Get the last trading day (excluding today) and its closing price.

    Parameters:
    - data (pd.DataFrame): Stock data.

    Returns:
    tuple: A tuple containing the last trading day (datetime.date)
           and its closing price (int).
    """
    today = datetime.date.today()
    data.index = pd.to_datetime(data.index)
    sorted_data = data.sort_index()

    clean_data = sorted_data.dropna()

    if not clean_data.empty:
        last_trading_day = clean_data.index[-1].date()
        if last_trading_day == today:
            if len(clean_data) > 1:
                last_trading_day = clean_data.index[-2].date()
                last_trading_day_close = int(clean_data.iloc[-2]['Close'])
            else:
                return None
        else:
            last_trading_day_close = int(clean_data.iloc[-1]['Close'])
    else:
        return None

    return last_trading_day, last_trading_day_close


def generate_response_text(ticker_symbol: str,
                           last_trading_date: datetime.date,
                           last_trading_day_close_price: int,
                           current_price: int):
    """
    Generate the response text for the stock data.

    Parameters:
    - ticker_symbol (str): The stock's ticker symbol.
    - last_trading_date (datetime.date): The last trading day.
    - last_trading_day_close_price (int): The closing price
                                          on the last trading day.
    - current_price (int): current stock price.

    Returns:
    str: The generated response text.
    """
    formatted_last_trading_date = last_trading_date.strftime('%Y-%m-%d')
    diff_price = current_price - last_trading_day_close_price
    diff_ratio = (diff_price / last_trading_day_close_price) * 100

    response_text = (
        '# HELP stock_value_last_trading_price Last Trading Close Price\n'
        '# TYPE stock_value_last_trading_price gauge\n'
        f'stock_value_last_trading_price{{ticker_symbol="{ticker_symbol}",'
        f'last_trading_date="{formatted_last_trading_date}"}} '
        f'{last_trading_day_close_price}\n'
        '# HELP stock_value_current_price Current Stock Price\n'
        '# TYPE stock_value_current_price gauge\n'
        f'stock_value_current_price{{ticker_symbol="{ticker_symbol}"}} '
        f'{current_price}\n'
        '# HELP stock_value_current_diff_price Price difference from last '
        'trading day\n'
        '# TYPE stock_value_current_diff_price gauge\n'
        f'stock_value_current_diff_price{{ticker_symbol="{ticker_symbol}"}} '
        f'{diff_price}\n'
        '# HELP stock_value_current_recent_ratio Ratio to the last trading day\n'
        '# TYPE stock_value_current_recent_ratio gauge\n'
        f'stock_value_current_recent_ratio{{ticker_symbol="{ticker_symbol}"}} '
        f'{diff_ratio}\n'
    )

    return response_text


app = Flask(__name__)


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Handle the HTTP request for metrics.

    This function fetches the stock data, determines the price for today and
    the last trading day, and then generates a response text to be returned
    to the client.

    Returns:
    Response: The HTTP response containing the metrics in plain text format.
    """
    load_config(app)

    response_text = ''
    ticker_symbols = app.config['TICKER_SYMBOLS']
    cache_file = app.config['CACHE_FILE']
    cache_seconds = app.config['CACHE_SECONDS']
    for ticker_symbol in ticker_symbols:
        data = get_stock_data(
            ticker_symbol,
            cache_file=cache_file,
            cache_seconds=cache_seconds
        )
        current_price = get_current_price(data)
        last_trading_date, last_trading_day_close_price = \
            get_last_trading_day_data(data)
        response_text += generate_response_text(
            ticker_symbol,
            last_trading_date,
            last_trading_day_close_price,
            current_price
        )
    return Response(response_text, content_type='text/plain; charset=utf-8')


@click.command()
@click.argument('ticker_symbol')
def ticker_symbol(ticker_symbol: str):
    """
    Retrieves the stock data for the given ticker symbol
    and prints the current price.

    Parameters:
    ticker_symbol (str): The ticker symbol of the stock.

    Returns:
    None
    """
    data = get_stock_data(ticker_symbol)
    if not data.empty:
        current_price = get_current_price(data)
        print(f'Ticker Symbol {ticker_symbol}: {current_price}')


if __name__ == "__main__":
    ticker_symbol()
