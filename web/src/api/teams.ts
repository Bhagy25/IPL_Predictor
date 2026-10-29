import { TeamListResponse, TeamOverviewResponse, HeadToHeadResponse } from '../types';

const API_BASE = '/api';

export async function fetchTeams(signal?: AbortSignal): Promise<TeamListResponse> {
  const res = await fetch(`${API_BASE}/teams`, {
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
  const res = await fetch(url, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch overview for team '${teamId}': HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchHeadToHead(team1: string, team2: string, signal?: AbortSignal): Promise<HeadToHeadResponse> {
  const params = new URLSearchParams({ team1, team2 });
  const res = await fetch(`${API_BASE}/teams/head-to-head?${params.toString()}`, {
    signal,
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch head-to-head for ${team1} vs ${team2}: HTTP ${res.status}`);
  }
  return res.json();
}
