import { PlayerListResponse, PlayerProfileResponse } from '../types';

const API_BASE = '/api';

export interface PlayerSearchParams {
  query?: string;
  role?: string;
  experience_filter?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export async function fetchPlayers(
  params?: PlayerSearchParams,
  signal?: AbortSignal
): Promise<PlayerListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.query) queryParams.set('query', params.query);
  if (params?.role) queryParams.set('role', params.role);
  if (params?.experience_filter) queryParams.set('experience_filter', params.experience_filter);
  if (params?.page) queryParams.set('page', params.page.toString());
  if (params?.page_size) queryParams.set('page_size', params.page_size.toString());
  if (params?.sort_by) queryParams.set('sort_by', params.sort_by);

  const url = `${API_BASE}/players?${queryParams.toString()}`;
  const res = await fetch(url, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch players: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchPlayerOverview(
  playerId: string,
  signal?: AbortSignal
): Promise<PlayerProfileResponse> {
  const res = await fetch(`${API_BASE}/players/${encodeURIComponent(playerId)}/overview`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch profile for player '${playerId}': HTTP ${res.status}`);
  }
  return res.json();
}
