from __future__ import annotations

import pathlib

from release.profiles import policy_for
from scripts.validate_ops_charter import validate

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_ops_charter_is_machine_valid_and_has_no_real_responder():
    assert validate() == []
    policy = policy_for("simulated_production")
    assert policy["human_approval_required"] is False
    charter = (ROOT / "ops" / "ops-charter.yaml").read_text(encoding="utf-8")
    assert "assigned_person: null" in charter
    assert "real_person_paged: false" in charter


def test_privacy_boundary_document_disclaims_legal_review():
    disclosure = (ROOT / "SIMULATION_DISCLOSURE.md").read_text(encoding="utf-8")
    privacy = (ROOT / "docs" / "legal" / "privacy-review-simulated.md").read_text(encoding="utf-8")
    assert "SIMULATION ONLY" in disclosure
    assert "not a legal review or legal advice" in privacy
    assert "No person has signed or approved" in privacy
