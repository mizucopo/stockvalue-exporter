"""Run bounded HTTP scenarios inside a network-isolated benchmark container."""

import argparse
import json
import os
import re
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path

from common import price_for

EVENT_DIRECTORY = Path("/tmp/gunicorn-benchmark-events")
BASE_URL = "http://127.0.0.1:9100"
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
DEFAULT_SYMBOLS = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "TSLA",
    "^GSPC",
    "^NDX",
    "998405.T",
    "^N225",
    "BTC-USD",
]


def records() -> list[dict]:
    result = []
    for path in EVENT_DIRECTORY.glob("*.jsonl"):
        for line in path.read_text().splitlines():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                # A currently writing event is read again in the next snapshot.
                continue
    return result


def counters(since: float) -> dict:
    per_pid: dict[str, Counter] = defaultdict(Counter)
    per_symbol: dict[str, Counter] = defaultdict(Counter)
    for record in records():
        if record["time"] >= since:
            per_pid[str(record["pid"])][record["kind"]] += 1
            per_symbol[record["symbol"]][record["kind"]] += 1
    total: Counter = Counter()
    for counts in per_pid.values():
        total.update(counts)
    return {
        "total": dict(total),
        "per_pid": {pid: dict(counts) for pid, counts in per_pid.items()},
        "per_symbol": {symbol: dict(counts) for symbol, counts in per_symbol.items()},
    }


def memory() -> dict:
    """RSS is server-only; cgroup usage includes this probe and exec processes."""
    master_pid = 1
    worker_pids = []
    with suppress(OSError):
        worker_pids = [
            int(pid) for pid in Path("/proc/1/task/1/children").read_text().split()
        ]
    rss = {}
    for pid in [master_pid, *worker_pids]:
        try:
            rss[str(pid)] = (
                int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * PAGE_SIZE
            )
        except OSError, IndexError:
            continue
    cgroup = {}
    for field in ["current", "peak"]:
        path = Path(f"/sys/fs/cgroup/memory.{field}")
        if path.exists():
            cgroup[field + "_bytes"] = int(path.read_text())
    if not cgroup:
        for field, filename in [
            ("current", "memory.usage_in_bytes"),
            ("peak", "memory.max_usage_in_bytes"),
        ]:
            path = Path("/sys/fs/cgroup/memory") / filename
            if path.exists():
                cgroup[field + "_bytes"] = int(path.read_text())
    return {
        "master_pid": master_pid,
        "worker_pids": worker_pids,
        "master_rss_bytes": rss.get("1", 0),
        "worker_rss_bytes": {pid: value for pid, value in rss.items() if pid != "1"},
        "server_rss_sum_bytes": sum(rss.values()),
        "cgroup": cgroup,
    }


def request(path: str, symbols: list[str] | None = None, timeout: float = 15) -> dict:
    url = BASE_URL + path
    if symbols is not None:
        url += "?" + urllib.parse.urlencode({"symbols": ",".join(symbols)})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode()
            status = response.status
            pid = response.headers.get("X-Benchmark-Pid")
        result = {"status": status, "pid": pid, "body": body}
    except urllib.error.HTTPError as error:
        result = {"status": error.code, "body": error.read().decode(), "pid": None}
    except Exception as error:
        result = {"status": None, "error": type(error).__name__, "pid": None}
    result["seconds"] = time.monotonic() - start
    return result


def verify_api(response: dict, symbols: list[str]) -> None:
    assert response["status"] == 200, response
    body = json.loads(response["body"])
    assert set(body["data"]) == set(symbols), body
    for symbol in symbols:
        assert body["data"][symbol]["current_price"] == price_for(symbol), body


def metric_symbols(response: dict) -> set[str]:
    assert response["status"] == 200, response
    return set(
        re.findall(
            r'^financial_price_current\{[^\n]*symbol="([^"]+)"',
            response["body"],
            re.MULTILINE,
        )
    )


def compact(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "body"}


def latency(responses: list[dict]) -> dict:
    times = sorted(response["seconds"] for response in responses)
    return {
        "count": len(times),
        "min_seconds": min(times),
        "median_seconds": statistics.median(times),
        "max_seconds": max(times),
        "responses": [compact(response) for response in responses],
    }


