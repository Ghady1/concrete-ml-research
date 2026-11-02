import type { components } from './api.generated';
export type MixInputs = components['schemas']['MixInputs'];
export type ModeAInputs = components['schemas']['ModeAInputs'];
export type Metadata = components['schemas']['Metadata'];
export type Prediction = components['schemas']['PredictionResponse'];
export type Design = components['schemas']['DesignResponse'];
export type Report = components['schemas']['StrengthReport'];
export type Visuals = components['schemas']['Visuals'];
export type Options = components['schemas']['Options'];
export type Flag = components['schemas']['Flag'];
export class ApiError extends Error {
  constructor(message: string, public fields: { path: string; message: string }[] = []) { super(message); }
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch('/api/v1' + path, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.error?.message || 'The local server could not complete this request.', data.error?.fields || []);
  return data as T;
}
export function download(name: string, content: string | Blob, type = 'application/json') {
  const blob = typeof content === 'string' ? new Blob([content], { type }) : content;
  const href = URL.createObjectURL(blob); const a = document.createElement('a');
  a.href = href; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(href), 1000);
}
export function pretty(value: string) { return value.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase()); }
export function fmt(value: number | null | undefined, digits = 2) {
  return value == null || !Number.isFinite(value) ? 'Unavailable' : value.toLocaleString('en-US', { maximumFractionDigits: digits });
}
