# Bounded ingest soak

> SIMULATION ONLY. Synthetic telemetry against a locally spawned ingest engine. No hosted deployment, real traffic, or production capacity is measured.

- Duration: 130.724 s (2.0 min requested)
- Ticks: 600 sent, 600 accepted, 0 dropped
- Errors: 0
- Latency (ms): p50=1.61 p95=2.831 p99=3.607
- Memory: 53012 KiB -> 53056 KiB (ratio 1.001)
- Healthy after: True
- Verdict: PASS

## Limitations

- Short verification runs are not the six-hour soak; pass `--minutes 360` for that shape.
- A single local engine is not a production capacity or HA claim.
