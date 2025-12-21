import { describe, it, expect, vi, beforeEach } from 'vitest';

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function setViteEnv(baseUrl: string, apiKey: string) {
  // Mutate import.meta.env before importing the client module
  const env: any = (import.meta as any).env || {};
  (import.meta as any).env = {
    ...env,
    VITE_API_BASE_URL: baseUrl,
    VITE_API_KEY: apiKey,
  };
}

describe('frontend/src/api/client', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('constructs URL using VITE_API_BASE_URL and attaches API key header (GET)', async () => {
    setViteEnv('http://localhost:9999/api', 'abc123');

    const calls: Array<{ input: any; init: any }> = [];
    const mockFetch: FetchLike = vi.fn(async (input: any, init?: any) => {
      calls.push({ input, init });
      return {
        ok: true,
        status: 200,
        headers: {
          get: (k: string) => (k.toLowerCase() === 'content-type' ? 'application/json' : null),
        } as any,
        json: async () => ({ ok: true }),
        text: async () => JSON.stringify({ ok: true }),
      } as Response;
    });

    // Dynamically import after setting env so defaults are picked up
    const mod = await import('./client');
    const client = mod.createApiClient({ fetchFn: mockFetch });

    const result = await client.apiGet<{ ok: boolean }>('/test', { q: 'x', n: 5 });
    expect(result).toEqual({ ok: true });

    expect(calls.length).toBe(1);
    const { input, init } = calls[0];
    expect(input).toBe('http://localhost:9999/api/test?q=x&n=5');
    expect(init?.method).toBe('GET');
    // Headers
    const headers = init?.headers as Record<string, string>;
    expect(headers['Accept']).toBe('application/json');
    expect(headers['x-api-key']).toBe('abc123');
  });

  it('sends JSON body and parses JSON response (POST)', async () => {
    setViteEnv('https://api.example.com/v1', 'k_456');

    const calls: Array<{ input: any; init: any }> = [];
    const mockFetch: FetchLike = vi.fn(async (input: any, init?: any) => {
      calls.push({ input, init });
      // Echo back a JSON payload
      return {
        ok: true,
        status: 200,
        headers: {
          get: (k: string) => (k.toLowerCase() === 'content-type' ? 'application/json' : null),
        } as any,
        json: async () => ({ id: 42, status: 'created' }),
        text: async () => JSON.stringify({ id: 42, status: 'created' }),
      } as Response;
    });

    const { createApiClient } = await import('./client');
    const client = createApiClient({ fetchFn: mockFetch });

    const payload = { name: 'Item', count: 2 };
    const res = await client.apiPost<{ id: number; status: string }, typeof payload>('/items', payload);
    expect(res).toEqual({ id: 42, status: 'created' });

    expect(calls.length).toBe(1);
    const { input, init } = calls[0];
    expect(input).toBe('https://api.example.com/v1/items');
    expect(init?.method).toBe('POST');

    const headers = init?.headers as Record<string, string>;
    expect(headers['Accept']).toBe('application/json');
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers['x-api-key']).toBe('k_456');

    expect(init?.body).toBe(JSON.stringify(payload));
  });

  it('surfaces HTTP errors with status and data', async () => {
    setViteEnv('http://localhost:3000/api', 'zzz');

    const mockFetch: FetchLike = vi.fn(async () => {
      return {
        ok: false,
        status: 404,
        headers: {
          get: (k: string) => (k.toLowerCase() === 'content-type' ? 'application/json' : null),
        } as any,
        json: async () => ({ error: { message: 'Not found' } }),
        text: async () => JSON.stringify({ error: { message: 'Not found' } }),
      } as Response;
    });

    const { createApiClient } = await import('./client');
    const client = createApiClient({ fetchFn: mockFetch });

    try {
      await client.apiGet('/missing');
      throw new Error('Expected to throw');
    } catch (err: any) {
      expect(err).toBeTruthy();
      expect(err.status).toBe(404);
      expect(err.data).toEqual({ error: { message: 'Not found' } });
      expect(String(err.message)).toContain('Not found');
    }
  });
});