import { MethodologyResponse } from '../types';
import { API_BASE, apiFetch } from './base';
import { ApiError } from './predict';

/** The benchmark, assumption evidence and final-model test behind the prediction tools. */
export async function fetchMethodology(signal?: AbortSignal): Promise<MethodologyResponse> {
  const what = 'Couldn’t load the prediction methodology.';
  try {
    const res = await apiFetch(`${API_BASE}/methodology`, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) throw new ApiError(res.status, what);
    return await res.json();
  } catch (exc) {
    if (exc instanceof ApiError || (exc as Error).name === 'AbortError') throw exc;
    throw new ApiError(0, what);
  }
}
