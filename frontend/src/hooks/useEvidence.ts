import { useState, useCallback, useEffect, useRef } from 'react';
import apiDefault, { type ApiClient } from '../api/client';

// Types aligned with backend Evidence schemas
export type EvidenceCreate = {
  evidence_type: string;
  policy_id?: number | null;
  policy_version_id?: number | null;
  source?: string | null;
  description?: string | null;
  content?: string | null; // used to compute content hash
  metadata?: Record<string, unknown> | null;
};

export type EvidenceOut = {
  id: number;
  tenant_id: number;
  policy_id?: number | null;
  policy_version_id?: number | null;
  evidence_type: string;
  source?: string | null;
  description?: string | null;
  content_hash?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string; // ISO date
  updated_at: string; // ISO date
};

type UseEvidenceState = {
  loading: boolean;
  error: Error | null;
  item: EvidenceOut | null; // last created/fetched evidence
};

export function useEvidence(client: ApiClient = apiDefault) {
  const [state, setState] = useState<UseEvidenceState>({ loading: false, error: null, item: null });

  // Avoid setState on unmounted component
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const ingestEvidence = useCallback(
    async (tenantId: number, payload: EvidenceCreate): Promise<EvidenceOut> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        // Pass tenant id via query string per backend route contract
        const res = await client.apiPost<EvidenceOut, EvidenceCreate>(`/evidence?tenant_id=${tenantId}`, payload);
        if (mountedRef.current) {
          setState({ loading: false, error: null, item: res });
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to ingest evidence'));
        if (mountedRef.current) setState({ loading: false, error: e, item: null });
        throw e;
      }
    },
    [client]
  );

  const fetchEvidence = useCallback(
    async (evidenceId: number): Promise<EvidenceOut> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await client.apiGet<EvidenceOut>(`/evidence/${evidenceId}`);
        if (mountedRef.current) {
          setState({ loading: false, error: null, item: res });
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to fetch evidence'));
        if (mountedRef.current) setState({ loading: false, error: e, item: null });
        throw e;
      }
    },
    [client]
  );

  const resetError = useCallback(() => setState((s) => ({ ...s, error: null })), []);

  return {
    ingestEvidence,
    fetchEvidence,
    loading: state.loading,
    error: state.error,
    item: state.item,
    resetError,
  };
}

export default useEvidence;
