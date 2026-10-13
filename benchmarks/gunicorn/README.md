# Offline Gunicorn comparison

Run the three layouts against the **same locally built Docker image**:

```sh
python benchmarks/gunicorn/run.py \
  --image stockvalue-exporter:issue-73-baseline \
  --output /tmp/issue-73-baseline.json
```

`--repeats` defaults to 1 and is bounded to 5; `--delay` defaults to 0.1 seconds
per quote. No image is pulled or built by this command. Containers have identical
2 CPU / 512 MiB limits, run as the image's normal user, and are removed even if a
probe fails. The fixture directory is mounted read-only. No host port is exposed.

The fixture imports the actual `src.main:web` application and replaces only
`yfinance.Ticker.info` with deterministic nonzero data and a short delay. The
actual Ticker constructor, fetcher, cache, views and Prometheus registry execute.
Observation hooks record cache lookup hits/misses and quote fetch starts/ends
separately, per PID and symbol; a second cache lookup after waiting for a lock
therefore remains distinguishable from a real fetch. Responses carry an
observation-only worker PID header. Python sockets reject external addresses and
Docker `--network none` also prevents native curl networking.

Each run records master and individual worker RSS, server RSS sum, cgroup memory
current/peak, an idle snapshot, and 20 ms workload samples. RSS sums count shared
pages repeatedly; cgroup memory also includes the small in-container probe and
exec process. Peak memory is for that container's lifetime. Compare these measures
with their stated meanings rather than treating RSS sum as physical memory.
The cold default-nine and maximum-twelve scrape results additionally contain a
`scrape_memory` sampler scoped to each HTTP request, from immediately before
sending it until its response body is read. It records server RSS peak and cgroup
current maximum at a nominal 20 ms interval, plus start/end snapshots so a shorter
request still has samples. These sampled maxima are specific to that scrape;
the cgroup `peak_bytes` inside an RSS snapshot retains its container-lifetime
meaning. The outer workload sampler continues to cover the whole workload.

The bounded workload covers eight sequential same-symbol requests, four cold
same-symbol requests together, cold default-nine and maximum-twelve scrapes,
warm API/metrics latency, cached API and health during a 1.2 second cold API, and
four disjoint simultaneous scrapes. Warm latency follows bounded priming until
every worker has cached `WARM`. API prices and ordinary scrape symbol sets are
asserted. Disjoint response contamination is reported as a quality outcome so
the unchanged threaded baseline can expose a failure without discarding evidence.
All lookup/fetch counts are stored in JSON; HTTP bodies are not retained.
Latency includes the loopback HTTP client and observation-hook I/O; it is a
comparison within this fixture rather than an absolute production estimate.

A fresh container separately tests Gunicorn's 2 second worker timeout with a
5 second quote. It records the HTTP outcome, worker PID changes, post-probe health,
and timeout log count. A threaded worker's heartbeat may remain alive throughout
a slow request, so Gunicorn's timeout must not be interpreted as a per-request
deadline.

These are reproducible offline fixture measurements. They do not establish
real Yahoo latency, rate limits, native yfinance/curl thread safety, or production
capacity. Deployment checks and any carefully limited live-network validation
must be reported separately.