class Sampler:
    def __init__(self) -> None:
        self.stop = threading.Event()
        # Boundary snapshots keep even a sub-interval request measurable.
        self.samples: list[dict] = [memory()]
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self) -> None:
        while not self.stop.is_set():
            self.samples.append(memory())
            self.stop.wait(0.02)

    def finish(self) -> dict:
        self.stop.set()
        self.thread.join()
        self.samples.append(memory())
        peak = max(self.samples, key=lambda value: value["server_rss_sum_bytes"])
        return {
            "sample_interval_seconds": 0.02,
            "sample_count": len(self.samples),
            "server_rss_peak_sample": peak,
            "cgroup_current_max_sample_bytes": max(
                sample["cgroup"].get("current_bytes", 0) for sample in self.samples
            ),
        }


def wait_ready(workers: int) -> None:
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        response = request("/health", timeout=0.3)
        worker_pids = memory()["worker_pids"]
        ready_pids = {
            value["pid"] for value in records() if value["kind"] == "worker_ready"
        }
        if (
            response["status"] == 200
            and len(worker_pids) == workers
            and set(worker_pids) <= ready_pids
        ):
            return
        time.sleep(0.05)
    raise RuntimeError("Gunicorn did not become ready within 25 seconds")


def prime_all_workers(workers: int, symbol: str) -> dict:
    """Bounded priming distinguishes warm-cache latency from process routing."""
    seen = set()
    responses = []
    for _ in range(16):
        # Cold parallel fetches keep accepted connections occupied, letting
        # every sync worker accept work before any one can serve the next batch.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            batch = list(
                executor.map(lambda _: request("/api/stocks", [symbol]), range(workers))
            )
        for response in batch:
            verify_api(response, [symbol])
            seen.add(response["pid"])
            responses.append(compact(response))
        if len(seen) == workers:
            return {"seen_worker_pids": sorted(seen), "responses": responses}
    raise RuntimeError(f"Unable to warm all {workers} workers after 64 attempts")


def scenario(name: str, run, output: dict) -> None:
    start = time.monotonic()
    value = run()
    output[name] = {"result": value, "counters": counters(start), "memory": memory()}


