"""Dev-only CLI for Person A handoffs. Integration must call ``simulate()`` directly.

    PYTHONPATH=backend python -m bedflow.sim --seed 42
    PYTHONPATH=backend python -m bedflow.sim --seed 42 --scenario faster_turnover --full
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from bedflow.contracts import SimulationConfig
from bedflow.sim.engine import simulate

BASE_CONFIG = {
    "arrival_rate_per_hour": 3.0,
    "physicians": 4,
    "ed_spaces": 8,
    "ward_beds": 24,
    "initial_ward_occupied": 21,
    "admission_probability": 0.20,
    "mean_physician_service_min": 35.0,
    "mean_inpatient_los_h": 36.0,
    "bed_turnover_min": 120.0,
    "warmup_h": 72,
    "measurement_h": 168,
    "followup_h": 12,
    "snapshot_every_min": 15,
}
SCENARIO_OVERRIDES = {
    "baseline": {},
    "more_physicians": {"physicians": 6},
    "faster_turnover": {"bed_turnover_min": 30.0},
    "more_ward_beds": {"ward_beds": 28},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", choices=sorted(SCENARIO_OVERRIDES), default="baseline")
    parser.add_argument("--full", action="store_true", help="print the full SimulationResult JSON")
    args = parser.parse_args()

    config = SimulationConfig(**{**BASE_CONFIG, **SCENARIO_OVERRIDES[args.scenario]})
    started = time.perf_counter()
    result = simulate(config, args.seed).model_copy(update={"scenario_id": args.scenario})
    elapsed = time.perf_counter() - started

    if args.full:
        print(result.model_dump_json(indent=2))
    else:
        print(json.dumps({
            "scenario_id": result.scenario_id,
            "seed": result.seed,
            "config": config.model_dump(),
            "metrics": result.metrics.model_dump(),
            "timeline_snapshots": len(result.timeline),
            "timeline_minutes": [result.timeline[0].minute, result.timeline[-1].minute]
            if result.timeline else None,
            "patient_examples": [
                {"patient_id": p.patient_id, "admission_wait_min": p.admission_wait_min,
                 "milestones": [m.type for m in p.milestones]}
                for p in result.patient_examples
            ],
        }, indent=2))
    print(f"simulate() wall time: {elapsed * 1000:.0f} ms", file=sys.stderr)


if __name__ == "__main__":
    main()
