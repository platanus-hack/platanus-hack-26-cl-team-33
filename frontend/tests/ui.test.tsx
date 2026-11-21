// @vitest-environment jsdom
import React from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { api } from '../src/api/client';
import { Simulate } from '../src/pages/Simulate';
import { Compare } from '../src/pages/Compare';
import { Replay } from '../src/components/Replay';
import { number } from '../src/components/common';
import fixture from '../src/mocks/simulate_response.json';
import comparison from '../src/mocks/compare_response.json';
import type { SimulationResult, CompareResponse } from '../src/types/api';
vi.mock('../src/api/client', () => ({ useMock: false, api: { simulate: vi.fn(), compare: vi.fn() } }));
// Chart layout is browser-tested separately; avoid zero-sized jsdom containers.
vi.mock('recharts', async importOriginal => ({ ...await importOriginal<typeof import('recharts')>(), ResponsiveContainer: () => <div>Chart</div> }));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
test('null metrics are unavailable rather than zero percent', () => { expect(number(null,'%')).toBe('Not available'); });
test('scenario edits clear previous results and send the actual override', async () => {
  vi.mocked(api.simulate).mockResolvedValue({ data: fixture as SimulationResult, fixture: false });
  render(<Simulate/>);
  fireEvent.click(screen.getByRole('button',{ name: /Run simulation/ }));
  await screen.findByText('81.25%');
  fireEvent.click(screen.getByRole('radio',{ name: /More physicians/ }));
  expect(screen.queryByText('81.25%')).toBeNull();
  fireEvent.click(screen.getByRole('button',{ name: /Run simulation/ }));
  await waitFor(() => expect(api.simulate).toHaveBeenLastCalledWith(expect.objectContaining({ scenario_id: 'more_physicians', config: expect.objectContaining({ physicians: 6 }) })));
});
test('failed rerun removes old KPI values and shows an error', async () => {
  vi.mocked(api.simulate).mockResolvedValueOnce({ data: fixture as SimulationResult, fixture: false }).mockRejectedValueOnce(Error('API unavailable'));
  render(<Simulate/>);
  fireEvent.click(screen.getByRole('button',{ name: /Run simulation/ }));
  await screen.findByText('81.25%');
  fireEvent.click(screen.getByRole('button',{ name: /Run simulation/ }));
  await screen.findByRole('alert');
  expect(screen.queryByText('81.25%')).toBeNull();
});
test('replay scrubbing uses the actual snapshot minute', () => {
  render(<Replay result={fixture as SimulationResult}/>);
  fireEvent.change(screen.getByRole('slider'),{ target: { value: '2' } });
  expect(screen.getAllByText(/D3 00:30/).length).toBeGreaterThan(0);
});
test('comparison shows paired percentage points and inconclusive intervals', async () => {
  vi.mocked(api.compare).mockResolvedValue({ data: comparison as CompareResponse, fixture: false });
  render(<Compare/>);
  fireEvent.click(screen.getByRole('button',{ name: /Run comparison/ }));
  await screen.findByText('Inconclusive: interval includes zero');
  expect(screen.getByText('0.25 pp (-1.25 to 1.75 pp)')).toBeTruthy();
});

test('HTTP stub results disclose fixtures on both screens', async () => {
  vi.mocked(api.simulate).mockResolvedValue({ data: fixture as SimulationResult, fixture: true });
  const simulation = render(<Simulate/>);
  fireEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await screen.findByText('Fixture preview — synthetic layout data.');
  expect(screen.getByText(/Fixed baseline fixture preview/)).toBeTruthy();
  simulation.unmount();
  vi.mocked(api.compare).mockResolvedValue({ data: comparison as CompareResponse, fixture: true });
  render(<Compare/>);
  fireEvent.click(screen.getByRole('button', { name: /Run comparison/ }));
  await screen.findByText('Fixture preview — synthetic layout data.');
  expect(screen.getAllByText('Illustrative fixture interval only')).toHaveLength(2);
});

test('zero-admission responses render unavailable KPIs while retaining utilization', async () => {
  const data = structuredClone(fixture) as SimulationResult;
  Object.assign(data.metrics, { eligible_admissions: 0, admitted_within_12h_count: 0, admitted_within_12h_pct: null, mean_wait_to_bed_capped_12h_min: null, p90_wait_to_bed_capped_12h_min: null });
  vi.mocked(api.simulate).mockResolvedValue({ data, fixture: false });
  render(<Simulate/>);
  fireEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await screen.findByText('0 of 0 eligible indications');
  expect(screen.getAllByText('Not available')).toHaveLength(2);
  expect(screen.getByText('75%')).toBeTruthy();
});

test('demo reset clears the prior result and restores baseline', async () => {
  vi.mocked(api.simulate).mockResolvedValue({ data: fixture as SimulationResult, fixture: false });
  render(<Simulate/>);
  fireEvent.click(screen.getByRole('radio', { name: /More physicians/ }));
  fireEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await screen.findByText('81.25%');
  fireEvent.click(screen.getByRole('button', { name: 'Demo configuration' }));
  expect(screen.queryByText('81.25%')).toBeNull();
  expect((screen.getByRole('radio', { name: /Baseline/ }) as HTMLInputElement).checked).toBe(true);
});

test('comparison clears old results while pending and after failure', async () => {
  let reject!: (reason: Error) => void;
  vi.mocked(api.compare).mockResolvedValueOnce({ data: comparison as CompareResponse, fixture: false }).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; }));
  render(<Compare/>);
  fireEvent.click(screen.getByRole('button', { name: /Run comparison/ }));
  await screen.findByText('0.25 pp (-1.25 to 1.75 pp)');
  fireEvent.click(screen.getByRole('button', { name: /Run comparison/ }));
  expect(screen.queryByRole('table')).toBeNull();
  expect((screen.getByRole('button', { name: /Comparing/ }) as HTMLButtonElement).disabled).toBe(true);
  reject(Error('API unavailable'));
  await screen.findByRole('alert');
  expect(screen.queryByRole('table')).toBeNull();
});

test('replay advances actual snapshots, pauses, and stops at the last snapshot', () => {
  vi.useFakeTimers();
  try {
    const view = render(<Replay result={fixture as SimulationResult}/>);
    fireEvent.click(screen.getByRole('button', { name: 'Play replay' }));
    act(() => vi.advanceTimersByTime(700));
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1');
    fireEvent.click(screen.getByRole('button', { name: 'Pause replay' }));
    act(() => vi.advanceTimersByTime(1400));
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1');
    fireEvent.click(screen.getByRole('button', { name: 'Play replay' }));
    act(() => vi.advanceTimersByTime(3500));
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('4');
    expect(screen.getByRole('button', { name: 'Play replay' })).toBeTruthy();
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  } finally { vi.useRealTimers(); }
});
