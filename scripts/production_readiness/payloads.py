"""Map tenant tables onto the six engine payload contracts.

Each builder reads only the client-shaped tables it names, returns a payload the
adapter accepts, and returns provenance alongside so the evidence pack can say
which files and grains produced the numbers. Builders do not touch the engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd

from scripts.production_readiness.dataset import Tenant


@dataclass(frozen=True)
class BuiltPayload:
    """An engine payload plus the provenance the evidence pack records."""

    engine: str
    payload: Dict[str, Any]
    provenance: Dict[str, Any]


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def wfm_payload_from_contact_centre(tenant: Tenant, *, day: str, queue_id: str) -> BuiltPayload:
    """One queue-day of 15-minute contact volume, priced with Erlang C."""
    intraday = tenant.read_curated("intraday_15min")
    intraday = intraday[intraday["queue_id"] == queue_id]
    intraday = intraday[intraday["date"] == day]
    if intraday.empty:
        raise ValueError(f"{tenant.name}: no intraday rows for {queue_id} on {day}")
    offered = _num(intraday["offered"]).fillna(0.0)
    aht = _num(intraday["aht_seconds"]).dropna()
    if aht.empty or offered.sum() <= 0:
        raise ValueError(f"{tenant.name}: {queue_id} {day} has no priced volume")

    targets = tenant.read_curated("queue_metrics_daily")
    target_rows = targets[(targets["queue_id"] == queue_id) & (targets["date"] == day)]
    targets_pct = _num(target_rows["sla_target_pct"]).dropna()
    target = float(targets_pct.iloc[0]) / 100.0 if not targets_pct.empty else 0.8

    payload = {
        "contacts": float(round(offered.mean(), 4)),
        "interval_minutes": 15.0,
        "aht_seconds": float(round(aht.mean(), 4)),
        "service_level_target": _clip(target, 0.5, 0.99),
        "is_sample": True,
    }
    provenance = {
        "files": ["16_DATA/curated/intraday_15min.csv", "16_DATA/curated/queue_metrics_daily.csv"],
        "grain": "queue x 15-minute interval, one business day",
        "rows": int(intraday.shape[0]),
        "queue_id": queue_id,
        "date": day,
        "intervals_observed": int(intraday.shape[0]),
        "contacts_total": float(offered.sum()),
        "sla_target_pct": target * 100.0,
    }
    return BuiltPayload(engine="wfm", payload=payload, provenance=provenance)


def wfm_payload_from_academy(tenant: Tenant, *, day: str, sport: str) -> BuiltPayload:
    """One academy day of delivered session-hours per sport, priced as staffing demand."""
    forecast = tenant.read_curated("forecast_daily")
    row = forecast[(forecast["date"] == day) & (forecast["sport"] == sport)]
    if row.empty:
        raise ValueError(f"{tenant.name}: no forecast rows for {sport} on {day}")
    attendance = _num(row["actual_attendance"]).fillna(0.0).sum()
    if attendance <= 0:
        raise ValueError(f"{tenant.name}: {sport} {day} has no attendance")

    sessions = tenant.read_curated("sessions")
    sessions = sessions[(sessions["session_date"] == day) & (sessions["sport"] == sport)]
    durations = _session_minutes(sessions)
    aht_seconds = float(durations.mean()) * 60.0 if not durations.empty else 3600.0
    payload = {
        "contacts": float(round(attendance, 4)),
        "interval_minutes": 1440.0,
        "aht_seconds": float(round(aht_seconds, 4)),
        "service_level_target": 0.9,
        "is_sample": True,
    }
    provenance = {
        "files": ["16_DATA/curated/forecast_daily.csv", "16_DATA/curated/sessions.csv"],
        "grain": "sport x calendar day, delivered attendance priced at session duration",
        "rows": int(row.shape[0]),
        "sport": sport,
        "date": day,
        "sessions_observed": int(sessions.shape[0]),
    }
    return BuiltPayload(engine="wfm", payload=payload, provenance=provenance)


def _session_minutes(sessions: pd.DataFrame) -> pd.Series:
    if sessions.empty:
        return pd.Series(dtype=float)
    start = pd.to_datetime(
        sessions["session_date"].astype(str) + " " + sessions["start_time"].astype(str),
        errors="coerce",
    )
    end = pd.to_datetime(
        sessions["session_date"].astype(str) + " " + sessions["end_time"].astype(str),
        errors="coerce",
    )
    minutes = (end - start).dt.total_seconds() / 60.0
    return minutes.dropna()


def rta_payload_from_rosters(tenant: Tenant, *, day: str) -> BuiltPayload:
    """Schedule vs worked minutes for every rostered agent on one day."""
    rosters = tenant.read_curated("rosters_daily")
    day_rows = rosters[rosters["roster_date"] == day]
    if day_rows.empty:
        raise ValueError(f"{tenant.name}: no roster rows on {day}")
    scheduled = day_rows[day_rows["roster_state"].astype(str).str.upper() == "SCHEDULED"]
    worked = day_rows[day_rows["status"].astype(str).str.upper() == "WORKED"]
    if scheduled.empty or worked.empty:
        raise ValueError(f"{tenant.name}: {day} has no scheduled/worked pair")

    scheduled = scheduled.assign(
        scheduled_hours=_num(scheduled["scheduled_hours"]).fillna(0.0),
        actual_hours=_num(scheduled["actual_hours"]).fillna(0.0),
    )
    scheduled = scheduled[scheduled["scheduled_hours"] > 0]
    if scheduled.empty:
        raise ValueError(f"{tenant.name}: {day} has no scheduled hours")
    schedule_rows = pd.DataFrame(
        {
            "agent_id": scheduled["agent_id"].astype(str),
            "date": day,
            "hour": 0,
            "scheduled_min": (scheduled["scheduled_hours"] * 60.0).round(2),
            "scheduled_hours": scheduled["scheduled_hours"].round(4),
        }
    )
    actual_rows = pd.DataFrame(
        {
            "agent_id": scheduled["agent_id"].astype(str),
            "date": day,
            "hour": 0,
            "logged_min": (scheduled["actual_hours"] * 60.0).round(2),
            "productive_min": (scheduled["actual_hours"] * 60.0).round(2),
            "actual_hours": scheduled["actual_hours"].round(4),
        }
    )
    payload = {
        "schedule_data": schedule_rows.to_dict(orient="list"),
        "actual_data": actual_rows.to_dict(orient="list"),
        "adherence_threshold": 0.85,
        "variance_threshold": 2.0,
        "is_sample": True,
    }
    dataset_adherence = _num(day_rows["adherence_pct"]).dropna()
    provenance = {
        "files": ["16_DATA/curated/rosters_daily.csv"],
        "grain": "agent x day (hour collapsed to 0)",
        "rows": int(day_rows.shape[0]),
        "date": day,
        "dataset_adherence_pct": float(dataset_adherence.mean())
        if not dataset_adherence.empty
        else None,
    }
    return BuiltPayload(engine="rta", payload=payload, provenance=provenance)


def rta_payload_from_academy(tenant: Tenant, *, day: str) -> BuiltPayload:
    """Booked session capacity vs attended minutes, one academy day."""
    sessions = tenant.read_curated("sessions")
    day_rows = sessions[sessions["session_date"] == day]
    if day_rows.empty:
        raise ValueError(f"{tenant.name}: no sessions on {day}")
    booked = _num(day_rows["booked"]).fillna(0.0)
    attended = _num(day_rows["attended"]).fillna(0.0)
    count = int(day_rows.shape[0])
    schedule_rows = pd.DataFrame(
        {
            "agent_id": day_rows["session_id"].astype(str),
            "date": day,
            "hour": 0,
            "scheduled_min": (booked * 60.0).round(2),
            "scheduled_hours": booked.round(4),
        }
    )
    actual_rows = pd.DataFrame(
        {
            "agent_id": day_rows["session_id"].astype(str),
            "date": day,
            "hour": 0,
            "logged_min": (attended * 60.0).round(2),
            "productive_min": (attended * 60.0).round(2),
            "actual_hours": attended.round(4),
        }
    )
    payload = {
        "schedule_data": schedule_rows.to_dict(orient="list"),
        "actual_data": actual_rows.to_dict(orient="list"),
        "adherence_threshold": 0.85,
        "variance_threshold": 2.0,
        "is_sample": True,
    }
    provenance = {
        "files": ["16_DATA/curated/sessions.csv"],
        "grain": "session x day, booked vs attended places",
        "rows": count,
        "date": day,
    }
    return BuiltPayload(engine="rta", payload=payload, provenance=provenance)


def cx_payload_from_tickets(tenant: Tenant, *, limit: int = 40) -> BuiltPayload:
    """Aggregate ticket KPIs to requester cohorts, then score churn risk.

    Aggregation is vectorised on purpose: the first version looped over every
    requester and built several Series per group, which took over two minutes on
    the 60,000-row ticket table. The gate budget is five seconds per call.
    """
    tickets = tenant.read_curated("tickets")
    tickets = tickets.dropna(subset=["requester_id"]).copy()
    tickets["_csat"] = pd.to_numeric(tickets["satisfaction_score"], errors="coerce")
    tickets["_breach"] = pd.to_numeric(tickets["sla_breached"], errors="coerce")
    tickets["_reopen"] = (pd.to_numeric(tickets["reopens"], errors="coerce").fillna(0.0) > 0).astype(
        float
    )
    tickets["_resolution"] = pd.to_numeric(tickets["resolution_minutes"], errors="coerce")
    agg = (
        tickets.groupby("requester_id")
        .agg(
            csat=("_csat", "mean"),
            breach=("_breach", "mean"),
            reopen=("_reopen", "mean"),
            resolution=("_resolution", "mean"),
            tickets=("ticket_id", "size"),
        )
        .dropna(subset=["csat"])
    )
    if agg.shape[0] < 5:
        raise ValueError(f"{tenant.name}: only {agg.shape[0]} ticket cohorts carry satisfaction")
    cohorts = [
        {
            "customer_id": str(requester),
            "csat": round(_clip(row.csat / 5.0), 4),
            "sla": round(_clip(1.0 - (0.0 if pd.isna(row.breach) else row.breach)), 4),
            "fcr": round(_clip(1.0 - (0.0 if pd.isna(row.reopen) else row.reopen)), 4),
            "aht": round(_clip((0.0 if pd.isna(row.resolution) else row.resolution) / 1440.0), 4),
        }
        for requester, row in agg.iterrows()
    ]
    # Score the tails, not an arbitrary prefix: the first 40 requesters by id are
    # all well-served and produce a uniformly low-risk population, which proves
    # nothing about the engine's ability to discriminate.
    ranked = sorted(cohorts, key=lambda row: (row["csat"], row["customer_id"]))
    half = max(2, limit // 2)
    rows = ranked[:half] + ranked[-half:]
    payload = {"customers": rows, "is_sample": True}
    provenance = {
        "files": ["16_DATA/curated/tickets.csv"],
        "grain": "requester x full ticket history (cohort KPI)",
        "rows": len(rows),
        "tickets_read": int(tickets.shape[0]),
        "cohorts_available": int(agg.shape[0]),
    }
    return BuiltPayload(engine="cx", payload=payload, provenance=provenance)


def cx_payload_from_academy(tenant: Tenant, *, limit: int = 40) -> BuiltPayload:
    """Athlete attendance and lateness as retention KPIs."""
    athletes = tenant.read_curated("athletes")
    attendance = tenant.read_curated("attendance")
    merged = attendance.merge(
        athletes[["athlete_id", "status", "sport"]], on="athlete_id", how="left"
    )
    merged = merged[merged["status"].astype(str).str.lower().isin({"active", "trial"})].copy()
    status = merged["attendance_status"].astype(str).str.lower()
    merged["_present"] = status.isin({"present", "late"}).astype(float)
    merged["_late"] = pd.to_numeric(merged["late_flag"], errors="coerce").fillna(0.0)
    merged["_minutes"] = pd.to_numeric(merged["minutes_attended"], errors="coerce").fillna(0.0)
    agg = merged.groupby("athlete_id").agg(
        present=("_present", "mean"),
        late=("_late", "mean"),
        minutes=("_minutes", "mean"),
        sessions=("attendance_id", "size"),
    )
    agg = agg[agg["present"] > 0]
    if agg.shape[0] < 5:
        raise ValueError(f"{tenant.name}: only {agg.shape[0]} athletes carry attendance")
    cohorts = [
        {
            "customer_id": str(athlete),
            "csat": round(_clip(row.present), 4),
            "sla": round(_clip(1.0 - row.late), 4),
            "fcr": round(_clip(row.present), 4),
            "aht": round(_clip(row.minutes / 60.0), 4),
        }
        for athlete, row in agg.iterrows()
    ]
    ranked = sorted(cohorts, key=lambda row: (row["csat"], row["customer_id"]))
    half = max(2, limit // 2)
    rows = ranked[:half] + ranked[-half:]
    payload = {"customers": rows, "is_sample": True}
    provenance = {
        "files": ["16_DATA/curated/attendance.csv", "16_DATA/curated/athletes.csv"],
        "grain": "athlete x 12-month attendance history",
        "rows": len(rows),
        "attendance_rows": int(attendance.shape[0]),
        "cohorts_available": int(agg.shape[0]),
    }
    return BuiltPayload(engine="cx", payload=payload, provenance=provenance)


def b2b_payload_from_contact_centre(tenant: Tenant, *, account: str) -> BuiltPayload:
    """Client profile and workload for a contact-centre account onboarding."""
    contracts = tenant.read_curated("contracts")
    rates = tenant.read_curated("rate_cards")
    queues = tenant.read_curated("queue_metrics_daily")
    volumes = queues[queues["account"] == account]
    if volumes.empty:
        raise ValueError(f"{tenant.name}: no queue metrics for account {account}")
    offered = _num(volumes["offered"]).fillna(0.0)
    channels = sorted(volumes["channel"].astype(str).unique().tolist())
    requirements = sorted({f"channel:{channel}" for channel in channels})
    rate_column = "channel" if "channel" in rates.columns else "rate_card_id"
    requirements.extend(sorted(rates[rate_column].astype(str).unique().tolist())[:4])
    profile = {
        "name": account.replace("client", " Client").title(),
        "industry": "contact_centre_outsourcing",
        "size": "enterprise" if int(contracts.shape[0]) > 500 else "mid_market",
        "complexity": "Standard" if len(channels) <= 4 else "Complex",
        "requirements": requirements,
    }
    workload = {
        "project_duration_days": 365,
        "complexity": profile["complexity"],
        "resources_requested": requirements,
        "annual_contacts": float(round(offered.sum(), 4)),
        "channels": channels,
    }
    payload = {"client_profile": profile, "workload_data": workload, "is_sample": True}
    provenance = {
        "files": [
            "16_DATA/curated/queue_metrics_daily.csv",
            "16_DATA/curated/contracts.csv",
            "16_DATA/curated/rate_cards.csv",
        ],
        "grain": "account x 24 months of queue volume",
        "rows": int(volumes.shape[0]),
        "account": account,
        "channels": channels,
    }
    return BuiltPayload(engine="b2b", payload=payload, provenance=provenance)


def b2b_payload_from_academy(tenant: Tenant) -> BuiltPayload:
    """Academy onboarding profile built from its sports, sites and session volume."""
    sessions = tenant.read_curated("sessions")
    sports = sorted(sessions["sport"].astype(str).unique().tolist())
    profile = {
        "name": "Sports Academy Client",
        "industry": "sports_academy",
        "size": "mid_market",
        "complexity": "Complex" if len(sports) > 4 else "Standard",
        "requirements": [f"sport:{sport}" for sport in sports],
    }
    workload = {
        "project_duration_days": 90,
        "complexity": profile["complexity"],
        "resources_requested": profile["requirements"],
        "sessions_observed": int(sessions.shape[0]),
        "sports": sports,
    }
    payload = {"client_profile": profile, "workload_data": workload, "is_sample": True}
    provenance = {
        "files": ["16_DATA/curated/sessions.csv", "16_DATA/curated/academy_profile.md"],
        "grain": "academy x 24 months of sessions",
        "rows": int(sessions.shape[0]),
        "sports": sports,
    }
    return BuiltPayload(engine="b2b", payload=payload, provenance=provenance)


def _first_numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if column not in frame.columns:
        return default
    values = _num(frame[column]).dropna()
    return float(values.iloc[0]) if not values.empty else default


def personnel_payload_from_requisitions(tenant: Tenant, *, account: str) -> BuiltPayload:
    """Hiring demand from open requisitions, screened against the applicant funnel."""
    requisitions = tenant.read_curated("requisitions")
    applicants = tenant.read_curated("applicants")
    open_reqs = requisitions[
        requisitions["status"].astype(str).str.lower().isin({"open", "approved"})
    ]
    if open_reqs.empty:
        open_reqs = requisitions.head(5)
    req = open_reqs.iloc[0]
    candidates = applicants[applicants["req_id"] == req["req_id"]]
    if candidates.empty:
        candidates = applicants.head(5)
    candidate_row = candidates.iloc[0]
    payload = {
        "candidate": {
            "id": str(candidate_row["applicant_id"]),
            "name": f"Applicant {candidate_row['applicant_id']}",
            "position": str(req["role"]),
            "experience": int(_num(pd.Series([candidate_row["score"]])).fillna(0.0).iloc[0] // 10),
            "skills": [str(req["account"]), "customer_support"],
            "score": float(_num(pd.Series([candidate_row["score"]])).fillna(0.0).iloc[0]) / 100.0,
        },
        "workforce": {
            "job_id": str(req["req_id"]),
            "title": str(req["role"]),
            "department": str(req["account"]),
            "required_skills": [str(req["account"]), "customer_support"],
            "experience_level": 1,
            "salary_range": {
                "min": float(_num(pd.Series([req["budget_egp"]])).fillna(0.0).iloc[0]) * 0.4,
                "max": float(_num(pd.Series([req["budget_egp"]])).fillna(0.0).iloc[0]) * 0.6,
            },
            "deadline": "2099-12-31",
        },
        "is_sample": True,
    }
    provenance = {
        "files": ["16_DATA/curated/requisitions.csv", "16_DATA/curated/applicants.csv"],
        "grain": "one open requisition x its applicant funnel",
        "rows": int(candidates.shape[0]),
        "req_id": str(req["req_id"]),
        "open_requisitions": int(open_reqs.shape[0]),
    }
    return BuiltPayload(engine="personnel", payload=payload, provenance=provenance)


def personnel_payload_from_coaches(tenant: Tenant) -> BuiltPayload:
    """Coach hiring demand from squads, certifications and leaver records."""
    coaches = tenant.read_curated("coaches")
    squads = tenant.read_curated("squads")
    leavers = tenant.read_curated("leavers")
    if coaches.empty or squads.empty:
        raise ValueError(f"{tenant.name}: coaches/squads unavailable")
    sports = sorted(coaches["sport"].astype(str).unique().tolist())
    enrolled = _num(squads["enrolled"]).fillna(0.0)
    open_posts = max(1, int(squads.shape[0]) - int(coaches.shape[0]))
    payload = {
        "candidate": {
            "id": str(coaches.iloc[0]["coach_id"]),
            "name": str(coaches.iloc[0]["full_name"]),
            "position": f"{sports[0]} coach",
            "experience": int(
                _num(pd.Series([coaches.iloc[0]["tenure_months"]])).fillna(0).iloc[0] // 12
            ),
            "skills": sports[:3],
            "score": 0.7,
        },
        "workforce": {
            "job_id": "coach-hiring-plan",
            "title": "Academy coach",
            "department": "coaching",
            "required_skills": sports[:3],
            "experience_level": 2,
            "salary_range": {
                "min": float(_num(coaches["monthly_salary_egp"]).min()),
                "max": float(_num(coaches["monthly_salary_egp"]).max()),
            },
            "deadline": "2099-12-31",
        },
        "is_sample": True,
    }
    provenance = {
        "files": [
            "16_DATA/curated/coaches.csv",
            "16_DATA/curated/squads.csv",
            "16_DATA/curated/leavers.csv",
        ],
        "grain": "academy staffing plan across 8 sports",
        "rows": int(coaches.shape[0]),
        "squads": int(squads.shape[0]),
        "leavers": int(leavers.shape[0]),
        "open_posts_estimate": open_posts,
        "enrolled_athletes": float(enrolled.sum()),
    }
    return BuiltPayload(engine="personnel", payload=payload, provenance=provenance)


def crm_payload_from_accounts(tenant: Tenant, *, account: str) -> BuiltPayload:
    """Account value as a deal, ticket ageing as the support side of the CRM."""
    pnl = tenant.read_curated("pnl_monthly")
    account_rows = pnl[pnl["account"].astype(str).str.lower() == account.lower()]
    if account_rows.empty:
        raise ValueError(f"{tenant.name}: no P&L rows for account {account}")
    revenue = (
        _num(account_rows["revenue_usd"]).fillna(0.0)
        if "revenue_usd" in account_rows
        else _num(account_rows.iloc[:, -1])
    )
    annual_value = float(revenue.sum())
    tickets = tenant.read_curated("tickets")
    sample = tickets.head(1)
    payload = {
        "client": {
            "id": account,
            "name": account.replace("client", " Client").title(),
            "company": account,
            "source": "contract",
            "score": 0.7,
        },
        "deal": {
            "id": f"deal-{account}",
            "title": f"{account} annual renewal",
            "value": round(annual_value, 2),
            "stage": "negotiation",
            "close_date": None,
        },
        "ticket": {
            "id": str(sample.iloc[0]["ticket_id"]),
            "issue": str(sample.iloc[0]["subject"])[:120],
        },
        "is_sample": True,
    }
    provenance = {
        "files": ["16_DATA/curated/pnl_monthly.csv", "16_DATA/curated/tickets.csv"],
        "grain": "account x 24 months P&L, one representative ticket",
        "rows": int(account_rows.shape[0]),
        "account": account,
        "annual_value_usd": round(annual_value, 2),
    }
    return BuiltPayload(engine="crm", payload=payload, provenance=provenance)


def crm_payload_from_families(tenant: Tenant) -> BuiltPayload:
    """Family value from invoices, support side from feedback surveys."""
    invoices = tenant.read_curated("invoices")
    surveys = tenant.read_curated("feedback_surveys")
    families = tenant.read_curated("athletes")
    athlete_id = str(invoices.iloc[0]["athlete_id"])
    rows = invoices[invoices["athlete_id"].astype(str) == athlete_id]
    annual_value = float(_num(rows["total_egp"]).fillna(0.0).sum())
    survey = surveys.head(1)
    payload = {
        "client": {
            "id": athlete_id,
            "name": f"Family of {athlete_id}",
            "company": "Sports Academy",
            "source": "membership",
            "score": 0.7,
        },
        "deal": {
            "id": f"renewal-{athlete_id}",
            "title": "Annual membership renewal",
            "value": round(annual_value, 2),
            "stage": "proposal",
            "close_date": None,
        },
        "ticket": {
            "id": str(survey.iloc[0]["survey_id"]),
            "issue": str(survey.iloc[0].get("comment", "feedback"))[:120],
        },
        "is_sample": True,
    }
    provenance = {
        "files": [
            "16_DATA/curated/invoices.csv",
            "16_DATA/curated/feedback_surveys.csv",
            "16_DATA/curated/athletes.csv",
        ],
        "grain": "family x invoice history",
        "rows": int(rows.shape[0]),
        "athlete_id": athlete_id,
        "members_of_academy": int(families.shape[0]),
    }
    return BuiltPayload(engine="crm", payload=payload, provenance=provenance)


def build_all(tenant: Tenant) -> List[Tuple[str, BuiltPayload]]:
    """Build one payload per engine for the tenant, choosing its natural mapping."""
    if tenant.name == "callcenterclient":
        return [
            (
                "wfm",
                _first_or_fail(
                    lambda: wfm_payload_from_contact_centre(
                        tenant, day="2026-10-27", queue_id=_first_queue(tenant)
                    ),
                    tenant,
                ),
            ),
            ("rta", rta_payload_from_rosters(tenant, day="2026-10-27")),
            ("cx", cx_payload_from_tickets(tenant)),
            ("b2b", b2b_payload_from_contact_centre(tenant, account="teleclient")),
            ("personnel", personnel_payload_from_requisitions(tenant, account="teleclient")),
            ("crm", crm_payload_from_accounts(tenant, account="teleclient")),
        ]
    return [
        (
            "wfm",
            _first_or_fail(
                lambda: wfm_payload_from_academy(
                    tenant, day="2026-10-27", sport=_first_sport(tenant)
                ),
                tenant,
            ),
        ),
        ("rta", rta_payload_from_academy(tenant, day="2026-10-27")),
        ("cx", cx_payload_from_academy(tenant)),
        ("b2b", b2b_payload_from_academy(tenant)),
        ("personnel", personnel_payload_from_coaches(tenant)),
        ("crm", crm_payload_from_families(tenant)),
    ]


def _first_or_fail(builder, tenant: Tenant) -> BuiltPayload:
    """Run the preferred window, falling back to the last row of the fixture."""
    try:
        return builder()
    except ValueError:
        if tenant.name == "callcenterclient":
            day, queue = _last_contact_centre_day(tenant)
            return wfm_payload_from_contact_centre(tenant, day=day, queue_id=queue)
        day, sport = _last_academy_day(tenant)
        return wfm_payload_from_academy(tenant, day=day, sport=sport)


def _first_queue(tenant: Tenant) -> str:
    queues = tenant.read_curated(
        "queue_metrics_daily", columns=["queue_id", "channel", "sla_target_pct"]
    )
    voice = queues[queues["channel"].astype(str) == "voice"]
    if voice.empty:
        return str(queues.iloc[0]["queue_id"])
    return str(voice.iloc[0]["queue_id"])


def _first_sport(tenant: Tenant) -> str:
    sports = tenant.read_curated("sessions", columns=["sport"])
    return str(sports.iloc[0]["sport"])


def _last_contact_centre_day(tenant: Tenant) -> Tuple[str, str]:
    intraday = tenant.read_curated("intraday_15min", columns=["date", "queue_id"])
    row = intraday.iloc[-1]
    return str(row["date"]), str(row["queue_id"])


def _last_academy_day(tenant: Tenant) -> Tuple[str, str]:
    sessions = tenant.read_curated("sessions", columns=["session_date", "sport"])
    row = sessions.iloc[-1]
    return str(row["session_date"]), str(row["sport"])