# Agreed application repository layout

```text
bedflow-chile/
├── backend/
│   ├── bedflow/
│   │   ├── contracts.py          # C owns; frozen versioned Pydantic schema
│   │   ├── api/                  # C owns; HTTP endpoints, validation
│   │   ├── experiments/          # C owns; paired replications, summaries
│   │   └── sim/                  # A owns; engine, stochastic generation, model
│   └── tests/
│       ├── sim/                 # A owns
│       ├── api/                 # C owns
│       └── integration/         # C owns
├── frontend/
│   └── src/
│       ├── types/api.ts         # C-coordinated shared interface, B imports
│       ├── api/                 # B owns; HTTP/mock adapter
│       ├── pages/               # B owns; Simulate, Compare
│       ├── components/          # B owns; KPI, graphs, replay, controls
│       └── mocks/               # B can copy identical root fixtures
├── fixtures/                    # C owns; v1.0 checked canonical JSON
├── spec/                        # all read, C maintains, changes with consensus
├── prompts/                     # role prompts, not executable app code
├── docs/                        # C owns; assumptions, demo, limitations
├── .github/                     # C owns; CI
└── README.md                     # C owns; setup/run
```

**A → C:** Python `simulate(config, seed)` returns `SimulationResult`.

**C → B:** HTTP JSON only; B must not directly import Python or parse CLI output.

**Fixtures:** A and C must not change fixture numeric claims to match desired impacts. They are mock UI test payloads. Replace mock mode before judging and store optional demo backup as a separately labeled *real computed* artifact with config and seeds.

## Development startup commands (target; Person C establishes actual environment)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install simpy numpy pydantic fastapi 'uvicorn[standard]' pytest httpx
PYTHONPATH=backend pytest backend/tests -q
PYTHONPATH=backend uvicorn bedflow.api.mock_api:app --reload
# second shell
cd frontend && npm install && npm run dev
```

Mock API runs only if `fixtures/` is copied to the repository root and the starter schema exists at `backend/bedflow/contracts.py`. It is a **scaffold**, not the completed backend.
