import React, { useEffect, useState } from 'react';
import usePolicies, { type PolicyOut, type PolicyVersionOut } from '../hooks/usePolicies';

const Home: React.FC = () => {
  const { items, total, loading, error, listPolicies, getActiveVersion } = usePolicies();
  const [activeVersions, setActiveVersions] = useState<Record<number, PolicyVersionOut | null>>({});

  const [tenantId, setTenantId] = useState<number>(1);
  const TZ = 'Asia/Kolkata';

  const onLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await listPolicies(tenantId, { offset: 0, limit: 50 });
    } catch {
      // error state handled below
    }
  };

  // Auto-load policies on mount for default tenant
  useEffect(() => {
    listPolicies(tenantId, { offset: 0, limit: 50 }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When items change, fetch active version for each (best-effort)
  useEffect(() => {
    (async () => {
      for (const p of items) {
        if (!(p.id in activeVersions)) {
          try {
            const v = await getActiveVersion(p.id);
            setActiveVersions((prev) => ({ ...prev, [p.id]: v ?? null }));
          } catch {
            setActiveVersions((prev) => ({ ...prev, [p.id]: null }));
          }
        }
      }
    })();
  }, [items]);

  const fmtInTZ = (iso?: string, tz?: string) => {
    if (!iso) return '—';
    const tzUse = tz || TZ;
    try {
      let s = String(iso);
      const hasTZ = /Z$|[+-]\d{2}:\d{2}$/.test(s);
      if (!hasTZ) {
        s = s.replace(' ', 'T');
        if (!/T/.test(s)) s = s + 'T00:00:00';
        s = s + 'Z';
      }
      const d = new Date(s);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleString('en-IN', {
        timeZone: tzUse, year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="container py-4">
      <header className="mb-4 d-flex align-items-center justify-content-between">
        <p className="text-muted mb-0 fs-5">
          Multimodel Policy Management: evaluate content against policies and risk engines, manage evidence, and audit decisions.
        </p>
        <span className="badge bg-secondary">Timezone: {TZ}</span>
      </header>

      <nav className="mb-4">
        <a className="btn btn-primary me-2" href="/protect">Try Protect</a>
      </nav>

      <section className="mb-4">
        <h5 className="mb-3">Explore Policies</h5>
        <form onSubmit={onLoad} className="row g-3 align-items-end">
          <div className="col-sm-3 d-none">
            <input id="tenantId" type="hidden" value={tenantId} readOnly />
          </div>
          <div className="col-sm-3">
            <button type="submit" className="btn btn-success" disabled={loading}>
              {loading ? 'Loading…' : 'Load Policies'}
            </button>
          </div>
        </form>
        {error && (
          <div className="alert alert-danger mt-3" role="alert">
            <strong>Error:</strong> {error.message}
          </div>
        )}
      </section>

      <section>
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="mb-0">Policies</h5>
          <small className="text-muted">Total: {total}</small>
        </div>
        {items.length === 0 ? (
          <div className="text-muted">No policies loaded. Use the form above to fetch policies for a tenant.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Name</th>
                  <th scope="col">Policy ID</th>
                  <th scope="col">Active Version</th>
                  <th scope="col">Active</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p: PolicyOut) => {
                  const v = activeVersions[p.id];
                  return (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>{p.name}</td>
                    <td><code>{p.id}</code></td>
                    <td>{v ? `v${v.version}` : '—'}</td>
                    <td>
                      {p.is_active ? (
                        <span className="badge bg-success">active</span>
                      ) : (
                        <span className="badge bg-secondary">inactive</span>
                      )}
                    </td>
                    <td>{fmtInTZ(p.created_at, TZ)}</td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Home;
