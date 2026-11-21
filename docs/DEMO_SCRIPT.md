# Demo script (3 minutes)

Always state: **synthetic model; MINSAL 85% is a reference target, not our result.** Never prescript a numeric outcome — read numbers from the screen/API, and if intervals straddle zero say so.

Before the demo: start API (`BEDFLOW_MODE=real`), confirm `GET /health` shows `"mode": "real-engine"` (not `stub-fixture-not-real`), open the UI.

| Time | Action |
| --- | --- |
| 0:00–0:25 | Context: Chile's 12-hour admission target and ED boarding. |
| 0:25–1:00 | Simulate page, baseline: show ED waiting/treatment/boarding and ward occupancy replay. |
| 1:00–1:40 | Switch to *More physicians*, run; explain the measured effect, including if it does not help admission delay. |
| 1:40–2:20 | Compare page: *Faster bed turnover* and *More staffed ward beds* on the same seeds; discuss tradeoffs and uncertainty. |
| 2:20–2:50 | Paired difference (percentage points) with intervals; explain where the bottleneck moves **only if the computed results support it**. |
| 2:50–3:00 | Assumptions, limitations (`docs/MODEL_LIMITATIONS.md`), and how pilot calibration could make it operational. |

Backup: if the live run fails, show the real-engine artifact in `docs/results/benchmark_<n>seeds.json` (labeled with config, seeds, commit). Generate it with `python scripts/run_scenarios.py`.
