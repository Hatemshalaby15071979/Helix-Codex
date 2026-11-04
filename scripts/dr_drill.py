#!/usr/bin/env python3
"""Disposable local disaster-recovery drill (simulated volume loss).

The plan asks for three repeated drills: stop the stack, destroy its volumes,
restore the newest verified backup into a clean environment, verify health,
schema, audit chain and tenant rows, and measure RTO/RPO.

There is no hosted stack in this branch, so this drill exercises the durable
state and the real backup/restore code paths in a disposable directory. It does
not prove a container-orchestrated restore, and it says so in its report.

Usage::

    python scripts/dr_drill.py --runs 3 --out docs/production_readiness/evidence/dr

Exit 0 only when every run restores and verifies; 1 otherwise.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helix_codex_app import db  # noqa: E402
from helix_codex_app.scripts.backup_app import backup_app  # noqa: E402
from helix_codex_app.scripts.restore_app import restore_app  # noqa: E402
from security.audit import AuditRecord, AuditTrail  # noqa: E402

DISCLOSURE = (
    "SIMULATION ONLY. Disposable local state, synthetic rows, no hosted stack. "
    "RTO/RPO measure this machine and these code paths; a real deployment needs a "
    "container-orchestrated drill against the real backup target."
)
TENANTS = ("tenant-callcenter", "tenant-sportacademy")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _seed(work: pathlib.Path) -> dict[str, object]:
    """Create an app DB, an audit chain and a memory tree from nothing."""
    app_db = work / "app.db"
    conn = db.connect(db_path=str(app_db))
    try:
        db._init_schema(conn)
        ids: list[str] = []
        for index, tenant in enumerate(TENANTS):
            ids.append(
                db.record_node(
                    conn,
                    tenant_id=tenant,
                    correlation_id=f"drill-{index}",
                    classification="internal",
                    nature="simulated_event",
                    kind="event",
                    created_by="dr-drill",
                    provenance_source="synthetic",
                    provenance_data_mode="simulated_realistic",
                    body={"drill": True, "tenant": tenant},
                )
            )
    finally:
        db.close(conn)

    audit_db = work / "audit.db"
    trail = AuditTrail(db_path=str(audit_db))
    try:
        previous = None
        for tenant in TENANTS:
            record = AuditRecord.new(
                event_type="drill_seed",
                actor="dr-drill",
                actor_type="service",
                decision="allowed",
                tenant_id=tenant,
                previous_hash=previous,
            )
            trail.append(record)
            previous = record.current_hash
    finally:
        trail.close()

    memory = work / "memory_stores"
    memory.mkdir()
    return {"app_db": app_db, "audit_db": audit_db, "memory": memory, "node_ids": ids}


def _count_rows(path: pathlib.Path) -> int:
    conn = db.connect(db_path=str(path))
    try:
        row = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return int(row[0]) if row else 0
    finally:
        db.close(conn)


def run_once(run_number: int) -> dict[str, object]:
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"helix-dr-{run_number}-"))
    backup_dir = work / "backup"
    restored_dir = work / "restored"
    backup_dir.mkdir()
    result: dict[str, object] = {"run": run_number, "temp_root": str(work), "steps": []}
    try:
        seeded = _seed(work)
        seeded_nodes = _count_rows(seeded["app_db"])
        result["steps"].append({"step": "seed", "nodes": seeded_nodes})

        manifest = backup_app(
            db_path=str(seeded["app_db"]),
            memory_root=str(seeded["memory"]),
            target_dir=str(backup_dir),
            audit_db_path=str(seeded["audit_db"]),
            release_manifest_path=str(ROOT / "release" / "release-manifest.json"),
        )
        backup_created = dt.datetime.fromisoformat(
            str(manifest["created_at"]).replace("Z", "+00:00")
        )
        result["steps"].append(
            {
                "step": "backup",
                "backup_created_at": _iso(backup_created),
                "nodes": manifest["node_count"],
                "files": len(manifest["files"]),
            }
        )

        # Simulated volume loss: remove every piece of live state, including the
        # audit DB and memory tree, before the restore starts.
        for path in (seeded["app_db"], seeded["audit_db"], seeded["memory"]):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        result["steps"].append({"step": "destroy", "removed": ["app.db", "audit.db", "memory"]})

        restore_started = _now()
        restored = restore_app(backup_dir=str(backup_dir), target_dir=str(restored_dir))
        restore_finished = _now()
        rto_seconds = (restore_finished - restore_started).total_seconds()
        rpo_seconds = (restore_started - backup_created).total_seconds()

        restored_db = restored_dir / "helix_codex_app" / "app.db"
        restored_nodes = _count_rows(restored_db) if restored_db.is_file() else 0
        schema_tables = 0
        if restored_db.is_file():
            conn = db.connect(db_path=str(restored_db))
            try:
                schema_tables = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                    ).fetchone()[0]
                )
            finally:
                db.close(conn)

        passed = bool(
            restored.get("verified")
            and restored_nodes == seeded_nodes
            and restored.get("chains_verified")
            and restored.get("audit", {}).get("ok")
            and schema_tables > 0
        )
        result.update(
            {
                "rto_seconds": round(rto_seconds, 4),
                "rpo_seconds": round(rpo_seconds, 4),
                "restored_nodes": restored_nodes,
                "schema_tables": schema_tables,
                "chains_verified": restored.get("chains_verified"),
                "audit": restored.get("audit"),
                "verified": restored.get("verified"),
                "passed": passed,
            }
        )
        result["steps"].append(
            {
                "step": "restore",
                "rto_seconds": round(rto_seconds, 4),
                "rpo_seconds": round(rpo_seconds, 4),
                "nodes": restored_nodes,
                "schema_tables": schema_tables,
            }
        )
        return result
    except Exception as exc:  # noqa: BLE001 - a raising drill is a failed drill
        result.update({"passed": False, "error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)
        result["cleanup"] = {"temp_root": str(work), "removed": not work.exists()}


def _render(report: dict[str, object]) -> str:
    runs = report["runs"]
    lines = [
        "# Disaster-recovery drill (simulated volume loss)",
        "",
        f"> {DISCLOSURE}",
        "",
        f"**Runs:** {len(runs)}  ",
        f"**Passed:** {report['passed']}/{len(runs)}  ",
        f"**Generated:** {report['generated_at']}",
        "",
        "| Run | Passed | RTO (s) | RPO (s) | Nodes | Tables | Audit chain | Error |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        lines.append(
            f"| {run['run']} | {run.get('passed')} | {run.get('rto_seconds', '-')} | "
            f"{run.get('rpo_seconds', '-')} | {run.get('restored_nodes', '-')} | "
            f"{run.get('schema_tables', '-')} | "
            f"{run.get('audit', {}).get('ok', '-')} | {run.get('error', '-')} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The drill destroys disposable local files, not container volumes.",
            "- RTO/RPO are single-machine measurements and are not production SLOs.",
            "- The restore target is clean by construction; it does not exercise a cold standby host.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", default=str(ROOT / "docs/production_readiness/evidence/dr"))
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be >= 1")

    started = time.monotonic()
    runs = [run_once(index + 1) for index in range(args.runs)]
    report = {
        "generated_at": _iso(_now()),
        "disclosure": DISCLOSURE,
        "duration_seconds": round(time.monotonic() - started, 3),
        "runs": runs,
        "passed": sum(1 for run in runs if run.get("passed")),
        "all_passed": all(run.get("passed") for run in runs),
    }
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dr-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (out / "dr-report.md").write_text(_render(report), encoding="utf-8")
    for run in runs:
        state = "PASS" if run.get("passed") else "FAIL"
        print(
            f"[{state}] run {run['run']}: RTO={run.get('rto_seconds', '-')}s "
            f"RPO={run.get('rpo_seconds', '-')}s {run.get('error', '')}"
        )
    print(
        f"DR_DRILL: {'PASS' if report['all_passed'] else 'FAIL'} ({report['passed']}/{len(runs)})"
    )
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
