"""Concurrent cache, upstream and real HTTP route contracts without Yahoo traffic."""

import runpy
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event, Lock
from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask, request
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families
from werkzeug.test import TestResponse

from src.base_view import BaseView
from src.cache import LRUCache
from src.metrics_view import MetricsView
from src.stock_fetcher import StockDataFetcher

INFO = {"currentPrice": 110.0, "previousClose": 100.0}


def test_cache_iterators_survive_concurrent_mutation() -> None:
    """A caller can iterate a snapshot after eviction, clear or another read."""
    cache: LRUCache[int] = LRUCache(max_size=2)
    cache.put("AAPL", 1)
    cache.put("MSFT", 2)
    keys = cache.keys()
    items = iter(cache)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(cache.get, "AAPL").result(timeout=2)
        pool.submit(cache.put, "TSLA", 3).result(timeout=2)
        pool.submit(cache.clear).result(timeout=2)
    assert list(keys) == ["AAPL", "MSFT"]
    assert list(items) == ["AAPL", "MSFT"]
    assert cache == {}


def test_cache_read_is_atomic_with_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eviction cannot remove the value between its TTL check and return."""
    cache: LRUCache[int] = LRUCache(max_size=1)
    cache.put("AAPL", 1)
    checking = Event()
    writer_started = Event()
    writer_finished = Event()
    is_expired = cache._is_expired

    def paused_check(key: str) -> bool:
        checking.set()
        assert writer_started.wait(2)
        writer_finished.wait(0.1)
        return is_expired(key)

    def evict() -> None:
        assert checking.wait(2)
        writer_started.set()
        cache.put("MSFT", 2)
        writer_finished.set()

    monkeypatch.setattr(cache, "_is_expired", paused_check)
    with ThreadPoolExecutor(max_workers=2) as pool:
        read = pool.submit(cache.get, "AAPL")
        write = pool.submit(evict)
        assert read.result(timeout=2) == 1
        write.result(timeout=2)
    assert cache.size() == 1


def test_concurrent_misses_fetch_once_and_keep_warm_reads_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiters share one cold result while an unrelated cached symbol stays usable."""
    fetcher = StockDataFetcher()
    warm = {"symbol": "MSFT", "current_price": 123.0}
    fetcher.cache.put("MSFT", warm)
    entered = Event()
    release = Event()
    calls: list[str] = []
    calls_lock = Lock()

    class Ticker:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        @property
        def info(self) -> dict[str, float]:
            with calls_lock:
                calls.append(self.symbol)
            entered.set()
            assert release.wait(2)
            return INFO.copy()

    monkeypatch.setattr("src.stock_fetcher.yf.Ticker", Ticker)
    with ThreadPoolExecutor(max_workers=5) as pool:
        first = pool.submit(fetcher.get_stock_data, ["AAPL"])
        assert entered.wait(2)
        waiters = [pool.submit(fetcher.get_stock_data, ["AAPL"]) for _ in range(3)]
        try:
            assert pool.submit(fetcher.get_stock_data, ["MSFT"]).result(timeout=1) == {
                "MSFT": warm
            }
        finally:
            release.set()
        results = [future.result(timeout=2) for future in [first, *waiters]]
    assert calls == ["AAPL"]
    assert all(result == results[0] for result in results)
    assert results[0]["AAPL"]["current_price"] == 110.0


