import {
  EDAAnalysisResponse,
  EDACatalogResponse,
  EDAFilterOptionsResponse,
  EDAPlayerComparisonResponse,
  EDASummaryResponse,
} from '../types';

import { API_BASE, apiFetch } from './base';

/** Query values for the full-history analysis; undefined values are left to the API defaults. */
export interface EDAQuery {
  season_from?: number;
  season_to?: number;
  team?: string;
  venue?: string;
  venue_min_matches?: number;
  bat_min_balls?: number;
  bowl_min_balls?: number;
}

const queryString = (params: Record<string, string | number | undefined>): string => {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : '';
};

async function getJSON<T>(url: string, what: string, signal?: AbortSignal): Promise<T> {
  const res = await apiFetch(url, { signal, headers: { 'Accept': 'application/json' } });
  if (!res.ok) {
    // The API explains invalid filters (422) in `detail`
    const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
    throw new Error(detail ? `${what}: ${detail}` : `Failed to fetch ${what}: HTTP ${res.status}`);
  }
  return res.json();
}

export function fetchEDAFilters(signal?: AbortSignal): Promise<EDAFilterOptionsResponse> {
  return getJSON(`${API_BASE}/eda/filters`, 'EDA filter options', signal);
}

export function fetchEDAAnalysis(query: EDAQuery, signal?: AbortSignal): Promise<EDAAnalysisResponse> {
  return getJSON(`${API_BASE}/eda/analysis${queryString({ ...query })}`, 'full-history analysis', signal);
}

export function fetchPlayerComparison(
  players: string[],
  query: Pick<EDAQuery, 'season_from' | 'season_to' | 'team' | 'venue'>,
  signal?: AbortSignal,
): Promise<EDAPlayerComparisonResponse> {
  return getJSON(
    `${API_BASE}/eda/player-comparison${queryString({ players: players.join(','), ...query })}`,
    'player comparison',
    signal,
  );
}

export function fetchEDACatalog(signal?: AbortSignal): Promise<EDACatalogResponse> {
  return getJSON(`${API_BASE}/eda/catalog`, 'EDA catalog', signal);
}

export function fetchEDASummary(signal?: AbortSignal): Promise<EDASummaryResponse> {
  return getJSON(`${API_BASE}/eda/summary`, 'EDA summary tables', signal);
}
