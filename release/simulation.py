"""Machine-verifiable, explicitly simulated release-gate receipts.

The local simulation authority uses ML-DSA-65 via OpenSSL 3.5 or later. Its
private key exists only in a temporary directory while a pack is signed; the
pack retains the public key, detached manifest signature, and one signed
tamper-evident receipt for each substituted gate. This is simulation evidence,
not human approval, independent certification, or legal advice.
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

SIMULATION_GATE_NAMES = (
    "signed_production_evidence",
    "certified_data_isolation",
    "external_observer_audit",
    "production_deployment_architecture",
    "disaster_recovery_evidence",
    "operational_ownership",
    "incident_oncall_ownership",
    "security_review",
    "legal_privacy_review",
)

PROFILE_BUNDLE_FILES = (
    "release/release-profiles.yaml",
    "release/profiles.py",
    "release/gate.py",
    "release/simulation.py",
    "release/manifest.py",
    "release/manifest.schema.json",
    "scripts/create_simulation_signoff.py",
    "scripts/verify_simulation_signoff.py",
    "scripts/release_gate.py",
    "scripts/validate_ops_charter.py",
    "ops/ops-charter.yaml",
    "docs/legal/privacy-review-simulated.md",
    "SIMULATION_DISCLOSURE.md",
)
SIMULATION_PACK_ENV = "HELIX_SIMULATION_EVIDENCE_DIR"
SIGNATURE_ALGORITHM = "ML-DSA-65"
_GENESIS_HASH = "0" * 64


class SimulationEvidenceError(RuntimeError):
    """A simulation pack cannot be created or verified safely."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def profile_bundle_sha256(repo_root: pathlib.Path) -> str:
    """Hash the exact profile source and the code that interprets it."""
    digest = hashlib.sha256()
    root = repo_root.resolve()
    for relative in PROFILE_BUNDLE_FILES:
        path = root / relative
        if not path.is_file():
            raise SimulationEvidenceError(f"profile bundle file is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _openssl_path() -> str:
    path = shutil.which("openssl")
    if path is None:
        raise SimulationEvidenceError("OpenSSL with ML-DSA-65 support is required")
    return path


def _run_openssl(args: list[str], *, timeout: float = 30) -> subprocess.CompletedProcess[bytes]:
    try:
        # The executable and argument names are controlled by this module.
        return subprocess.run(
            [_openssl_path(), *args],
            check=False,
            capture_output=True,
            timeout=timeout,
        )  # noqa: S603
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SimulationEvidenceError(f"OpenSSL operation failed: {exc}") from exc


def _require_mldsa_support() -> None:
    result = _run_openssl(["list", "-signature-algorithms"])
    if result.returncode != 0 or b"ML-DSA-65" not in result.stdout:
        raise SimulationEvidenceError("OpenSSL does not provide ML-DSA-65")


def _write_private_key(directory: pathlib.Path) -> pathlib.Path:
    private_key = directory / "simulation-authority-private.pem"
    result = _run_openssl(["genpkey", "-algorithm", SIGNATURE_ALGORITHM, "-out", str(private_key)])
    if result.returncode != 0:
        raise SimulationEvidenceError(
            "ML-DSA-65 key generation failed: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    os.chmod(private_key, 0o600)
    return private_key


def _public_key(private_key: pathlib.Path, output: pathlib.Path) -> bytes:
    result = _run_openssl(["pkey", "-in", str(private_key), "-pubout", "-out", str(output)])
    if result.returncode != 0:
        raise SimulationEvidenceError(
            "ML-DSA-65 public-key export failed: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return output.read_bytes()


def _sign(private_key: pathlib.Path, message: bytes, directory: pathlib.Path, name: str) -> bytes:
    input_path = directory / f"{name}.input"
    signature_path = directory / f"{name}.signature"
    input_path.write_bytes(message)
    result = _run_openssl(
        [
            "pkeyutl",
            "-sign",
            "-inkey",
            str(private_key),
            "-rawin",
            "-in",
            str(input_path),
            "-out",
            str(signature_path),
        ]
    )
    if result.returncode != 0:
        raise SimulationEvidenceError(
            "ML-DSA-65 signing failed: " + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return signature_path.read_bytes()


def _verify_signature(
    public_key: bytes,
    message: bytes,
    signature: bytes,
    directory: pathlib.Path,
    name: str,
) -> bool:
    key_path = directory / f"{name}.public.pem"
    input_path = directory / f"{name}.input"
    signature_path = directory / f"{name}.signature"
    key_path.write_bytes(public_key)
    input_path.write_bytes(message)
    signature_path.write_bytes(signature)
    result = _run_openssl(
        [
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            str(key_path),
            "-rawin",
            "-in",
            str(input_path),
            "-sigfile",
            str(signature_path),
        ]
    )
    return result.returncode == 0


def _evidence_is_machine_generated(
    evidence: Mapping[str, Any],
    repo_root: pathlib.Path,
) -> bool:
    checks = evidence.get("checks")
    root = repo_root.resolve()

    def valid_check(check: Any) -> bool:
        if not isinstance(check, dict):
            return False
        source = check.get("source")
        command = check.get("command")
        output = check.get("output")
        if (
            not str(check.get("name", "")).strip()
            or check.get("ok") is not True
            or not isinstance(check.get("exit_code"), int)
            or isinstance(check.get("exit_code"), bool)
            or check["exit_code"] != 0
            or not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) and part for part in command)
            or not isinstance(output, str)
            or check.get("output_sha256") != _sha256(output.encode("utf-8"))
            or not isinstance(source, str)
            or not source.strip()
        ):
            return False
        source_path = (root / source).resolve()
        try:
            source_path.relative_to(root)
        except ValueError:
            return False
        return source_path.is_file() and check.get("source_sha256") == _sha256(
            source_path.read_bytes()
        )

    return (
        evidence.get("ok") is True
        and evidence.get("simulation") is True
        and isinstance(evidence.get("disclosure"), str)
        and "simulat" in evidence["disclosure"].casefold()
        and isinstance(checks, list)
        and bool(checks)
        and all(valid_check(check) for check in checks)
    )


def create_simulation_signoff(
    repo_root: pathlib.Path,
    pack_dir: pathlib.Path,
    gate_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Write a signed bundle and receipt chain after all nine gates are green."""
    _require_mldsa_support()
    expected = set(SIMULATION_GATE_NAMES)
    if set(gate_evidence) != expected:
        missing = sorted(expected - set(gate_evidence))
        extra = sorted(set(gate_evidence) - expected)
        raise SimulationEvidenceError(f"gate set mismatch; missing={missing}, extra={extra}")
    invalid = [
        name
        for name, result in gate_evidence.items()
        if not isinstance(result, Mapping) or not _evidence_is_machine_generated(result, repo_root)
    ]
    if invalid:
        raise SimulationEvidenceError(
            f"gates lack passing, disclosed machine evidence: {', '.join(sorted(invalid))}"
        )

    pack_dir = pack_dir.resolve()
    if pack_dir.exists():
        raise FileExistsError(f"simulation evidence directory already exists: {pack_dir}")
    pack_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = pathlib.Path(
        tempfile.mkdtemp(prefix=f".{pack_dir.name}.staging-", dir=pack_dir.parent)
    )
    evidence_dir = staging_dir / "gate-evidence"
    evidence_dir.mkdir()
    bundle_digest = profile_bundle_sha256(repo_root)
    receipt_lines: list[bytes] = []
    gate_manifest: dict[str, dict[str, Any]] = {}
    previous_hash = _GENESIS_HASH

    try:
        with tempfile.TemporaryDirectory(prefix="helix-simulation-authority-") as temp_name:
            signing_dir = pathlib.Path(temp_name)
            private_key = _write_private_key(signing_dir)
            public_key = _public_key(private_key, signing_dir / "simulation-authority-public.pem")
            fingerprint = _sha256(public_key)

            for sequence, gate in enumerate(SIMULATION_GATE_NAMES, start=1):
                evidence_path = evidence_dir / f"{gate}.json"
                evidence_bytes = _canonical_json(dict(gate_evidence[gate])) + b"\n"
                evidence_path.write_bytes(evidence_bytes)
                evidence_digest = _sha256(evidence_bytes)
                core = {
                    "sequence": sequence,
                    "previous_receipt_hash": previous_hash,
                    "gate": gate,
                    "profile_bundle_sha256": bundle_digest,
                    "evidence_sha256": evidence_digest,
                    "simulation": True,
                }
                receipt_hash = _sha256(_canonical_json(core))
                signed_receipt = {**core, "receipt_sha256": receipt_hash}
                signature = _sign(private_key, _canonical_json(signed_receipt), signing_dir, gate)
                receipt = {
                    **signed_receipt,
                    "signature_b64": base64.b64encode(signature).decode("ascii"),
                }
                receipt_lines.append(_canonical_json(receipt) + b"\n")
                gate_manifest[gate] = {
                    "ok": True,
                    "sequence": sequence,
                    "receipt_sha256": receipt_hash,
                    "evidence_sha256": evidence_digest,
                }
                previous_hash = receipt_hash

            audit_bytes = b"".join(receipt_lines)
            (staging_dir / "audit_receipts.jsonl").write_bytes(audit_bytes)
            (staging_dir / "simulation-authority-public.pem").write_bytes(public_key)
            manifest = {
                "schema_version": 1,
                "profile": "simulated_production",
                "simulation": True,
                "signature_algorithm": SIGNATURE_ALGORITHM,
                "authority_fingerprint_sha256": fingerprint,
                "profile_bundle_sha256": bundle_digest,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "gate_names": list(SIMULATION_GATE_NAMES),
                "gates": gate_manifest,
                "audit_receipts_sha256": _sha256(audit_bytes),
                "disclosure": (
                    "SIMULATION ONLY: machine-generated evidence on synthetic fixtures; "
                    "not human approval, independent certification, or legal advice."
                ),
            }
            manifest_bytes = _canonical_json(manifest)
            signature = _sign(private_key, manifest_bytes, signing_dir, "manifest")
            (staging_dir / "simulation-manifest.json").write_bytes(manifest_bytes + b"\n")
            (staging_dir / "simulation-manifest.sig").write_text(
                base64.b64encode(signature).decode("ascii") + "\n",
                encoding="ascii",
            )
        os.replace(staging_dir, pack_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return manifest


def simulation_evidence_dir() -> pathlib.Path | None:
    value = os.environ.get(SIMULATION_PACK_ENV, "").strip()
    return pathlib.Path(value) if value else None


def verify_simulation_signoff(
    pack_dir: pathlib.Path | None,
    repo_root: pathlib.Path,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Offline verification of profile hash, manifest signature, receipts, and chain."""
    if pack_dir is None:
        return False, f"{SIMULATION_PACK_ENV} is not set", None
    try:
        manifest_path = pack_dir / "simulation-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False, "simulation manifest is not a JSON object", None
        signature_text = (pack_dir / "simulation-manifest.sig").read_text(encoding="ascii").strip()
        signature = base64.b64decode(signature_text, validate=True)
        public_key = (pack_dir / "simulation-authority-public.pem").read_bytes()
        if (
            manifest.get("profile") != "simulated_production"
            or manifest.get("simulation") is not True
        ):
            return False, "manifest is not a disclosed simulated profile", None
        if manifest.get("signature_algorithm") != SIGNATURE_ALGORITHM:
            return False, "manifest signature algorithm is not ML-DSA-65", None
        if manifest.get("authority_fingerprint_sha256") != _sha256(public_key):
            return False, "simulation authority fingerprint mismatch", None
        if manifest.get("profile_bundle_sha256") != profile_bundle_sha256(repo_root):
            return False, "profile bundle hash mismatch", None
        disclosure = manifest.get("disclosure")
        if not isinstance(disclosure, str) or not disclosure.startswith("SIMULATION ONLY:"):
            return False, "simulation disclosure is missing", None

        with tempfile.TemporaryDirectory(prefix="helix-simulation-verify-") as temp_name:
            verified = _verify_signature(
                public_key,
                _canonical_json(manifest),
                signature,
                pathlib.Path(temp_name),
                "manifest",
            )
        if not verified:
            return False, "simulation manifest signature invalid", None

        audit_path = pack_dir / "audit_receipts.jsonl"
        audit_bytes = audit_path.read_bytes()
        if manifest.get("audit_receipts_sha256") != _sha256(audit_bytes):
            return False, "audit receipt file hash mismatch", None
        raw_receipts = [json.loads(line) for line in audit_bytes.splitlines() if line.strip()]
        if not all(isinstance(item, dict) for item in raw_receipts):
            return False, "audit receipt is not a JSON object", None
        if [item.get("gate") for item in raw_receipts] != list(SIMULATION_GATE_NAMES):
            return False, "audit receipts are missing, extra, or out of order", None

        previous_hash = _GENESIS_HASH
        for sequence, receipt in enumerate(raw_receipts, start=1):
            gate = SIMULATION_GATE_NAMES[sequence - 1]
            evidence_path = pack_dir / "gate-evidence" / f"{gate}.json"
            evidence_bytes = evidence_path.read_bytes()
            evidence = json.loads(evidence_bytes)
            if not isinstance(evidence, dict):
                return False, f"{gate}: evidence is not a JSON object", None
            evidence_digest = _sha256(evidence_bytes)
            core = {
                "sequence": sequence,
                "previous_receipt_hash": previous_hash,
                "gate": gate,
                "profile_bundle_sha256": manifest["profile_bundle_sha256"],
                "evidence_sha256": evidence_digest,
                "simulation": True,
            }
            receipt_hash = _sha256(_canonical_json(core))
            signed_receipt = {**core, "receipt_sha256": receipt_hash}
            if receipt != {
                **signed_receipt,
                "signature_b64": receipt.get("signature_b64"),
            }:
                return False, f"{gate}: receipt fields or hash chain mismatch", None
            if not _evidence_is_machine_generated(evidence, repo_root):
                return False, f"{gate}: evidence is not passing disclosed machine evidence", None
            try:
                receipt_signature = base64.b64decode(receipt["signature_b64"], validate=True)
            except (KeyError, binascii.Error, ValueError):
                return False, f"{gate}: receipt signature is malformed", None
            with tempfile.TemporaryDirectory(prefix="helix-simulation-receipt-") as temp_name:
                valid_signature = _verify_signature(
                    public_key,
                    _canonical_json(signed_receipt),
                    receipt_signature,
                    pathlib.Path(temp_name),
                    gate,
                )
            if not valid_signature:
                return False, f"{gate}: receipt signature invalid", None
            declared_gates = manifest.get("gates")
            if not isinstance(declared_gates, dict):
                return False, "manifest gate references are malformed", None
            declared = declared_gates.get(gate)
            if not isinstance(declared, dict):
                return False, f"{gate}: manifest receipt reference is missing", None
            if (
                declared.get("ok") is not True
                or declared.get("sequence") != sequence
                or declared.get("receipt_sha256") != receipt_hash
                or declared.get("evidence_sha256") != evidence_digest
            ):
                return False, f"{gate}: manifest receipt reference mismatch", None
            previous_hash = receipt_hash

        if manifest.get("gate_names") != list(SIMULATION_GATE_NAMES):
            return False, "manifest gate list mismatch", None
        return (
            True,
            "all nine simulation receipts and the post-quantum audit chain verify",
            manifest,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        binascii.Error,
        SimulationEvidenceError,
    ) as exc:
        return False, f"simulation evidence verification failed: {type(exc).__name__}: {exc}", None
