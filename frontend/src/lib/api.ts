/**
 * Typed fetch wrapper for the backend API.
 *
 * Derived from the Vite base so the same build works at the root and under a
 * path prefix (e.g. served at /haze-watch/, the API is /haze-watch/api/v1).
 * Set VITE_API_BASE_URL only for a cross-origin backend.
 *
 * All commercial/financial payloads are synthetic and carry `synthetic: true`.
 * See docs/api-contract.md for the planned contract.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? `${import.meta.env.BASE_URL}api/v1`;

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
