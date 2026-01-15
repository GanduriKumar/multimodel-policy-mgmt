import React, { useCallback, useEffect, useState } from 'react';
import usePolicies, { type PolicyOut, type PolicyVersionOut, type CreatePolicyPayload } from '../hooks/usePolicies';

const Policies: React.FC = () => {
  const { items, total, loading, error, listPolicies, createPolicy, addVersion, activateVersion, getActiveVersion, listVersions, deletePolicy, resetError } = usePolicies();

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
  const [selectedJson, setSelectedJson] = useState<{
    policyId: number;
    jsonText: string;
    activeVersion: number | null;
    busy: boolean;
    error: string | null;
    lastSaved?: number | null;
  } | null>(null);

  // Compare versions panel state
  const [comparePanel, setComparePanel] = useState<{
    open: boolean;
    policyId: number | null;
    versions: PolicyVersionOut[];
    leftVersion?: number;
    rightVersion?: number;
    diff?: string;
    busy: boolean;
    error: string | null;
  }>({ open: false, policyId: null, versions: [], busy: false, error: null });

  const getRow = useCallback(
    (policyId: number): RowState =>
      rowState[policyId] ?? {
        docText: JSON.stringify({
          blocked_terms: [],
          allowed_sources: [],
          required_evidence_types: [],
          pii_rules: {
            deny_when_any_pii: false,
            deny_on_email: false,
            deny_on_phone: false,
            deny_on_ssn: false,
            deny_on_ipv4: false,
            deny_on_credit_card: false,
          },
          risk_threshold: 50,
        }, null, 2),
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

  const loadSelectedJson = useCallback(async (policyId: number) => {
    try {
      const cur = await getActiveVersion(policyId);
      const doc = cur?.document ?? {
        blocked_terms: [],
        allowed_sources: [],
        required_evidence_types: [],
        pii_rules: {
          deny_when_any_pii: false,
          deny_on_email: false,
          deny_on_phone: false,
          deny_on_ssn: false,
          deny_on_ipv4: false,
          deny_on_credit_card: false,
        },
        risk_threshold: 50,
      };
      const text = JSON.stringify(doc, null, 2);
      setSelectedJson({ policyId, jsonText: text, activeVersion: cur?.version ?? null, busy: false, error: null, lastSaved: null });
      // Reflect the freshly fetched active version in the table immediately
      setRow(policyId, { lastVersion: cur ?? null });
    } catch (e: any) {
      const text = JSON.stringify({
        blocked_terms: [],
        allowed_sources: [],
        required_evidence_types: [],
        pii_rules: {
          deny_when_any_pii: false,
          deny_on_email: false,
          deny_on_phone: false,
          deny_on_ssn: false,
          deny_on_ipv4: false,
          deny_on_credit_card: false,
        },
        risk_threshold: 50,
      }, null, 2);
      setSelectedJson({ policyId, jsonText: text, activeVersion: null, busy: false, error: e?.message ?? 'Failed to load policy JSON', lastSaved: null });
    }
  }, [getActiveVersion, setRow]);

  const openCompare = useCallback(async (policyId: number) => {
    setComparePanel({ open: true, policyId, versions: [], leftVersion: undefined, rightVersion: undefined, diff: undefined, busy: true, error: null });
    try {
      const res = await listVersions(policyId, { limit: 200 });
      setComparePanel((s) => ({ ...(s || { open: true, policyId }), open: true, policyId, versions: res.items || [], busy: false, error: null }));
    } catch (e: any) {
      setComparePanel((s) => ({ ...(s || { open: true, policyId }), open: true, policyId, versions: [], busy: false, error: e?.message ?? 'Failed to load versions' }));
    }
  }, [listVersions]);

  const computeDiff = useCallback((a: unknown, b: unknown): string => {
    try {
      const aStr = JSON.stringify(a, null, 2);
      const bStr = JSON.stringify(b, null, 2);
      // Simple line-by-line diff
      const aLines = aStr.split('\n');
      const bLines = bStr.split('\n');
      const max = Math.max(aLines.length, bLines.length);
      const out: string[] = [];
      for (let i = 0; i < max; i++) {
        const l = aLines[i] ?? '';
        const r = bLines[i] ?? '';
        if (l === r) {
          out.push('  ' + l);
        } else {
          if (l) out.push('- ' + l);
          if (r) out.push('+ ' + r);
        }
      }
      return out.join('\n');
    } catch (e: any) {
      return 'Failed to diff: ' + (e?.message ?? 'error');
    }
  }, []);

  const onSelectCompareSide = useCallback((side: 'left'|'right', versionNum: number | undefined) => {
    setComparePanel((s) => {
      if (!s) return s as any;
      const leftVersion = side === 'left' ? versionNum : s.leftVersion;
      const rightVersion = side === 'right' ? versionNum : s.rightVersion;
      let diff: string | undefined = s.diff;
      if (leftVersion && rightVersion && leftVersion !== rightVersion) {
        const va = s.versions.find(v => v.version === leftVersion);
        const vb = s.versions.find(v => v.version === rightVersion);
        if (va && vb) diff = computeDiff(va.document, vb.document);
      } else {
        diff = undefined;
      }
      return { ...s, leftVersion, rightVersion, diff };
    });
  }, [computeDiff]);

  // Auto-load policies when page mounts or tenant changes
  useEffect(() => {
    // best-effort load
    listPolicies(tenantId, { offset: 0, limit: 50 }).catch(() => {/* handled by hook */});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  // For each listed policy, fetch its currently active version if unknown
  useEffect(() => {
    (async () => {
      for (const p of items) {
        const rs = rowState[p.id];
        if (rs === undefined || rs.lastVersion === undefined) {
          try {
            const cur = await getActiveVersion(p.id);
            setRow(p.id, { lastVersion: cur ?? null });
          } catch {
            // ignore per-row fetch issues; shown when interacting
          }
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

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
    // Always check the current active version before attempting activation
    try {
      const cur = await getActiveVersion(policy.id);
      if (cur) {
        setRow(policy.id, { lastVersion: cur });
        if (cur.version === versionNum && cur.is_active) {
          setRow(policy.id, { error: 'selected version is already active' });
          return;
        }
      }
    } catch {
      // If fetch fails or no active, proceed to activation attempt
    }
    // If the selected version is already active (based on last known state), show info and skip call
    if (rs.lastVersion && rs.lastVersion.version === versionNum && rs.lastVersion.is_active) {
      setRow(policy.id, { error: 'selected version is already active' });
      return;
    }
    setRow(policy.id, { busy: true, error: null });
    try {
      const pv = await activateVersion(policy.id, versionNum);
      setRow(policy.id, { busy: false, lastVersion: pv, error: null });
    } catch (e: any) {
      // If activation failed due to not found, verify current active and update UI to avoid stale error
      const msg = String(e?.message ?? 'Failed to activate version');
      // Fallback: if our last known version already matches and is active, show already-active
      const curState = getRow(policy.id);
      if (curState.lastVersion && curState.lastVersion.version === versionNum && curState.lastVersion.is_active) {
        setRow(policy.id, { busy: false, error: 'selected version is already active' });
        return;
      }
      if (/not found/i.test(msg)) {
        try {
          const cur = await getActiveVersion(policy.id);
          if (cur && cur.version === versionNum) {
            // It is already active, surface friendly message
            setRow(policy.id, { busy: false, lastVersion: cur, error: 'selected version is already active' });
            return;
          } else if (cur) {
            setRow(policy.id, { busy: false, lastVersion: cur, error: `Policy version not found (active is v${cur.version})` });
            return;
          }
        } catch { /* ignore follow-up errors */ }
      }
      setRow(policy.id, { busy: false, error: msg });
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
        {comparePanel.open && (
          <div className="card mb-3">
            <div className="card-header d-flex justify-content-between align-items-center">
              <span>Compare Policy Versions {comparePanel.policyId ? <small className="text-muted">(Policy ID: {comparePanel.policyId})</small> : null}</span>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setComparePanel({ open: false, policyId: null, versions: [], busy: false, error: null })}>Close</button>
            </div>
            <div className="card-body">
              {comparePanel.error && <div className="alert alert-warning" role="alert">{comparePanel.error}</div>}
              {comparePanel.busy ? (
                <div className="text-muted">Loading versions…</div>
              ) : comparePanel.versions.length <= 1 ? (
                <div className="text-muted">Need at least two versions to compare.</div>
              ) : (
                <>
                  <div className="row g-3 align-items-end">
                    <div className="col-md-4">
                      <label className="form-label">Left version</label>
                      <select className="form-select" value={comparePanel.leftVersion ?? ''} onChange={(e) => onSelectCompareSide('left', e.target.value ? Number(e.target.value) : undefined)}>
                        <option value="">Select…</option>
                        {comparePanel.versions.map(v => (
                          <option key={v.id} value={v.version}>v{v.version} {v.is_active ? '(active)' : ''}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Right version</label>
                      <select className="form-select" value={comparePanel.rightVersion ?? ''} onChange={(e) => onSelectCompareSide('right', e.target.value ? Number(e.target.value) : undefined)}>
                        <option value="">Select…</option>
                        {comparePanel.versions.map(v => (
                          <option key={v.id} value={v.version}>v{v.version} {v.is_active ? '(active)' : ''}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Active Version</label>
                      <div>
                        {(() => {
                          const act = comparePanel.versions.find(v => v.is_active);
                          return act ? <span>v{act.version}</span> : <span>—</span>;
                        })()}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3">
                    <label className="form-label">Diff (Left → Right)</label>
                    {comparePanel.diff ? (
                      <div className="bg-light p-3 border rounded" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
                        {comparePanel.diff.split('\n').map((ln, idx) => {
                          const isAdd = ln.startsWith('+ ');
                          const isDel = ln.startsWith('- ');
                          const style: React.CSSProperties = {
                            paddingLeft: '8px',
                            backgroundColor: isAdd ? '#d1e7dd' : isDel ? '#fff3cd' : undefined,
                            borderLeft: isAdd ? '4px solid #198754' : isDel ? '4px solid #ffc107' : undefined,
                          };
                          return (
                            <div key={idx} style={style}>{ln}</div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="bg-light p-3 border rounded text-muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
                        Select two versions to see a diff.
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
        {selectedJson && (
          <div className="card mb-3">
            <div className="card-header d-flex justify-content-between align-items-center">
              <span>Policy JSON (ID: {selectedJson.policyId}) {selectedJson.activeVersion ? <small className="text-muted">- active v{selectedJson.activeVersion}</small> : null}</span>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setSelectedJson(null)}>Close</button>
            </div>
            <div className="card-body">
              {selectedJson.error && (
                <div className="alert alert-warning" role="alert">{selectedJson.error}</div>
              )}
              <form className="mb-2" onSubmit={async (e) => {
                e.preventDefault();
                setSelectedJson((s) => (s ? { ...s, busy: true, error: null } : s));
                try {
                  const pid = selectedJson?.policyId;
                  const doc = JSON.parse(selectedJson!.jsonText);
                  const pv = await addVersion(pid!, doc, true);
                  // Update the JSON panel and the table row to reflect new active version immediately
                  setSelectedJson((s) => (s ? { ...s, busy: false, activeVersion: pv.version, lastSaved: pv.version } : s));
                  if (pid) {
                    setRow(pid, { lastVersion: pv });
                  }
                } catch (err: any) {
                  const msg = err?.message ?? 'Failed to save new version';
                  setSelectedJson((s) => (s ? { ...s, busy: false, error: msg } : s));
                }
              }}>
                <label className="form-label">Active Policy Document (JSON)</label>
                <textarea
                  className="form-control"
                  rows={12}
                  value={selectedJson.jsonText}
                  onChange={(e) => setSelectedJson((s) => (s ? { ...s, jsonText: e.target.value, error: null } : s))}
                />
                <div className="d-flex gap-2 mt-2">
                  <button className="btn btn-primary" disabled={selectedJson.busy}>
                    {selectedJson.busy ? 'Saving…' : 'Save as new active version'}
                  </button>
                  {selectedJson.lastSaved ? <span className="text-muted">Saved v{selectedJson.lastSaved}</span> : null}
                </div>
              </form>
            </div>
          </div>
        )}
        <div className="card">
          <div className="card-header">Create Policy</div>
          <div className="card-body">
            <form onSubmit={onCreatePolicy} className="row g-3">
              <div className="col-md-3">
                <label htmlFor="name" className="form-label">Name</label>
                <input id="name" className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="col-md-3">
                <label htmlFor="slug" className="form-label">Policy ID</label>
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
                  <th>Name / Policy ID</th>
                  <th>Status</th>
                  <th>Active Version</th>
                  <th>Created</th>
                  <th style={{ width: 450 }}>Versioning</th>
                  <th>Actions</th>
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
                        <small className="text-muted">ID: <code>{p.id}</code></small>
                        {p.description ? <div className="text-muted small mt-1">{p.description}</div> : null}
                      </td>
                      <td>
                        {p.is_active ? (
                          <span className="badge bg-success">active</span>
                        ) : (
                          <span className="badge bg-secondary">inactive</span>
                        )}
                      </td>
                      <td>
                        {rs.lastVersion
                          ? (
                              <span>
                                v{rs.lastVersion.version} {rs.lastVersion.is_active ? (
                                  <span className="badge bg-success ms-1">active</span>
                                ) : (
                                  <span className="badge bg-secondary ms-1">inactive</span>
                                )}
                              </span>
                            )
                          : '—'}
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
                              onChange={(e) => setRow(p.id, { activateInput: e.target.value, error: null })}
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
                      <td className="d-flex gap-2">
                        <button
                          className="btn btn-sm btn-outline-primary"
                          title="Compare versions"
                          onClick={async () => openCompare(p.id)}
                        >
                          Compare
                        </button>
                        <button
                          className="btn btn-sm btn-outline-danger"
                          title="Delete policy"
                          onClick={async () => {
                            if (!confirm(`Delete policy ${p.name} (id=${p.id})? This cannot be undone.`)) return;
                            try {
                              await deletePolicy(p.id);
                            } catch (e: any) {
                              alert(e?.message ?? 'Failed to delete');
                            }
                          }}
                        >
                          Delete
                        </button>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          title="View / Edit policy"
                          onClick={async () => {
                            await loadSelectedJson(p.id);
                          }}
                        >
                          View
                        </button>
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