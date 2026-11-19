import { HoldoutReplayMatchResponse, HoldoutReplayResponse } from '../types';
import { ApiError } from './predict';

import { API_BASE, apiFetch } from './base';

async function get<T>(path: string, what: string, signal?: AbortSignal): Promise<T> {
  try {
    const res = await apiFetch(`${API_BASE}${path}`, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) throw new ApiError(res.status, what);
    return await res.json();
  } catch (exc) {
    if (exc instanceof ApiError || (exc as Error).name === 'AbortError') throw exc;
    throw new ApiError(0, what);
  }
}

export const fetchHoldoutReplay = (signal?: AbortSignal) =>
  get<HoldoutReplayResponse>('/predict/holdout-replay', 'Couldn’t load the 2026 replay.', signal);

export const fetchHoldoutReplayMatch = (matchId: number, signal?: AbortSignal) =>
  get<HoldoutReplayMatchResponse>(`/predict/holdout-replay/${matchId}`, 'Couldn’t load forecasts for this match.', signal);
