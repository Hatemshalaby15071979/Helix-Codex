"""Unit tests for the production-readiness harness.

The dataset-backed run lives in `scripts/production_readiness/run.py`; these
tests pin the measurement rules the run depends on, including the two defects the
first live run exposed: a closed-state vocabulary that missed `solved`, and a
label check that must refuse a result claiming live data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.production_readiness import gates, ingest
from scripts.production_readiness.run import READY


def test_readiness_label_is_explicitly_simulation_scoped():
    assert READY == "SIMULATION_READINESS_EVIDENCED"


def _frame(rows):
    return pd.DataFrame(rows).astype(str)


def test_duplicate_keys_and_whitespace_are_measured():
    frame = _frame(
        {
            "Ticket ID": ["1", "1", "2"],
            "Subject": [" hello ", "hello", "ok"],
        }
    )
    duplicates = ingest.find_duplicate_keys(frame, "Ticket ID")
    padding = ingest.find_whitespace(frame, ["Subject"])
    assert duplicates.count == 1
    assert padding.count == 1


def test_mixed_timezones_need_two_representations():
    single = _frame({"Created at": ["2026-09-12T14:54:54Z", "2026-09-13T10:00:00Z"]})
    mixed = _frame({"Created at": ["2026-09-12T14:54:54Z", "2026-09-13T10:00:00+02:00"]})
    assert ingest.find_mixed_timezones(single, "Created at").count == 0
    assert ingest.find_mixed_timezones(mixed, "Created at").count == 2


def test_null_closed_dates_use_the_fixture_closed_vocabulary():
    """`closed` alone measured zero on 270 blank dates in `solved` cases."""
    frame = _frame(
        {
            "Status": ["solved", "solved", "open"],
            "Closed Date": ["", "2026-10-01T00:00:00Z", ""],
        }
    )
    only_literal = ingest.find_null_on_closed(frame, "Status", "Closed Date", ("closed",))
    fixture_vocabulary = ingest.find_null_on_closed(
        frame, "Status", "Closed Date", ("solved", "closed")
    )
    assert only_literal.count == 0
    assert fixture_vocabulary.count == 1


def test_clean_tickets_dedupes_and_parses_mixed_offsets():
    frame = _frame(
        {
            "Ticket ID": ["T-1", "T-1", "T-2"],
            "Subject": [" one ", "one", "two"],
            "Status": ["SOLVED", "solved", "Open"],
            "Priority": ["NORMAL", "normal", "high"],
            "Created at": [
                "2026-09-12T14:54:54Z",
                "2026-09-12T14:54:54Z",
                "2026-09-13T10:00:00+02:00",
            ],
        }
    )
    cleaned = ingest.clean_tickets(frame)
    assert len(cleaned) == 2
    assert cleaned["created_at"].notna().all()
    assert set(cleaned["status"]) == {"solved", "open"}


def test_orphan_references_are_quarantined_without_silent_loss():
    frame = _frame(
        {"Assignee": ["A-1", "A-999", "A-2", "A-999"], "Ticket ID": ["1", "2", "3", "4"]}
    )
    retained, quarantined = ingest.quarantine_unmatched_references(
        frame, "Assignee", {"A-1", "A-2"}
    )
    assert len(retained) == 2
    assert len(quarantined) == 2
    assert len(retained) + len(quarantined) == len(frame)
    assert set(quarantined["Assignee"]) == {"A-999"}


def test_vendor_reader_detects_bom_crlf_and_cp1252(tmp_path):
    bom_file = tmp_path / "bom.csv"
    bom_file.write_bytes("Name,Value\r\nsynthetic,caf\u00e9\r\n".encode("utf-8-sig"))
    frame, metadata = ingest.read_vendor_csv(bom_file)
    assert metadata == {"encoding": "utf-8-sig", "bom": True, "crlf": True}
    assert frame.loc[0, "Value"] == "caf\u00e9"

    legacy_file = tmp_path / "legacy.csv"
    legacy_file.write_bytes("Name,Value\r\nsynthetic,caf\u00e9\r\n".encode("cp1252"))
    frame, metadata = ingest.read_vendor_csv(legacy_file)
    assert metadata["encoding"] == "cp1252"
    assert frame.loc[0, "Value"] == "caf\u00e9"


def test_schema_variant_ticketid_is_normalized():
    frame = _frame({"TicketID": ["T-1", "T-2"], "Created at": ["2026-10-01T00:00:00Z"] * 2})
    cleaned = ingest.clean_tickets(frame)
    assert cleaned.ticket_id.tolist() == ["T-1", "T-2"]


def test_attendance_reconciliation_refuses_outside_coverage():
    frame = _frame({"session_date": ["2026-06-01", "2026-06-02"]})
    assert (
        len(ingest.reconcile_with_coverage(frame, "session_date", "2026-06-01", "2026-06-02")) == 2
    )
    with pytest.raises(ValueError, match="outside the declared"):
        ingest.reconcile_with_coverage(frame, "session_date", "2026-06-02", "2026-06-02")


class _StubTenant:
    def __init__(self, name="stub", *, mismatch=False, disclosure=True, tables=40):
        self.name = name
        self._mismatch = mismatch
        self._disclosure = disclosure
        self._tables = [f"t{index}" for index in range(tables)]

    def verify_manifest(self):
        from scripts.production_readiness.dataset import ManifestReport

        if self._mismatch:
            return ManifestReport(listed=10, missing=["x.csv"], mismatched=[])
        return ManifestReport(listed=10)

    def available_tables(self):
        return self._tables

    def disclosure_ok(self):
        return self._disclosure


def test_fixture_gate_fails_closed_on_a_manifest_mismatch():
    context = gates.RunContext(tenants=[_StubTenant(mismatch=True)])
    result = gates.gate_fixture_integrity(context)
    assert result.ok is False
    assert "missing" in result.detail


def test_fixture_gate_fails_closed_without_disclosure():
    context = gates.RunContext(tenants=[_StubTenant(disclosure=False)])
    result = gates.gate_fixture_integrity(context)
    assert result.ok is False
    assert "disclosure" in result.detail


def test_disclosure_gate_rejects_a_result_that_claims_live_data():
    context = gates.RunContext(tenants=[_StubTenant()])
    context.calls.append(
        gates.EngineCall(
            engine="wfm",
            tenant="stub",
            client_id="client",
            capability="wfm_forecast",
            payload_digest="a",
            result_digest="b",
            duration_ms=1,
            data_mode="real",
            is_sample=False,
            warnings=[],
            error=None,
        )
    )
    result = gates.gate_synthetic_disclosure(context)
    assert result.ok is False
    assert "data_mode" in result.detail
