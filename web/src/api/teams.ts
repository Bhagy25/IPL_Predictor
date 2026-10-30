import { TeamListResponse, TeamOverviewResponse, TeamVenueResponse, HeadToHeadResponse } from '../types';

import { API_BASE, apiFetch } from './base';

export async function fetchTeams(signal?: AbortSignal): Promise<TeamListResponse> {
  const res = await apiFetch(`${API_BASE}/teams`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch teams: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchTeamOverview(teamId: string, season?: number, signal?: AbortSignal): Promise<TeamOverviewResponse> {
  const url = season 
    ? `${API_BASE}/teams/${encodeURIComponent(teamId)}/overview?season=${season}`
    : `${API_BASE}/teams/${encodeURIComponent(teamId)}/overview`;
  const res = await apiFetch(url, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview for team '${teamId}': HTTP ${res.status}`);
  }
  return res.json();
}

// minMatches: venues with at least this many matches in the selection (1 = every venue)
export async function fetchTeamVenues(teamId: string, season: number | undefined, minMatches: number, signal?: AbortSignal): Promise<TeamVenueResponse> {
  const params = new URLSearchParams({ min_matches: String(minMatches) });
  if (season) params.set('season', String(season));
  const res = await apiFetch(`${API_BASE}/teams/${encodeURIComponent(teamId)}/venues?${params.toString()}`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch venues for team '${teamId}': HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchHeadToHead(team1: string, team2: string, season?: number, signal?: AbortSignal): Promise<HeadToHeadResponse> {
  const params = new URLSearchParams({ team1, team2 });
  if (season) params.set('season', String(season));
  const res = await apiFetch(`${API_BASE}/teams/head-to-head?${params.toString()}`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch head-to-head for ${team1} vs ${team2}: HTTP ${res.status}`);
  }
  return res.json();
}
