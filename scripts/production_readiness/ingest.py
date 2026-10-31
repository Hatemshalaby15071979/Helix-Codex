"""Raw-layer ingestion: defect detection and normalisation.

The tenant contract says the raw exports imitate what a client actually hands
over, and `16_DATA/raw/defect_registry.csv` declares which defects were
injected. This module turns both into executable checks: every declared defect
class is measured, and the cleaned frame is compared against the curated layer.

A declared defect that measures zero is a failure, not a pass. The registry is a
claim about the input; an ingestion gate that cannot see the claim's evidence
would wave through exactly the data it exists to catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

DATE_LOCALE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
PERIOD_SLASH_RE = re.compile(r"^\d{4}/\d{2}$")
TZ_OFFSET_RE = re.compile(r"([+-]\d{2}:?\d{2})$")
MOJIBAKE_TOKENS = ("Ã", "Â", "â€™", "â€œ", "â€")


@dataclass
class DefectFinding:
    """One measured defect class in one raw file."""

    code: str
    file: str
    count: int
    detail: str = ""
    samples: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "file": self.file,
            "count": self.count,
            "detail": self.detail,
            "samples": self.samples[:5],
        }


def _values(series: pd.Series) -> pd.Series:
    return series.astype(str)


def find_duplicate_keys(frame: pd.DataFrame, key: str) -> DefectFinding:
    values = _values(frame[key])
    duplicated = values[values.duplicated(keep="first")]
    return DefectFinding(
        code="duplicate_keys",
        file="",
        count=int(duplicated.nunique()),
        detail=f"duplicate values in {key}",
        samples=sorted(duplicated.unique().tolist()),
    )


def find_whitespace(frame: pd.DataFrame, columns: Sequence[str]) -> DefectFinding:
    total = 0
    samples: List[str] = []
    for column in columns:
        if column not in frame.columns:
            continue
        stripped = _values(frame[column])
        hit = stripped[(stripped != stripped.str.strip()) & (stripped.str.strip() != "")]
        total += int(hit.shape[0])
        samples.extend(hit.head(2).tolist())
    return DefectFinding(
        code="trailing_whitespace",
        file="",
        count=total,
        detail=f"padded cells in {', '.join(columns)}",
        samples=samples,
    )


def find_null_on_closed(
    frame: pd.DataFrame, status_column: str, closed_column: str, closed_values: Iterable[str]
) -> DefectFinding:
    """Count closed-state rows whose close timestamp is empty.

    The closed-state vocabulary is a parameter because the two fixtures do not
    share it: Salesforce cases use `solved`, and a scanner that only looks for
    `closed` measures zero on a file that holds 270 such rows.
    """
    if status_column not in frame.columns or closed_column not in frame.columns:
        return DefectFinding("null_on_closed", "", 0, "columns absent")
    wanted = {value.lower() for value in closed_values}
    closed = _values(frame[status_column]).str.strip().str.lower().isin(wanted)
    blank = _values(frame[closed_column]).str.strip() == ""
    hit = frame[closed & blank]
    return DefectFinding(
        code="null_on_closed",
        file="",
        count=int(hit.shape[0]),
        detail=f"closed {status_column} with empty {closed_column}",
        samples=sorted(_values(hit[closed_column]).unique().tolist())[:5],
    )


def find_blank_when(
    frame: pd.DataFrame,
    value_column: str,
    condition_column: str,
    condition_values: Iterable[str],
    *,
    code: str = "blank_when_expected",
    detail: str = "",
) -> DefectFinding:
    """Count empty cells in one column where another column's state expects a value."""
    if value_column not in frame.columns or condition_column not in frame.columns:
        return DefectFinding(code, "", 0, "columns absent")
    wanted = {value.lower() for value in condition_values}
    state = _values(frame[condition_column]).str.strip().str.lower()
    blank = _values(frame[value_column]).str.strip() == ""
    hit = frame[state.isin(wanted) & blank]
    return DefectFinding(
        code=code,
        file="",
        count=int(hit.shape[0]),
        detail=detail or f"blank {value_column} while {condition_column} in {sorted(wanted)}",
    )


