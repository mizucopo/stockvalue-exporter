"""Compare Gunicorn layouts using one local image and offline fixtures."""

import argparse
import json
import platform
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

CONFIGURATIONS = [
    ("4-sync", 4, 1),
    ("1-sync", 1, 1),
    ("1-gthread-4", 1, 4),
]


def docker(*arguments: str, timeout: float = 90) -> str:
    process = subprocess.run(
        ["docker", *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return process.stdout.strip()


def probe(image: str, workers: int, threads: int, delay: float, slow: bool) -> dict:
    name = "issue73-benchmark-" + uuid.uuid4().hex[:12]
    directory = Path(__file__).resolve().parent
    command = [
        "run",
        "--pull",
        "never",
        "--detach",
        "--name",
        name,
        "--network",
        "none",
        "--cpus",
        "2",
        "--memory",
        "512m",
        "--mount",
        f"type=bind,src={directory},dst=/benchmark,readonly",
        "--env",
        "PYTHONPATH=/benchmark:/app",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "LOG_LEVEL=WARNING",
        "--env",
        "ENABLE_DEBUG_METRICS=true",
        "--env",
        f"BENCHMARK_DELAY={delay}",
        image,
        "gunicorn",
        "--workers",
        str(workers),
        "--threads",
        str(threads),
        "--worker-class",
        "sync" if threads == 1 else "gthread",
        "--bind",
        "127.0.0.1:9100",
        "--timeout",
        "2" if slow else "30",
        "--chdir",
        "/app",
        "fixture_app:web",
    ]
    try:
        docker(*command)
        client = [
            "exec",
            name,
            "python",
            "/benchmark/probe.py",
            "--workers",
            str(workers),
        ]
        if slow:
            client.append("--timeout-probe")
        try:
            result = json.loads(docker(*client))
        except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
            logs = subprocess.run(
                ["docker", "logs", name], capture_output=True, text=True, check=False
            )
            detail = (
                error.stderr if isinstance(error, subprocess.CalledProcessError) else ""
            )
            raise RuntimeError(
                f"Probe failed: {error}\n{detail}\n"
                f"Server logs:\n{logs.stdout}{logs.stderr}"
            ) from error
        logs = subprocess.run(
            ["docker", "logs", name], capture_output=True, text=True, check=True
        )
        result["worker_timeout_log_count"] = (logs.stdout + logs.stderr).count(
            "WORKER TIMEOUT"
        )
        return result
    finally:
        # Run even if startup, assertions, Docker exec, or JSON parsing fails.
        subprocess.run(
            ["docker", "rm", "--force", name],
            capture_output=True,
            check=False,
            timeout=30,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="stockvalue-exporter:issue-73-baseline")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 5 or not 0 < args.delay <= 1:
        parser.error("Use 1..5 repeats and a fixture delay greater than 0 and <=1s")
    image_info = json.loads(docker("image", "inspect", args.image))[0]
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "host_platform": platform.platform(),
        "host_python": platform.python_version(),
        "image": args.image,
        "image_id": image_info["Id"],
        "image_architecture": image_info["Architecture"],
        "fixture_delay_seconds": args.delay,
        "container_cpu_limit": 2,
        "container_memory_limit_bytes": 512 * 1024 * 1024,
        "measurement_scope": (
            "Offline fixture replacing only yfinance.Ticker.info; actual Flask, "
            "Gunicorn, fetcher, cache and Prometheus code. No live Yahoo requests. "
            "RSS sum includes shared pages more than once; cgroup also includes "
            "the in-container probe. This does not measure Yahoo latency/rate "
            "limits, curl concurrency safety, or deployment load."
        ),
        "runs": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for repeat in range(args.repeats):
            for label, workers, threads in CONFIGURATIONS:
                print(f"Measuring {label}, repeat {repeat + 1}", flush=True)
                entry = {
                    "configuration": label,
                    "repeat": repeat + 1,
                    "workers": workers,
                    "threads": threads,
                    "workload": probe(args.image, workers, threads, args.delay, False),
                    "timeout_probe": probe(
                        args.image, workers, threads, args.delay, True
                    ),
                }
                report["runs"].append(entry)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
    except Exception as error:
        report["harness_error"] = str(error)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        raise
    print(f"Saved {len(report['runs'])} runs to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
