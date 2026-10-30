import { HoldoutReplayMatchResponse, HoldoutReplayResponse } from '../types';
import { ApiError } from './predict';

import { API_BASE, apiFetch } from './base';

async function get<T>(path: string, what: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await apiFetch(`${API_BASE}${path}`, { signal, headers: { Accept: 'application/json' } });
  } catch (exc) {
    if ((exc as Error).name === 'AbortError') throw exc;
    throw new ApiError(0, `${what}: the analytical backend could not be reached`);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // body was not JSON
    }
    throw new ApiError(res.status, `${what}: ${detail}`);
  }
  return res.json();
}

export const fetchHoldoutReplay = (signal?: AbortSignal) =>
  get<HoldoutReplayResponse>('/predict/holdout-replay', 'Could not load the 2026 holdout replay', signal);

export const fetchHoldoutReplayMatch = (matchId: number, signal?: AbortSignal) =>
  get<HoldoutReplayMatchResponse>(`/predict/holdout-replay/${matchId}`, `Could not load match ${matchId}`, signal);