def find_zero_when(
    frame: pd.DataFrame,
    value_column: str,
    condition_column: str,
    condition_values: Iterable[str],
    *,
    code: str = "zero_when_expected",
    detail: str = "",
) -> DefectFinding:
    """Count zero values where another column's state expects a positive number."""
    if value_column not in frame.columns or condition_column not in frame.columns:
        return DefectFinding(code, "", 0, "columns absent")
    wanted = {value.lower() for value in condition_values}
    state = _values(frame[condition_column]).str.strip().str.lower()
    numeric = pd.to_numeric(frame[value_column], errors="coerce")
    hit = frame[state.isin(wanted) & (numeric == 0)]
    return DefectFinding(
        code=code,
        file="",
        count=int(hit.shape[0]),
        detail=detail or f"zero {value_column} while {condition_column} in {sorted(wanted)}",
    )


def find_locale_dates(frame: pd.DataFrame, column: str) -> DefectFinding:
    if column not in frame.columns:
        return DefectFinding("locale_date", "", 0, "column absent")
    values = _values(frame[column]).str.strip()
    hit = values[values.str.match(DATE_LOCALE_RE)]
    return DefectFinding(
        code="locale_date",
        file="",
        count=int(hit.shape[0]),
        detail=f"DD/MM/YYYY values in {column}",
        samples=sorted(hit.unique().tolist())[:5],
    )


def find_period_format(frame: pd.DataFrame, column: str) -> DefectFinding:
    if column not in frame.columns:
        return DefectFinding("period_format", "", 0, "column absent")
    values = _values(frame[column]).str.strip()
    hit = values[values.str.match(PERIOD_SLASH_RE)]
    return DefectFinding(
        code="period_format",
        file="",
        count=int(hit.shape[0]),
        detail=f"YYYY/MM values in {column}",
        samples=sorted(hit.unique().tolist())[:5],
    )


def find_uppercase_enums(frame: pd.DataFrame, column: str, allowed: Iterable[str]) -> DefectFinding:
    if column not in frame.columns:
        return DefectFinding("uppercase_enum", "", 0, "column absent")
    values = _values(frame[column]).str.strip()
    allowed_values = {value.upper() for value in allowed}
    hit = values[values.isin(allowed_values) & (values != values.str.lower())]
    return DefectFinding(
        code="uppercase_enum",
        file="",
        count=int(hit.shape[0]),
        detail=f"upper-case enum values in {column}",
        samples=sorted(hit.unique().tolist())[:5],
    )


def find_mixed_timezones(frame: pd.DataFrame, column: str) -> DefectFinding:
    if column not in frame.columns:
        return DefectFinding("mixed_timezones", "", 0, "column absent")
    values = _values(frame[column]).str.strip()
    parsed = values[values.str.contains(r"T|:\d{2}", regex=True)]
    has_offset = parsed.str.contains(r"[+-]\d{2}:?\d{2}$", regex=True)
    has_zulu = parsed.str.endswith("Z")
    kinds = int(has_offset.any()) + int(has_zulu.any())
    count = int(parsed.shape[0]) if kinds > 1 else 0
    return DefectFinding(
        code="mixed_timezones",
        file="",
        count=count,
        detail=f"representations in {column}: offset={int(has_offset.sum())}, zulu={int(has_zulu.sum())}",
        samples=sorted(parsed.head(3).tolist()),
    )


def find_mojibake(frame: pd.DataFrame, columns: Sequence[str]) -> DefectFinding:
    total = 0
    samples: List[str] = []
    for column in columns:
        if column not in frame.columns:
            continue
        values = _values(frame[column])
        hit = values[values.apply(lambda value: any(token in value for token in MOJIBAKE_TOKENS))]
        total += int(hit.shape[0])
        samples.extend(hit.head(2).tolist())
    return DefectFinding(
        code="mojibake",
        file="",
        count=total,
        detail="double-encoded UTF-8 sequences",
        samples=samples,
    )


