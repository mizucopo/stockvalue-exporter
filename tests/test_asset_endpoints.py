"""HTTP contracts for all supported asset types through the application entrypoint."""

import runpy
from datetime import datetime
from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from flask import Flask
from flask.testing import FlaskClient
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families

from src.base_view import BaseView

pytestmark = pytest.mark.integration

FETCH_TIMESTAMP = 1_750_000_000.0
ASSETS = {
    "AAPL": ("Apple", "stock", "EUR", "XPAR", 1234, 9000),
    "USDJPY=X": ("US Dollar / Yen", "forex", "JPY", "FX", 0, 0),
    "^GSPC": ("S&P 500", "index", "USD", "INDEX", 1234, 0),
    "BTC-USD": ("Bitcoin", "crypto", "USD", "CRYPTO", 1234, 9000),
}
SYMBOL_QUERY = [("symbols", " aapl,usdjpy=x "), ("symbols", "^gspc,btc-usd")]


@pytest.fixture
def endpoint_client(monkeypatch: pytest.MonkeyPatch) -> tuple[FlaskClient, Mock]:
    """Run the real route setup with isolated metrics and only upstream data mocked."""
    registry = CollectorRegistry()
    monkeypatch.setattr("src.metrics_factory.REGISTRY", registry)
    monkeypatch.setattr(
        "src.metrics_view.generate_latest", partial(generate_latest, registry=registry)
    )
    monkeypatch.setattr("src.config.config.ENABLE_DEBUG_METRICS", True)
    monkeypatch.setattr("src.config.config.AUTO_CLEAR_METRICS", True)
    monkeypatch.setattr("src.stock_fetcher.time.time", lambda: FETCH_TIMESTAMP)
    # src.main configures this shared view dependency; restore it during teardown.
    monkeypatch.setattr(BaseView, "_app_instance", BaseView._app_instance)

    upstream = Mock(
        side_effect=lambda symbol: SimpleNamespace(
            info={
                "longName": ASSETS[symbol][0],
                "currentPrice": 110.0,
                "previousClose": 100.0,
                "volume": 1234,
                "marketCap": 9000,
                "currency": "EUR",
                "exchange": "XPAR",
            }
        )
    )
    monkeypatch.setattr("src.stock_fetcher.yf.Ticker", upstream)

    namespace = runpy.run_module("src.main", run_name="src._endpoint_contract")
    web = namespace["web"]
    assert isinstance(web, Flask)
    web.config["TESTING"] = True
    return web.test_client(), upstream


def test_metrics_http_contract_for_all_asset_types(
    endpoint_client: tuple[FlaskClient, Mock],
) -> None:
    """Expose the current financial sample names, labels and asset-specific fields."""
    client, upstream = endpoint_client
    response = client.get("/metrics", query_string=SYMBOL_QUERY)

    assert response.status_code == 200
    assert response.content_type == "text/plain; charset=utf-8"
    families = list(text_string_to_metric_families(response.get_data(as_text=True)))
    samples = [sample for family in families for sample in family.samples]
    # Client-generated creation timestamps can be disabled independently of the app.
    actual = {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for family in families
        if family.type == "gauge" and not family.name.endswith("_created")
        for sample in family.samples
    }
    expected = {}
    for symbol, (
        name,
        asset_type,
        currency,
        exchange,
        volume,
        market_cap,
    ) in ASSETS.items():
        labels = {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "asset_type": asset_type,
        }
        for metric_name, value in {
            "financial_previous_close": 100.0,
            "financial_price_change": 10.0,
            "financial_price_change_percent": 10.0,
        }.items():
            expected[(metric_name, tuple(sorted(labels.items())))] = value
        price_labels = {**labels, "currency": currency}
        expected[("financial_price_current", tuple(sorted(price_labels.items())))] = (
            110.0
        )
        timestamp_labels = {"symbol": symbol, "asset_type": asset_type}
        expected[
            (
                "financial_last_updated_timestamp",
                tuple(sorted(timestamp_labels.items())),
            )
        ] = FETCH_TIMESTAMP
        if volume:
            expected[("financial_volume_current", tuple(sorted(labels.items())))] = (
                volume
            )
        if market_cap:
            expected[("financial_market_cap", tuple(sorted(labels.items())))] = (
                market_cap
            )

    # Exact sample equality also checks missing forex volume and forex/index market cap.
    assert actual == expected
    assert not any(sample.name.endswith("fetch_errors_total") for sample in samples)
    upstream.assert_has_calls([call(symbol) for symbol in ASSETS])
    assert upstream.call_count == len(ASSETS)


def test_stocks_http_contract_for_all_asset_types(
    endpoint_client: tuple[FlaskClient, Mock],
) -> None:
    """Keep the JSON envelope and normalized financial data for every asset type."""
    client, upstream = endpoint_client
    response = client.get("/api/stocks", query_string=SYMBOL_QUERY)

    assert response.status_code == 200
    assert response.content_type == "application/json"
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert set(payload) == {"timestamp", "symbols", "data"}
    assert isinstance(payload["timestamp"], str)
    datetime.fromisoformat(payload["timestamp"])
    assert payload["symbols"] == list(ASSETS)
    expected_data = {
        symbol: {
            "symbol": symbol,
            "name": name,
            "currency": currency,
            "exchange": exchange,
            "asset_type": asset_type,
            "current_price": 110.0,
            "previous_close": 100.0,
            "price_change": 10.0,
            "price_change_percent": 10.0,
            "volume": volume,
            "market_cap": market_cap,
            "timestamp": FETCH_TIMESTAMP,
        }
        for symbol, (name, asset_type, currency, exchange, volume, market_cap) in (
            ASSETS.items()
        )
    }
    assert payload["data"] == expected_data
    upstream.assert_has_calls([call(symbol) for symbol in ASSETS])
    assert upstream.call_count == len(ASSETS)
