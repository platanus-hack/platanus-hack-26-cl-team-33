/** BedFlow Chile v1.0 — FROZEN API types. Owner: Person C; B consumes.
 *  All times are simulated minutes; percentages are 0–100.
 */
export interface SimulationConfig {
  arrival_rate_per_hour: number;
  physicians: number;
  ed_spaces: number;
  ward_beds: number;
  initial_ward_occupied: number;
  admission_probability: number;
  mean_physician_service_min: number;
  mean_inpatient_los_h: number;
  bed_turnover_min: number;
  warmup_h: number;
  measurement_h: number;
  followup_h: number;
  snapshot_every_min: number;
}
export interface SimulateRequest {
  scenario_id: string;
  seed: number;
  config: SimulationConfig;
}
export interface SimulationMetrics {
  eligible_admissions: number;
  admitted_within_12h_count: number;
  admitted_within_12h_pct: number | null;
  mean_wait_to_bed_capped_12h_min: number | null;
  p90_wait_to_bed_capped_12h_min: number | null;
  avg_ed_bay_utilization_pct: number;
  avg_ward_occupancy_pct: number;
  max_ed_boarding: number;
  ed_arrivals_measured: number;
}
export interface TimelineSnapshot {
  minute: number;
  ed_waiting: number;
  ed_treatment: number;
  ed_boarding: number;
  ward_occupied: number;
  ward_turnover: number;
  ward_ready: number;
}
export type MilestoneType =
  | 'ED_ARRIVAL' | 'ED_BAY_ENTER' | 'PHYSICIAN_START' | 'PHYSICIAN_END'
  | 'ADMISSION_INDICATED' | 'WARD_ADMITTED' | 'ED_DISCHARGED'
  | 'WARD_DISCHARGED' | 'BED_READY';
export interface PatientMilestone { minute: number; type: MilestoneType; }
export interface PatientExample {
  patient_id: number;
  admission_wait_min: number | null;
  milestones: PatientMilestone[];
}
export interface SimulationResult {
  schema_version: '1.0';
  scenario_id: string;
  seed: number;
  metrics: SimulationMetrics;
  timeline: TimelineSnapshot[];
  patient_examples: PatientExample[];
}
export type ScenarioId =
  | 'baseline' | 'more_physicians' | 'faster_turnover' | 'more_ward_beds';
export interface ScenarioVariant {
  scenario_id: ScenarioId;
  label: string;
  overrides: Partial<Pick<SimulationConfig, 'physicians' | 'bed_turnover_min' | 'ward_beds'>>;
}
export interface CompareRequest {
  base_config: SimulationConfig;
  seeds: number[];
  scenarios: ScenarioVariant[];
}
export interface MetricStats { mean: number; ci95_low: number; ci95_high: number; }
export interface CompareSummary {
  admitted_within_12h_pct: MetricStats;
  mean_wait_to_bed_capped_12h_min: MetricStats;
  avg_ed_bay_utilization_pct: MetricStats;
}
export interface CompareScenarioResult {
  scenario_id: ScenarioId;
  label: string;
  summary: CompareSummary;
  paired_delta_12h_pp: MetricStats | null;
}
export interface CompareResponse {
  schema_version: '1.0';
  seeds: number[];
  results: CompareScenarioResult[];
}
