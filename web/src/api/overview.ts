import { OverviewSummaryResponse, OverviewChartsResponse } from '../types';

import { API_BASE, apiFetch } from './base';

export interface HealthResponse {
  status: string;
  version: string;
  archive_matches: number | null;
  timestamp: string;
  service: string;
  derived_tables?: { available: boolean; detail: string; build_command?: string } | null;
  // Extent of the loaded archive, counted by the API; null when the data failed to load
  archive?: {
    matches: number;
    seasons: number;
    first_season: number;
    last_season: number;
    first_match_date: string;
    last_match_date: string;
  } | null;
  prediction_models?: Record<string, { available: boolean; detail: string }> | null;
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await apiFetch(`${API_BASE}/health`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchOverviewSummary(signal?: AbortSignal): Promise<OverviewSummaryResponse> {
  const res = await apiFetch(`${API_BASE}/overview/summary`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview summary: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchOverviewCharts(signal?: AbortSignal): Promise<OverviewChartsResponse> {
  const res = await apiFetch(`${API_BASE}/overview/charts`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview charts: HTTP ${res.status}`);
  }
  return res.json();
}
