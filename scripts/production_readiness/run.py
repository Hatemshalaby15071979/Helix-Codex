"""Execute the production-readiness gates and write an evidence pack.

Usage::

    python scripts/production_readiness/run.py --out evidence/production_readiness/run-1
    python scripts/production_readiness/run.py --tenant callcenterclient --json

Exit code 0 only when every gate is green. A red gate is a refusal to certify,
not a warning: the pack records the failure, the label becomes NOT_READY, and the
process exits non-zero.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import socket
import sys
from typing import Any, Dict, List, Optional, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.production_readiness import gates  # noqa: E402
from scripts.production_readiness.dataset import TENANTS, Tenant, load_tenants  # noqa: E402

READY = "SIMULATION_READINESS_EVIDENCED"
NOT_READY = "NOT_READY"

SYNTHETIC_DISCLOSURE = (
    "SYNTHETIC FIXTURE. callcenterclient and sportacademyclient are synthetic, "
    "client-shaped datasets built from documented generators. They contain no real "
    "client, customer, athlete or employee records. They are used here to exercise "
    "ingestion and the six engines against realistic operational shapes; no number "
    "in this pack is a claim about a real organisation."
)
REAL_DISCLOSURE = (
    "REAL-ONLY VIEW. The curated input is `16_DATA/real_only/`: accepted owner-supplied "
    "rows from the TelecomAcademy hub workbook, tracked per row in `REAL_DATA_REGISTER.csv`. "
    "No synthetic baseline row is included. Coverage is partial (8 of 39 tables); "
    "gates needing other tables must fail closed rather than fall back to synthetic data."
)
DISCLOSURE = REAL_DISCLOSURE if os.environ.get("HELIX_TENANT_CURATED_DIR") else SYNTHETIC_DISCLOSURE

MAPPED_TABLES = {
    "callcenterclient": [
        "agents",
        "rosters_daily",
        "queue_metrics_daily",
        "intraday_15min",
        "tickets",
        "pnl_monthly",
        "rate_cards",
        "requisitions",
        "applicants",
    ],
    "sportacademyclient": [
        "athletes",
        "coaches",
        "squads",
        "sessions",
        "attendance",
        "forecast_daily",
        "invoices",
        "feedback_surveys",
        "leavers",
    ],
}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_digest(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: pathlib.Path) -> int:
    with open(path, "rb") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _git_commit() -> str:
    """Read HEAD from the object store without shelling out to git."""
    git_dir = _ROOT / ".git"
    head_path = git_dir / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    if not head.startswith("ref:"):
        return head or "unknown"
    ref = head.split(" ", 1)[1].strip()
    try:
        return (git_dir / ref).read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        packed = git_dir / "packed-refs"
        try:
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.endswith(" " + ref):
                    return line.split(" ", 1)[0]
        except OSError:
            pass
    return "unknown"


def _run_id(now: datetime.datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def _tenant_manifest(tenant: Tenant) -> Dict[str, Any]:
    manifest_path = tenant.root / "21_MANIFEST" / "sha256sums.txt"
    tables: Dict[str, int] = {}
    for table in MAPPED_TABLES.get(tenant.name, []):
        path = tenant.table_path(table)
        if path.exists():
            tables[table] = _line_count(path)
    return {
        "root": str(tenant.root),
        "curated_dir": str(tenant.curated_dir),
        "curated_override": os.environ.get("HELIX_TENANT_CURATED_DIR", ""),
        "manifest_sha256": _file_digest(manifest_path) if manifest_path.exists() else "missing",
        "files_listed": len(tenant.manifest()),
        "curated_tables": len(tenant.available_tables()),
        "raw_exports": tenant.raw_names(),
        "mapped_table_rows": tables,
        "disclosure_present": tenant.disclosure_ok(),
    }


def _render_summary(
    run_id: str, label: str, results: Sequence[gates.GateResult], calls: Sequence[gates.EngineCall]
) -> str:
    passed = sum(1 for result in results if result.ok)
    lines = [
        "# Production-readiness evidence pack",
        "",
        f"**Run:** `{run_id}`  ",
        f"**Label:** `{label}`  ",
        f"**Gates:** {passed}/{len(results)} green  ",
        f"**Engine calls:** {len(calls)}  ",
        "",
        f"> {DISCLOSURE}",
        "",
        "## Gates",
        "",
        "| Gate | Title | Verdict | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        verdict = "PASS" if result.ok else "**FAIL**"
        detail = result.detail.replace("|", "\\|")
        lines.append(f"| `{result.gate_id}` | {result.title} | {verdict} | {detail} |")
    lines.extend(
        [
            "",
            "## Engine calls",
            "",
            "| Engine | Tenant | Client | Capability | Mode | ms | Error |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for call in calls:
        error = "-" if call.error is None else f"`{call.error.get('code')}`"
        lines.append(
            f"| {call.engine} | {call.tenant} | {call.client_id} | {call.capability} | "
            f"{call.data_mode} | {call.duration_ms} | {error} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python scripts/production_readiness/run.py \\",
            "  --out evidence/production_readiness/reproduce",
            "```",
            "",
            "A green pack is evidence that the six engines compute on these fixtures under",
            "the stated gates. It is not a `PRODUCTION` label: the nine production-only",
            "gates in `release/release-profiles.yaml` still require signed external evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def execute(tenants: Sequence[Tenant], out_dir: pathlib.Path) -> Dict[str, Any]:
    """Run every gate, write the pack, return the summary."""
    started = datetime.datetime.now(datetime.timezone.utc)
    run_id = _run_id(started)
    context = gates.RunContext(tenants=list(tenants))
    results: List[gates.GateResult] = []
    for gate_fn in gates.GATES:
        try:
            result = gate_fn(context)
        except Exception as exc:  # noqa: BLE001 - a raising gate is a red gate
            result = gates.GateResult(
                gate_id=getattr(gate_fn, "__name__", "unknown").upper(),
                title=getattr(gate_fn, "__name__", "unknown"),
                ok=False,
                detail=f"gate raised {type(exc).__name__}: {exc}",
            )
        results.append(result)
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.gate_id} {result.title} — {result.detail}")

    label = READY if all(result.ok for result in results) else NOT_READY
    finished = datetime.datetime.now(datetime.timezone.utc)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    datasets = {tenant.name: _tenant_manifest(tenant) for tenant in tenants}
    manifest = {
        "run_id": run_id,
        "label": label,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "host": socket.gethostname(),
        "disclosure": DISCLOSURE,
        "datasets": datasets,
        "datasets_digest": _sha256_text(json.dumps(datasets, sort_keys=True)),
    }
    gate_payload = {
        "run_id": run_id,
        "label": label,
        "summary": {
            "gates": len(results),
            "passed": sum(1 for result in results if result.ok),
            "failed": sum(1 for result in results if not result.ok),
        },
        "gates": [result.as_dict() for result in results],
    }
    calls_payload = {
        "run_id": run_id,
        "count": len(context.calls),
        "calls": [call.as_dict() for call in context.calls],
    }

    _write_json(out / "run_manifest.json", manifest)
    _write_json(out / "gate_results.json", gate_payload)
    _write_json(out / "engine_calls.json", calls_payload)
    (out / "EVIDENCE_SUMMARY.md").write_text(
        _render_summary(run_id, label, results, context.calls), encoding="utf-8"
    )
    checksums = {
        name: _file_digest(out / name)
        for name in (
            "run_manifest.json",
            "gate_results.json",
            "engine_calls.json",
            "EVIDENCE_SUMMARY.md",
        )
    }
    (out / "checksums.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )

    return {
        "label": label,
        "run_id": run_id,
        "out": str(out),
        "gates": len(results),
        "passed": gate_payload["summary"]["passed"],
        "checksums": checksums,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the production-readiness gates")
    parser.add_argument("--tenant", choices=("all",) + TENANTS, default="all")
    parser.add_argument("--out", default=None, help="evidence directory")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    names = TENANTS if args.tenant == "all" else (args.tenant,)
    try:
        tenants = load_tenants(names)
    except Exception as exc:  # noqa: BLE001 - no fixture, no verdict
        print(f"[FAIL] fixtures unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    out = (
        pathlib.Path(args.out)
        if args.out
        else pathlib.Path("evidence")
        / "production_readiness"
        / _run_id(datetime.datetime.now(datetime.timezone.utc))
    )
    summary = execute(tenants, out)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"label={summary['label']} gates={summary['passed']}/{summary['gates']} out={summary['out']}"
        )
    return 0 if summary["label"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