def run_workload(workers: int) -> dict:
    wait_ready(workers)
    output = {"idle_memory": memory(), "scenarios": {}}
    scenarios = output["scenarios"]
    sampler = Sampler()
    sampler.thread.start()
    try:

        def sequential():
            responses = [request("/api/stocks", ["SEQUENTIAL"]) for _ in range(8)]
            for response in responses:
                verify_api(response, ["SEQUENTIAL"])
            return latency(responses)

        scenario("same_symbol_sequential", sequential, scenarios)

        def concurrent():
            with ThreadPoolExecutor(max_workers=4) as executor:
                responses = list(
                    executor.map(
                        lambda _: request("/api/stocks", ["CONCURRENT"]), range(4)
                    )
                )
            for response in responses:
                verify_api(response, ["CONCURRENT"])
            return latency(responses)

        scenario("same_symbol_concurrent_cold", concurrent, scenarios)

        def scrape(symbols):
            scrape_sampler = Sampler()
            scrape_sampler.thread.start()
            try:
                response = request("/metrics", symbols)
            finally:
                scrape_memory = scrape_sampler.finish()
            expected = DEFAULT_SYMBOLS if symbols is None else symbols
            actual = metric_symbols(response)
            assert actual == set(expected), {"expected": expected, "actual": actual}
            return {
                **compact(response),
                "symbols": sorted(actual),
                "scrape_memory": scrape_memory,
            }

        scenario("cold_scrape_default_9", lambda: scrape(None), scenarios)
        scenario(
            "cold_scrape_max_12",
            lambda: scrape([f"MAX{index:02}" for index in range(12)]),
            scenarios,
        )
        scenario(
            "prime_all_workers", lambda: prime_all_workers(workers, "WARM"), scenarios
        )

        def warm(path):
            responses = [request(path, ["WARM"]) for _ in range(8)]
            for response in responses:
                if path == "/api/stocks":
                    verify_api(response, ["WARM"])
                else:
                    assert metric_symbols(response) == {"WARM"}
            return latency(responses)

        scenario("warm_api", lambda: warm("/api/stocks"), scenarios)
        scenario("warm_metrics", lambda: warm("/metrics"), scenarios)

        def mixed():
            with ThreadPoolExecutor(max_workers=3) as executor:
                cold = executor.submit(request, "/api/stocks", ["BLOCK"])
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if any(
                        value["kind"] == "fetch_start" and value["symbol"] == "BLOCK"
                        for value in records()
                    ):
                        break
                    time.sleep(0.005)
                else:
                    raise RuntimeError("Cold API did not enter its fixture fetch")
                cached = executor.submit(request, "/api/stocks", ["WARM"])
                health = executor.submit(request, "/health")
                cold_result = cold.result()
                cached_result = cached.result()
                health_result = health.result()
            verify_api(cold_result, ["BLOCK"])
            verify_api(cached_result, ["WARM"])
            assert health_result["status"] == 200, health_result
            return {
                "cold_api": compact(cold_result),
                "cached_api_during_cold": compact(cached_result),
                "health_during_cold": compact(health_result),
            }

        scenario("cold_api_with_cached_api_and_health", mixed, scenarios)

        def disjoint():
            symbols = [f"DISJOINT{index}" for index in range(4)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                responses = list(
                    executor.map(lambda symbol: request("/metrics", [symbol]), symbols)
                )
            reports = []
            for symbol, response in zip(symbols, responses, strict=True):
                actual = metric_symbols(response)
                reports.append(
                    {
                        **compact(response),
                        "expected_symbols": [symbol],
                        "actual_symbols": sorted(actual),
                        "isolated": actual == {symbol},
                    }
                )
            return {
                "all_responses_isolated": all(value["isolated"] for value in reports),
                "responses": reports,
            }

        scenario("concurrent_disjoint_metrics", disjoint, scenarios)
        assert not any(value["kind"] == "blocked_network" for value in records())
        output["quality"] = {
            "valid_api_prices_and_single_request_metrics": True,
            "concurrent_metrics_isolated": scenarios["concurrent_disjoint_metrics"][
                "result"
            ]["all_responses_isolated"],
            "blocked_external_socket_attempts": 0,
        }
    finally:
        output["workload_memory"] = sampler.finish()
    return output


def run_timeout(workers: int) -> dict:
    """A 2s Gunicorn timeout and 5s quote show sync/gthread timeout semantics."""
    wait_ready(workers)
    before = memory()
    start = time.monotonic()
    response = request("/api/stocks", ["TIMEOUT"], timeout=9)
    if response["status"] == 200:
        verify_api(response, ["TIMEOUT"])
    else:
        assert response["status"] in (None, 500), compact(response)
    deadline = time.monotonic() + 8
    after = memory()
    expect_restart = response["status"] != 200
    while time.monotonic() < deadline:
        ready_pids = {
            value["pid"] for value in records() if value["kind"] == "worker_ready"
        }
        changed = set(before["worker_pids"]) != set(after["worker_pids"])
        if (
            len(after["worker_pids"]) == workers
            and set(after["worker_pids"]) <= ready_pids
            and (not expect_restart or changed)
        ):
            break
        time.sleep(0.05)
        after = memory()
    if expect_restart:
        assert set(before["worker_pids"]) != set(after["worker_pids"]), after
    health = request("/health")
    assert health["status"] == 200, health
    return {
        "gunicorn_timeout_seconds": 2,
        "fixture_delay_seconds": 5,
        "response": compact(response),
        "workers_before": before["worker_pids"],
        "workers_after": after["worker_pids"],
        "worker_restarted": set(before["worker_pids"]) != set(after["worker_pids"]),
        "health_after": compact(health),
        "counters": counters(start),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--timeout-probe", action="store_true")
    args = parser.parse_args()
    result = (
        run_timeout(args.workers) if args.timeout_probe else run_workload(args.workers)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
