"""Run the 4 canonical scenarios on matched seeds with the REAL engine and save a
labeled benchmark artifact (config, seeds, engine commit, timestamp).

Usage: python scripts/run_scenarios.py [--seeds 20] [--out docs/results]
Requires Person A's bedflow.sim.engine; refuses to run on the stub.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bedflow.contracts import CompareRequest  # noqa: E402
from bedflow.experiments.compare import compare  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "results")
    args = parser.parse_args()

    try:
        from bedflow.sim.engine import simulate
    except ImportError:
        sys.exit("bedflow.sim.engine not available: refusing to produce non-real results")

    request = json.loads((ROOT / "fixtures" / "compare_request.json").read_text(encoding="utf-8"))
    request["seeds"] = list(range(101, 101 + args.seeds))
    req = CompareRequest.model_validate(request)

    start = time.perf_counter()
    response = compare(req.base_config, req.scenarios, req.seeds, simulate)
    elapsed = time.perf_counter() - start

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    artifact = {
        "label": "REAL ENGINE RESULT - synthetic model, not validated for real hospital decisions",
        "computed_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "elapsed_seconds": round(elapsed, 2),
        "request": req.model_dump(),
        "response": response.model_dump(),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"benchmark_{args.seeds}seeds.json"
    path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
