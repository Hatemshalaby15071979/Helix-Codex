from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess

import pytest

from release import gate, simulation

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mldsa_available() -> bool:
    openssl = shutil.which("openssl")
    if openssl is None:
        return False
    result = subprocess.run(
        [openssl, "list", "-signature-algorithms"],
        check=False,
        capture_output=True,
        timeout=10,
    )
    return result.returncode == 0 and b"ML-DSA-65" in result.stdout


pytestmark = pytest.mark.skipif(not _mldsa_available(), reason="OpenSSL ML-DSA-65 is unavailable")


def _passing_evidence() -> dict[str, dict[str, object]]:
    source = ROOT / "tests" / "test_simulation_release_evidence.py"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    output = "1 passed"
    return {
        gate_name: {
            "ok": True,
            "simulation": True,
            "disclosure": "Synthetic-only simulation evidence.",
            "checks": [
                {
                    "name": f"{gate_name} machine verification",
                    "ok": True,
                    "command": [
                        "python",
                        "-m",
                        "pytest",
                        "tests/test_simulation_release_evidence.py",
                    ],
                    "exit_code": 0,
                    "output": output,
                    "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
                    "source": source.relative_to(ROOT).as_posix(),
                    "source_sha256": source_hash,
                }
            ],
        }
        for gate_name in simulation.SIMULATION_GATE_NAMES
    }


@pytest.fixture
def signed_pack(tmp_path: pathlib.Path) -> pathlib.Path:
    simulation._require_mldsa_support()
    pack = tmp_path / "simulation-pack"
    simulation.create_simulation_signoff(ROOT, pack, _passing_evidence())
    return pack


def test_signed_pack_has_nine_receipts_and_no_private_key(signed_pack: pathlib.Path):
    valid, detail, manifest = simulation.verify_simulation_signoff(signed_pack, ROOT)

    assert valid, detail
    assert manifest is not None
    assert manifest["signature_algorithm"] == "ML-DSA-65"
    assert manifest["simulation"] is True
    assert len(manifest["gates"]) == 9
    assert len((signed_pack / "audit_receipts.jsonl").read_text().splitlines()) == 9
    assert not list(signed_pack.rglob("*private*"))


def test_signing_rejects_missing_or_undisclosed_gate_evidence(tmp_path: pathlib.Path):
    evidence = _passing_evidence()
    evidence.pop(simulation.SIMULATION_GATE_NAMES[0])
    with pytest.raises(simulation.SimulationEvidenceError, match="gate set mismatch"):
        simulation.create_simulation_signoff(ROOT, tmp_path / "missing", evidence)

    evidence = _passing_evidence()
    evidence[simulation.SIMULATION_GATE_NAMES[0]]["disclosure"] = "unscoped evidence"
    pack = tmp_path / "invalid"
    with pytest.raises(simulation.SimulationEvidenceError, match="machine evidence"):
        simulation.create_simulation_signoff(ROOT, pack, evidence)
    assert not pack.exists()


def test_signing_rejects_source_or_output_hash_mismatch(tmp_path: pathlib.Path):
    evidence = _passing_evidence()
    first_gate = simulation.SIMULATION_GATE_NAMES[0]
    evidence[first_gate]["checks"][0]["source_sha256"] = "0" * 64

    with pytest.raises(simulation.SimulationEvidenceError, match="machine evidence"):
        simulation.create_simulation_signoff(ROOT, tmp_path / "source-mismatch", evidence)


def test_verification_fails_closed_for_wrong_bundle_hash(signed_pack: pathlib.Path, monkeypatch):
    monkeypatch.setattr(simulation, "profile_bundle_sha256", lambda _root: "0" * 64)
    valid, detail, manifest = simulation.verify_simulation_signoff(signed_pack, ROOT)

    assert not valid
    assert detail == "profile bundle hash mismatch"
    assert manifest is None


def test_verification_detects_tampered_receipt_file(signed_pack: pathlib.Path):
    receipt_file = signed_pack / "audit_receipts.jsonl"
    receipt_file.write_bytes(receipt_file.read_bytes() + b"\n")

    valid, detail, manifest = simulation.verify_simulation_signoff(signed_pack, ROOT)

    assert not valid
    assert detail == "audit receipt file hash mismatch"
    assert manifest is None


def test_verification_detects_invalid_manifest_signature(signed_pack: pathlib.Path):
    (signed_pack / "simulation-manifest.sig").write_text("aW52YWxpZA==\n", encoding="ascii")

    valid, detail, manifest = simulation.verify_simulation_signoff(signed_pack, ROOT)

    assert not valid
    assert detail == "simulation manifest signature invalid"
    assert manifest is None


def test_verification_detects_tampered_gate_evidence(signed_pack: pathlib.Path):
    evidence_file = signed_pack / "gate-evidence" / f"{simulation.SIMULATION_GATE_NAMES[0]}.json"
    evidence = json.loads(evidence_file.read_text())
    evidence["checks"][0]["ok"] = False
    evidence_file.write_text(json.dumps(evidence), encoding="utf-8")

    valid, detail, manifest = simulation.verify_simulation_signoff(signed_pack, ROOT)

    assert not valid
    assert "receipt fields or hash chain mismatch" in detail
    assert manifest is None


def test_release_gate_binds_the_nine_receipts_to_simulated_profile(
    signed_pack: pathlib.Path, monkeypatch
):
    monkeypatch.setenv(simulation.SIMULATION_PACK_ENV, str(signed_pack))
    manifest_args: dict[str, object] = {}
    for gate_name in gate.profiles.GATE_NAMES:
        monkeypatch.setitem(gate.GATE_IMPL, gate_name, lambda: (True, "test gate passed"))
    monkeypatch.setattr(
        gate.manifest_mod,
        "build_manifest",
        lambda **kwargs: manifest_args.update(kwargs) or {},
    )
    monkeypatch.setattr(
        gate.observability,
        "run_observability_report",
        lambda: {"all_ok": True},
    )
    monkeypatch.setattr(
        gate.harness_mod,
        "run_harness",
        lambda **_kwargs: {"all_ok": True, "summary": {}},
    )

    result = gate.run_gate(profile="simulated_production", write_evidence=False)

    assert result["classification"] == "SIMULATED_PRODUCTION_READY"
    assert result["all_gates_green"] is True
    assert result["permitted_c8_outcome"] is True
    assert manifest_args["release_approved"] is False
    assert "does not claim" in result["gates"]["release_approval"]["detail"]
    assert "separate verifier process" in result["gates"]["external_observer_audit"]["detail"]


def test_release_gate_fails_closed_without_a_signed_pack(monkeypatch):
    monkeypatch.delenv(simulation.SIMULATION_PACK_ENV, raising=False)
    for gate_name in gate.profiles.GATE_NAMES:
        monkeypatch.setitem(gate.GATE_IMPL, gate_name, lambda: (True, "test gate passed"))
    monkeypatch.setattr(
        gate.observability,
        "run_observability_report",
        lambda: {"all_ok": True},
    )
    monkeypatch.setattr(
        gate.harness_mod,
        "run_harness",
        lambda **_kwargs: {"all_ok": True, "summary": {}},
    )

    result = gate.run_gate(profile="simulated_production", write_evidence=False)

    assert result["classification"] == "NOT_READY"
    assert result["exit_code"] == 1
    assert all(
        not result["gates"][gate_name]["ok"] for gate_name in simulation.SIMULATION_GATE_NAMES
    )
