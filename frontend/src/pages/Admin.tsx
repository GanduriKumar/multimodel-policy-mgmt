import React, { useCallback, useState } from 'react';
import api from '../api/client';

const Admin: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const resetAll = useCallback(async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      // Call backend maintenance endpoint
      const res = await api.apiPost<{ ok: boolean; cleared: string[]; note?: string }>(
        '/admin/reset-all',
        {}
      );
      setResult(`Cleared: ${res.cleared?.join(', ') || '—'}`);
    } catch (e: any) {
      setError(e?.message || 'Reset failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h1 className="mb-0">Admin</h1>
        <a className="btn btn-outline-secondary" href="/">Home</a>
      </div>

      <div className="card">
        <div className="card-header">Maintenance</div>
        <div className="card-body">
          <p className="text-muted">Reset policies, evidence, and logs. Use with caution.</p>
          <button className="btn btn-danger" disabled={loading} onClick={resetAll}>
            {loading ? 'Resetting…' : 'Reset all data'}
          </button>

          {error && (
            <div className="alert alert-danger mt-3" role="alert">{error}</div>
          )}
          {result && (
            <div className="alert alert-success mt-3" role="alert">{result}</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Admin;
