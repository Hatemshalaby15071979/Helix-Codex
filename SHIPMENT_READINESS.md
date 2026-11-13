# Helix Prime GitHub shipment readiness

**Assessment date:** 2026-11-06 (re-verified; prior assessment 2026-11-05)
**Local branch:** `release/simulated-production-2026-11`
**Base HEAD before this audit's commits:** `803f893` (see `git log` for the
shipment and evidence commit SHAs)
**GitHub destination:** <https://github.com/Hatemshalaby15071979/Helix-Codex>
**Remote configured in this checkout:** none (documented state in AGENTS.md;
the owner must add the remote and push — this audit never pushed)

Local-only repository shipment assessment. No push, tag, GitHub release, or
deployment was made. Production remains `NOT_READY` by design (nine
external-only gates: signed production evidence, certified data isolation,
external observer audit, production deployment architecture, disaster
recovery evidence, operational ownership, incident on-call ownership,
security review, legal/privacy review). A simulated classification never
authorizes production deployment.

## Initial state (2026-11-06)

- Checkout `cloned_repos/Helix-Prime`, branch
  `release/simulated-production-2026-11`, HEAD `803f893`, **no git remote**.
- 22 uncommitted entries from prior shipment work (18 modified files,
  untracked `SHIPMENT_READINESS.md`, `release/requirements-api.in`,
  `release/requirements-api.lock.txt`, `scripts/compile_api_lock.sh`),
  reviewed file-by-file and preserved.
- Prior report recorded an interrupted Docker-builder test run
  (1,911 passed / 9 failed) and an unrun Trivy scan.

## Findings and fixes

1. **The 9 prior test failures are environment artifacts, not regressions
   (verified).** The Docker builder lacks `git` (2 preflight tests shell out
   to it) and the host Python lacks the locked optional deps
   (`matplotlib`, `scikit-learn` → smoke `engines 4/6`). In a clean venv
   installed from `release/requirements.lock.txt` +
   `requirements-dev.txt`, all 122 tests in the six affected files pass, the
   C0 smoke passes (`engines 6/6, agents 4/4`), and the **full suite passes:
   2,107 passed in 381.94s** (2026-11-06, plain `pytest -q` in the locked
   venv; the CI variant adds `-m "not smoke"` plus coverage gates, see
   below).
2. **`ruff format --check` failed on the prior edits (fixed).**
   `scripts/check_dependencies.py` (new API-lock validation) was reformatted
   with `ruff format`; the full-repo format check now passes (474 files).
3. **Image vulnerability scan now actually run (fixed the underlying
   failure).** Trivy (v0.58.0, HIGH/CRITICAL, `--ignore-unfixed`) on the
   pre-fix image found **54 fixable OS-package vulnerabilities** in the
   Debian 12.11 base — the configured CI scan (`exit-code: '1'`) would have
   failed. Added `apt-get upgrade` to the runtime stage of
   `infra/docker/Dockerfile`, rebuilt (`helix-prime-api:prod-sim`,
   203,341,221 bytes, ~194 MiB), and rescanned: **0 HIGH/CRITICAL**
   (OS and Python). New image smoke-tested read-only as UID 10001:
   `/healthz` 200. Full JSON report retained outside the repo during the
   audit; CI uploads its own report as an artifact.
4. **CI hardening (prior edits, reviewed and kept).** All-branch triggers,
   `permissions: contents: read`, hash-verified API lock install, CycloneDX
   SBOMs, SHA-pinned Trivy action, ephemeral synthetic secrets with cleanup,
   loopback-only simulated stack verification, and a readiness workflow that
   now installs the lockfile. `python-publish.yml` triggers only on a
   published GitHub release and uploads build artifacts without publishing
   to PyPI.
5. **Documentation honesty (prior edits, reviewed and kept).** Badges no
   longer claim hosted CI; README/release/security/setup-guide state the
   empty destination, the simulated-only scope, and the API-lock process;
   marketing/index pages drop the stale "public demo" claims.

## Checks run (2026-11-06, exact outcomes)

Environment: clean venv from `release/requirements.lock.txt` +
`requirements-dev.txt` (Python 3.14.4 host; project supports 3.12+).

