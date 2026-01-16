import React, { useCallback, useState } from 'react';
import api from '../api/client';

const Admin: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  // Reports state
  const [preset, setPreset] = useState<string>('last24h');
  const [fromIso, setFromIso] = useState<string>('');
  const [toIso, setToIso] = useState<string>('');
  const [format, setFormat] = useState<string>('html');
  const [downloading, setDownloading] = useState(false);

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

  const downloadReport = useCallback(async () => {
    setError(null);
    setDownloading(true);
    try {
      const base = (import.meta as any).env?.VITE_API_BASE_URL || '';
      const baseNorm = String(base).replace(/\/$/, '');
      const hasApiSuffix = baseNorm.toLowerCase().endsWith('/api');
      const usp = new URLSearchParams();
      usp.set('tenant_id', '1');
      usp.set('preset', preset);
      if (preset === 'custom') {
        if (fromIso) usp.set('from', fromIso);
        if (toIso) usp.set('to', toIso);
      }
      usp.set('tz', 'Asia/Kolkata');
      usp.set('format', format);
      const path = `${hasApiSuffix ? '' : '/api'}/reports/policy-changes`;
      const url = `${baseNorm}${path}?${usp.toString()}`;
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'policy-changes-report.' + (format === 'ndjson' ? 'ndjson' : format);
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e: any) {
      setError(e?.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  }, [preset, fromIso, toIso, format]);

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

      <div className="card mt-4">
        <div className="card-header">Reports</div>
        <div className="card-body">
          <h5 className="mb-3">Policy Changes</h5>
          <div className="row g-3 align-items-end">
            <div className="col-sm-3">
              <label className="form-label">Preset</label>
              <select className="form-select" value={preset} onChange={e => setPreset(e.target.value)}>
                <option value="last24h">Last 24h</option>
                <option value="last7d">Last 7d</option>
                <option value="last30d">Last 30d</option>
                <option value="this_month">This month</option>
                <option value="last_month">Last month</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            {preset === 'custom' && (
              <>
                <div className="col-sm-3">
                  <label className="form-label">From (ISO)</label>
                  <input className="form-control" placeholder="2026-01-16T00:00:00Z" value={fromIso} onChange={e => setFromIso(e.target.value)} />
                </div>
                <div className="col-sm-3">
                  <label className="form-label">To (ISO)</label>
                  <input className="form-control" placeholder="2026-01-16T23:59:59Z" value={toIso} onChange={e => setToIso(e.target.value)} />
                </div>
              </>
            )}
            <div className="col-sm-2">
              <label className="form-label">Format</label>
              <select className="form-select" value={format} onChange={e => setFormat(e.target.value)}>
                <option value="html">HTML</option>
                <option value="csv">CSV</option>
                <option value="ndjson">NDJSON</option>
                <option value="json">JSON</option>
              </select>
            </div>
            <div className="col-sm-12">
              <button className="btn btn-primary" onClick={downloadReport} disabled={downloading}>
                {downloading ? 'Generating…' : 'Generate & Download'}
              </button>
            </div>
          </div>
          <p className="text-muted mt-2">Timezone: Asia/Kolkata. Tenant: 1. HTML is a responsive report; CSV/NDJSON/JSON for SIEM.</p>
        </div>
      </div>
    </div>
  );
};

export default Admin;
