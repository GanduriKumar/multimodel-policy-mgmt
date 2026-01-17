import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../api/client';
import useReports, { type ComplianceFramework, type ReportFormat } from '../hooks/useReports';

type DecisionEvent = {
  tenant_id: number;
  policy_id: number | null;
  policy_version_id: number | null;
  request_log_id: number;
  decision_log_id: number;
  allowed: boolean;
  reasons: string[] | null;
  risk_score: number | null;
  decided_at_utc: string;
  decided_at_local: string;
  local_timezone: string;
  policy_name?: string | null;
};

type PolicyChangeEvent = {
  tenant_id: number;
  policy_id: number;
  policy_name: string;
  version_id?: number | null;
  version?: number | null;
  is_active?: boolean | null;
  change_type: 'policy_created' | 'policy_updated' | 'policy_activated' | 'policy_deactivated' | 'version_created' | 'version_activated' | 'version_deactivated' | string;
  changed_at_utc: string;
  changed_at_local: string;
  local_timezone: string;
};

function getApiBase(): string {
  const base = (import.meta as any).env?.VITE_API_BASE_URL || '';
  return String(base).replace(/\/$/, '');
}

// In development, backend allows missing API key; omit header to avoid 401s.

const TENANT_ID = '1'; // hidden in UI; defaulted to 1 for on-prem
const TZ = 'Asia/Kolkata';

