import { EDACatalogResponse, EDASummaryResponse, EDAFullHistoryResponse } from '../types';

const API_BASE = '/api';

export async function fetchEDAFullHistory(signal?: AbortSignal): Promise<EDAFullHistoryResponse> {
  const res = await fetch(`${API_BASE}/eda/full-history`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch full-history EDA: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchEDACatalog(signal?: AbortSignal): Promise<EDACatalogResponse> {
  const res = await fetch(`${API_BASE}/eda/catalog`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch EDA catalog: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchEDASummary(signal?: AbortSignal): Promise<EDASummaryResponse> {
  const res = await fetch(`${API_BASE}/eda/summary`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch EDA summary tables: HTTP ${res.status}`);
  }
  return res.json();
}
