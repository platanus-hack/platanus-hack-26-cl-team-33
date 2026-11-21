import type { CompareRequest, ScenarioId, SimulateRequest, SimulationConfig } from '../types/api';
import comparison from '../mocks/compare_request.json' with { type: 'json' };
export const comparisonRequest = comparison as CompareRequest;
export const baseConfig: SimulationConfig = comparisonRequest.base_config;
export const scenarios = comparisonRequest.scenarios;
export function simulationRequest(id: ScenarioId, seed = 42): SimulateRequest {
  const scenario = scenarios.find(s => s.scenario_id === id)!;
  return { scenario_id: id, seed, config: { ...baseConfig, ...scenario.overrides } };
}
export const changes: Record<ScenarioId, string> = {
  baseline: '4 physicians · 120 min turnover · 24 ward beds',
  more_physicians: 'Physicians: 4 → 6',
  faster_turnover: 'Bed turnover: 120 → 30 min',
  more_ward_beds: 'Ward beds: 24 → 28 · initial occupied stays 21',
};
