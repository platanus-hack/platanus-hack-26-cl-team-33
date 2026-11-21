import type { CompareRequest, CompareResponse, SimulateRequest, SimulationResult } from '../types/api';
import simulationFixture from '../mocks/simulate_response.json' with { type: 'json' };
import comparisonFixture from '../mocks/compare_response.json' with { type: 'json' };
export type Result<T> = { data: T; fixture: boolean };
const env = import.meta.env ?? {};
export const useMock = env.VITE_USE_MOCK === 'true' || (env.DEV === true && env.VITE_USE_MOCK !== 'false');
export function createApi(mock: boolean, fetcher: typeof fetch = fetch) {
  async function post<T>(endpoint: 'simulate' | 'compare', request: unknown): Promise<Result<T>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120_000);
    try {
      const response = await fetcher(`/api/v1/${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), signal: controller.signal });
      if (!response.ok) throw new Error(response.status === 422 ? 'The API rejected the configuration (422). Check the agreed request contract.' : `The experiment failed (HTTP ${response.status}). Please retry.`);
      const data = await response.json();
      if (data.schema_version !== '1.0' || (endpoint === 'simulate' ? !data.metrics || !Array.isArray(data.timeline) : !Array.isArray(data.results))) throw new Error('The API returned an unsupported response. Check the backend contract.');
      const mode = (response.headers.get('X-BedFlow-Mode') || '').toLowerCase();
      return { data, fixture: /mock|stub|fixture/.test(mode) };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') throw new Error('The experiment timed out after 120 seconds. Please retry.');
      if (error instanceof TypeError) throw new Error('Cannot reach the API. Check the backend and /api proxy, then retry.');
      throw error;
    } finally { clearTimeout(timer); }
  }
  return {
    async simulate(request: SimulateRequest): Promise<Result<SimulationResult>> {
      if (!mock) return post('simulate', request);
      // Preserve fixture identity: these values never claim to simulate an intervention.
      return { data: structuredClone(simulationFixture) as SimulationResult, fixture: true };
    },
    async compare(request: CompareRequest): Promise<Result<CompareResponse>> {
      if (!mock) return post('compare', request);
      return { data: structuredClone(comparisonFixture) as CompareResponse, fixture: true };
    },
  };
}
export const api = createApi(useMock);
