# Production-readiness evidence pack

**Run:** `20261031T073347Z`  
**Label:** `PRODUCTION_READINESS_EVIDENCED`  
**Gates:** 12/12 green  
**Engine calls:** 20  

> SYNTHETIC FIXTURE. callcenterclient and sportacademyclient are synthetic, client-shaped datasets built from documented generators. They contain no real client, customer, athlete or employee records. They are used here to exercise ingestion and the six engines against realistic operational shapes; no number in this pack is a claim about a real organisation.

## Gates

| Gate | Title | Verdict | Detail |
| --- | --- | --- | --- |
| `PR-G01` | fixture integrity + disclosure | PASS | both fixtures match their hash manifest and carry disclosure |
| `PR-G02` | raw-layer defect detection | PASS | all declared raw defects detected and cleaned |
| `PR-G03` | WFM staffing on real queue-day volume | PASS | Erlang C staffing is plausible on both fixtures |
| `PR-G04` | RTA adherence on roster/attendance data | PASS | adherence reproduces the fixture within 2pp |
| `PR-G05` | CX risk on real ticket/attendance cohorts | PASS | risk is bounded and ordered with CSAT |
| `PR-G06` | B2B onboarding from client profile | PASS | SOP + staffing plan generated from tenant profile |
| `PR-G07` | Personnel pipeline from requisitions/coaches | PASS | pipeline carries the real requisition and candidate |
| `PR-G08` | CRM pipeline on tenant account value | PASS | deal value is carried from tenant finance data |
| `PR-G09` | engine authorisation fails closed | PASS | all six adapters deny an unknown role |
| `PR-G10` | synthetic-data disclosure on results | PASS | every tenant-derived result is labelled sample |
| `PR-G11` | determinism of engine results | PASS | repeated calls are byte-identical in their metrics |
| `PR-G12` | engine latency budget | PASS | all 20 calls under 5000ms |

## Engine calls

| Engine | Tenant | Client | Capability | Mode | ms | Error |
| --- | --- | --- | --- | --- | --- | --- |
| wfm | callcenterclient | teleclient | wfm_forecast | sample | 143 | - |
| wfm | sportacademyclient | academy | wfm_forecast | sample | 58 | - |
| rta | callcenterclient | teleclient | rta_adherence | sample | 252 | - |
| rta | sportacademyclient | academy | rta_adherence | sample | 115 | - |
| cx | callcenterclient | travbookclient | churn_risk_scoring | sample | 61 | - |
| cx | sportacademyclient | academy | churn_risk_scoring | sample | 61 | - |
| b2b | callcenterclient | teleclient | b2b_onboarding | sample | 58 | - |
| b2b | sportacademyclient | academy | b2b_onboarding | sample | 58 | - |
| personnel | callcenterclient | teleclient | talent_acquisition | sample | 59 | - |
| personnel | sportacademyclient | academy | talent_acquisition | sample | 58 | - |
| crm | callcenterclient | teleclient | sales_pipeline | sample | 58 | - |
| crm | sportacademyclient | academy | sales_pipeline | sample | 60 | - |
| wfm | callcenterclient | teleclient | wfm_forecast | sample | 58 | - |
| wfm | callcenterclient | teleclient | wfm_forecast | sample | 57 | - |
| rta | callcenterclient | teleclient | rta_adherence | sample | 86 | - |
| rta | callcenterclient | teleclient | rta_adherence | sample | 113 | - |
| wfm | sportacademyclient | academy | wfm_forecast | sample | 59 | - |
| wfm | sportacademyclient | academy | wfm_forecast | sample | 59 | - |
| rta | sportacademyclient | academy | rta_adherence | sample | 75 | - |
| rta | sportacademyclient | academy | rta_adherence | sample | 75 | - |

## Reproduce

```bash
python scripts/production_readiness/run.py \
  --out evidence/production_readiness/reproduce
```

A green pack is evidence that the six engines compute on these fixtures under
the stated gates. It is not a `PRODUCTION` label: the nine production-only
gates in `release/release-profiles.yaml` still require signed external evidence.
