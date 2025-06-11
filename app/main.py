import tomllib
import time
import logging
import threading
from pathlib import Path
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import yfinance as yf
from datetime import datetime


# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_version():
    """pyproject.tomlからバージョンを取得"""
    try:
        # 現在のファイルと同じディレクトリのpyproject.tomlを読み込み
        pyproject_path = Path(__file__).parent / "pyproject.toml"

        if not pyproject_path.exists():
            return 1

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    except Exception as e:
        print(f"Error reading version from pyproject.toml: {e}")
        return 1

def get_app_info():
    """アプリケーション情報を取得"""
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"

        if not pyproject_path.exists():
            return {"name": "stockvalue-exporter", "version": "unknown", "description": "Unknown"}

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            project = data.get("project", {})
            return {
                "name": project.get("name", "stockvalue-exporter"),
                "version": project.get("version", "unknown"),
                "description": project.get("description", "Stock value exporter for Prometheus")
            }
    except Exception as e:
        print(f"Error reading app info from pyproject.toml: {e}")
        return {"name": "stockvalue-exporter", "version": "unknown", "description": "Unknown"}

# アプリケーション起動時に情報を取得
APP_INFO = get_app_info()
APP_NAME = APP_INFO["name"]
APP_VERSION = APP_INFO["version"]
APP_DESCRIPTION = APP_INFO["description"]

# Prometheusメトリクス定義
stock_price = Gauge(
    'stock_price_current',
    'Current stock price',
    ['symbol', 'name', 'currency', 'exchange']
)

stock_volume = Gauge(
    'stock_volume_current',
    'Current stock volume',
    ['symbol', 'name', 'exchange']
)

stock_market_cap = Gauge(
    'stock_market_cap',
    'Market capitalization',
    ['symbol', 'name', 'exchange']
)

stock_pe_ratio = Gauge(
    'stock_pe_ratio',
    'Price to Earnings ratio',
    ['symbol', 'name', 'exchange']
)

stock_dividend_yield = Gauge(
    'stock_dividend_yield',
    'Dividend yield percentage',
    ['symbol', 'name', 'exchange']
)

stock_52week_high = Gauge(
    'stock_52week_high',
    '52 week high price',
    ['symbol', 'name', 'exchange']
)

stock_52week_low = Gauge(
    'stock_52week_low',
    '52 week low price',
    ['symbol', 'name', 'exchange']
)

# 前日比関連メトリクス
stock_previous_close = Gauge(
    'stock_previous_close',
    'Previous day closing price',
    ['symbol', 'name', 'exchange']
)

stock_price_change = Gauge(
    'stock_price_change',
    'Price change from previous close',
    ['symbol', 'name', 'exchange']
)

stock_price_change_percent = Gauge(
    'stock_price_change_percent',
    'Price change percentage from previous close',
    ['symbol', 'name', 'exchange']
)

# エラーメトリクス
stock_fetch_errors = Counter(
    'stock_fetch_errors_total',
    'Total stock fetch errors',
    ['symbol', 'error_type']
)

stock_fetch_duration = Histogram(
    'stock_fetch_duration_seconds',
    'Time spent fetching stock data',
    ['symbol']
)

# 最終更新時刻
stock_last_updated = Gauge(
    'stock_last_updated_timestamp',
    'Last updated timestamp',
    ['symbol']
)

class StockDataFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5分間キャッシュ

    def get_stock_data(self, symbols):
        """指定された銘柄の株価データを取得"""
        results = {}

        for symbol in symbols:
            start_time = time.time()

            try:
                # キャッシュチェック
                if self._is_cached(symbol):
                    results[symbol] = self.cache[symbol]['data']
                    continue

                # Yahoo Finance APIから株価データ取得
                ticker = yf.Ticker(symbol)
                info = ticker.info

                if not info:
                    raise ValueError(f"No data found for symbol: {symbol}")

                # 株価データの構造化
                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                previous_close = info.get('previousClose', info.get('regularMarketPreviousClose', 0))

                # 前日比計算
                price_change = current_price - previous_close if previous_close else 0
                price_change_percent = (price_change / previous_close * 100) if previous_close else 0

                stock_data = {
                    'symbol': symbol,
                    'name': info.get('longName', info.get('shortName', symbol)),
                    'currency': info.get('currency', 'USD'),
                    'exchange': info.get('exchange', 'Unknown'),
                    'current_price': current_price,
                    'previous_close': previous_close,
                    'price_change': price_change,
                    'price_change_percent': price_change_percent,
                    'volume': info.get('volume', info.get('regularMarketVolume', 0)),
                    'market_cap': info.get('marketCap', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'dividend_yield': info.get('dividendYield', 0),
                    'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                    'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                    'timestamp': time.time()
                }

                # キャッシュに保存
                self.cache[symbol] = {
                    'data': stock_data,
                    'timestamp': time.time()
                }

                results[symbol] = stock_data

                # メトリクス記録
                duration = time.time() - start_time
                stock_fetch_duration.labels(symbol=symbol).observe(duration)

                logger.info(f"Successfully fetched data for {symbol}: ${stock_data['current_price']} (${stock_data['price_change']:+.2f}, {stock_data['price_change_percent']:+.2f}%)")

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                stock_fetch_errors.labels(symbol=symbol, error_type=type(e).__name__).inc()

                # エラー時のデフォルト値
                results[symbol] = {
                    'symbol': symbol,
                    'name': symbol,
                    'currency': 'USD',
                    'exchange': 'Unknown',
                    'current_price': 0,
                    'previous_close': 0,
                    'price_change': 0,
                    'price_change_percent': 0,
                    'volume': 0,
                    'market_cap': 0,
                    'pe_ratio': 0,
                    'dividend_yield': 0,
                    'fifty_two_week_high': 0,
                    'fifty_two_week_low': 0,
                    'timestamp': time.time()
                }

        return results

    def _is_cached(self, symbol):
        """キャッシュが有効かチェック"""
        if symbol not in self.cache:
            return False

        cache_age = time.time() - self.cache[symbol]['timestamp']
        return cache_age < self.cache_ttl

# グローバルインスタンス
fetcher = StockDataFetcher()

def update_prometheus_metrics(stock_data_dict):
    """PrometheusメトリクスをStock dataで更新"""
    for symbol, data in stock_data_dict.items():
        try:
            labels = {
                'symbol': data['symbol'],
                'name': data['name'],
                'exchange': data['exchange']
            }

            # 価格関連メトリクス
            stock_price.labels(
                symbol=data['symbol'],
                name=data['name'],
                currency=data['currency'],
                exchange=data['exchange']
            ).set(data['current_price'])

            stock_volume.labels(**labels).set(data['volume'])
            stock_market_cap.labels(**labels).set(data['market_cap'])
            stock_pe_ratio.labels(**labels).set(data['pe_ratio'])
            stock_dividend_yield.labels(**labels).set(data['dividend_yield'] * 100 if data['dividend_yield'] else 0)
            stock_52week_high.labels(**labels).set(data['fifty_two_week_high'])
            stock_52week_low.labels(**labels).set(data['fifty_two_week_low'])

            # 前日比関連メトリクス
            stock_previous_close.labels(**labels).set(data['previous_close'])
            stock_price_change.labels(**labels).set(data['price_change'])
            stock_price_change_percent.labels(**labels).set(data['price_change_percent'])

            # 最終更新時刻
            stock_last_updated.labels(symbol=data['symbol']).set(data['timestamp'])

        except Exception as e:
            logger.error(f"Error updating metrics for {symbol}: {e}")
            stock_fetch_errors.labels(symbol=symbol, error_type='metric_update_error').inc()

@app.route('/')
def health():
    """ヘルスチェック"""
    return f"{APP_NAME} v{APP_VERSION} is running!"

@app.route('/health')
def health_json():
    """ヘルスチェック（JSON形式）"""
    return jsonify({
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "status": "running",
        "message": f"{APP_NAME} v{APP_VERSION} is running!"
    })

@app.route('/version')
def version():
    """バージョン情報"""
    return jsonify({
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION
    })

@app.route('/metrics')
def metrics():
    """Prometheusメトリクスエンドポイント"""
    try:
        # URLパラメータから銘柄リストを取得（配列対応）
        symbols_list = request.args.getlist('symbols')

        if not symbols_list:
            # 単一パラメータの場合（カンマ区切り）
            symbols_param = request.args.get('symbols', '')
            if symbols_param:
                symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            else:
                # デフォルト銘柄
                symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        else:
            # 配列パラメータの場合
            symbols = [s.strip().upper() for s in symbols_list if s.strip()]

        if not symbols:
            logger.warning("No symbols provided for metrics collection")
            return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

        logger.info(f"Fetching metrics for symbols: {symbols}")

        # 株価データ取得
        stock_data = fetcher.get_stock_data(symbols)

        # メトリクス更新
        update_prometheus_metrics(stock_data)

        return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error in metrics endpoint: {e}")
        return generate_latest(), 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/api/stocks')
def get_stocks():
    """株価データAPI（デバッグ用）"""
    # 配列パラメータ対応
    symbols_list = request.args.getlist('symbols')

    if not symbols_list:
        # 単一パラメータの場合（カンマ区切り）
        symbols_param = request.args.get('symbols', 'AAPL,GOOGL')
        symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    else:
        # 配列パラメータの場合
        symbols = [s.strip().upper() for s in symbols_list if s.strip()]

    stock_data = fetcher.get_stock_data(symbols)

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'symbols': symbols,
        'data': stock_data
    })

if __name__ == "__main__":
    print(f"Starting {APP_NAME} v{APP_VERSION}")
    print(f"Description: {APP_DESCRIPTION}")
    print("Metrics available at: http://localhost:8080/metrics")
    print("Example: http://localhost:8080/metrics?symbols=AAPL,GOOGL,MSFT")
    app.run(host='0.0.0.0', port=8080, debug=False)
