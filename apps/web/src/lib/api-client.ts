import { ApiError, parseApiErrorResponse } from "@/lib/api-error";

/**
 * The only `fetch` call site in the app.
 *
 * Base URL resolution keeps the Phase 7 container fix intact: the server needs
 * the internal `API_URL` (`http://api:8000/api/v1`) for SSR while the browser
 * needs the externally reachable `NEXT_PUBLIC_API_URL`
 * (`http://localhost:8000/api/v1`).
 */
const BROWSER_API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function apiBaseUrl(): string {
  return typeof window === "undefined"
    ? (process.env.API_URL ?? BROWSER_API_BASE)
    : BROWSER_API_BASE;
}

const JSON_HEADERS = { Accept: "application/json" };

async function readErrorBody(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => "");
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      // Submission state must always come from the API, never from a cache.
      cache: "no-store",
      headers: { ...JSON_HEADERS, ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR");
  }
  if (!response.ok) {
    throw parseApiErrorResponse(response.status, await readErrorBody(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return (text ? (JSON.parse(text) as T) : (undefined as T));
}

export function apiJsonRequest<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  return apiRequest<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export function apiUploadRequest<T>(
  path: string,
  file: File,
  field = "file",
): Promise<T> {
  // Content-Type is intentionally omitted: the browser must set the multipart
  // boundary itself.
  const form = new FormData();
  form.append(field, file);
  return apiRequest<T>(path, { method: "POST", body: form });
}
