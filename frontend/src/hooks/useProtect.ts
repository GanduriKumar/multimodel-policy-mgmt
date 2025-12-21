import { useState, useCallback, useRef, useEffect } from 'react';
import apiDefault, { type ApiClient } from '../api/client';

export type ProtectPayload = {
  tenant_id: number;
  policy_slug: string;
  input_text: string;
  evidence_types?: string[];
  request_id?: string;
  user_agent?: string;
  client_ip?: string;
  metadata?: Record<string, unknown>;
};

export type ProtectResponse = {
  allowed: boolean;
  reasons: string[];
  risk_score: number;
  request_log_id?: number | null;
  decision_log_id?: number | null;
};

type UseProtectOptions = {
  client?: ApiClient; // optional for testing (inject a mock client)
};

type UseProtectState = {
  loading: boolean;
  error: Error | null;
  data: ProtectResponse | null;
};

export function useProtect(options: UseProtectOptions = {}) {
  const client = options.client ?? apiDefault;

  const [state, setState] = useState<UseProtectState>({
    loading: false,
    error: null,
    data: null,
  });

  // Track mounted state to avoid setting state on unmounted component
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const protect = useCallback(
    async (payload: ProtectPayload): Promise<ProtectResponse> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await client.apiPost<ProtectResponse, ProtectPayload>('/protect', payload);
        if (mountedRef.current) {
          setState({ loading: false, error: null, data: res });
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Request failed'));
        if (mountedRef.current) {
          setState({ loading: false, error: e, data: null });
        }
        throw e;
      }
    },
    [client]
  );

  return {
    protect,
    loading: state.loading,
    error: state.error,
    data: state.data,
  };
}

export default useProtect;