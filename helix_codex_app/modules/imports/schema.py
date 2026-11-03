"""Embedded curated-layer schemas for the two simulated tenant fixtures.

Scope is the eighteen tables mapped by the production-readiness harness
(`scripts/production_readiness/run.py: MAPPED_TABLES`) — the documented
consumer contract (`20_INTERFACE/consumer_contract.md`). Each schema declares
the exact column set, the primary key (uniqueness enforced per file), and the
columns that are type-checked. Everything else is accepted as free text; the
harness does the heavy semantic validation, this importer guarantees shape,
uniqueness and tenant scoping only.

The importer auto-detects which fixture a file came from by matching its
header against these schemas; a file that matches neither is refused. A file
matching the *other* tenant's schema is still refused for this tenant's
import — shape is not identity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSchema:
    table_name: str
    tenant_profile: str  # "callcenterclient" | "sportacademyclient"
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    numeric: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    booleans: tuple[str, ...] = ()


SCHEMAS: tuple[TableSchema, ...] = (
    # ── callcenterclient ────────────────────────────────────────────────
    TableSchema(
        "agents",
        "callcenterclient",
        (
            "agent_id",
            "first_name",
            "last_name",
            "full_name",
            "gender",
            "account",
            "site",
            "team_id",
            "pod_id",
            "job_role",
            "tl1_id",
            "tl2_id",
            "hire_date",
            "tenure_months",
            "employment_type",
            "shift_code",
            "rest_day_1",
            "rest_day_2",
            "language_primary",
            "language_secondary",
            "monthly_base_egp",
            "work_email",
            "asset_tag",
            "status",
            "performance_tier",
            "quality_baseline",
            "adherence_baseline",
            "csat_baseline",
            "attrition_risk_band",
        ),
        ("agent_id",),
        numeric=(
            "tenure_months",
            "monthly_base_egp",
            "quality_baseline",
            "adherence_baseline",
            "csat_baseline",
        ),
        dates=("hire_date",),
    ),
    TableSchema(
        "rosters_daily",
        "callcenterclient",
        (
            "agent_id",
            "roster_date",
            "team_id",
            "account",
            "site",
            "shift_code",
            "status",
            "scheduled_hours",
            "actual_hours",
            "adherence_pct",
            "handle_hours",
            "aux_hours",
            "conformance_pct",
            "roster_state",
        ),
        ("agent_id", "roster_date"),
        numeric=(
            "scheduled_hours",
            "actual_hours",
            "adherence_pct",
            "handle_hours",
            "aux_hours",
            "conformance_pct",
        ),
        dates=("roster_date",),
    ),
    TableSchema(
        "queue_metrics_daily",
        "callcenterclient",
        (
            "date",
            "account",
            "queue_id",
            "queue_name",
            "channel",
            "offered",
            "handled",
            "abandoned",
            "short_abandoned",
            "aht_seconds",
            "asa_seconds",
            "sla_pct",
            "sla_target_pct",
            "threshold_seconds",
            "occupancy_pct",
            "scheduled_fte",
            "required_fte",
            "forecast_offered",
            "forecast_error_pct",
            "abandon_rate_pct",
            "fcr_pct",
            "csat_pct",
            "qa_pct",
        ),
        ("queue_id", "date"),
        numeric=(
            "offered",
            "handled",
            "abandoned",
            "short_abandoned",
            "aht_seconds",
            "asa_seconds",
            "sla_pct",
            "sla_target_pct",
            "threshold_seconds",
            "occupancy_pct",
            "scheduled_fte",
            "required_fte",
            "forecast_offered",
            "forecast_error_pct",
            "abandon_rate_pct",
            "fcr_pct",
            "csat_pct",
            "qa_pct",
        ),
        dates=("date",),
    ),
    TableSchema(
        "intraday_15min",
        "callcenterclient",
        (
            "date",
            "interval_start",
            "queue_id",
            "queue_name",
            "channel",
            "offered",
            "handled",
            "abandoned",
            "aht_seconds",
            "sla_pct",
            "occupancy_pct",
            "staffed_agents",
            "adherence_pct",
        ),
        ("queue_id", "date", "interval_start"),
        numeric=(
            "offered",
            "handled",
            "abandoned",
            "aht_seconds",
            "sla_pct",
            "occupancy_pct",
            "staffed_agents",
            "adherence_pct",
        ),
        dates=("date",),
    ),
    TableSchema(
        "tickets",
        "callcenterclient",
        (
            "ticket_id",
            "created_at",
            "solved_at",
            "requester_id",
            "organization_id",
            "assignee_id",
            "group_id",
            "subject",
            "description",
            "status",
            "priority",
            "type",
            "channel",
            "tags",
            "sla_policy",
            "first_reply_minutes",
            "resolution_minutes",
            "sla_breached",
            "reopens",
            "satisfaction_score",
            "escalation_level",
            "escalated_to",
            "macro_used",
            "kb_article_id",
            "language",
            "country",
        ),
        ("ticket_id",),
        numeric=(
            "first_reply_minutes",
            "resolution_minutes",
            "reopens",
            "satisfaction_score",
            "escalation_level",
        ),
        dates=("created_at", "solved_at"),
        booleans=("sla_breached",),
    ),
    TableSchema(
        "pnl_monthly",
        "callcenterclient",
        (
            "month",
            "account",
            "revenue_usd",
            "direct_payroll_usd",
            "technology_usd",
            "facilities_usd",
            "telecom_usd",
            "recruitment_training_usd",
            "corporate_usd",
            "sales_usd",
            "depreciation_other_usd",
            "ebitda_usd",
            "margin_pct",
        ),
        ("month", "account"),
        numeric=(
            "revenue_usd",
            "direct_payroll_usd",
            "technology_usd",
            "facilities_usd",
            "telecom_usd",
            "recruitment_training_usd",
            "corporate_usd",
            "sales_usd",
            "depreciation_other_usd",
            "ebitda_usd",
            "margin_pct",
        ),
    ),
    TableSchema(
        "rate_cards",
        "callcenterclient",
        (
            "rate_card_id",
            "account",
            "channel",
            "rate_usd",
            "rate_effective_usd",
            "valid_from",
            "valid_to",
            "currency",
        ),
        ("rate_card_id",),
        numeric=("rate_usd", "rate_effective_usd"),
        dates=("valid_from", "valid_to"),
    ),
    TableSchema(
        "requisitions",
        "callcenterclient",
        (
            "req_id",
            "account",
            "role",
            "site",
            "openings",
            "opened_on",
            "closed_on",
            "status",
            "recruiter_id",
            "priority",
            "budget_egp",
        ),
        ("req_id",),
        numeric=("openings", "budget_egp"),
        dates=("opened_on", "closed_on"),
    ),
    TableSchema(
        "applicants",
        "callcenterclient",
        (
            "applicant_id",
            "req_id",
            "account",
            "source",
            "applied_on",
            "stage",
            "status",
            "outcome",
            "score",
            "hired_employee_id",
        ),
        ("applicant_id",),
        numeric=("score",),
        dates=("applied_on",),
    ),
    # ── sportacademyclient ──────────────────────────────────────────────
    TableSchema(
        "athletes",
        "sportacademyclient",
        (
            "athlete_id",
            "first_name",
            "last_name",
            "full_name",
            "gender",
            "date_of_birth",
            "age_group",
            "sport",
            "program",
            "squad_id",
            "site",
            "join_date",
            "tenure_months",
            "membership_type",
            "monthly_fee_egp",
            "guardian_name",
            "guardian_phone",
            "email",
            "status",
            "scholarship_pct",
            "medical_clearance_date",
            "emergency_contact",
            "performance_level",
            "coach_id",
        ),
        ("athlete_id",),
        numeric=("tenure_months", "monthly_fee_egp", "scholarship_pct"),
        dates=("date_of_birth", "join_date", "medical_clearance_date"),
    ),
    TableSchema(
        "coaches",
        "sportacademyclient",
        (
            "coach_id",
            "first_name",
            "last_name",
            "full_name",
            "gender",
            "sport",
            "role",
            "level",
            "site",
            "hire_date",
            "tenure_months",
            "employment_type",
            "weekly_hours",
            "monthly_salary_egp",
            "certification_status",
            "email",
            "status",
        ),
        ("coach_id",),
        numeric=("tenure_months", "weekly_hours", "monthly_salary_egp"),
        dates=("hire_date",),
    ),
    TableSchema(
        "squads",
        "sportacademyclient",
        (
            "squad_id",
            "sport",
            "program",
            "age_group",
            "site",
            "coach_id",
            "capacity",
            "enrolled",
            "level",
            "status",
        ),
        ("squad_id",),
        numeric=("capacity", "enrolled"),
    ),
    TableSchema(
        "sessions",
        "sportacademyclient",
        (
            "session_id",
            "session_date",
            "start_time",
            "end_time",
            "sport",
            "squad_id",
            "coach_id",
            "facility_id",
            "capacity",
            "booked",
            "attended",
            "status",
            "session_type",
        ),
        ("session_id",),
        numeric=("capacity", "booked", "attended"),
        dates=("session_date",),
    ),
    TableSchema(
        "attendance",
        "sportacademyclient",
        (
            "attendance_id",
            "session_id",
            "athlete_id",
            "attendance_status",
            "minutes_attended",
            "late_flag",
            "reason",
        ),
        ("attendance_id",),
        numeric=("minutes_attended",),
        booleans=("late_flag",),
    ),
    TableSchema(
        "forecast_daily",
        "sportacademyclient",
        (
            "date",
            "sport",
            "forecast_sessions",
            "actual_sessions",
            "forecast_attendance",
            "actual_attendance",
            "error_pct",
            "forecast_athletes",
        ),
        ("date", "sport"),
        numeric=(
            "forecast_sessions",
            "actual_sessions",
            "forecast_attendance",
            "actual_attendance",
            "error_pct",
            "forecast_athletes",
        ),
        dates=("date",),
    ),
    TableSchema(
        "invoices",
        "sportacademyclient",
        (
            "invoice_id",
            "month",
            "athlete_id",
            "program",
            "amount_egp",
            "discount_egp",
            "vat_egp",
            "total_egp",
            "status",
            "issued_on",
        ),
        ("invoice_id",),
        numeric=("amount_egp", "discount_egp", "vat_egp", "total_egp"),
        dates=("issued_on",),
    ),
    TableSchema(
        "feedback_surveys",
        "sportacademyclient",
        (
            "survey_id",
            "survey_date",
            "respondent_type",
            "athlete_id",
            "nps_score",
            "coaching_rating",
            "facility_rating",
            "admin_rating",
            "comment",
        ),
        ("survey_id",),
        numeric=(
            "nps_score",
            "coaching_rating",
            "facility_rating",
            "admin_rating",
        ),
        dates=("survey_date",),
    ),
    TableSchema(
        "leavers",
        "sportacademyclient",
        (
            "leaver_id",
            "employee_id",
            "role",
            "site",
            "hire_date",
            "last_day",
            "tenure_months",
            "reason",
            "regretted",
            "replacement_req_id",
        ),
        ("leaver_id",),
        numeric=("tenure_months",),
        dates=("hire_date", "last_day"),
        booleans=("regretted",),
    ),
)

MAX_BYTES = 25 * 1024 * 1024
MAX_ROWS = 100_000

_SCHEMAS_BY_HEADER = {frozenset(s.columns): s for s in SCHEMAS}


def detect(header: list[str]) -> TableSchema | None:
    """Return the schema whose exact column set matches, else None."""
    return _SCHEMAS_BY_HEADER.get(frozenset(header))


def nearest_miss(header: list[str]) -> str:
    """Describe the closest schema mismatch for the error message."""
    offered = set(header)
    best: tuple[int, TableSchema] | None = None
    for schema in SCHEMAS:
        missing = len(set(schema.columns) - offered)
        extra = len(offered - set(schema.columns))
        score = missing + extra
        if best is None or score < best[0]:
            best = (score, schema)
    if best is None:
        raise RuntimeError("no CSV import schemas are registered")
    score, schema = best
    missing = sorted(set(schema.columns) - offered)
    extra = sorted(offered - set(schema.columns))
    parts = []
    if missing:
        parts.append(f"missing {missing[:5]}")
    if extra:
        parts.append(f"unexpected {extra[:5]}")
    return f"closest match is {schema.tenant_profile}/{schema.table_name} ({'; '.join(parts) or 'reordered'})"
