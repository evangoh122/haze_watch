/**
 * Typed fetch wrapper for the backend API.
 *
 * Defaults to the same-origin `/api/v1` path so the app works from any host
 * (dev proxy and Docker/SPA hosting) instead of pointing at the viewer's own
 * machine. Set VITE_API_BASE_URL only for cross-origin backends.
 *
 * All commercial/financial payloads are synthetic and carry `synthetic: true`.
 * See docs/api-contract.md for the planned contract.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`);
  }
  return (await response.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`);
  }
  return (await response.json()) as T;
}
