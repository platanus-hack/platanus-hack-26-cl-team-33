// Run with a real API and Vite's HTTP-mode proxy already listening.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { createApi } from '../src/api/client.ts';
import { comparisonRequest, simulationRequest } from '../src/api/scenarios.ts';
const origin = process.env.BEDFLOW_TEST_ORIGIN || 'http://127.0.0.1:5174';
const traces = [];
const api = createApi(false, async (path, options) => {
  const response = await fetch(new URL(path, origin), options);
  const body = await response.clone().json();
  traces.push({ path, request: JSON.parse(options.body), status: response.status, mode: response.headers.get('X-BedFlow-Mode'), response: body });
  assert.equal(response.headers.get('X-BedFlow-Mode'), 'real-engine');
  return response;
});
for (const scenario of comparisonRequest.scenarios) {
  const request = simulationRequest(scenario.scenario_id);
  const { data, fixture } = await api.simulate(request);
  assert.equal(fixture, false);
  assert.equal(data.scenario_id, request.scenario_id);
  assert.equal(data.seed, 42);
  assert.equal(data.timeline.length, 672);
  for (const point of data.timeline) {
    assert.ok(point.ed_treatment + point.ed_boarding <= request.config.ed_spaces);
    assert.equal(point.ward_occupied + point.ward_turnover + point.ward_ready, request.config.ward_beds);
  }
  console.log(`${scenario.scenario_id}: ${data.metrics.admitted_within_12h_pct}% admission within 12h; ${data.timeline.length} snapshots`);
}
const comparison = await api.compare(comparisonRequest);
assert.equal(comparison.fixture, false);
assert.deepEqual(comparison.data.seeds, [101, 102, 103, 104, 105]);
assert.deepEqual(comparison.data.results.map(r => r.scenario_id), comparisonRequest.scenarios.map(r => r.scenario_id));
const emptyRequest = simulationRequest('baseline');
emptyRequest.config.admission_probability = 0;
const empty = await api.simulate(emptyRequest);
assert.equal(empty.data.metrics.eligible_admissions, 0);
for (const key of ['admitted_within_12h_pct', 'mean_wait_to_bed_capped_12h_min', 'p90_wait_to_bed_capped_12h_min']) assert.equal(empty.data.metrics[key], null);
const noAdmissionsComparison = structuredClone(comparisonRequest);
noAdmissionsComparison.base_config.admission_probability = 0;
await assert.rejects(api.compare(noAdmissionsComparison), /422/);
await writeFile(new URL('../evidence/real-api-trace.json', import.meta.url), JSON.stringify({ captured_at: new Date().toISOString(), origin, api_commit: '8b9134d72a09784cc91b70f1f16397e4fa8cadd4', engine_commit: '8d4e1a381ccdfe658867d9d49fcb8e46df7dc086', traces }) + '\n');
console.log('PASS: four scenarios, comparison, null-admission metrics, zero-valid-seed rejection; real-engine headers throughout.');
