import { OverviewSummaryResponse, OverviewChartsResponse } from '../types';

const API_BASE = '/api';

export interface HealthResponse {
  status: string;
  version: string;
  archive_matches: number;
  timestamp: string;
  service: string;
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchOverviewSummary(signal?: AbortSignal): Promise<OverviewSummaryResponse> {
  const res = await fetch(`${API_BASE}/overview/summary`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview summary: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchOverviewCharts(signal?: AbortSignal): Promise<OverviewChartsResponse> {
  const res = await fetch(`${API_BASE}/overview/charts`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview charts: HTTP ${res.status}`);
  }
  return res.json();
}