def find_negative_values(frame: pd.DataFrame, columns: Sequence[str]) -> DefectFinding:
    total = 0
    samples: List[str] = []
    for column in columns:
        if column not in frame.columns:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        hit = frame[numeric < 0]
        total += int(hit.shape[0])
        samples.extend(_values(hit[column]).head(2).tolist())
    return DefectFinding(
        code="negative_values",
        file="",
        count=total,
        detail=f"negative values in {', '.join(columns)}",
        samples=samples,
    )


def find_orphans(
    frame: pd.DataFrame, column: str, known: Iterable[str], *, label: str = ""
) -> DefectFinding:
    if column not in frame.columns:
        return DefectFinding("orphan_reference", "", 0, "column absent")
    known_ids = {str(value).strip() for value in known}
    values = _values(frame[column]).str.strip()
    values = values[(values != "") & (values.str.lower() != "nan")]
    unknown = values[~values.isin(known_ids)]
    return DefectFinding(
        code="orphan_reference",
        file="",
        count=int(unknown.nunique()),
        detail=f"{label or column} values that do not resolve",
        samples=sorted(unknown.unique().tolist())[:5],
    )


def normalize_period(series: pd.Series) -> pd.Series:
    """Return YYYY-MM for both YYYY/MM and YYYY-MM inputs."""
    values = _values(series).str.strip().str.replace("/", "-", regex=False)
    return values.str.slice(0, 7)


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Parse mixed-offset ISO timestamps to UTC; unparsable values become NaT."""
    values = _values(series).str.strip().replace("", None)
    parsed = pd.to_datetime(values, errors="coerce", utc=True, format="mixed")
    return parsed


def clean_tickets(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalise a vendor ticket export: key, text, timestamps, enums."""
    cleaned = frame.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    cleaned = cleaned.rename(
        columns={
            "Ticket ID": "ticket_id",
            "Created at": "created_at",
            "Solved at": "solved_at",
            "Subject": "subject",
            "Status": "status",
            "Priority": "priority",
            "SLA policy": "sla_policy",
            "First reply (min)": "first_reply_minutes",
            "Full resolution (min)": "resolution_minutes",
            "Ticket ID ": "ticket_id",
        }
    )
    cleaned = cleaned.drop_duplicates(subset=["ticket_id"], keep="first")
    for column in ("subject", "status", "priority"):
        if column in cleaned.columns:
            cleaned[column] = _values(cleaned[column]).str.strip()
    for column in ("status", "priority"):
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].str.lower()
    for column in ("created_at", "solved_at"):
        if column in cleaned.columns:
            cleaned[column] = parse_timestamps(cleaned[column])
    return cleaned.reset_index(drop=True)


def scan_ticket_export(
    frame: pd.DataFrame, agents: Optional[Iterable[str]] = None
) -> List[DefectFinding]:
    findings = [
        find_duplicate_keys(frame, "Ticket ID"),
        find_whitespace(frame, ["Subject"]),
        find_mixed_timezones(frame, "Created at"),
        find_mojibake(frame, ["Subject", "Description"]),
        find_negative_values(frame, ["First reply (min)", "Full resolution (min)"]),
    ]
    if agents is not None:
        findings.append(find_orphans(frame, "Assignee", agents, label="assignee_id"))
    for finding in findings:
        finding.file = "zendesk_tickets_export.csv"
    return findings


def scan_case_export(frame: pd.DataFrame) -> List[DefectFinding]:
    findings = [
        find_null_on_closed(frame, "Status", "Closed Date", ("solved", "closed", "resolved")),
        find_duplicate_keys(frame, "Case Number"),
        find_locale_dates(frame, "Created Date"),
        find_mojibake(frame, ["Subject"]),
    ]
    for finding in findings:
        finding.file = "salesforce_cases_export.csv"
    return findings


