#!/usr/bin/env python3
"""Bounded ingest soak against the cockpit engine at a 1,500-seat shape.

The plan asks for a six-hour, 1,500-seat soak with flat memory, latency
percentiles and zero dropped ticks. This script implements the measurement. The
default duration is intentionally short so a normal verification run is cheap;
``--minutes 360`` is the six-hour shape and must be chosen explicitly.

Usage::

    python scripts/soak_ingest.py --minutes 2 --rate 5 --out evidence/soak
    python scripts/soak_ingest.py --minutes 360 --rate 5   # six-hour shape

Exit 0 only when every tick was accepted, the engine stayed healthy, and memory
did not grow without bound; 1 otherwise; 2 when the engine could not start.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ingest_engine.py"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DISCLOSURE = (
    "SIMULATION ONLY. Synthetic telemetry against a locally spawned ingest engine. "
    "No hosted deployment, real traffic, or production capacity is measured."
)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _health(base: str, timeout: float = 2.0) -> bool:
    try:
        with OPENER.open(f"{base}/healthz", timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _rss_kib(pid: int) -> int | None:
    status = pathlib.Path(f"/proc/{pid}/status")
    try:
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _payload(index: int) -> dict[str, object]:
    # 1,500-seat shape: 1,500 active agents, ~10% in AUX, a stable queue.
    active = 1_500
    aux = 150 + (index % 5)
    waiting = 40 + (index % 17)
    return {
        "metrics": {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "calls_waiting": waiting,
            "longest_wait_time": float(12 + index % 9),
            "sla_percentage": 82.0,
            "active_agents": active,
            "aux_agents": aux,
        },
        "state": {"is_spike_active": False, "current_interval_volume": 413 + (index % 11)},
    }


def run(minutes: float, rate: float, out: pathlib.Path) -> int:
    import asyncio

    import httpx

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    handle, log_name = tempfile.mkstemp(prefix="helix-soak-", suffix=".log")
    log_path = pathlib.Path(log_name)
    # Fixed argv, locally resolved interpreter; no untrusted input reaches the shell.
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(ENGINE), "--host", "127.0.0.1", "--port", str(port)],  # noqa: S603
        cwd=ROOT,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    os.close(handle)
    started = time.monotonic()
    samples: list[float] = []
    errors: list[str] = []
    sent = 0
    memory: list[dict[str, object]] = []
    try:
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print(f"SOAK: engine exited early ({process.returncode})", file=sys.stderr)
                print(
                    log_path.read_text(encoding="utf-8", errors="replace")[-2000:], file=sys.stderr
                )
                return 2
            if _health(base):
                break
            time.sleep(0.25)
        else:
            print("SOAK: engine never became healthy", file=sys.stderr)
            return 2

        async def drive() -> None:
            nonlocal sent
            timeout = httpx.Timeout(10.0)
            async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
                end = time.monotonic() + minutes * 60.0
                interval = 1.0 / max(rate, 0.01)
                next_at = time.monotonic()
                while time.monotonic() < end:
                    payload = _payload(sent)
                    tick_started = time.monotonic()
                    try:
                        response = await client.post(f"{base}/api/v1/telemetry", json=payload)
                        elapsed = time.monotonic() - tick_started
                        if response.status_code != 200:
                            errors.append(f"tick {sent}: HTTP {response.status_code}")
                        else:
                            samples.append(elapsed)
                    except Exception as exc:  # noqa: BLE001 - a failed tick is data
                        errors.append(f"tick {sent}: {type(exc).__name__}: {exc}")
                    sent += 1
                    next_at += interval
                    delay = next_at - time.monotonic()
                    if delay > 0:
                        await asyncio.sleep(delay)

        async def monitor() -> None:
            while time.monotonic() < started + minutes * 60.0 + 1.0:
                rss = _rss_kib(process.pid)
                memory.append({"at": round(time.monotonic() - started, 2), "rss_kib": rss})
                await asyncio.sleep(min(10.0, max(1.0, minutes * 60.0 / 10.0)))

        async def main() -> None:
            await asyncio.gather(drive(), monitor())

        asyncio.run(main())
        healthy_after = _health(base)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        log_path.unlink(missing_ok=True)

    rss_values = [int(item["rss_kib"]) for item in memory if item["rss_kib"] is not None]
    rss_start = rss_values[0] if rss_values else 0
    rss_end = rss_values[-1] if rss_values else 0
    growth_ratio = (rss_end / rss_start) if rss_start else 1.0
    elapsed = time.monotonic() - started
    dropped = sent - len(samples)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "disclosure": DISCLOSURE,
        "configuration": {"minutes": minutes, "rate_per_second": rate, "seats": 1500},
        "duration_seconds": round(elapsed, 3),
        "ticks_sent": sent,
        "ticks_accepted": len(samples),
        "ticks_dropped": max(0, dropped),
        "errors": errors[:20],
        "error_count": len(errors),
        "latency_ms": {
            "p50": round(_percentile(samples, 0.50) * 1000.0, 3),
            "p95": round(_percentile(samples, 0.95) * 1000.0, 3),
            "p99": round(_percentile(samples, 0.99) * 1000.0, 3),
            "max": round(max(samples) * 1000.0, 3) if samples else 0.0,
        },
        "memory_kib": {
            "samples": memory,
            "start": rss_start,
            "end": rss_end,
            "growth_ratio": round(growth_ratio, 3),
        },
        "healthy_after": healthy_after,
        "engine_log_tail": log_tail[-1000:],
    }
    flat_memory = growth_ratio <= 1.20
    report["passed"] = bool(
        sent > 0 and not errors and healthy_after and flat_memory and max(0, dropped) == 0
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "soak-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (out / "soak-report.md").write_text(
        "\n".join(
            [
                "# Bounded ingest soak",
                "",
                f"> {DISCLOSURE}",
                "",
                f"- Duration: {report['duration_seconds']} s ({minutes} min requested)",
                f"- Ticks: {sent} sent, {len(samples)} accepted, {max(0, dropped)} dropped",
                f"- Errors: {len(errors)}",
                f"- Latency (ms): p50={report['latency_ms']['p50']} "
                f"p95={report['latency_ms']['p95']} p99={report['latency_ms']['p99']}",
                f"- Memory: {rss_start} KiB -> {rss_end} KiB (ratio {growth_ratio:.3f})",
                f"- Healthy after: {healthy_after}",
                f"- Verdict: {'PASS' if report['passed'] else 'FAIL'}",
                "",
                "## Limitations",
                "",
                "- Short verification runs are not the six-hour soak; pass `--minutes 360` for that shape.",
                "- A single local engine is not a production capacity or HA claim.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"SOAK: {'PASS' if report['passed'] else 'FAIL'} "
        f"sent={sent} accepted={len(samples)} errors={len(errors)} "
        f"p95={report['latency_ms']['p95']}ms rss_ratio={growth_ratio:.3f}"
    )
    return 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=float, default=2.0)
    parser.add_argument("--rate", type=float, default=5.0, help="ticks per second")
    parser.add_argument("--out", default=str(ROOT / "docs/production_readiness/evidence/soak"))
    args = parser.parse_args(argv)
    if args.minutes <= 0 or args.rate <= 0:
        parser.error("--minutes and --rate must be positive")
    return run(args.minutes, args.rate, pathlib.Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
