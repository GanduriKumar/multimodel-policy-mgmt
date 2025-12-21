import { useCallback, useEffect, useRef, useState } from 'react';
import apiDefault, { type ApiClient } from '../api/client';

export type AuditListRow = {
  request_log_id: number;
  tenant_id: number;
  decision_id?: number | null;
  decision?: boolean | null;
  risk_score?: number | null;
  created_at: string; // ISO date
};

export type AuditListResponse = {
  items: AuditListRow[];
  total: number;
};

export type DecisionDetail = {
  decision_id: number;
  request_log_id: number;
  tenant_id: number;
  allowed: boolean;
  risk_score?: number | null;
  policy_id?: number | null;
  policy_version_id?: number | null;
  policy_reasons: string[];
  risk_reasons: string[];
  evidence_ids: number[];
  created_at: string;
};

type UseAuditState = {
  list: AuditListRow[];
  total: number;
  loading: boolean;
  error: Error | null;
  detail: DecisionDetail | null;
};

export function useAudit(client: ApiClient = apiDefault) {
  const [state, setState] = useState<UseAuditState>({
    list: [],
    total: 0,
    loading: false,
    error: null,
    detail: null,
  });

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const listRequests = useCallback(
    async (tenantId: number, opts?: { offset?: number; limit?: number }) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await client.apiGet<AuditListResponse>('/audit/requests', {
          tenant_id: tenantId,
          offset: opts?.offset ?? 0,
          limit: opts?.limit ?? 50,
        });
        if (mountedRef.current) {
          setState((s) => ({
            ...s,
            list: res.items ?? [],
            total: typeof res.total === 'number' ? res.total : (res.items?.length ?? 0),
            loading: false,
          }));
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to list audit requests'));
        if (mountedRef.current) setState((s) => ({ ...s, loading: false, error: e }));
        throw e;
      }
    },
    [client]
  );

  const getDecisionDetail = useCallback(
    async (decisionIdOrRequestId: number) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await client.apiGet<DecisionDetail>(`/audit/decisions/${decisionIdOrRequestId}`);
        if (mountedRef.current) {
          setState((s) => ({ ...s, detail: res, loading: false }));
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to fetch decision detail'));
        if (mountedRef.current) setState((s) => ({ ...s, loading: false, error: e }));
        throw e;
      }
    },
    [client]
  );

  const resetError = useCallback(() => setState((s) => ({ ...s, error: null })), []);

  return {
    // state
    list: state.list,
    total: state.total,
    loading: state.loading,
    error: state.error,
    detail: state.detail,
    // actions
    listRequests,
    getDecisionDetail,
    resetError,
  };
}

export default useAudit;