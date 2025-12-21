import React, { useState } from 'react';
import usePolicies, { type PolicyOut } from '../hooks/usePolicies';

const Home: React.FC = () => {
  const { items, total, loading, error, listPolicies } = usePolicies();

  const [tenantId, setTenantId] = useState<number>(1);

  const onLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await listPolicies(tenantId, { offset: 0, limit: 50 });
    } catch {
      // error state handled below
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
      <header className="mb-4">
        <h1 className="mb-2">SatyaSethu</h1>
        <p className="text-muted mb-0">
          Multimodel Policy Management: evaluate content against policies and risk engines, manage evidence, and audit decisions.
        </p>
      </header>

      <nav className="mb-4">
        <a className="btn btn-primary me-2" href="/protect">Try Protect</a>
        <a className="btn btn-outline-secondary" href="/">Home</a>
      </nav>

      <section className="mb-4">
        <h5 className="mb-3">Explore Policies</h5>
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
                  <th scope="col">Slug</th>
                  <th scope="col">Active</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p: PolicyOut) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>{p.name}</td>
                    <td><code>{p.slug}</code></td>
                    <td>
                      {p.is_active ? (
                        <span className="badge bg-success">active</span>
                      ) : (
                        <span className="badge bg-secondary">inactive</span>
                      )}
                    </td>
                    <td>{fmt(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Home;
