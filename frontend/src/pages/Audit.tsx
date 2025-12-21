import React, { useCallback, useState } from 'react';
import useAudit, { type AuditListRow, type DecisionDetail } from '../hooks/useAudit';

const AuditPage: React.FC = () => {
  const { list, total, loading, error, detail, listRequests, getDecisionDetail, resetError } = useAudit();

  // List controls
  const [tenantId, setTenantId] = useState<number>(1);
  const [offset, setOffset] = useState<number>(0);
  const [limit, setLimit] = useState<number>(20);

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
    const idNum = Number(detailId);
    if (!idNum || idNum < 1) return;
    try {
      await getDecisionDetail(idNum);
    } catch {
      // handled by error state
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
        <a className="btn btn-outline-secondary" href="/">Home</a>
      </div>

      <section className="mb-4">
        <form onSubmit={onLoad} className="row g-3 align-items-end">
          <div className="col-sm-3">
            <label htmlFor="tenantId" className="form-label">Tenant ID</label>
            <input id="tenantId" type="number" min={1} className="form-control" value={tenantId} onChange={(e) => setTenantId(Number(e.target.value))} />
          </div>
          <div className="col-sm-2">
            <label htmlFor="offset" className="form-label">Offset</label>
            <input id="offset" type="number" min={0} className="form-control" value={offset} onChange={(e) => setOffset(Number(e.target.value))} />
          </div>
          <div className="col-sm-2">
            <label htmlFor="limit" className="form-label">Limit</label>
            <input id="limit" type="number" min={1} max={200} className="form-control" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <div className="col-sm-3">
            <button className="btn btn-primary" disabled={loading}>{loading ? 'Loading…' : 'Load Requests'}</button>
          </div>
        </form>
      </section>

      <section className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="mb-0">Requests</h5>
          <small className="text-muted">Total: {total}</small>
        </div>
        {list.length === 0 ? (
          <div className="text-muted">No requests loaded. Use the form above.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Tenant</th>
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
                <div className="col-sm-3"><strong>Policy ID:</strong> {detail.policy_id ?? '—'}</div>
                <div className="col-sm-3"><strong>Version ID:</strong> {detail.policy_version_id ?? '—'}</div>
                <div className="col-sm-3"><strong>Created:</strong> {fmt(detail.created_at)}</div>
              </div>

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
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default AuditPage;
