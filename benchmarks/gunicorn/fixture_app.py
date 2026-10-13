"""Load the real WSGI app with offline quotes and observation-only hooks.

Mount this directory read-only at /benchmark. No production source is changed.
The container must also use --network none: curl_cffi does not use Python sockets.
"""

import ipaddress
import json
import os
import socket
import threading
import time
from pathlib import Path

import yfinance as yf
from common import quote_for

EVENT_DIRECTORY = Path("/tmp/gunicorn-benchmark-events")
EVENT_DIRECTORY.mkdir(exist_ok=True)
EVENT_LOCK = threading.Lock()
BASE_DELAY = float(os.environ.get("BENCHMARK_DELAY", "0.1"))


def event(kind: str, symbol: str = "") -> None:
    """Append bounded observation records, separately for each worker PID."""
    record = {
        "time": time.monotonic(),
        "pid": os.getpid(),
        "thread": threading.get_ident(),
        "kind": kind,
        "symbol": symbol,
    }
    with EVENT_LOCK, (EVENT_DIRECTORY / f"{os.getpid()}.jsonl").open("a") as stream:
        stream.write(json.dumps(record) + "\n")


original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex


def check_address(address: object) -> None:
    """Permit Unix sockets and loopback only; deny unresolved hostnames too."""
    if isinstance(address, tuple):
        host = str(address[0])
        try:
            allowed = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            allowed = False
        if not allowed:
            event("blocked_network", host)
            raise RuntimeError(f"Benchmark blocked external socket address: {host}")


def offline_connect(connection: socket.socket, address: object) -> None:
    check_address(address)
    original_connect(connection, address)


def offline_connect_ex(connection: socket.socket, address: object) -> int:
    check_address(address)
    return original_connect_ex(connection, address)


socket.socket.connect = offline_connect
socket.socket.connect_ex = offline_connect_ex


def fixture_info(ticker: yf.Ticker) -> dict[str, object]:
    """Replace only Ticker.info; keep the real Ticker constructor and app path."""
    symbol = ticker.ticker
    event("fetch_start", symbol)
    delay = BASE_DELAY
    if symbol == "BLOCK":
        delay = 1.2
    elif symbol == "TIMEOUT":
        delay = 5.0
    elif symbol.startswith("DISJOINT"):
        delay = 0.15 * (int(symbol[-1]) + 1)
    time.sleep(delay)
    event("fetch_end", symbol)
    return quote_for(symbol)


yf.Ticker.info = property(fixture_info)

# Import only after guarding sockets and replacing the quote property.
from flask import Response  # noqa: E402

from src.main import app, web  # noqa: E402

original_cache_get = app.fetcher.cache.get


def observed_cache_get(key: str) -> object:
    value = original_cache_get(key)
    event("cache_hit" if value is not None else "cache_miss", key)
    return value


app.fetcher.cache.get = observed_cache_get


@web.after_request
def identify_worker(response: Response) -> Response:
    """Identify which independent process served each actual app response."""
    response.headers["X-Benchmark-Pid"] = str(os.getpid())
    return response


event("worker_ready")
