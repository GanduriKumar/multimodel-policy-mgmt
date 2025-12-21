/**
 * Minimal API client for the frontend.
 *
 * - Reads base URL and API key from Vite env (VITE_API_BASE_URL, VITE_API_KEY)
 * - Exposes helper methods: apiGet and apiPost
 * - Allows injecting a custom fetch implementation for unit testing
 */

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface ApiClient {
  apiGet<T = unknown>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T>;
  apiPost<T = unknown, B = unknown>(path: string, body?: B): Promise<T>;
}

interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  fetchFn?: FetchLike;
  apiKeyHeader?: string; // default: 'x-api-key'
}

// Read defaults from Vite environment
const ENV = (import.meta as any).env ?? {};
const DEFAULT_BASE_URL: string | undefined = ENV.VITE_API_BASE_URL;
const DEFAULT_API_KEY: string | undefined = ENV.VITE_API_KEY;

function buildUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function buildQuery(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue;
    usp.append(k, String(v));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

async function handleResponse<T>(res: Response): Promise<T> {
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  const data = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined);
  if (!res.ok) {
    const err: any = new Error((data && (data.message || data.error?.message)) || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return (data as T) ?? (undefined as unknown as T);
}

export function createApiClient(options: ClientOptions = {}): ApiClient {
  const baseUrl = options.baseUrl || DEFAULT_BASE_URL || "";
  const apiKey = options.apiKey || DEFAULT_API_KEY;
  const apiKeyHeader = options.apiKeyHeader || "x-api-key";
  const fetchFn: FetchLike = options.fetchFn || (globalThis.fetch as FetchLike);

  if (!baseUrl) {
    // Friendly error to catch misconfiguration early in dev
    // Do not throw in module scope to keep tests flexible
    // eslint-disable-next-line no-console
    console.warn("API base URL is not configured. Set VITE_API_BASE_URL in your env.");
  }

  // Shared headers
  const defaultHeaders: Record<string, string> = {
    Accept: "application/json",
  };
  if (apiKey) {
    defaultHeaders[apiKeyHeader] = apiKey;
  }

  // GET helper
  async function apiGet<T = unknown>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    const url = buildUrl(baseUrl, path) + buildQuery(params);
    const res = await fetchFn(url, {
      method: "GET",
      headers: defaultHeaders,
      credentials: "include",
    });
    return handleResponse<T>(res);
  }

  // POST helper
  async function apiPost<T = unknown, B = unknown>(path: string, body?: B): Promise<T> {
    const url = buildUrl(baseUrl, path);
    const headers: Record<string, string> = {
      ...defaultHeaders,
      "Content-Type": "application/json",
    };
    const res = await fetchFn(url, {
      method: "POST",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
    });
    return handleResponse<T>(res);
  }

  return { apiGet, apiPost };
}

// Default client instance for app usage
export const api = createApiClient();
export default api;
