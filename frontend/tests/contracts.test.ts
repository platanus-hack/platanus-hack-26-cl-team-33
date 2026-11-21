import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { comparisonRequest, simulationRequest } from '../src/api/scenarios.ts';

test('canonical scenarios change exactly their assigned field and keep initial occupancy', () => {
  const expected = { baseline: {}, more_physicians: { physicians: 6 }, faster_turnover: { bed_turnover_min: 30 }, more_ward_beds: { ward_beds: 28 } };
  for (const [id, override] of Object.entries(expected)) {
    const request = simulationRequest(id as Parameters<typeof simulationRequest>[0]);
    assert.deepEqual(request, { scenario_id: id, seed: 42, config: { ...comparisonRequest.base_config, ...override } });
    assert.equal(request.config.initial_ward_occupied, 21);
  }
  assert.deepEqual(comparisonRequest.seeds, [101,102,103,104,105]);
  assert.equal(comparisonRequest.scenarios.length, 4);
});

test('frontend fixture copies remain byte-identical to the frozen source', async () => {
  for (const file of ['simulate_request.json','simulate_response.json','compare_request.json','compare_response.json']) {
    assert.equal(await readFile(new URL(`../src/mocks/${file}`, import.meta.url),'utf8'), await readFile(new URL(`../../fixtures/${file}`, import.meta.url),'utf8'));
  }
});

test('fixture snapshots preserve disjoint ED use and ward capacity', async () => {
  const data = JSON.parse(await readFile(new URL('../src/mocks/simulate_response.json', import.meta.url),'utf8'));
  for (const s of data.timeline) {
    assert.ok(s.ed_treatment + s.ed_boarding <= comparisonRequest.base_config.ed_spaces);
    assert.equal(s.ward_occupied + s.ward_turnover + s.ward_ready, comparisonRequest.base_config.ward_beds);
  }
});
