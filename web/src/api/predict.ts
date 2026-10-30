import {
  BatterPredictionRequest,
  BatterPredictionResponse,
  PredictionModelsResponse,
  PredictionOptionsResponse,
  WicketPredictionRequest,
  WicketPredictionResponse,
} from '../types';

import { API_BASE } from './base';

/** A failed request: HTTP status (0 when the backend could not be reached) and any per-field messages from a 422. */
export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string[]>;
  generalErrors: string[];

  constructor(status: number, message: string, fieldErrors: Record<string, string[]> = {}, generalErrors: string[] = []) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.generalErrors = generalErrors;
  }
}

interface ValidationItem { loc?: (string | number)[]; msg?: string }

/** Reads FastAPI's error body: a list of {loc, msg} (422) or a single detail string. */
async function toApiError(res: Response, what: string): Promise<ApiError> {
  let detail: unknown = null;
  try {
    detail = (await res.json())?.detail;
  } catch {
    // body was not JSON
  }
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string[]> = {};
    const generalErrors: string[] = [];
    (detail as ValidationItem[]).forEach((item) => {
      const msg = item.msg ?? 'Invalid value';
      const loc = item.loc ?? [];
      const field = loc[0] === 'body' && loc.length > 1 ? String(loc[loc.length - 1]) : null;
      if (field) (fieldErrors[field] ??= []).push(msg);
      else generalErrors.push(msg);
    });
    return new ApiError(res.status, `${what}: please correct the highlighted inputs`, fieldErrors, generalErrors);
  }
  const text = typeof detail === 'string' ? detail : `HTTP ${res.status}`;
  return new ApiError(res.status, `${what}: ${text}`);
}

async function request<T>(path: string, what: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.headers ?? {}) } });
  } catch (exc) {
    if ((exc as Error).name === 'AbortError') throw exc;
    throw new ApiError(0, `${what}: the analytical backend could not be reached`);
  }
  if (!res.ok) throw await toApiError(res, what);
  return res.json();
}

export const fetchPredictOptions = (signal?: AbortSignal) =>
  request<PredictionOptionsResponse>('/predict/options', 'Could not load prediction inputs', { signal });

export const fetchPredictModels = (signal?: AbortSignal) =>
  request<PredictionModelsResponse>('/predict/models', 'Could not load model evaluation', { signal });

const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json' },
  signal,
});

export const predictWicket = (body: WicketPredictionRequest, signal?: AbortSignal) =>
  request<WicketPredictionResponse>('/predict/wicket', 'Wicket prediction failed', post(body, signal));

export const predictBatter = (body: BatterPredictionRequest, signal?: AbortSignal) =>
  request<BatterPredictionResponse>('/predict/batter', 'Batter prediction failed', post(body, signal));
