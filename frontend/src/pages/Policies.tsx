import React, { useCallback, useMemo, useState } from 'react';
import usePolicies, { type PolicyOut, type PolicyVersionOut, type CreatePolicyPayload } from '../hooks/usePolicies';

const Policies: React.FC = () => {
  const { items, total, loading, error, listPolicies, createPolicy, addVersion, activateVersion, resetError } = usePolicies();

  // Tenant selector
  const [tenantId, setTenantId] = useState<number>(1);

  // Create policy form
  const [name, setName] = useState<string>('');
  const [slug, setSlug] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [isActive, setIsActive] = useState<boolean>(true);
  const [creating, setCreating] = useState<boolean>(false);

  // Per-policy UI state for versioning and activation
  type RowState = {
    docText: string;
    isActive: boolean;
    activateInput: string;
    busy: boolean;
    error: string | null;
    lastVersion?: PolicyVersionOut | null;
  };
  const [rowState, setRowState] = useState<Record<number, RowState>>({});

  const getRow = useCallback(
    (policyId: number): RowState =>
      rowState[policyId] ?? {
        docText: '{"risk_threshold": 80}',
        isActive: true,
        activateInput: '',
        busy: false,
        error: null,
        lastVersion: undefined,
      },
    [rowState]
  );

  const setRow = useCallback((policyId: number, partial: Partial<RowState>) => {
    setRowState((prev) => ({ ...prev, [policyId]: { ...getRow(policyId), ...partial } }));
  }, [getRow]);

  const onLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    await listPolicies(tenantId, { offset: 0, limit: 50 });
  };

  const onCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    setCreating(true);
    try {
      const payload: CreatePolicyPayload = {
        tenant_id: tenantId,
        name: name.trim(),
        slug: slug.trim(),
        description: description.trim() || null,
        is_active: isActive,
      };
      await createPolicy(payload);
      setName('');
      setSlug('');
      setDescription('');
      setIsActive(true);
    } catch {
      // error handled via hook
    } finally {
      setCreating(false);
    }
  };

  const parseJson = (text: string): Record<string, unknown> => {
    try {
      return JSON.parse(text);
    } catch (e: any) {
      throw new Error(`Invalid JSON: ${e?.message ?? 'parse error'}`);
    }
  };

  const onAddVersion = async (policy: PolicyOut) => {
    resetError();
    const rs = getRow(policy.id);
    setRow(policy.id, { busy: true, error: null });
    try {
      const document = parseJson(rs.docText);
      const pv = await addVersion(policy.id, document, rs.isActive);
      setRow(policy.id, { lastVersion: pv, busy: false });
    } catch (e: any) {
      setRow(policy.id, { busy: false, error: e?.message ?? 'Failed to add version' });
    }
  };

  const onActivateVersion = async (policy: PolicyOut) => {
    resetError();
    const rs = getRow(policy.id);
    const versionNum = Number(rs.activateInput);
    if (!versionNum || versionNum < 1) {
      setRow(policy.id, { error: 'Enter a valid version number (>= 1)' });
      return;
    }
    setRow(policy.id, { busy: true, error: null });
    try {
      const pv = await activateVersion(policy.id, versionNum);
      setRow(policy.id, { busy: false, lastVersion: pv });
    } catch (e: any) {
      setRow(policy.id, { busy: false, error: e?.message ?? 'Failed to activate version' });
    }
  };

  const fmt = (iso?: string) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return isNaN(d.getTime()) ? iso : d.toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h1 className="mb-0">Policies</h1>
        <a className="btn btn-outline-secondary" href="/">Home</a>
      </div>

      {/* Tenant & load */}
      <section className="mb-4">
        <form onSubmit={onLoad} className="row g-3 align-items-end">
          <div className="col-sm-3">
            <label htmlFor="tenantId" className="form-label">Tenant ID</label>
            <input
              id="tenantId"
              type="number"
              min={1}
              className="form-control"
              value={tenantId}
              onChange={(e) => setTenantId(Number(e.target.value))}
            />
          </div>
          <div className="col-sm-3">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Loading…' : 'Load Policies'}
            </button>
          </div>
        </form>
      </section>

      {/* Create policy */}
      <section className="mb-4">
        <div className="card">
          <div className="card-header">Create Policy</div>
          <div className="card-body">
            <form onSubmit={onCreatePolicy} className="row g-3">
              <div className="col-md-3">
                <label htmlFor="name" className="form-label">Name</label>
                <input id="name" className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="col-md-3">
                <label htmlFor="slug" className="form-label">Slug</label>
                <input id="slug" className="form-control" value={slug} onChange={(e) => setSlug(e.target.value)} required />
              </div>
              <div className="col-md-4">
                <label htmlFor="desc" className="form-label">Description</label>
                <input id="desc" className="form-control" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
              <div className="col-md-2 d-flex align-items-center">
                <div className="form-check mt-3">
                  <input id="active" type="checkbox" className="form-check-input" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
                  <label htmlFor="active" className="form-check-label">Active</label>
                </div>
              </div>
              <div className="col-12">
                <button className="btn btn-success" disabled={creating}>
                  {creating ? 'Creating…' : 'Create Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {error && (
        <div className="alert alert-danger" role="alert">
          <strong>Error:</strong> {error.message}
        </div>
      )}

      {/* Policies table */}
      <section>
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="mb-0">Policies</h5>
          <small className="text-muted">Total: {total}</small>
        </div>
        {items.length === 0 ? (
          <div className="text-muted">No policies loaded. Use "Load Policies" to fetch for the selected tenant.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name / Slug</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ width: 450 }}>Versioning</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => {
                  const rs = getRow(p.id);
                  return (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>
                        <div className="fw-semibold">{p.name}</div>
                        <code>{p.slug}</code>
                        {p.description ? <div className="text-muted small mt-1">{p.description}</div> : null}
                      </td>
                      <td>
                        {p.is_active ? (
                          <span className="badge bg-success">active</span>
                        ) : (
                          <span className="badge bg-secondary">inactive</span>
                        )}
                      </td>
                      <td>{fmt(p.created_at)}</td>
                      <td>
                        <div className="row g-2">
                          <div className="col-7">
                            <input
                              className="form-control form-control-sm"
                              placeholder='Version JSON e.g. {"risk_threshold":75}'
                              value={rs.docText}
                              onChange={(e) => setRow(p.id, { docText: e.target.value })}
                            />
                          </div>
                          <div className="col-2 d-flex align-items-center">
                            <div className="form-check">
                              <input
                                id={`act-${p.id}`}
                                type="checkbox"
                                className="form-check-input"
                                checked={rs.isActive}
                                onChange={(e) => setRow(p.id, { isActive: e.target.checked })}
                              />
                              <label htmlFor={`act-${p.id}`} className="form-check-label small">
                                Active
                              </label>
                            </div>
                          </div>
                          <div className="col-3 d-grid">
                            <button
                              className="btn btn-sm btn-outline-primary"
                              disabled={rs.busy}
                              onClick={() => onAddVersion(p)}
                              type="button"
                            >
                              {rs.busy ? 'Adding…' : 'Add Version'}
                            </button>
                          </div>

                          <div className="col-6">
                            <input
                              className="form-control form-control-sm"
                              placeholder="Version # to activate"
                              value={rs.activateInput}
                              onChange={(e) => setRow(p.id, { activateInput: e.target.value })}
                            />
                          </div>
                          <div className="col-3 d-grid">
                            <button
                              className="btn btn-sm btn-outline-success"
                              disabled={rs.busy}
                              onClick={() => onActivateVersion(p)}
                              type="button"
                            >
                              {rs.busy ? 'Activating…' : 'Activate'}
                            </button>
                          </div>
                          <div className="col-12">
                            {rs.error && <div className="text-danger small">{rs.error}</div>}
                            {rs.lastVersion && (
                              <div className="text-muted small">
                                Last version: v{rs.lastVersion.version} ({rs.lastVersion.is_active ? 'active' : 'inactive'})
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Policies;