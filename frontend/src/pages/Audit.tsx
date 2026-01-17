import React, { useCallback, useEffect, useState } from 'react';
import useAudit, { type AuditListRow, type DecisionDetail } from '../hooks/useAudit';
import useEvidence from '../hooks/useEvidence';
import api from '../api/client';

const AuditPage: React.FC = () => {
  const { list, total, loading, error, detail, listRequests, getDecisionDetail, resetError } = useAudit();
  const { fetchEvidence, item: evidenceItem, loading: evidenceLoading, error: evidenceError, resetError: resetEvidenceError } = useEvidence();
  const [policyInfo, setPolicyInfo] = useState<{ id: number; name: string; slug: string } | null>(null);
  const [policyVersionInfo, setPolicyVersionInfo] = useState<{ id: number; version: number } | null>(null);

  // List controls
  const [tenantId] = useState<number>(1);
  const [offset, setOffset] = useState<number>(0);
  const [limit, setLimit] = useState<number>(20);
  // Display timezone (match Dashboard default)
  const TZ = 'Asia/Kolkata';

  // Detail control
  const [detailId, setDetailId] = useState<string>('');

  const onLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    try {
      await listRequests(tenantId, { offset, limit });
    } catch {
      // surfaced via error state
    }
  };

  const onFetchDetail = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    resetEvidenceError();
    const idNum = Number(detailId);
    if (!idNum || idNum < 1) return;
    try {
      await getDecisionDetail(idNum);
    } catch {
      // handled by error state
    }
  };

  // When an evidence item is loaded, fetch its policy and version details for friendlier display
  useEffect(() => {
    let cancelled = false;
    async function loadPolicyContext() {
      setPolicyInfo(null);
      setPolicyVersionInfo(null);
      if (!evidenceItem || !evidenceItem.policy_id) return;
      try {
        const pol = await api.apiGet<{ id: number; name: string; slug: string }>(`/policies/${evidenceItem.policy_id}`);
        if (!cancelled && pol) setPolicyInfo({ id: pol.id, name: pol.name, slug: pol.slug });
      } catch {}
      try {
        if (!evidenceItem?.policy_id) return;
        const list = await api.apiGet<{ items: Array<{ id: number; version: number }> }>(`/policies/${evidenceItem.policy_id}/versions`);
        if (cancelled || !list?.items?.length) return;
        const match = list.items.find(v => v.id === evidenceItem.policy_version_id);
        if (!cancelled && match) setPolicyVersionInfo({ id: match.id, version: match.version });
      } catch {}
    }
    loadPolicyContext();
    return () => { cancelled = true; };
  }, [evidenceItem]);

  const fmt = (iso?: string) => {
    if (!iso) return '—';
    try {
      // Normalize to ISO; if timezone is missing, assume UTC
      let s = String(iso);
      const hasTZ = /Z$|[+-]\d{2}:\d{2}$/.test(s);
      if (!hasTZ) {
        // Replace space with 'T' if present for strict ISO, then append Z
        s = s.replace(' ', 'T');
        if (!/T/.test(s)) s = s + 'T00:00:00';
        s = s + 'Z';
      }
      const d = new Date(s);
      if (isNaN(d.getTime())) return iso;
      // Use en-IN normative date format and explicit timezone
      return d.toLocaleString('en-IN', {
        timeZone: TZ,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      });
    } catch {
      return iso;
    }
  };

  const viewRowDetail = useCallback(
    async (row: AuditListRow) => {
      resetError();
      const id = row.decision_id || row.request_log_id; // route supports both patterns
      await getDecisionDetail(id!);
    },
    [getDecisionDetail, resetError]
  );

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h1 className="mb-0">Audit</h1>
        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-secondary">Timezone: {TZ}</span>
          <a className="btn btn-outline-secondary" href="/">Home</a>
        </div>
      </div>

      <section className="mb-4">
        <form onSubmit={onLoad} className="row g-3 align-items-end">
          <input id="tenantId" type="hidden" value={tenantId} readOnly />
          <div className="col-sm-2">
            <label htmlFor="offset" className="form-label">Offset</label>
            <input id="offset" type="number" min={0} className="form-control" value={offset} onChange={(e) => setOffset(Number(e.target.value))} />
          </div>
          <div className="col-sm-2">
            <label htmlFor="limit" className="form-label">Limit</label>
            <input id="limit" type="number" min={1} max={200} className="form-control" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <div className="col-sm-3">
            <button className="btn btn-primary" disabled={loading}>{loading ? 'Loading…' : 'Load Decision Logs'}</button>
          </div>
        </form>
      </section>

      <section className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="mb-0">Decision Logs</h5>
          <small className="text-muted">Total: {total}</small>
        </div>
        {list.length === 0 ? (
          <div className="text-muted">No decision logs loaded. Use the form above.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Tenant</th>
                  <th>Stage</th>
                  <th>LLM Provider</th>
                  <th>Model</th>
                  <th>Input Preview</th>
                  <th>Decision</th>
                  <th>Risk</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.request_log_id}>
                    <td>{r.request_log_id}</td>
                    <td>{r.tenant_id}</td>
                    <td>
                      {r.stage === 'pre' ? (
                        <span className="badge bg-info">Pre-check</span>
                      ) : r.stage === 'post' ? (
                        <span className="badge bg-warning">Post-check</span>
                      ) : (
                        <span className="badge bg-secondary">—</span>
                      )}
                    </td>
                    <td>
                      {r.llm_provider ? (
                        <span className="badge bg-primary">{r.llm_provider}</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      <small className="text-muted">{r.llm_model || '—'}</small>
                    </td>
                    <td>
                      <small className="text-muted" style={{ maxWidth: '200px', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {r.input_text_preview || '—'}
                      </small>
                    </td>
                    <td>
                      {r.decision === undefined || r.decision === null ? (
                        <span className="badge bg-secondary">n/a</span>
                      ) : r.decision ? (
                        <span className="badge bg-success">allow</span>
                      ) : (
                        <span className="badge bg-danger">deny</span>
                      )}
                    </td>
                    <td>{r.risk_score ?? '—'}</td>
                    <td>{fmt(r.created_at)}</td>
                    <td>
                      <button className="btn btn-sm btn-outline-primary" onClick={() => viewRowDetail(r)}>
                        View Detail
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mb-4">
        <div className="card">
          <div className="card-header">Fetch Decision Detail</div>
          <div className="card-body">
            <form onSubmit={onFetchDetail} className="row g-3 align-items-end">
              <div className="col-sm-3">
                <label htmlFor="detailId" className="form-label">Decision or Request ID</label>
                <input id="detailId" className="form-control" value={detailId} onChange={(e) => setDetailId(e.target.value)} placeholder="e.g., 5" />
              </div>
              <div className="col-sm-3">
                <button className="btn btn-outline-primary" disabled={loading || !detailId}>Fetch</button>
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

      {detail && (
        <section>
          <div className="card">
            <div className="card-header">Decision Detail</div>
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-3"><strong>Decision ID:</strong> {detail.decision_id}</div>
                <div className="col-sm-3"><strong>Request ID:</strong> {detail.request_log_id}</div>
                <div className="col-sm-3"><strong>Tenant:</strong> {detail.tenant_id}</div>
                <div className="col-sm-3"><strong>Risk:</strong> {detail.risk_score ?? '—'}</div>
              </div>
              <div className="row mb-2">
                <div className="col-sm-3">
                  <strong>Decision:</strong>{' '}
                  {detail.allowed ? (
                    <span className="badge bg-success">allow</span>
                  ) : (
                    <span className="badge bg-danger">deny</span>
                  )}
                </div>
                <div className="col-sm-3">
                  <strong>Stage:</strong>{' '}
                  {detail.stage === 'pre' ? (
                    <span className="badge bg-info">Pre-check</span>
                  ) : detail.stage === 'post' ? (
                    <span className="badge bg-warning">Post-check</span>
                  ) : (
                    <span className="badge bg-secondary">—</span>
                  )}
                </div>
                <div className="col-sm-3"><strong>Policy ID:</strong> {detail.policy_id ?? '—'}</div>
                <div className="col-sm-3"><strong>Version ID:</strong> {detail.policy_version_id ?? '—'}</div>
              </div>
              <div className="row mb-2">
                <div className="col-sm-6"><strong>Correlation ID:</strong> <code>{detail.correlation_id ?? '—'}</code></div>
                <div className="col-sm-6"><strong>Created:</strong> {fmt(detail.created_at)}</div>
              </div>
              {detail.input_text && (
                <div className="row mb-3">
                  <div className="col-12">
                    <strong>Input Text:</strong>
                    <div className="mt-1 p-2 bg-light border rounded">
                      <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: '0.875rem' }}>{detail.input_text}</pre>
                    </div>
                  </div>
                </div>
              )}

              <div className="row">
                <div className="col-md-6">
                  <h6>Policy Reasons</h6>
                  {detail.policy_reasons?.length ? (
                    <ul className="list-group mb-3">
                      {detail.policy_reasons.map((r, i) => (
                        <li key={`pr-${i}`} className="list-group-item">{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted">None</p>
                  )}
                </div>
                <div className="col-md-6">
                  <h6>Risk Reasons</h6>
                  {detail.risk_reasons?.length ? (
                    <ul className="list-group mb-3">
                      {detail.risk_reasons.map((r, i) => (
                        <li key={`rr-${i}`} className="list-group-item">{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted">None</p>
                  )}
                </div>
              </div>

              <div className="row mt-3">
                <div className="col-12">
                  <h6>Sources (Evidence)</h6>
                  {detail.evidence_sources && detail.evidence_sources.length > 0 ? (
                    <div className="table-responsive">
                      <table className="table table-sm align-middle">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Source</th>
                            <th>Text Preview</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detail.evidence_sources.map((source, idx) => (
                            <tr key={idx}>
                              <td>{idx + 1}</td>
                              <td>
                                {source.source_uri ? (
                                  <a href={source.source_uri} target="_blank" rel="noopener noreferrer" className="text-decoration-none">
                                    {source.source_uri}
                                  </a>
                                ) : (
                                  <span className="text-muted">No URI</span>
                                )}
                              </td>
                              <td>
                                <small className="text-muted">
                                  {source.text.substring(0, 100)}{source.text.length > 100 ? '...' : ''}
                                </small>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-muted">No sources referenced for this decision.</p>
                  )}

                  {evidenceError && (
                    <div className="alert alert-warning mt-2" role="alert">
                      Failed to fetch evidence: {evidenceError.message}
                    </div>
                  )}

                  {evidenceItem && (
                    <div className="card mt-2">
                      <div className="card-header">Evidence Detail (ID {evidenceItem.id})</div>
                      <div className="card-body small">
                        <div className="row g-3">
                          <div className="col-md-6">
                            <div className="mb-2"><strong>Type</strong><div>{evidenceItem.evidence_type}</div></div>
                            <div className="mb-2"><strong>Captured</strong><div>{new Date(evidenceItem.created_at).toLocaleString()}</div></div>
                            <div className="mb-2"><strong>Description</strong><div>{evidenceItem.description || '—'}</div></div>
                          </div>
                          <div className="col-md-6">
                            <div className="mb-2">
                              <strong>Policy Context</strong>
                              <div>
                                {policyInfo ? (
                                  <span title={`Policy ID ${policyInfo.id}`}>Policy: {policyInfo.name} ({policyInfo.slug})</span>
                                ) : (
                                  <span>Policy: {evidenceItem.policy_id ?? '—'}</span>
                                )}
                              </div>
                              <div>
                                {policyVersionInfo ? (
                                  <span title={`Version ID ${policyVersionInfo.id}`}>Version: {policyVersionInfo.version}</span>
                                ) : (
                                  <span>Version: {evidenceItem.policy_version_id ?? '—'}</span>
                                )}
                              </div>
                            </div>
                            <div className="mb-2"><strong>Source</strong><div>{evidenceItem.source || '—'}</div></div>
                            <div className="mb-2"><strong>Content Hash</strong><div><code>{evidenceItem.content_hash || '—'}</code></div></div>
                          </div>
                        </div>
                        {evidenceItem.metadata && (
                          <details className="mt-2">
                            <summary className="text-muted">Metadata</summary>
                            <pre className="mt-2 bg-light p-2 border rounded"><code>{JSON.stringify(evidenceItem.metadata, null, 2)}</code></pre>
                          </details>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default AuditPage;
