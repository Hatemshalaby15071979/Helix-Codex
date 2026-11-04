# App CSV import drill (both tenants, real HTTP routes)

> SIMULATION ONLY. Synthetic curated fixtures, a disposable local SQLite app database, and the real authenticated App import routes. No real client data was uploaded and no external service was contacted.

**Passed:** True  
**Generated:** 2026-11-04T02:20:02.220908Z

| Tenant | Imported files | Skipped | Failed | Rows | Idempotent | Isolated |
| --- | --- | --- | --- | --- | --- | --- |
| callcenterclient | 6 | 33 | 0 | 17944 | True | True |
| sportacademyclient | 8 | 32 | 0 | 166739 | True | True |

## Limitations

- The upload is driven through the App's authenticated HTTP import routes, not a browser click path.
- Only curated exports with a declared schema are imported; unmatched files are listed as skipped.
- The readiness harness still reads the fixture files directly; it is not re-pointed at the App database.
