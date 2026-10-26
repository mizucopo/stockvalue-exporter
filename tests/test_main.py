"""Startup and HTTP contracts with fresh configuration and Prometheus state."""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _check_startup(debug_enabled: bool) -> None:
    """Import the real entrypoint and mock only the external financial data API."""
    from prometheus_client.parser import text_string_to_metric_families

    from src import main
    from src.config import config

    assert config.ENABLE_DEBUG_METRICS is debug_enabled
    metrics = main.metrics_factory.get_all_metrics()
    assert len(metrics) == (9 if debug_enabled else 7)
    assert main.app.fetcher.financial_fetch_duration is metrics.get(
        "financial_fetch_duration"
    )
    assert main.app.fetcher.financial_fetch_errors is metrics.get(
        "financial_fetch_errors"
    )

    def ticker(symbol: str) -> SimpleNamespace:
        if symbol == "MSFT":
            raise RuntimeError("Upstream unavailable")
        return SimpleNamespace(
            info={
                "longName": "Apple",
                "currentPrice": 110.0,
                "previousClose": 100.0,
                "volume": 1234,
                "marketCap": 9000,
                "currency": "USD",
                "exchange": "NASDAQ",
            }
        )

    main.web.config["TESTING"] = True
    client = main.web.test_client()
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "running"

    with patch("src.stock_fetcher.yf.Ticker", side_effect=ticker) as upstream:
        response = client.get("/metrics?symbols=AAPL,MSFT")
        assert response.status_code == 200
        exposition = response.get_data(as_text=True)
        families = {
            family.name: family
            for family in text_string_to_metric_families(exposition)
            if family.name.startswith("financial_")
            and not family.name.endswith("_created")
        }
        core_names = {
            "financial_price_current",
            "financial_volume_current",
            "financial_market_cap",
            "financial_previous_close",
            "financial_price_change",
            "financial_price_change_percent",
            "financial_last_updated_timestamp",
        }
        expected_names = core_names.copy()
        if debug_enabled:
            expected_names.update(
                {"financial_fetch_duration_seconds", "financial_fetch_errors"}
            )
        assert set(families) == expected_names
        for name in core_names:
            assert any(
                sample.labels["symbol"] == "AAPL" for sample in families[name].samples
            )
        if debug_enabled:
            for family_name, sample_name in (
                (
                    "financial_fetch_duration_seconds",
                    "financial_fetch_duration_seconds_count",
                ),
                ("financial_fetch_errors", "financial_fetch_errors_total"),
            ):
                samples = families[family_name].samples
                assert sum(s.value for s in samples if s.name == sample_name) == 1

        stocks = client.get("/api/stocks?symbols=AAPL")
        assert stocks.status_code == 200
        payload = stocks.get_json()
        assert payload["symbols"] == ["AAPL"]
        assert payload["data"]["AAPL"]["current_price"] == 110.0
        assert upstream.call_count == 2  # The API route reuses the successful fetch.


def _check_invalid_metric_type(metric_key: str, expected_type: str) -> None:
    """An absent metric is valid, but an invalid non-None metric must be rejected."""
    from src.metrics_factory import MetricsFactory

    with patch.object(
        MetricsFactory,
        "get_metric",
        side_effect=lambda key: "invalid" if key == metric_key else None,
    ):
        with pytest.raises(
            TypeError, match=f"Expected {expected_type} for {metric_key}"
        ):
            importlib.import_module("src.main")


def _run_in_fresh_process(
    command: str, environment: str, debug_metrics: str | None
) -> None:
    env = os.environ.copy()
    env["ENVIRONMENT"] = environment
    env["AUTO_CLEAR_METRICS"] = "true"
    env.pop("ENABLE_DEBUG_METRICS", None)
    if debug_metrics is not None:
        env["ENABLE_DEBUG_METRICS"] = debug_metrics
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from tests.test_main import _check_startup, _check_invalid_metric_type\n"
            + command,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("environment", "debug_metrics", "debug_enabled"),
    [
        pytest.param("production", None, False, id="production-default"),
        pytest.param("production", "false", False, id="production-explicit-false"),
        pytest.param("development", "false", False, id="development-explicit-false"),
        pytest.param("production", "true", True, id="production-explicit-true"),
        pytest.param("development", None, True, id="development-default"),
        pytest.param("development", "true", True, id="development-explicit-true"),
    ],
)
def test_startup_and_http_contract(
    environment: str, debug_metrics: str | None, debug_enabled: bool
) -> None:
    _run_in_fresh_process(
        f"_check_startup({debug_enabled!r})", environment, debug_metrics
    )


@pytest.mark.parametrize(
    ("request_timeout", "max_retries"),
    [("30", "3"), ("1", "0"), ("unused", "unused")],
    ids=["old-defaults", "custom-values", "non-numeric-values"],
)
@pytest.mark.parametrize(
    ("environment", "debug_enabled"),
    [("production", False), ("development", True)],
)
def test_startup_ignores_unused_timeout_retry_environment(
    monkeypatch: pytest.MonkeyPatch,
    request_timeout: str,
    max_retries: str,
    environment: str,
    debug_enabled: bool,
) -> None:
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", request_timeout)
    monkeypatch.setenv("MAX_RETRIES", max_retries)
    _run_in_fresh_process(f"_check_startup({debug_enabled!r})", environment, None)


@pytest.mark.parametrize("debug_metrics", ["false", "true"])
@pytest.mark.parametrize(
    ("metric_key", "expected_type"),
    [("financial_fetch_duration", "Histogram"), ("financial_fetch_errors", "Counter")],
)
def test_startup_rejects_invalid_metric_types(
    metric_key: str, expected_type: str, debug_metrics: str
) -> None:
    _run_in_fresh_process(
        f"_check_invalid_metric_type({metric_key!r}, {expected_type!r})",
        "development",
        debug_metrics,
    )
