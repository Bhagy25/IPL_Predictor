import { PlayerListResponse, PlayerMatchLogResponse, PlayerProfileResponse } from '../types';

const API_BASE = '/api';

export interface PlayerSearchParams {
  query?: string;
  role?: string;
  experience_filter?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  min_innings?: number | null;
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
  if (params?.min_innings) queryParams.set('min_innings', params.min_innings.toString());

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

// season: every number in the profile is computed for that season only; omit for the full career
export async function fetchPlayerOverview(
  playerId: string,
  season?: number | null,
  signal?: AbortSignal
): Promise<PlayerProfileResponse> {
  const query = season != null ? `?season=${season}` : '';
  const res = await fetch(`${API_BASE}/players/${encodeURIComponent(playerId)}/overview${query}`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch profile for player '${playerId}': HTTP ${res.status}`);
  }
  return res.json();
}

export interface PlayerMatchesParams {
  season?: number | null;
  page?: number;
  page_size?: number;
}

export async function fetchPlayerMatches(
  playerId: string,
  params?: PlayerMatchesParams,
  signal?: AbortSignal
): Promise<PlayerMatchLogResponse> {
  const queryParams = new URLSearchParams();
  if (params?.season != null) queryParams.set('season', params.season.toString());
  if (params?.page) queryParams.set('page', params.page.toString());
  if (params?.page_size) queryParams.set('page_size', params.page_size.toString());

  const res = await fetch(`${API_BASE}/players/${encodeURIComponent(playerId)}/matches?${queryParams.toString()}`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch match log for player '${playerId}': HTTP ${res.status}`);
  }
  return res.json();
}
