# Consumer caveats — synthetic tenant fixtures

**Status:** current for the `simulated_production` evidence pack (2026-11-04).
**Applies to:** `callcenterclient` and `sportacademyclient`, the two synthetic,
client-shaped fixture estates under `External tenant data/` (outside this repo).

**SIMULATION ONLY.** Both estates are generated. No real customer, athlete, employee,
or patient record is present. Every number produced from them is a statement about
the fixture, not about a real organisation. A real client's first-week data will
differ in volume, drift, schema evolution, and edge cases; see
[REAL_CLIENT_ACTIVATION.md](../release/REAL_CLIENT_ACTIVATION.md).

## 1. Tickets are a sample; queue metrics are authoritative (CallCenterClient)

`tickets` and `cases` are a **documented ~2.7% sample** of contact volume
(`ASSUMPTIONS.md` AS-07, `DECISIONS.md` BD-03). `queue_metrics_daily` is the
authoritative volume source.

- Do not reconcile ticket **counts** to queue volumes — they will never match.
- Reconcile ticket **rates** (tickets per 100 contacts) instead.
- Any CX or quality conclusion that divides ticket counts by queue volume must say
  it is using a sampled numerator.

## 2. Time zones and business dates

- All **timestamps are UTC**.
- All **business dates** (for example `rosters_daily.roster_date`, P&L months,
  scheduling weeks) are **Africa/Cairo** dates.
- Egypt observes daylight saving in some years; date arithmetic must use a real
  tz database, never a fixed UTC+2 offset.
- A “day” in a WFM or CX answer means a Cairo business day. Presenting it as UTC can
  move up to two hours of volume into the wrong day.

## 3. Load order and referential integrity

Load dimensions before facts:

1. dimensions: `agents`, `support_staff`, `teams`, `coaches`, `squads`, `athletes`
2. facts: `rosters_daily`, `queue_metrics_daily`, `intraday_15min`, `tickets`,
   `attendance`, `sessions`, `invoices`, `pnl_monthly`

All declared foreign keys resolve in the frozen snapshot. A partial or reordered
load will fail validation rather than silently dropping rows. The App import path
enforces the same order and refuses a hard error transactionally.

## 4. Idempotent re-import

The curated layer is **idempotent by primary key**. Re-importing the same file is a
replace, not an append. This is what makes retries safe. Consumer consequences:

- re-uploading a corrected file replaces rows by primary key;
- deleting a row from the source file does **not** delete it from an existing target
  (no tombstone semantics in the curated layer);
- two files that disagree on the same primary key resolve to the last committed
  import, and the earlier version remains in the audit trail.

## 5. Schema coverage is partial by design

The App import drill imports only tables that have a declared schema in
`16_DATA/schemas/*.json`. In the 2026-11-04 drill that meant:

- `callcenterclient`: 6 tables imported, 33 curated CSVs skipped;
- `sportacademyclient`: 8 tables imported, 32 curated CSVs skipped.

A skipped file is **not** an error; it means no contract exists yet. Readiness gates
still consume those files directly through the harness. Do not present the App
import as “all tenant data imported”.

## 6. SLA and projection windows

- SLA percentages are measured over the fixture's declared interval, not a rolling
  contractual window.
- Forecast and capacity outputs project from the frozen snapshot; they are not
  live forecasts and have no drift correction.
- Erlang-C / WFM answers assume the documented shrinkage and occupancy inputs
  (`ASSUMPTIONS.md`). Change one assumption and the answer moves; it is a model
  output, not a measurement.

## 7. SportAcademyClient specifics

- Attendance baseline is **86% of booked**, with declared seasonality.
- Safeguarding and medical tables are **Restricted**: least privilege, logged
  access, statutory retention. They must never be surfaced to a general dashboard
  audience.
- Monthly fees are EGP-denominated and programme-dependent; do not aggregate across
  programmes without stating the weighting.

## 8. What a real client must confirm on day one

1. Row counts and date coverage for every table they expect to use.
2. Whether their CRM exports are complete or sampled, and at what rate.
3. Their business time zone(s) and DST rules.
4. Primary-key uniqueness and foreign-key completeness in their export.
5. Whether deletes are represented at all (tombstones vs full snapshots).
6. Which tables have a schema contract and which are exploratory.
7. Currency, VAT, and on-cost assumptions for any financial answer.
8. Restricted-data handling (medical, safeguarding, disciplinary) and retention.
9. Their real SLA definition and measurement window.
10. Their expected peak concurrency and volume shape, before trusting any capacity
    or performance result.

Until those are confirmed in writing, every output remains a simulation result.
