# GLOBAL PROMPT — paste in ALL three AI coding sessions

You are developing **BedFlow Chile**, a 36-hour hackathon project in the **Simulations** track. This is a fictional, evidence-informed discrete-event simulator of an emergency department and its connection to inpatient beds. It answers: **"What would happen to hospital admission delays if we changed clinicians, bed turnover, or inpatient-bed capacity?"**

This is **not** a triage simulator, clinical diagnosis model, deterioration simulator, undertriage system, multi-hospital dispatch tool, or real patient-management product. Do not introduce any of those features.

Our canonical sources of truth are `spec/PROJECT_SPEC.md` and `spec/CONTRACTS.md`, plus the Python/TypeScript schema stubs and JSON fixtures. Read all before coding. Follow your dedicated role prompt; do not edit another owner's directories or shared contracts. The owner of the shared contract is Person C; any change requires agreement by all three developers and synchronized updates to fixtures/tests.

Stack: Python 3.12, SimPy, NumPy, Pydantic v2, FastAPI, pytest, React + Vite + TypeScript, Tailwind, Recharts. No real-time sensors, external hospital APIs or LLM-required backend logic. Browser requests go only to `/api/v1/simulate` and `/api/v1/compare`.

**Model rules:** Simulated arrivals queue for an ED bay. A patient retains the bay through initial physician treatment, and if hospitalization is indicated, while boarding for a ward bed. Physicians are released after ED treatment. Inpatient bed allocation is capacity-constrained; admitted patients stay for synthetic lengths of stay; on ward discharge, beds undergo configurable turnover before becoming ready. Existing inpatient occupancy is simulated at startup. Use seeded stochastic processes and pre-generated exogenous patient inputs. All results are computed from actual simulation events.

**Main metric:** percentage of hospitalization indications in the measurement window that reach a ward bed within 12 hours from indication, including outcomes in a 12-hour follow-up. Chile's ≥85% target is reference context, **not a model result**.

**Exactly four MVP scenarios:** baseline; 4→6 physicians; bed turnover 120→30 min; 24→28 ward beds keeping initial occupied beds at 21. Initial synthetic base parameters, metric field names, unit conventions, event names and API shapes are specified in the contracts file; never improvise alternatives.

Your coding routine: (1) make the smallest working increment; (2) add/update tests; (3) run those tests; (4) show exact changed files, commands, expected JSON shape and blockers; (5) commit only in your owned paths. No fake improvements, no hardcoded charts, no misleading real-world medical claims.

**H12 mandatory:** Real UI → real API → real SimPy engine → computed metrics/timeline → real UI. **H20:** four working scenarios and comparisons. After H20, prioritize correctness, robust UX, and presentation over new features.

When uncertain, prefer simplifying the implementation to preserve agreed API and scientific integrity. Avoid speculative architectural overhauls. Each handoff must name changed paths, public interfaces, test commands/results, and required input from another role.
