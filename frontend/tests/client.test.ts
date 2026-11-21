import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApi } from '../src/api/client.ts';
import { comparisonRequest, simulationRequest } from '../src/api/scenarios.ts';
import simulation from '../src/mocks/simulate_response.json' with { type: 'json' };
import comparison from '../src/mocks/compare_response.json' with { type: 'json' };

test('HTTP adapter posts exact scenario configuration and preserves response metrics', async () => {
  const request = simulationRequest('more_ward_beds');
  const api = createApi(false, async (url, options) => {
    assert.equal(url, '/api/v1/simulate');
    assert.equal(options?.method, 'POST');
    assert.deepEqual(JSON.parse(String(options?.body)), request);
    return new Response(JSON.stringify(simulation));
  });
  const result = await api.simulate(request);
  assert.deepEqual(result.data, simulation);
  assert.equal(result.fixture, false);
});

test('comparison posts all four variants with the matched seed list', async () => {
  const api = createApi(false, async (url, options) => {
    assert.equal(url, '/api/v1/compare');
    assert.deepEqual(JSON.parse(String(options?.body)), comparisonRequest);
    return new Response(JSON.stringify(comparison));
  });
  assert.deepEqual((await api.compare(comparisonRequest)).data, comparison);
});

test('HTTP fixture server is disclosed even when local mock mode is off', async () => {
  for (const mode of ['mock-fixture-not-real', 'stub-fixture-not-real', 'STUB']) {
    const api = createApi(false, async () => new Response(JSON.stringify(simulation), { headers: { 'X-BedFlow-Mode': mode } }));
    assert.equal((await api.simulate(simulationRequest('baseline'))).fixture, true);
  }
  const api = createApi(false, async () => new Response(JSON.stringify(simulation), { headers: { 'X-BedFlow-Mode': 'real-engine' } }));
  assert.equal((await api.simulate(simulationRequest('baseline'))).fixture, false);
});

test('fixtures preserve identity and are isolated between requests', async () => {
  const api = createApi(true, async () => { throw Error('Mock must not fetch'); });
  const first = await api.simulate(simulationRequest('more_physicians'));
  assert.equal(first.fixture, true);
  assert.equal(first.data.scenario_id, 'baseline');
  first.data.metrics.eligible_admissions = 0;
  assert.deepEqual((await api.simulate(simulationRequest('baseline'))).data, simulation);
});

test('null admission metrics are preserved without converting them into zero', async () => {
  const data = { ...simulation, metrics: { ...simulation.metrics, eligible_admissions: 0, admitted_within_12h_count: 0, admitted_within_12h_pct: null, mean_wait_to_bed_capped_12h_min: null } };
  const api = createApi(false, async () => new Response(JSON.stringify(data)));
  assert.equal((await api.simulate(simulationRequest('baseline'))).data.metrics.admitted_within_12h_pct, null);
});

test('validation and server errors reject instead of returning stale data', async () => {
  for (const status of [422,500]) {
    const api = createApi(false, async () => new Response('{}', { status }));
    await assert.rejects(api.simulate(simulationRequest('baseline')), new RegExp(String(status)));
  }
});

test('network, abort and contract-version failures are actionable', async () => {
  const request = simulationRequest('baseline');
  await assert.rejects(createApi(false, async () => { throw new TypeError('fetch failed'); }).simulate(request), /Cannot reach the API/);
  await assert.rejects(createApi(false, async () => { throw new DOMException('aborted','AbortError'); }).simulate(request), /timed out/);
  await assert.rejects(createApi(false, async () => new Response('{"schema_version":"2.0"}')).simulate(request), /unsupported response/);
});
