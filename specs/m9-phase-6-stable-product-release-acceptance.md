# M9.6 — Stable Product Release Acceptance

status: implementing

## 1. Objective

Close the M9 productization mainline by proving that the already-integrated M9.1-M9.5 capabilities operate as one stable product and by shipping versioned release identity, operator documentation and a bounded recovery contract.

M9.6 is an acceptance/release phase. It does not redefine harmonic Source truth, M4 prospective methodology, Outcome Engine behavior or M8 statistical authorization.

## 2. Composite Stable Product contract

A Stable Product candidate must demonstrate, in one formal release flow, that:

1. automated market-data scheduling and QFQ readiness are product services;
2. automated harmonic analysis advances from canonical data identity and remains viewport-independent;
3. the end-to-end workbench renders canonical bars, harmonic geometry, PRZ, lifecycle, targets and Chinese decision-support context;
4. background evidence maintenance runs without daily user intervention and distinguishes operational failure from evidence insufficiency;
5. a single supervisor, built Web, backup/restore/update and verified no-Git release identity support normal zero-CLI operation;
6. ISSUE-0066 may remain open, but win-rate/alpha/profitability/statistical-significance and evidence-based calibration remain unavailable;
7. Source Coverage, M4 37-component methodology and 4-component Outcome Engine freezes remain intact;
8. the product remains research/decision support only and does not execute securities trades.

## 3. Versioned release identity

The candidate uses `pyproject.toml` `project.version` as the release version. `governance/STABLE_RELEASE.json` binds the Stable Product channel, phase, operator guide, recovery contract and acceptance report contract.

The deterministic M9.5 package builder remains authoritative for the release ZIP and exact release HEAD. M9.6 must not introduce a second package format or identity mechanism.

The release package must include:

- `OPERATOR_GUIDE.md`;
- `RECOVERY_CONTRACT.md`;
- `governance/STABLE_RELEASE.json`;
- the existing one-click entry points and verified `HTCN_RELEASE_IDENTITY.json`.

## 4. Formal acceptance report

`scripts/m9_stable_release_acceptance.py` runs after the formal browser and freeze gates. It emits `artifacts/reports/m9-stable-release-acceptance.json` and fails closed unless all of these are true:

- M9.1-M9.5 are closed and M9.6 is the active/closed phase;
- Product Completion Policy keeps M7 background, M8 claims-only and zero-CLI release semantics;
- ISSUE-0066 does not block M9 release;
- the deterministic release package is verified and excludes mutable/private market data;
- the extracted no-Git package passes M4 methodology, Outcome Engine and supervisor preflight checks;
- all one-click entry points exist;
- operator/recovery documents contain the stable product, claims-only and bounded recovery contracts.

The acceptance report itself does not unlock statistical claims.

## 5. CI ordering

Formal release CI must run in this order:

1. Project OS and main-release lineage;
2. Web build;
3. deterministic M9.5 release package build/verification;
4. browser acceptance, including M9.3 workbench, M9.4 evidence observability and M9.5 reliability;
5. Phase18 / Phase21 browser evidence;
6. M4 37/37 and Outcome 4/4 freeze guards;
7. M9.6 Stable Product release acceptance report;
8. upload the release package and acceptance evidence.

Because the M9.6 step is after the browser/freeze steps, it cannot report acceptance when an earlier formal gate failed.

## 6. User-computer boundary

No user-computer run is required for M9.6. Hosted CI, repository fixtures and packaged no-Git verification are sufficient for product release acceptance.

A later user-requested local UAT remains optional and does not retroactively become a release blocker.

## 7. Exit gate

M9.6 may close only when:

- formal PR validation is green on the exact ledger-bearing candidate;
- the formal CI artifact contains the verified release package and `m9-stable-release-acceptance.json` with `accepted=true`;
- canonical main post-merge validation is green;
- operator guide and recovery contract are packaged and version-bound;
- Project State, Milestones, Decision/Attempt ledgers and Stable Release record are closed consistently;
- M9 is marked product-complete while M7 remains an operational background evidence track and M8 remains claims-gated by ISSUE-0066.
