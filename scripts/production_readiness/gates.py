"""Fail-closed gates over the six engines and the two tenant fixtures.

Each gate returns a :class:`GateResult`. A gate is green only when its named
precondition held *and* the engine produced a number: an engine error, an empty
sample, a missing vendor defect, a mislabelled data mode or a non-deterministic
result all fail the gate. Nothing here raises to the caller; the runner reports
red gates and exits non-zero.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from scripts.production_readiness import ingest
from scripts.production_readiness.dataset import Tenant
from scripts.production_readiness.payloads import BuiltPayload, build_all

OWNER = {
    "wfm": "ops_gm",
    "rta": "ops_gm",
    "cx": "ops_gm",
    "b2b": "sales_gm",
    "personnel": "hr_personnel_gm",
    "crm": "sales_gm",
}

ACADEMY_SPORTS = (
    "football",
    "basketball",
    "swimming",
    "tennis",
    "athletics",
    "gymnastics",
    "martial_arts",
    "padel",
)


@dataclass
class EngineCall:
    """One adapter invocation, recorded for the evidence pack."""

    engine: str
    tenant: str
    client_id: str
    capability: str
    payload_digest: str
    result_digest: str
    duration_ms: int
    data_mode: str
    is_sample: bool
    warnings: List[str]
    error: Optional[Dict[str, Any]]
    metrics: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "tenant": self.tenant,
            "client_id": self.client_id,
            "capability": self.capability,
            "payload_digest": self.payload_digest,
            "result_digest": self.result_digest,
            "duration_ms": self.duration_ms,
            "data_mode": self.data_mode,
            "is_sample": self.is_sample,
            "warnings": list(self.warnings),
            "error": self.error,
            "metrics_digest": hashlib.sha256(_canonical(self.metrics).encode("utf-8")).hexdigest(),
        }


@dataclass
class GateResult:
    """The verdict of one gate, with the numbers that produced it."""

    gate_id: str
    title: str
    ok: bool
    detail: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "title": self.title,
            "ok": self.ok,
            "detail": self.detail,
            "metrics": self.metrics,
            "evidence": list(self.evidence),
        }


@dataclass
class RunContext:
    """Mutable state shared by the gates during one run."""

    tenants: List[Tenant]
    calls: List[EngineCall] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _adapter(engine: str):
    if engine == "wfm":
        from engines.wfm.adapter import adapt
    elif engine == "rta":
        from engines.rta.adapter import adapt
    elif engine == "cx":
        from engines.cx.adapter import adapt
    elif engine == "b2b":
        from engines.b2b.adapter import adapt
    elif engine == "personnel":
        from engines.personnel.adapter import adapt
    elif engine == "crm":
        from engines.crm.adapter import adapt
    else:
        raise ValueError(f"unknown engine {engine}")
    return adapt


def call_engine(
    context: RunContext,
    built: BuiltPayload,
    tenant: Tenant,
    client_id: str,
    *,
    role: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> EngineCall:
    """Invoke one adapter and record everything the evidence pack needs."""
    engine = built.engine
    owner = role or OWNER[engine]
    correlation = correlation_id or f"pr-{engine}-{tenant.name}-{len(context.calls)}"
    adapter = _adapter(engine)
    start = time.time()
    result = adapter(
        input_payload=built.payload,
        tenant_id=f"tenant-{tenant.name}",
        client_id=client_id,
        correlation_id=correlation,
        causation_id=None,
        actor=owner,
        owning_role_id=owner,
        is_sample=True,
    )
    duration = int((time.time() - start) * 1000)
    call = EngineCall(
        engine=engine,
        tenant=tenant.name,
        client_id=client_id,
        capability=(result.capability_ids[0] if result.capability_ids else ""),
        payload_digest=_digest(built.payload),
        result_digest=_digest({"metrics": result.metrics, "error": result.error}),
        duration_ms=duration,
        data_mode=str(result.data_mode),
        is_sample=bool(result.is_sample),
        warnings=list(result.warnings),
        error=result.error,
        metrics=result.metrics,
    )
    context.calls.append(call)
    return call


def gate_fixture_integrity(context: RunContext) -> GateResult:
    """The input is what its manifest says it is, in its declared data mode.

    A synthetic fixture is complete only with >=30 curated tables. A declared
    real view is necessarily partial (the client supplies a subset), so its
    completeness rule is different: the view's own manifest must declare real,
    every declared table must exist at its declared row count, and the named
    provenance register must match its digest. Both modes still require the
    estate hash manifest and the dataset-card disclosure to be intact.
    """
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        report = tenant.verify_manifest()
        mode = getattr(tenant, "data_mode", "synthetic")
        metrics[tenant.name] = {
            "files_listed": report.listed,
            "missing": len(report.missing),
            "mismatched": len(report.mismatched),
            "tables": len(tenant.available_tables()),
            "data_mode": mode,
            "disclosure_present": tenant.disclosure_ok(),
        }
        if not report.ok:
            problems.append(
                f"{tenant.name}: {len(report.missing)} missing, {len(report.mismatched)} mismatched"
            )
        if not tenant.disclosure_ok():
            problems.append(f"{tenant.name}: disclosure missing")

        if mode == "real":
            view = tenant.real_view_report()
            metrics[tenant.name]["real_view"] = view
            problems.extend(f"{tenant.name}: {issue}" for issue in view["problems"])
        elif mode == "synthetic":
            if len(tenant.available_tables()) < 30:
                problems.append(
                    f"{tenant.name}: only {len(tenant.available_tables())} curated tables"
                )
        else:
            problems.append(f"{tenant.name}: invalid declared data_mode {mode!r}")
    ok = not problems
    detail = (
        "inputs match their manifests and carry disclosure in their declared data mode"
        if ok
        else "; ".join(problems)
    )
    return GateResult("PR-G01", "fixture integrity + disclosure", ok, detail, metrics)


REQUIRED_DEFECTS = {
    "callcenterclient": {
        "zendesk_tickets_export.csv": ("duplicate_keys", "trailing_whitespace", "mixed_timezones"),
        "salesforce_cases_export.csv": ("null_on_closed",),
        "wfm_schedule_export.csv": ("locale_date", "uppercase_enum"),
        "payroll_export.csv": ("period_format",),
    },
    "sportacademyclient": {
        "playmetrics_registrations.csv": ("duplicate_keys", "trailing_whitespace"),
        "session_export.csv": ("locale_date", "uppercase_enum"),
        "payroll_export.csv": ("period_format",),
        "applicant_export.csv": ("blank_score_in_progress",),
        "itsm_export.csv": ("closed_at_null_on_open", "zero_resolution_on_open"),
    },
}


def gate_raw_defect_detection(context: RunContext) -> GateResult:
    """Every defect the raw layer declares is actually present and detected."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        required = REQUIRED_DEFECTS.get(tenant.name, {})
        if not required:
            problems.append(f"{tenant.name}: no defect contract declared")
            continue
        if "agents" in tenant.available_tables():
            known = set(tenant.read_curated("agents", columns=["agent_id"])["agent_id"].astype(str))
            sports: List[str] = []
        else:
            known = set(
                tenant.read_curated("coaches", columns=["coach_id"])["coach_id"].astype(str)
            )
            sports = sorted(
                tenant.read_curated("sessions", columns=["sport"])["sport"]
                .astype(str)
                .unique()
                .tolist()
            )
        per_file: Dict[str, Dict[str, Any]] = {}
        for name in required:
            try:
                frame = tenant.read_raw(name)
            except Exception as exc:  # noqa: BLE001 - fail closed with the reason
                problems.append(f"{tenant.name}/{name}: unreadable ({exc})")
                continue
            counts = {
                finding.code: finding.count
                for finding in ingest.scan_raw_export(name, frame, agents=known, sports=sports)
            }
            chaos_file = tenant.root / "16_DATA" / "raw_chaos" / name
            overlay: Dict[str, int] = {}
            overlay_cleaning: Dict[str, int] = {}
            if chaos_file.exists():
                overlay_frame = pd.read_csv(
                    chaos_file, dtype=str, keep_default_na=False, low_memory=False
                )
                overlay = {
                    finding.code: finding.count
                    for finding in ingest.scan_raw_export(
                        name, overlay_frame, agents=known, sports=sports
                    )
                }
                if tenant.name == "callcenterclient" and name == "zendesk_tickets_export.csv":
                    deduped = ingest.clean_tickets(overlay_frame)
                    retained, quarantined = ingest.quarantine_unmatched_references(
                        deduped, "Assignee", known
                    )
                    overlay_cleaning = {
                        "deduplicated_rows": int(len(deduped)),
                        "orphan_rows_quarantined": int(len(quarantined)),
                        "joinable_rows_retained": int(len(retained)),
                    }
                    if quarantined.empty or len(retained) + len(quarantined) != len(deduped):
                        problems.append(
                            f"{tenant.name}/{name}: orphan rows were not quarantined and counted"
                        )
            found_in: Dict[str, str] = {}
            for code in required[name]:
                if counts.get(code, 0) > 0:
                    found_in[code] = "raw"
                elif overlay.get(code, 0) > 0:
                    found_in[code] = "raw_chaos"
                else:
                    problems.append(
                        f"{tenant.name}/{name}: declared defect {code} measured 0 in raw and overlay"
                    )
            per_file[name] = {
                "raw_counts": counts,
                "chaos_counts": overlay,
                "overlay_cleaning": overlay_cleaning,
                "found_in": found_in,
                "primary_missing": [
                    code for code in required[name] if found_in.get(code) == "raw_chaos"
                ],
            }
        metrics[tenant.name] = {"defects": per_file}
        if tenant.name == "callcenterclient":
            raw = tenant.read_raw("zendesk_tickets_export.csv")
            cleaned = ingest.clean_tickets(raw)
            parsed = cleaned["created_at"].notna().mean() if "created_at" in cleaned else 0.0
            metrics[tenant.name].update(
                {
                    "tickets_raw_rows": int(raw.shape[0]),
                    "tickets_clean_rows": int(cleaned.shape[0]),
                    "duplicates_removed": int(raw.shape[0]) - int(cleaned.shape[0]),
                    "timestamps_parsed_pct": round(float(parsed) * 100.0, 2),
                }
            )
            if int(raw.shape[0]) == int(cleaned.shape[0]):
                problems.append(f"{tenant.name}: duplicate ticket keys were not removed")
            if float(parsed) < 1.0:
                problems.append(f"{tenant.name}: only {parsed:.2%} of ticket timestamps parsed")
            chaos_dir = tenant.root / "16_DATA" / "raw_chaos"
            schema_frame, schema_metadata = ingest.read_vendor_csv(
                chaos_dir / "zendesk_tickets_export_2025-09.csv"
            )
            schema_clean = ingest.clean_tickets(schema_frame)
            cp_frame, cp_metadata = ingest.read_vendor_csv(chaos_dir / "tickets_cp1252.csv")
            if (
                len(schema_clean) != schema_frame.TicketID.nunique()
                or schema_clean.ticket_id.isna().any()
            ):
                problems.append(
                    "callcenterclient: monthly TicketID schema variant did not normalize cleanly"
                )
            if len(cp_frame) != 100 or cp_metadata["encoding"] != "cp1252":
                problems.append(
                    "callcenterclient: cp1252 export was not decoded with all rows retained"
                )
            if not schema_metadata["bom"] or not schema_metadata["crlf"]:
                problems.append("callcenterclient: BOM/CRLF variant was not detected")
            metrics[tenant.name]["format_and_schema_variants"] = {
                "bom_variant": schema_metadata,
                "schema_variant_rows_retained": int(len(schema_clean)),
                "cp1252_variant": cp_metadata,
                "cp1252_rows_retained": int(len(cp_frame)),
            }
    try:
        workspace = pathlib.Path(__file__).resolve().parents[4]
        tools_dir = str(workspace / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from tenant_fidelity import validate_fidelity

        fidelity = validate_fidelity(context.tenants[0].root.parent)
        metrics["fidelity_acceptance"] = fidelity
    except Exception as exc:  # fail closed if a declared scenario cannot be proved
        problems.append(f"tenant EXT fidelity acceptance failed: {type(exc).__name__}: {exc}")
    ok = not problems
    detail = "all declared raw defects detected and cleaned" if ok else "; ".join(problems)
    return GateResult("PR-G02", "raw-layer defect detection", ok, detail, metrics)


def _queue_day(tenant: Tenant) -> Tuple[str, str, float]:
    from scripts.production_readiness.payloads import _first_queue

    day = "2026-10-27"
    queue_id = _first_queue(tenant)
    intraday = tenant.read_curated("intraday_15min")
    rows = intraday[(intraday["queue_id"] == queue_id) & (intraday["date"] == day)]
    if rows.empty:
        latest = intraday["date"].astype(str).max()
        rows = intraday[(intraday["queue_id"] == queue_id) & (intraday["date"] == latest)]
        day = latest
    staffed = pd.to_numeric(rows["staffed_agents"], errors="coerce").dropna()
    return day, queue_id, float(staffed.mean()) if not staffed.empty else 0.0


def gate_wfm_staffing(context: RunContext) -> GateResult:
    """Erlang C pricing of real queue-day volume produces plausible staffing."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["wfm"]
        client = "teleclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        optimal = float(call.metrics.get("optimal_agents", 0) or 0)
        service_level = float(call.metrics.get("service_level_achieved", -1) or -1)
        traffic = float(call.metrics.get("traffic_intensity", 0) or 0)
        if not 0 < optimal <= 2000:
            problems.append(f"{tenant.name}: optimal_agents={optimal} out of range")
        if not 0.0 <= service_level <= 1.0:
            problems.append(f"{tenant.name}: service_level_achieved={service_level} not a fraction")
        if traffic <= 0:
            problems.append(f"{tenant.name}: traffic_intensity={traffic} not positive")
        ratio = None
        if tenant.name == "callcenterclient":
            day, queue_id, observed = _queue_day(tenant)
            ratio = round(optimal / observed, 3) if observed else None
        else:
            coaches = tenant.read_curated("coaches")
            sport = built.provenance.get("sport") if "sport" in built.provenance else None
            observed = (
                float(coaches[coaches["sport"].astype(str) == str(sport)].shape[0])
                if sport
                else 0.0
            )
            ratio = round(optimal / observed, 3) if observed else None
        if ratio is not None and not 0.2 <= ratio <= 5.0:
            problems.append(f"{tenant.name}: required/observed staffing ratio {ratio} implausible")
        metrics[tenant.name] = {
            "client": client,
            "contacts": built.payload["contacts"],
            "interval_minutes": built.payload["interval_minutes"],
            "aht_seconds": built.payload["aht_seconds"],
            "service_level_target": built.payload["service_level_target"],
            "optimal_agents": optimal,
            "service_level_achieved": round(service_level, 4),
            "traffic_intensity": round(traffic, 2),
            "observed_staff_or_coaches": round(observed, 2) if ratio is not None else None,
            "required_to_observed": ratio,
            "provenance": built.provenance,
        }
        if (
            tenant.name == "callcenterclient"
            and getattr(tenant, "data_mode", "synthetic") == "synthetic"
        ):
            chaos_dir = tenant.root / "16_DATA" / "raw_chaos"
            wfm_chaos = pd.read_csv(chaos_dir / "wfm_queue_derived.csv", low_memory=False)
            outages = pd.read_csv(chaos_dir / "telephony_outages.csv", low_memory=False)
            offered = pd.to_numeric(outages.offered, errors="coerce")
            handled = pd.to_numeric(outages.handled, errors="coerce")
            safe_handled_rate = handled.div(offered.where(offered.ne(0))).fillna(0)
            if outages.date.nunique() != 2 or safe_handled_rate.isna().any():
                problems.append(
                    "callcenterclient: outage-day rate handling is incomplete or non-finite"
                )
            metrics["callcenterclient_wfm_chaos"] = {
                "short_abandon_count": int(pd.to_numeric(wfm_chaos["Short Abandon"]).sum()),
                "abandon_after_threshold_pct": round(
                    float(pd.to_numeric(wfm_chaos.abandon_after_threshold_pct).mean()), 3
                ),
                "outage_days": int(outages.date.nunique()),
                "outage_offered_contacts": int(offered.sum()),
                "outage_handled_contacts": int(handled.sum()),
                "outage_sla_zero_rows": int(pd.to_numeric(outages.sla_pct).eq(0).sum()),
            }
        elif tenant.name == "callcenterclient":
            metrics["callcenterclient_wfm_chaos"] = {
                "status": "NOT_APPLICABLE",
                "reason": "declared real input has no synthetic chaos overlay to verify",
            }
    ok = not problems
    detail = "Erlang C staffing is plausible on both fixtures" if ok else "; ".join(problems)
    return GateResult("PR-G03", "WFM staffing on real queue-day volume", ok, detail, metrics)


def gate_rta_adherence(context: RunContext) -> GateResult:
    """Schedule-vs-actual adherence reproduces the fixture's own adherence figures."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["rta"]
        client = "teleclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        adherence = float(call.metrics.get("overall_adherence", -1) or -1)
        if not 0.0 <= adherence <= 100.0:
            problems.append(f"{tenant.name}: overall_adherence={adherence} out of range")
        expected = None
        if tenant.name == "callcenterclient":
            expected = built.provenance.get("dataset_adherence_pct")
            tolerance = 2.0
        else:
            sessions = tenant.read_curated("sessions")
            day = built.provenance["date"]
            day_rows = sessions[sessions["session_date"] == day]
            booked = pd.to_numeric(day_rows["booked"], errors="coerce").sum()
            attended = pd.to_numeric(day_rows["attended"], errors="coerce").sum()
            expected = 100.0 * attended / booked if booked else None
            tolerance = 2.0
        if expected is not None:
            delta = abs(adherence - float(expected))
            if delta > tolerance:
                problems.append(
                    f"{tenant.name}: engine adherence {adherence:.2f} vs fixture {float(expected):.2f} "
                    f"(delta {delta:.2f}pp > {tolerance}pp)"
                )
            metrics[f"{tenant.name}_fixture_pct"] = round(float(expected), 3)
        metrics[tenant.name] = {
            "client": client,
            "overall_adherence_pct": round(adherence, 3),
            "scheduled_hours": round(float(call.metrics.get("total_scheduled_hours", 0) or 0), 2),
            "actual_hours": round(float(call.metrics.get("total_actual_hours", 0) or 0), 2),
            "agents_or_sessions": built.provenance.get("rows"),
            "provenance": built.provenance,
        }
        if (
            tenant.name == "callcenterclient"
            and getattr(tenant, "data_mode", "synthetic") == "synthetic"
        ):
            chaos_dir = tenant.root / "16_DATA" / "raw_chaos"
            split = pd.read_csv(chaos_dir / "split_shift_rosters.csv", low_memory=False)
            source = tenant.read_curated("rosters_daily")
            hours = ["scheduled_hours", "actual_hours", "handle_hours", "aux_hours"]
            split[hours] = split[hours].apply(pd.to_numeric, errors="coerce").fillna(0)
            source[hours] = source[hours].apply(pd.to_numeric, errors="coerce").fillna(0)
            split_totals = split.groupby(["agent_id", "roster_date"])[hours].sum().sort_index()
            source_totals = source.groupby(["agent_id", "roster_date"])[hours].sum().sort_index()
            totals_match = split_totals.round(3).equals(source_totals.round(3))
            if not totals_match:
                problems.append(
                    "callcenterclient: split-shift daily aggregation changed roster hours"
                )
            metrics["callcenterclient_split_shift"] = {
                "source_agent_days": int(len(source_totals)),
                "overlay_agent_days": int(len(split_totals)),
                "daily_hours_match_source": totals_match,
                "split_shift_agents": int(split.loc[split.split_marker == 1, "agent_id"].nunique()),
                "swap_marked_rows": int(pd.to_numeric(split.swap_marker).sum()),
            }
        elif tenant.name == "callcenterclient":
            metrics["callcenterclient_split_shift"] = {
                "status": "NOT_APPLICABLE",
                "reason": "split_shift_rosters.csv is a synthetic overlay keyed to synthetic agent ids; "
                "it is not a valid comparator for a declared real input",
            }
    ok = not problems
    detail = "adherence reproduces the fixture within 2pp" if ok else "; ".join(problems)
    return GateResult("PR-G04", "RTA adherence on roster/attendance data", ok, detail, metrics)


def _rank(values: Iterable[float]) -> List[float]:
    series = pd.Series(list(values))
    return series.rank(method="average").tolist()


def _spearman(left: Iterable[float], right: Iterable[float]) -> float:
    lhs = pd.Series(_rank(left))
    rhs = pd.Series(_rank(right))
    if lhs.std(ddof=0) == 0 or rhs.std(ddof=0) == 0:
        return 0.0
    return float(
        ((lhs - lhs.mean()) * (rhs - rhs.mean())).mean() / (lhs.std(ddof=0) * rhs.std(ddof=0))
    )


def gate_cx_risk(context: RunContext) -> GateResult:
    """Churn scores respond to real satisfaction and stay bounded and ordered."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["cx"]
        client = "travbookclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        risks = call.metrics.get("customer_risks", [])
        if not risks:
            problems.append(f"{tenant.name}: no customer risks returned")
            continue
        scores = [
            float(row.get("kpi_analysis", {}).get("weighted_score", -1) or -1) for row in risks
        ]
        csats = [float(row.get("kpi_data", {}).get("csat", 0) or 0) for row in risks]
        overall = float(call.metrics.get("overall_risk_score", -1) or -1)
        if not 0.0 <= overall <= 1.0:
            problems.append(f"{tenant.name}: overall_risk_score={overall} out of range")
        if any(score < 0 or score > 1 for score in scores):
            problems.append(f"{tenant.name}: a weighted KPI score is outside 0..1")
        correlation = _spearman(csats, scores)
        if correlation < 0.1:
            problems.append(
                f"{tenant.name}: KPI score does not rise with CSAT (rho={correlation:.3f})"
            )
        levels: Dict[str, int] = {}
        for row in risks:
            level = str(row.get("risk_level", "unknown"))
            levels[level] = levels.get(level, 0) + 1
        spread = max(scores) - min(scores)
        if len(levels) < 2 and spread <= 0.02:
            problems.append(
                f"{tenant.name}: risk engine returned one level and no score spread "
                f"for a tail-selected cohort ({levels}, spread={spread:.4f})"
            )
        metrics[tenant.name] = {
            "client": client,
            "customers_scored": len(risks),
            "overall_risk_score": round(overall, 4),
            "spearman_csat_vs_kpi_score": round(correlation, 4),
            "risk_levels": levels,
            "risk_score_spread": round(spread, 4),
            "provenance": built.provenance,
        }
    ok = not problems
    detail = "risk is bounded and ordered with CSAT" if ok else "; ".join(problems)
    return GateResult("PR-G05", "CX risk on real ticket/attendance cohorts", ok, detail, metrics)


def gate_b2b_onboarding(context: RunContext) -> GateResult:
    """Onboarding produces a real SOP and staffing plan from the tenant profile."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["b2b"]
        client = "teleclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        sop = call.metrics.get("sop", {}) or {}
        staffing = call.metrics.get("staffing_plan", {}) or {}
        if not sop.get("content"):
            problems.append(f"{tenant.name}: SOP has no content")
        if not staffing:
            problems.append(f"{tenant.name}: staffing plan is empty")
        if int(call.metrics.get("requirements_count", 0) or 0) < 1:
            problems.append(f"{tenant.name}: no requirements carried into onboarding")
        metrics[tenant.name] = {
            "client": client,
            "requirements": call.metrics.get("requirements_count"),
            "sop_keys": sorted(sop.keys())[:8],
            "staffing_keys": sorted(staffing.keys())[:8],
            "provenance": built.provenance,
        }
    ok = not problems
    detail = "SOP + staffing plan generated from tenant profile" if ok else "; ".join(problems)
    return GateResult("PR-G06", "B2B onboarding from client profile", ok, detail, metrics)


def gate_personnel_pipeline(context: RunContext) -> GateResult:
    """Hiring pipeline runs over real requisitions/applicants or coaches."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["personnel"]
        client = "teleclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        if int(call.metrics.get("total_candidates", 0) or 0) < 1:
            problems.append(f"{tenant.name}: no candidate entered the pipeline")
        if int(call.metrics.get("total_job_postings", 0) or 0) != 1:
            problems.append(f"{tenant.name}: expected exactly one job posting")
        metrics[tenant.name] = {
            "client": client,
            "candidates": call.metrics.get("total_candidates"),
            "postings": call.metrics.get("total_job_postings"),
            "pipeline_status": call.metrics.get("pipeline_status"),
            "provenance": built.provenance,
        }
    ok = not problems
    detail = "pipeline carries the real requisition and candidate" if ok else "; ".join(problems)
    return GateResult("PR-G07", "Personnel pipeline from requisitions/coaches", ok, detail, metrics)


def gate_crm_pipeline(context: RunContext) -> GateResult:
    """CRM pipeline value derives from real P&L / invoice history."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        built = dict(build_all(tenant))["crm"]
        client = "teleclient" if tenant.name == "callcenterclient" else "academy"
        call = call_engine(context, built, tenant, client)
        if call.error is not None:
            problems.append(f"{tenant.name}: engine error {call.error}")
            continue
        if int(call.metrics.get("total_deals", 0) or 0) < 1:
            problems.append(f"{tenant.name}: no deal reached the pipeline")
        if float(call.metrics.get("total_pipeline_value", 0) or 0) <= 0:
            problems.append(f"{tenant.name}: pipeline value is not positive")
        metrics[tenant.name] = {
            "client": client,
            "leads": call.metrics.get("total_leads"),
            "deals": call.metrics.get("total_deals"),
            "pipeline_value": round(float(call.metrics.get("total_pipeline_value", 0) or 0), 2),
            "provenance": built.provenance,
        }
    ok = not problems
    detail = "deal value is carried from tenant finance data" if ok else "; ".join(problems)
    return GateResult("PR-G08", "CRM pipeline on tenant account value", ok, detail, metrics)


def gate_authorization(context: RunContext) -> GateResult:
    """Every adapter refuses a role that owns no capability (fail-closed)."""
    from engines.contracts import ENGINE_BASELINE_PAYLOADS

    payloads = {
        "wfm": ENGINE_BASELINE_PAYLOADS["wfm"],
        "cx": ENGINE_BASELINE_PAYLOADS["cx"],
        "b2b": ENGINE_BASELINE_PAYLOADS["b2b"],
        "personnel": ENGINE_BASELINE_PAYLOADS["personnel"],
        "crm": ENGINE_BASELINE_PAYLOADS["crm"],
        "rta": {
            "schedule_data": {
                "agent_id": ["a"],
                "scheduled_min": [60],
                "date": ["2026-09-07"],
                "hour": [9],
                "scheduled_hours": [1.0],
            },
            "actual_data": {
                "agent_id": ["a"],
                "logged_min": [50],
                "productive_min": [50],
                "date": ["2026-09-07"],
                "hour": [9],
                "actual_hours": [0.83],
            },
            "is_sample": True,
        },
    }
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for engine, payload in payloads.items():
        adapter = _adapter(engine)
        result = adapter(
            input_payload=dict(payload),
            tenant_id="tenant-authz",
            client_id="client-authz",
            correlation_id=f"authz-{engine}",
            causation_id=None,
            actor="unknown_role",
            owning_role_id="unknown_role",
            is_sample=True,
        )
        code = (result.error or {}).get("code")
        metrics[engine] = {"error_code": code}
        if code != "unauthorized":
            problems.append(f"{engine}: unknown role was not denied (error={result.error})")
    ok = not problems
    detail = "all six adapters deny an unknown role" if ok else "; ".join(problems)
    return GateResult("PR-G09", "engine authorisation fails closed", ok, detail, metrics)


def gate_synthetic_disclosure(context: RunContext) -> GateResult:
    """Tenant-derived results are labelled sample with an explicit warning."""
    metrics: Dict[str, Any] = {"calls": len(context.calls)}
    problems: List[str] = []
    for call in context.calls:
        if call.error is not None:
            continue
        if call.data_mode != "sample":
            problems.append(f"{call.engine}/{call.tenant}: data_mode={call.data_mode!r}")
        if not call.is_sample:
            problems.append(f"{call.engine}/{call.tenant}: is_sample is false")
        if not any("sample" in warning.lower() for warning in call.warnings):
            problems.append(f"{call.engine}/{call.tenant}: no sample warning")
    for tenant in context.tenants:
        if not tenant.disclosure_ok():
            problems.append(f"{tenant.name}: fixture disclosure missing")
    ok = not problems
    detail = "every tenant-derived result is labelled sample" if ok else "; ".join(problems)
    return GateResult("PR-G10", "synthetic-data disclosure on results", ok, detail, metrics)


def gate_determinism(context: RunContext) -> GateResult:
    """A second call with the same payload returns the same metrics."""
    metrics: Dict[str, Any] = {}
    problems: List[str] = []
    for tenant in context.tenants:
        for engine in ("wfm", "rta"):
            built = dict(build_all(tenant))[engine]
            client = "teleclient" if tenant.name == "callcenterclient" else "academy"
            first = call_engine(context, built, tenant, client, correlation_id=f"det-{engine}-a")
            second = call_engine(context, built, tenant, client, correlation_id=f"det-{engine}-b")
            key = f"{tenant.name}:{engine}"
            metrics[key] = {
                "digest": first.payload_digest[:16],
                "stable": first.result_digest == second.result_digest,
            }
            if first.result_digest != second.result_digest:
                problems.append(f"{key}: repeated call produced different metrics")
    ok = not problems
    detail = "repeated calls are byte-identical in their metrics" if ok else "; ".join(problems)
    return GateResult("PR-G11", "determinism of engine results", ok, detail, metrics)


def gate_latency(context: RunContext) -> GateResult:
    """Every adapter call stays inside the readiness latency budget."""
    budget_ms = 5000
    slow = [call for call in context.calls if call.duration_ms > budget_ms]
    metrics = {
        "calls": len(context.calls),
        "max_ms": max((call.duration_ms for call in context.calls), default=0),
        "mean_ms": round(
            sum(call.duration_ms for call in context.calls) / max(1, len(context.calls)), 2
        ),
        "budget_ms": budget_ms,
    }
    ok = not slow
    detail = (
        f"all {len(context.calls)} calls under {budget_ms}ms"
        if ok
        else "; ".join(f"{call.engine}/{call.tenant} took {call.duration_ms}ms" for call in slow)
    )
    return GateResult("PR-G12", "engine latency budget", ok, detail, metrics)


GATES = (
    gate_fixture_integrity,
    gate_raw_defect_detection,
    gate_wfm_staffing,
    gate_rta_adherence,
    gate_cx_risk,
    gate_b2b_onboarding,
    gate_personnel_pipeline,
    gate_crm_pipeline,
    gate_authorization,
    gate_synthetic_disclosure,
    gate_determinism,
    gate_latency,
)