| Check | Command | Outcome |
| --- | --- | --- |
| Full test suite | `pytest -q -p no:cacheprovider` (locked venv) | **2,107 passed** in 381.94s |
| Targeted regressions | 6 previously-failing test files | **122 passed** |
| Smoke | `scripts/smoke.py` (locked venv) | `engines 6/6 agents 4/4`, PASS |
| Ruff lint | `ruff check .` | Exit 0 |
| Ruff format | `ruff format --check .` | 474 files formatted (after fix) |
| mypy | `mypy server/ connectors/ control_plane/ contracts/ security/` | No issues in 72 files |
| Bandit | `bandit -c bandit.yaml -r server/ connectors/ control_plane/ engines/ capabilities/ security/ -ll -q` | No findings |
| pip-audit (both locks) | `pip-audit -r release/requirements.lock.txt`; `pip-audit -r release/requirements-api.lock.txt` | **No known vulnerabilities** in either |
| Dependency drift | `scripts/check_dependencies.py` | Passed (incl. new API-lock hash/pin validation) |
| Governance drift | `scripts/check_governance_drift.py` | Only accepted financial-limit divergence |
| Migration drift | `scripts/check_migration_drift.py` | 21/21 objects agree |
| Claims drift | `scripts/check_claims_drift.py` | PASS |
| Fixture drift | `scripts/check_fixture_drift.py` | PASS |
| Capability mirrors | `scripts/sync_capability_mirrors.py --check` | Both mirrors current (22 mappings) |
| Governance authority | `GOVERNANCE/governance_check.py check` | PASS |
| Package build | `python -m build --outdir /tmp/opencode/helix-dist` | sdist + wheel `helix_codex_os-0.9.0` |
| Compose config | `docker compose -f infra/docker/docker-compose.prod-sim.yml config --quiet` | Exit 0 |
| Image build | `docker build -f infra/docker/Dockerfile -t helix-prime-api:prod-sim .` | Built, 203,341,221 bytes (after OS-upgrade fix; 182,125,015 before) |
| Image smoke | read-only, UID 10001, `GET /healthz` | 200 `{"status":"ok",...}` |
| Trivy image scan | Trivy 0.58.0 HIGH/CRITICAL `--ignore-unfixed` | Before fix: 54 OS vulns. After fix: **0** |
| Release gate (simulated) | `scripts/release_gate.py --profile simulated_production` with the regenerated 2026-11-06 signed pack | **SIMULATED_PRODUCTION_READY, all gates green** (23/23). The pack was re-signed after the final source commit from freshly re-run machine evidence (`docs/production_readiness/evidence/simulated-production-2026-11-06/`): all 14 gate checks re-executed green, ML-DSA-65 signature verifies offline. Simulation only — production gates remain red by design. |
| API lock hash install | `pip install --dry-run --require-hashes -r release/requirements-api.lock.txt` | Exit 0 (1,246 hash entries) |

The prior 2026-11-05 Docker/Compose simulation evidence (image build at
182,121,865 bytes, HTTPS `/readyz` 200, 12/12 harness gates) remains
historical evidence for that tree; the rebuilt image above supersedes the
image bytes, and the Compose stack was not re-run this session beyond
`config` validation and single-container smoke.

## Secret-history scan

- Scope: full reachable history (`git log --all -p`, 407 commits, 4,957
  objects) plus tracked-file audit, for private-key blocks, AWS/GitHub/API
  key shapes, and live-secret prefixes.
- Result: **no hits**. Tracked `.pem` files are the simulation authority
  public key (`simulation-authority-public.pem` — public by design) and a
  test fixture public key (`test_pub.pem`); no private keys, `.env` files,
  or live credentials are tracked. `infra/docker/secrets/` holds
  CI-generated synthetic tokens and is untracked. Prior scan (2,701 blobs,
  13 reviewed pattern hits, no credential identified) is consistent with
  this result. Pattern scans cannot prove no secret ever existed; no values
  are printed here.

## Remaining limitations (not waived)

- **No remote is configured** and the destination is empty: hosted CI,
  branch protection, artifacts, and release permissions cannot be verified
  until the owner adds the remote and pushes. CI's fixture-dependent
  readiness step also skips without the external synthetic fixtures; a skip
  is not a pass.
- Actions are mixed pinning: Trivy is SHA-pinned; `upload-artifact@v4` and
  the checkout/setup actions are tag-pinned. Base images are tag-pinned.
- Dependabot's pip ecosystem targets `/` while the hash locks live in
  `release/` — dependency PR automation may be ineffective for the locks
  until configured paths are reviewed by the owner (no change made here).
- Production gates (above) remain red by design; customer data, independent
  audits, approvals, and production operations evidence are owner-supplied
  and absent.

**Status: locally verified, not shipment-ready** for the owner's push decision (full suite,
static gates, dependency audits, image build/smoke, and Trivy scan pass on
the final tree), with hosted-only verification and the production gates
still open. Nothing was pushed, published, released, or deployed.