def test_upstream_serialization_and_lock_release_after_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared yfinance state is never used concurrently, even across fetchers."""
    first_fetcher = StockDataFetcher()
    second_fetcher = StockDataFetcher()
    entered = Event()
    second_started = Event()
    second_upstream = Event()
    active = 0
    maximum_active = 0
    state_lock = Lock()

    class Ticker:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        @property
        def info(self) -> dict[str, float]:
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            try:
                if self.symbol == "FAIL":
                    entered.set()
                    assert second_started.wait(2)
                    second_upstream.wait(0.1)
                    raise ValueError("fixture failure")
                second_upstream.set()
                return INFO.copy()
            finally:
                with state_lock:
                    active -= 1

    def second_request() -> dict[str, Any]:
        assert entered.wait(2)
        second_started.set()
        return second_fetcher.get_stock_data(["MSFT"])

    monkeypatch.setattr("src.stock_fetcher.yf.Ticker", Ticker)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_fetcher.get_stock_data, ["FAIL"])
        second = pool.submit(second_request)
        assert first.result(timeout=2)["FAIL"]["current_price"] == 0
        assert second.result(timeout=2)["MSFT"]["current_price"] == 110.0
    assert maximum_active == 1
    assert "FAIL" not in first_fetcher.cache


@pytest.fixture
def concurrent_web(monkeypatch: pytest.MonkeyPatch) -> Flask:
    registry = CollectorRegistry()
    monkeypatch.setattr("src.metrics_factory.REGISTRY", registry)
    monkeypatch.setattr(
        "src.metrics_view.generate_latest", partial(generate_latest, registry=registry)
    )
    monkeypatch.setattr("src.config.config.AUTO_CLEAR_METRICS", True)
    monkeypatch.setattr("src.config.config.ENABLE_DEBUG_METRICS", True)
    monkeypatch.setattr(BaseView, "_app_instance", BaseView._app_instance)
    monkeypatch.setattr(
        "src.stock_fetcher.yf.Ticker", lambda symbol: SimpleNamespace(info=INFO.copy())
    )
    namespace = runpy.run_module("src.main", run_name="src._concurrent_contract")
    web = namespace["web"]
    assert isinstance(web, Flask)
    web.config["TESTING"] = True
    return web


@pytest.mark.parametrize(
    ("auto_clear", "extra_query"),
    [(True, ""), (False, "&clear=true"), (False, "&force_clear=true")],
)
def test_concurrent_scrapes_keep_their_own_price_samples(
    concurrent_web: Flask,
    monkeypatch: pytest.MonkeyPatch,
    auto_clear: bool,
    extra_query: str,
) -> None:
    """Serialize clear, all gauge updates and output for distinct concurrent scrapes."""
    monkeypatch.setattr("src.config.config.AUTO_CLEAR_METRICS", auto_clear)
    first_updated = Event()
    second_started = Event()
    second_finished = Event()
    update = MetricsView.update_prometheus_metrics

    def paused_update(view: MetricsView, data: dict[str, Any]) -> None:
        update(view, data)
        if "AAPL" in data:
            first_updated.set()
            assert second_started.wait(2)
            second_finished.wait(0.1)

    def get(symbol: str) -> TestResponse:
        if symbol == "MSFT":
            assert first_updated.wait(2)
            second_started.set()
        with concurrent_web.test_client() as client:
            response = client.get(f"/metrics?symbols={symbol}{extra_query}")
        if symbol == "MSFT":
            second_finished.set()
        return response

    monkeypatch.setattr(MetricsView, "update_prometheus_metrics", paused_update)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(get, "AAPL")
        second = pool.submit(get, "MSFT")
        for future, symbol in [(first, "AAPL"), (second, "MSFT")]:
            response = future.result(timeout=2)
            assert response.status_code == 200
            assert response.content_type == "text/plain; charset=utf-8"
            families = text_string_to_metric_families(response.get_data(as_text=True))
            samples = {
                sample.labels["symbol"]: sample.value
                for family in families
                for sample in family.samples
                if sample.name == "financial_price_current"
            }
            assert samples == {symbol: 110.0}


def test_health_is_available_during_a_cold_scrape(
    concurrent_web: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = Event()
    release = Event()

    class Ticker:
        def __init__(self, symbol: str) -> None:
            pass

        @property
        def info(self) -> dict[str, float]:
            entered.set()
            assert release.wait(2)
            return INFO.copy()

    def get(path: str) -> TestResponse:
        with concurrent_web.test_client() as client:
            return client.get(path)

    monkeypatch.setattr("src.stock_fetcher.yf.Ticker", Ticker)
    with ThreadPoolExecutor(max_workers=2) as pool:
        scrape = pool.submit(get, "/metrics?symbols=AAPL")
        assert entered.wait(2)
        try:
            health = pool.submit(get, "/health").result(timeout=1)
            assert health.status_code == 200
            assert health.get_json()["status"] == "running"
        finally:
            release.set()
        assert scrape.result(timeout=2).status_code == 200


@pytest.mark.parametrize(("symbol", "status"), [("INVALID!", 400), ("ERROR", 500)])
def test_metrics_error_output_waits_for_complete_scrape(
    concurrent_web: Flask,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    status: int,
) -> None:
    """Error output cannot collect another request's partly updated gauge families."""
    price_updated = Event()
    error_started = Event()
    error_finished = Event()
    update = MetricsView._update_price_metrics
    parse = MetricsView._parse_request_parameters

    def paused_price_update(
        view: MetricsView, data: dict[str, Any], factory: Any
    ) -> None:
        update(view, data, factory)
        if data["symbol"] == "AAPL":
            price_updated.set()
            assert error_started.wait(2)
            error_finished.wait(0.1)

    def parse_or_fail(view: MetricsView) -> tuple[list[str], bool]:
        if request.args.get("symbols") == "ERROR":
            raise RuntimeError("fixture failure")
        return parse(view)

    def get(request_symbol: str) -> TestResponse:
        if request_symbol == symbol:
            assert price_updated.wait(2)
            error_started.set()
        with concurrent_web.test_client() as client:
            response = client.get("/metrics", query_string={"symbols": request_symbol})
        if request_symbol == symbol:
            error_finished.set()
        return response

    monkeypatch.setattr(MetricsView, "_update_price_metrics", paused_price_update)
    monkeypatch.setattr(MetricsView, "_parse_request_parameters", parse_or_fail)
    with ThreadPoolExecutor(max_workers=2) as pool:
        scrape = pool.submit(get, "AAPL")
        error = pool.submit(get, symbol)
        assert scrape.result(timeout=2).status_code == 200
        response = error.result(timeout=2)
    assert response.status_code == status
    families = text_string_to_metric_families(response.get_data(as_text=True))
    values = {
        sample.name: sample.value
        for family in families
        for sample in family.samples
        if sample.labels.get("symbol") == "AAPL"
    }
    assert values["financial_price_current"] == 110.0
    assert values["financial_previous_close"] == 100.0
    assert values["financial_price_change"] == 10.0
    assert get("MSFT").status_code == 200