const Dashboard: React.FC = () => {
  // Live data state
  const [decisions, setDecisions] = useState<DecisionEvent[]>([]);
  const [changes, setChanges] = useState<PolicyChangeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Download state (moved from Admin)
  const [polPreset, setPolPreset] = useState<string>('last24h');
  const [polFrom, setPolFrom] = useState('');
  const [polTo, setPolTo] = useState('');
  const [polFormat, setPolFormat] = useState('html');
  const [polBusy, setPolBusy] = useState(false);

  const [decPreset, setDecPreset] = useState<string>('last24h');
  const [decFrom, setDecFrom] = useState('');
  const [decTo, setDecTo] = useState('');
  const [decFormat, setDecFormat] = useState('html');
  const [decBusy, setDecBusy] = useState(false);

  // Chart refs
  const decisionsDayRef = useRef<HTMLCanvasElement | null>(null);
  const decisionsPolRef = useRef<HTMLCanvasElement | null>(null);
  const changesRef = useRef<HTMLCanvasElement | null>(null);

  // Aggregations
  const decByDay = useMemo(() => {
    const map: Record<string, { allow: number; deny: number }> = {};
    for (const d of decisions) {
      const day = (d.decided_at_local || '').split('T')[0] || (d.decided_at_utc || '').split('T')[0];
      if (!map[day]) map[day] = { allow: 0, deny: 0 };
      if (d.allowed) map[day].allow += 1; else map[day].deny += 1;
    }
    const labels = Object.keys(map).sort();
    return {
      labels,
      allow: labels.map(l => map[l].allow),
      deny: labels.map(l => map[l].deny),
    };
  }, [decisions]);

  const decByPolicyTop = useMemo(() => {
    const map: Record<string, { allow: number; deny: number }> = {};
    for (const d of decisions) {
      const p = d.policy_name || (d.policy_id != null ? String(d.policy_id) : 'unknown');
      if (!map[p]) map[p] = { allow: 0, deny: 0 };
      if (d.allowed) map[p].allow += 1; else map[p].deny += 1;
    }
    const entries = Object.entries(map).map(([k, v]) => [k, v.allow + v.deny] as const);
    entries.sort((a, b) => b[1] - a[1]);
    const labels = entries.slice(0, 10).map(e => e[0]);
    return {
      labels,
      allow: labels.map(l => map[l]?.allow || 0),
      deny: labels.map(l => map[l]?.deny || 0),
      total: labels.map(l => (map[l]?.allow || 0) + (map[l]?.deny || 0)),
    };
  }, [decisions]);

  const changesByType = useMemo(() => {
    const map: Record<string, Record<string, number>> = {};
    for (const c of changes) {
      const day = (c.changed_at_local || '').split('T')[0] || (c.changed_at_utc || '').split('T')[0];
      map[day] = map[day] || {};
      map[day][c.change_type] = (map[day][c.change_type] || 0) + 1;
    }
    const labels = Object.keys(map).sort();
    const typesSet = new Set<string>();
    for (const day of labels) for (const t of Object.keys(map[day])) typesSet.add(t);
    const types = Array.from(typesSet).sort();
    const datasets = types.map((t, i) => ({
      label: t,
      data: labels.map(l => map[l][t] || 0),
      backgroundColor: COLORS[i % COLORS.length],
      stack: 'changes',
    }));
    return { labels, datasets };
  }, [changes]);

  // Totals
  const totals = useMemo(() => {
    const totalDec = decisions.length;
    const allow = decisions.filter(d => d.allowed).length;
    const deny = totalDec - allow;
    const totalChanges = changes.length;
    return { totalDec, allow, deny, totalChanges };
  }, [decisions, changes]);

  // Fetch latest JSON arrays and poll
  useEffect(() => {
    let cancelled = false;
    const fetchAll = async () => {
      try {
        setError(null);
        setLoading(true);
        const base = getApiBase();
        const baseNorm = String(base).replace(/\/$/, '');
        const hasApiSuffix = baseNorm.toLowerCase().endsWith('/api');
        const urlDec = `${baseNorm}${hasApiSuffix ? '' : '/api'}/reports/decisions?` + new URLSearchParams({ tenant_id: TENANT_ID, preset: 'last24h', tz: TZ, format: 'json' }).toString();
        const urlPol = `${baseNorm}${hasApiSuffix ? '' : '/api'}/reports/policy-changes?` + new URLSearchParams({ tenant_id: TENANT_ID, preset: 'last7d', tz: TZ, format: 'json' }).toString();
        const [decRes, polRes] = await Promise.all([
          fetch(urlDec, { headers: { Accept: 'application/json' } }),
          fetch(urlPol, { headers: { Accept: 'application/json' } }),
        ]);
        if (!decRes.ok || !polRes.ok) {
          const dt = await decRes.text().catch(() => '');
          const pt = await polRes.text().catch(() => '');
          throw new Error(dt || pt || `HTTP ${decRes.status}/${polRes.status}`);
        }
        const [dec, pol] = await Promise.all([decRes.json(), polRes.json()]);
        if (!cancelled) {
          setDecisions(dec || []);
          setChanges(pol || []);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchAll();
    const iv = setInterval(fetchAll, 15000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  // Charts rendering with Chart.js via global window.Chart
  useEffect(() => {
    const Chart = (window as any).Chart;
    // Decisions per day — doughnut of totals in range
    let c1: any;
    if (Chart && decisionsDayRef.current) {
      const ctx = decisionsDayRef.current.getContext('2d');
      if (ctx) {
        if ((decisionsDayRef.current as any)._chart) {
          (decisionsDayRef.current as any)._chart.destroy();
        }
        const totAllow = decByDay.allow.reduce((a,b)=>a+b,0);
        const totDeny = decByDay.deny.reduce((a,b)=>a+b,0);
        c1 = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: ['allow', 'deny'],
            datasets: [
              { label: 'decisions', data: [totAllow, totDeny], backgroundColor: ['#198754', '#dc3545'] },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10, padding: 8, font: { size: 10 } } },
              tooltip: {
                callbacks: {
                  label: (ctx: any) => `${ctx.label}: ${ctx.parsed} (${percent(ctx.parsed, totAllow + totDeny)})`,
                },
              },
            },
            cutout: '55%',
          },
        });
        (decisionsDayRef.current as any)._chart = c1;
      }
    }

    // Decisions by policy (top 10) — doughnut
    let c2: any;
    if (Chart && decisionsPolRef.current) {
      const ctx = decisionsPolRef.current.getContext('2d');
      if (ctx) {
        if ((decisionsPolRef.current as any)._chart) {
          (decisionsPolRef.current as any)._chart.destroy();
        }
        c2 = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: decByPolicyTop.labels,
            datasets: [
              { label: 'total decisions', data: decByPolicyTop.total, backgroundColor: decByPolicyTop.labels.map((_, i) => COLORS[i % COLORS.length]) },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10, padding: 8, font: { size: 10 } } },
              tooltip: {
                callbacks: {
                  label: (ctx: any) => `${ctx.label}: ${ctx.parsed} (${percent(ctx.parsed, decByPolicyTop.total.reduce((a,b)=>a+b,0))})`,
                },
              },
            },
            cutout: '55%',
          },
        });
        (decisionsPolRef.current as any)._chart = c2;
      }
    }

    // Policy changes by type — stacked bar
    let c3: any;
    if (Chart && changesRef.current) {
      const ctx = changesRef.current.getContext('2d');
      if (ctx) {
        if ((changesRef.current as any)._chart) {
          (changesRef.current as any)._chart.destroy();
        }
        c3 = new Chart(ctx, {
          type: 'bar',
          data: { labels: changesByType.labels, datasets: changesByType.datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10, padding: 8, font: { size: 10 } } } },
            interaction: { mode: 'index', intersect: false },
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
          },
        });
        (changesRef.current as any)._chart = c3;
      }
    }

    return () => {
      if (c1) c1.destroy();
      if (c2) c2.destroy();
      if (c3) c3.destroy();
    };
  }, [decByDay, decByPolicyTop, changesByType]);

  // Downloads
  const downloadPolicyReport = useCallback(async () => {
    setError(null);
    setPolBusy(true);
    try {
      const base = getApiBase();
      const baseNorm = String(base).replace(/\/$/, '');
      const hasApiSuffix = baseNorm.toLowerCase().endsWith('/api');
      const usp = new URLSearchParams();
      usp.set('tenant_id', TENANT_ID);
      usp.set('preset', polPreset);
      if (polPreset === 'custom') {
        if (polFrom) usp.set('from', polFrom);
        if (polTo) usp.set('to', polTo);
      }
      usp.set('tz', TZ);
      usp.set('format', polFormat);
      const path = `${hasApiSuffix ? '' : '/api'}/reports/policy-changes`;
      const url = `${baseNorm}${path}?${usp.toString()}`;
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'policy-changes-report.' + (polFormat === 'ndjson' ? 'ndjson' : polFormat);
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e: any) {
      setError(e?.message || 'Download failed');
    } finally {
      setPolBusy(false);
    }
  }, [polPreset, polFrom, polTo, polFormat]);

  const downloadDecisionsReport = useCallback(async () => {
    setError(null);
    setDecBusy(true);
    try {
      const base = getApiBase();
      const baseNorm = String(base).replace(/\/$/, '');
      const hasApiSuffix = baseNorm.toLowerCase().endsWith('/api');
      const usp = new URLSearchParams();
      usp.set('tenant_id', TENANT_ID);
      usp.set('preset', decPreset);
      if (decPreset === 'custom') {
        if (decFrom) usp.set('from', decFrom);
        if (decTo) usp.set('to', decTo);
      }
      usp.set('tz', TZ);
      usp.set('format', decFormat);
      const path = `${hasApiSuffix ? '' : '/api'}/reports/decisions`;
      const url = `${baseNorm}${path}?${usp.toString()}`;
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'decisions-report.' + (decFormat === 'ndjson' ? 'ndjson' : decFormat);
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e: any) {
      setError(e?.message || 'Download failed');
    } finally {
      setDecBusy(false);
    }
  }, [decPreset, decFrom, decTo, decFormat]);

  // Compliance report download (per-policy)
  const { downloadComplianceReport } = useReports();
  const [compPolicyId, setCompPolicyId] = useState<string>('1');
  const [compFramework, setCompFramework] = useState<ComplianceFramework>('eu-ai-act');
  const [compFormat, setCompFormat] = useState<ReportFormat>('html');
  const [compBusy, setCompBusy] = useState(false);
  const onDownloadCompliance = useCallback(async () => {
    setError(null);
    setCompBusy(true);
    try {
      const pid = Number(compPolicyId);
      if (!pid || pid < 1) throw new Error('Enter a valid policy ID');
      await downloadComplianceReport(pid, compFramework, Number(TENANT_ID), compFormat);
    } catch (e: any) {
      setError(e?.message || 'Download failed');
    } finally {
      setCompBusy(false);
    }
  }, [compPolicyId, compFramework, compFormat]);

  return (
    <div className="container py-4 dashboard">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h1 className="mb-0">Dashboard</h1>
        <span className="badge bg-secondary">Timezone: {TZ}</span>
      </div>

      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      <div className="row g-3 mb-3">
        <div className="col-6 col-lg-3">
          <div className="card text-bg-light"><div className="card-body">
            <div className="text-muted small">Total decisions (24h)</div>
            <div className="fs-3 fw-semibold">{totals.totalDec}</div>
          </div></div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="card text-bg-light"><div className="card-body">
            <div className="text-muted small">Allowed</div>
            <div className="fs-3 fw-semibold text-success">{totals.allow}</div>
          </div></div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="card text-bg-light"><div className="card-body">
            <div className="text-muted small">Denied</div>
            <div className="fs-3 fw-semibold text-danger">{totals.deny}</div>
          </div></div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="card text-bg-light"><div className="card-body">
            <div className="text-muted small">Policy changes (7d)</div>
            <div className="fs-3 fw-semibold">{totals.totalChanges}</div>
          </div></div>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-12 col-lg-4 d-flex">
          <div className="card h-100 w-100">
            <div className="card-header">Decisions — allow vs deny (24h)</div>
            <div className="card-body chart-body"><canvas ref={decisionsDayRef} style={{ width: '100%', height: '100%' }} /></div>
          </div>
        </div>
        <div className="col-12 col-lg-4 d-flex">
          <div className="card h-100 w-100">
            <div className="card-header">Decisions by policy (top 10)</div>
            <div className="card-body chart-body"><canvas ref={decisionsPolRef} style={{ width: '100%', height: '100%' }} /></div>
          </div>
        </div>
        <div className="col-12 col-lg-4 d-flex">
          <div className="card h-100 w-100">
            <div className="card-header">Policy changes</div>
            <div className="card-body chart-body"><canvas ref={changesRef} style={{ width: '100%', height: '100%' }} /></div>
          </div>
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-header">Generate & Download</div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-12 col-lg-4 d-flex">
              <div className="card w-100 h-100">
                <div className="card-header">Policy Changes</div>
                <div className="card-body">
                  <div className="row g-3 align-items-end">
                    <div className="col-sm-4">
                      <label className="form-label">Preset</label>
                      <select className="form-select" value={polPreset} onChange={e => setPolPreset(e.target.value)}>
                        <option value="last24h">Last 24h</option>
                        <option value="last7d">Last 7d</option>
                        <option value="last30d">Last 30d</option>
                        <option value="this_month">This month</option>
                        <option value="last_month">Last month</option>
                        <option value="custom">Custom</option>
                      </select>
                    </div>
                    {polPreset === 'custom' && (
                      <>
                        <div className="col-sm-4">
                          <label className="form-label">From (ISO)</label>
                          <input className="form-control" value={polFrom} onChange={e => setPolFrom(e.target.value)} placeholder="2026-01-16T00:00:00Z" />
                        </div>
                        <div className="col-sm-4">
                          <label className="form-label">To (ISO)</label>
                          <input className="form-control" value={polTo} onChange={e => setPolTo(e.target.value)} placeholder="2026-01-16T23:59:59Z" />
                        </div>
                      </>
                    )}
                    <div className="col-sm-4">
                      <label className="form-label">Format</label>
                      <select className="form-select" value={polFormat} onChange={e => setPolFormat(e.target.value)}>
                        <option value="html">HTML</option>
                        <option value="csv">CSV</option>
                        <option value="ndjson">NDJSON</option>
                        <option value="json">JSON</option>
                      </select>
                    </div>
                    <div className="col-12">
                      <button className="btn btn-primary" onClick={downloadPolicyReport} disabled={polBusy}>
                        {polBusy ? 'Generating…' : 'Generate & Download'}
                      </button>
                    </div>
                  </div>
                  <p className="text-muted small mt-2 mb-0">Timezone: {TZ}.</p>
                </div>
              </div>
            </div>

            <div className="col-12 col-lg-4 d-flex">
              <div className="card w-100 h-100">
                <div className="card-header">Decisions</div>
                <div className="card-body">
                  <div className="row g-3 align-items-end">
                    <div className="col-sm-4">
                      <label className="form-label">Preset</label>
                      <select className="form-select" value={decPreset} onChange={e => setDecPreset(e.target.value)}>
                        <option value="last24h">Last 24h</option>
                        <option value="last7d">Last 7d</option>
                        <option value="last30d">Last 30d</option>
                        <option value="this_month">This month</option>
                        <option value="last_month">Last month</option>
                        <option value="custom">Custom</option>
                      </select>
                    </div>
                    {decPreset === 'custom' && (
                      <>
                        <div className="col-sm-4">
                          <label className="form-label">From (ISO)</label>
                          <input className="form-control" value={decFrom} onChange={e => setDecFrom(e.target.value)} placeholder="2026-01-16T00:00:00Z" />
                        </div>
                        <div className="col-sm-4">
                          <label className="form-label">To (ISO)</label>
                          <input className="form-control" value={decTo} onChange={e => setDecTo(e.target.value)} placeholder="2026-01-16T23:59:59Z" />
                        </div>
                      </>
                    )}
                    <div className="col-sm-4">
                      <label className="form-label">Format</label>
                      <select className="form-select" value={decFormat} onChange={e => setDecFormat(e.target.value)}>
                        <option value="html">HTML</option>
                        <option value="csv">CSV</option>
                        <option value="ndjson">NDJSON</option>
                        <option value="json">JSON</option>
                      </select>
                    </div>
                    <div className="col-12">
                      <button className="btn btn-primary" onClick={downloadDecisionsReport} disabled={decBusy}>
                        {decBusy ? 'Generating…' : 'Generate & Download'}
                      </button>
                    </div>
                  </div>
                  <p className="text-muted small mt-2 mb-0">Timezone: {TZ}.</p>
                </div>
              </div>
            </div>
            <div className="col-12 col-lg-4 d-flex">
              <div className="card w-100 h-100">
                <div className="card-header">Regulatory Compliance</div>
                <div className="card-body">
                  <div className="row g-3 align-items-end">
                    <div className="col-sm-6">
                      <label className="form-label">Policy ID</label>
                      <input className="form-control" value={compPolicyId} onChange={e => setCompPolicyId(e.target.value)} placeholder="1" />
                    </div>
                    <div className="col-sm-6">
                      <label className="form-label">Framework</label>
                      <select className="form-select" value={compFramework} onChange={e => setCompFramework(e.target.value as ComplianceFramework)}>
                        <option value="eu-ai-act">EU AI Act</option>
                        <option value="nist-ai-rmf">NIST AI RMF</option>
                        <option value="nist-privacy">NIST Privacy</option>
                      </select>
                    </div>
                    <div className="col-sm-6">
                      <label className="form-label">Format</label>
                      <select className="form-select" value={compFormat} onChange={e => setCompFormat(e.target.value as ReportFormat)}>
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                        <option value="html">HTML</option>
                      </select>
                    </div>
                    <div className="col-12">
                      <button className="btn btn-primary" onClick={onDownloadCompliance} disabled={compBusy}>
                        {compBusy ? 'Generating…' : 'Generate & Download'}
                      </button>
                    </div>
                  </div>
                  <p className="text-muted small mt-2 mb-0">Download compliance report in selected format.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {loading && <div className="text-muted small mt-2">Loading…</div>}
    </div>
  );
};

const COLORS = [
  '#0d6efd','#198754','#dc3545','#6f42c1','#20c997','#ff8800','#6610f2','#fd7e14','#0dcaf0','#1982c4',
];

function alpha(hex: string, a: number): string {
  // hex like #rrggbb to rgba
  const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
  if (!m) return hex;
  const r = parseInt(m[1], 16);
  const g = parseInt(m[2], 16);
  const b = parseInt(m[3], 16);
  return `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, a))})`;
}

function percent(value: number, total: number): string {
  if (!total) return '0%';
  const p = (value / total) * 100;
  return `${p.toFixed(1)}%`;
}

export default Dashboard;