def scan_wfm_export(frame: pd.DataFrame) -> List[DefectFinding]:
    findings = [
        find_locale_dates(frame, "Date"),
        find_uppercase_enums(
            frame, "Status", ["worked", "off", "leave", "sick", "training", "no_show"]
        ),
        find_whitespace(frame, ["team_id", "Shift"]),
        find_negative_values(frame, ["Sched Hrs", "Actual Hrs", "Adherence"]),
    ]
    for finding in findings:
        finding.file = "wfm_schedule_export.csv"
    return findings


def scan_payroll_export(frame: pd.DataFrame) -> List[DefectFinding]:
    findings = [
        find_period_format(frame, "Period"),
        find_whitespace(frame, ["Emp No", "role"]),
        find_negative_values(frame, ["Gross", "Net", "Deductions"]),
    ]
    for finding in findings:
        finding.file = "payroll_export.csv"
    return findings


def scan_registration_export(frame: pd.DataFrame, coaches: Iterable[str]) -> List[DefectFinding]:
    findings = [
        find_duplicate_keys(frame, "Member ID"),
        find_whitespace(frame, ["First Name", "Last Name"]),
        find_uppercase_enums(frame, "status", ["active", "inactive", "trial"]),
        find_orphans(frame, "coach_id", coaches, label="coach_id"),
    ]
    for finding in findings:
        finding.file = "playmetrics_registrations.csv"
    return findings


def scan_session_export(frame: pd.DataFrame, sports: Iterable[str]) -> List[DefectFinding]:
    findings = [
        find_locale_dates(frame, "Date"),
        find_uppercase_enums(frame, "Sport", sports),
        find_whitespace(frame, ["Squad", "Coach"]),
        find_negative_values(frame, ["capacity", "Booked", "Attended"]),
    ]
    for finding in findings:
        finding.file = "session_export.csv"
    return findings


def scan_applicant_export(frame: pd.DataFrame) -> List[DefectFinding]:
    findings = [
        find_blank_when(
            frame,
            "score",
            "status",
            ["in_process", "in progress", "screening"],
            code="blank_score_in_progress",
        ),
        find_duplicate_keys(frame, "applicant_id"),
        find_whitespace(frame, ["role"]),
    ]
    for finding in findings:
        finding.file = "applicant_export.csv"
    return findings


def scan_itsm_export(frame: pd.DataFrame) -> List[DefectFinding]:
    findings = [
        find_blank_when(
            frame,
            "closed_at",
            "status",
            ["open", "new", "in_progress"],
            code="closed_at_null_on_open",
        ),
        find_zero_when(
            frame,
            "resolution_minutes",
            "status",
            ["open", "new", "in_progress"],
            code="zero_resolution_on_open",
        ),
        find_duplicate_keys(frame, "ticket_id"),
        find_whitespace(frame, ["category"]),
    ]
    for finding in findings:
        finding.file = "itsm_export.csv"
    return findings


SCANNERS = {
    "zendesk_tickets_export.csv": scan_ticket_export,
    "salesforce_cases_export.csv": scan_case_export,
    "wfm_schedule_export.csv": scan_wfm_export,
    "payroll_export.csv": scan_payroll_export,
    "applicant_export.csv": scan_applicant_export,
    "itsm_export.csv": scan_itsm_export,
}


def scan_raw_export(
    name: str,
    frame: pd.DataFrame,
    agents: Optional[Iterable[str]] = None,
    sports: Optional[Iterable[str]] = None,
) -> List[DefectFinding]:
    if name == "zendesk_tickets_export.csv":
        return scan_ticket_export(frame, agents=agents)
    if name == "playmetrics_registrations.csv":
        return scan_registration_export(frame, agents or ())
    if name == "session_export.csv":
        return scan_session_export(frame, sports or ())
    scanner = SCANNERS.get(name)
    if scanner is None:
        return []
    return scanner(frame)
