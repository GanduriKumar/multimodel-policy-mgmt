import { useState, useCallback, useEffect, useRef } from 'react';
import apiDefault, { type ApiClient } from '../api/client';

// Types aligned with backend schemas (lightweight)
export type PolicyOut = {
  id: number;
  tenant_id: number;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
  created_at: string; // ISO string
  updated_at: string; // ISO string
};

export type PolicyVersionOut = {
  id: number;
  policy_id: number;
  version: number;
  document: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type PolicyListResponse = {
  items: PolicyOut[];
  total: number;
};

export type CreatePolicyPayload = {
  tenant_id: number;
  name: string;
  slug: string;
  description?: string | null;
  is_active?: boolean;
};

export function usePolicies(client: ApiClient = apiDefault) {
  const [items, setItems] = useState<PolicyOut[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const listPolicies = useCallback(
    async (tenantId: number, opts?: { offset?: number; limit?: number }) => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          tenant_id: tenantId,
          offset: opts?.offset ?? 0,
          limit: opts?.limit ?? 50,
        } as const;
        const res = await client.apiGet<PolicyListResponse>('/policies', params as any);
        if (mountedRef.current) {
          setItems(res.items || []);
          setTotal(typeof res.total === 'number' ? res.total : (res.items?.length ?? 0));
          setLoading(false);
        }
        return res;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to list policies'));
        if (mountedRef.current) {
          setError(e);
          setLoading(false);
        }
        throw e;
      }
    },
    [client]
  );

  const createPolicy = useCallback(
    async (payload: CreatePolicyPayload) => {
      setError(null);
      try {
        const created = await client.apiPost<PolicyOut, CreatePolicyPayload>('/policies', payload);
        if (mountedRef.current) {
          // Optimistically insert into list
          setItems((prev) => [created, ...prev]);
          setTotal((t) => t + 1);
        }
        return created;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to create policy'));
        if (mountedRef.current) setError(e);
        throw e;
      }
    },
    [client]
  );

  const addVersion = useCallback(
    async (policyId: number, document: Record<string, unknown>, is_active: boolean = true) => {
      setError(null);
      try {
        const body = { policy_id: policyId, document, is_active };
        const pv = await client.apiPost<PolicyVersionOut, typeof body>(`/policies/${policyId}/versions`, body);
        return pv;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to add version'));
        if (mountedRef.current) setError(e);
        throw e;
      }
    },
    [client]
  );

  const activateVersion = useCallback(
    async (policyId: number, version: number) => {
      setError(null);
      try {
        const pv = await client.apiPost<PolicyVersionOut, undefined>(`/policies/${policyId}/versions/${version}/activate`);
        return pv;
      } catch (err: any) {
        const e = err instanceof Error ? err : new Error(String(err?.message ?? 'Failed to activate version'));
        if (mountedRef.current) setError(e);
        throw e;
      }
    },
    [client]
  );

  const resetError = useCallback(() => setError(null), []);

  return {
    // state
    items,
    total,
    loading,
    error,
    // actions
    listPolicies,
    createPolicy,
    addVersion,
    activateVersion,
    resetError,
  };
}

export default usePolicies;
