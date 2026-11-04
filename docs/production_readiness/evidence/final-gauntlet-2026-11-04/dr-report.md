# Disaster-recovery drill (simulated volume loss)

> SIMULATION ONLY. Disposable local state, synthetic rows, no hosted stack. RTO/RPO measure this machine and these code paths; a real deployment needs a container-orchestrated drill against the real backup target.

**Runs:** 3  
**Passed:** 3/3  
**Generated:** 2026-11-04T02:19:58.665003Z

| Run | Passed | RTO (s) | RPO (s) | Nodes | Tables | Audit chain | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | True | 0.0033 | 0.0002 | 2 | 32 | True | - |
| 2 | True | 0.0035 | 0.0002 | 2 | 32 | True | - |
| 3 | True | 0.0031 | 0.0002 | 2 | 32 | True | - |

## Limitations

- The drill destroys disposable local files, not container volumes.
- RTO/RPO are single-machine measurements and are not production SLOs.
- The restore target is clean by construction; it does not exercise a cold standby host.
