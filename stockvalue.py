from decimal import Decimal, ROUND_HALF_UP
import json
import os
import time

from flask import Flask, Response
import click
import numpy
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
                'CACHE_DIR': config.get('CACHE_DIR', '/tmp/'),
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
                   cache_dir: str = None,
                   cache_seconds: int = 0) -> pd.DataFrame:
    """
    Retrieve historical stock data for a given ticker symbol.

    Parameters:
    - ticker_symbol (str): The ticker symbol of the stock.
    - period (str, optional):
        The time period for which to retrieve the data.
        Defaults to "10d".
    - cache_dir (str, optional):
        The file path to cache the data.
        Defaults to None.
    - cache_seconds (int, optional):
        The number of seconds to consider the cache valid.
        Defaults to 0.

    Returns:
    pandas.DataFrame: The historical stock data.
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f'ticker_symbol_{ticker_symbol}.pkl')

    if cache_dir and os.path.exists(cache_file):
        file_modified_time = os.path.getmtime(cache_file)
        elapsed_time = time.time() - file_modified_time
        if elapsed_time < cache_seconds:
            return pd.read_pickle(cache_file)

    stock = yf.Ticker(ticker_symbol)
    data = stock.history(period=period)

    if cache_dir:
        data.to_pickle(cache_file)

    return data


def round_decimal_to_two_places(value: numpy.float64) -> Decimal:
    """
    Rounds a decimal value to two decimal places.

    Args:
    - value (numpy.float64): The decimal value to be rounded.

    Returns:
    Decimal: The rounded decimal value.
    """
    raw = Decimal(value)
    return raw.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_current_price(data: pd.DataFrame) -> Decimal:
    """
    Get the current price from the given DataFrame.

    Parameters:
    - data (pd.DataFrame): The DataFrame containing the stock data.

    Returns:
    Decimal: The current price.
    """
    price = round_decimal_to_two_places(data.loc[data.dropna().index[-1]]['Close'])
    return price


def get_last_trading_day_data(data: pd.DataFrame) -> Decimal:
    """
    Get the closing value of the last trading day from the given DataFrame.

    Args:
    - data (pd.DataFrame): The DataFrame containing the stock data.

    Returns:
    Decimal: The closing value of the last trading day, rounded to two decimal places.
    None: If the DataFrame is empty or contains only one trading day.
    """
    data.index = pd.to_datetime(data.index)
    sorted_data = data.sort_index()
    clean_data = sorted_data.dropna()

    if not clean_data.empty and len(clean_data) > 1:
        last_trading_day_close = round_decimal_to_two_places(clean_data.iloc[-2]['Close'])
    else:
        return None

    return last_trading_day_close


def generate_response_text(ticker_symbol: str,
                           current_price: Decimal,
                           last_trading_day_close_price: Decimal = None) -> str:
    """
    Generate the response text for the stock value.

    Args:
    - ticker_symbol (str):
        The ticker symbol of the stock.
    - current_price (Decimal):
        The current price of the stock.
    - last_trading_day_close_price (Decimal, optional):
        The closing price of the stock on the last trading day.
        Defaults to None.

    Returns:
    str: The response text containing the stock value information.
    """
    response_text = (
        '# HELP stock_value_current_price Current Stock Price\n'
        '# TYPE stock_value_current_price gauge\n'
        f'stock_value_current_price{{ticker_symbol="{ticker_symbol}"}} '
        f'{current_price}\n'
    )

    if last_trading_day_close_price is None:
        return response_text

    diff_price = current_price - last_trading_day_close_price
    diff_ratio = (diff_price / last_trading_day_close_price) * 100

    response_text += (
        '# HELP stock_value_last_trading_price Last Trading Close Price\n'
        '# TYPE stock_value_last_trading_price gauge\n'
        f'stock_value_last_trading_price{{ticker_symbol="{ticker_symbol}"}} '
        f'{last_trading_day_close_price}\n'
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
def metrics() -> Response:
    """
    Calculate and return the metrics for the stock values.

    This function retrieves stock data for the ticker symbols specified in the configuration,
    calculates the current price and the last trading day's close price for each ticker symbol,
    and generates a response text containing the metrics for each ticker symbol.

    Returns:
    Response: A response object containing the metrics as plain text.
    """
    load_config(app)

    response_text = ''
    ticker_symbols = app.config['TICKER_SYMBOLS']
    cache_dir = app.config['CACHE_DIR']
    cache_seconds = app.config['CACHE_SECONDS']
    for ticker_symbol in ticker_symbols:
        data = get_stock_data(
            ticker_symbol,
            cache_dir=cache_dir,
            cache_seconds=cache_seconds
        )
        current_price = get_current_price(data)
        last_trading_day_close_price = get_last_trading_day_data(data)
        response_text += generate_response_text(
            ticker_symbol,
            current_price,
            last_trading_day_close_price
        )
    return Response(response_text, content_type='text/plain; charset=utf-8')


@click.command()
@click.argument('ticker_symbol')
def ticker_symbol(ticker_symbol: str) -> None:
    """
    Retrieves stock data for the given ticker symbol and prints the current price,
    last trading day close price, difference price, and difference ratio.

    Args:
    - ticker_symbol (str): The ticker symbol of the stock.

    Returns:
    None
    """
    data = get_stock_data(ticker_symbol)
    if not data.empty:
        current_price = get_current_price(data)
        print(
            f'Ticker Symbol {ticker_symbol}\n'
            f'Current Price: {current_price}'
        )

        last_trading_day_close_price = get_last_trading_day_data(data)
        if last_trading_day_close_price:
            diff_price = current_price - last_trading_day_close_price
            diff_ratio = (diff_price / last_trading_day_close_price) * 100
            print(
                'Last Trading Day Close Price: '
                f'{last_trading_day_close_price}\n'
                'Difference Price: '
                f'{diff_price}\n'
                'Difference Ratio: '
                f'{diff_ratio}%'
            )


if __name__ == "__main__":
    ticker_symbol()
