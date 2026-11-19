import {
  BatterPredictionRequest,
  BatterPredictionResponse,
  PredictionModelsResponse,
  PredictionOptionsResponse,
  WicketPredictionRequest,
  WicketPredictionResponse,
} from '../types';

import { API_BASE, apiFetch } from './base';

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

/** Keeps input feedback from 422 responses and uses a public message for other failures. */
async function toApiError(res: Response, what: string): Promise<ApiError> {
  if (res.status !== 422) return new ApiError(res.status, what);
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
    return new ApiError(res.status, what, fieldErrors, generalErrors);
  }
  return new ApiError(res.status, what, {}, ['Check the prediction inputs and try again.']);
}

async function request<T>(path: string, what: string, init?: RequestInit): Promise<T> {
  try {
    const res = await apiFetch(`${API_BASE}${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.headers ?? {}) } });
    if (!res.ok) throw await toApiError(res, what);
    return await res.json();
  } catch (exc) {
    if (exc instanceof ApiError || (exc as Error).name === 'AbortError') throw exc;
    throw new ApiError(0, what);
  }
}

export const fetchPredictOptions = (signal?: AbortSignal) =>
  request<PredictionOptionsResponse>('/predict/options', 'Couldn’t load the prediction tools.', { signal });

export const fetchPredictModels = (signal?: AbortSignal) =>
  request<PredictionModelsResponse>('/predict/models', 'Couldn’t load the model evaluation.', { signal });

const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json' },
  signal,
});

export const predictWicket = (body: WicketPredictionRequest, signal?: AbortSignal) =>
  request<WicketPredictionResponse>('/predict/wicket', 'Couldn’t calculate wicket risk.', post(body, signal));

export const predictBatter = (body: BatterPredictionRequest, signal?: AbortSignal) =>
  request<BatterPredictionResponse>('/predict/batter', 'Couldn’t calculate batter milestones.', post(body, signal));
