import React, { useMemo, useState } from 'react';
import useProtect, { type ProtectPayload, type ProtectResponse } from '../hooks/useProtect';

const Protect: React.FC = () => {
  const { protect, loading, error, data } = useProtect();

  // Basic form state
  const [tenantId] = useState<number>(1);
  const [policyId, setPolicyId] = useState<number>(1);
  const [inputText, setInputText] = useState<string>('');
  const [evidenceTypesCsv, setEvidenceTypesCsv] = useState<string>('');
  const [evidenceIdsCsv, setEvidenceIdsCsv] = useState<string>(''); // hidden by default
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  
  // Evidence sources (for testing evidence display)
  const [evidenceSources, setEvidenceSources] = useState<Array<{ text: string; source_uri: string }>>([]);
  const [showEvidenceSources, setShowEvidenceSources] = useState<boolean>(false);

  const [submitted, setSubmitted] = useState<boolean>(false);

  const parseCsv = (value: string): string[] =>
    value
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);

    const evidence_types = parseCsv(evidenceTypesCsv);
    
    // Filter out empty evidence sources
    const validEvidenceSources = evidenceSources.filter(
      (s) => s.text.trim() || s.source_uri.trim()
    );

    const payload: ProtectPayload = {
      tenant_id: tenantId,
      policy_id: policyId,
      input_text: inputText,
      evidence_types: evidence_types.length ? evidence_types : undefined,
      evidence_payloads: validEvidenceSources.length > 0 ? validEvidenceSources : undefined,
      // evidenceIdsCsv is currently not used by the backend route; it’s shown for UI parity
      metadata: evidenceIdsCsv
        ? { evidence_ids: evidenceIdsCsv.split(',').map((s) => s.trim()).filter(Boolean) }
        : undefined,
    };

    try {
      await protect(payload);
    } catch {
      // Error is handled via hook's error state
    }
  };

  // Helpers to present user-friendly results
  const splitReasons = (reasons: string[] = []) => {
    const policy: string[] = [];
    const risk: string[] = [];
    for (const r of reasons) {
      if (
        r.startsWith('prompt_injection:') ||
        r.startsWith('pii_like:') ||
        r.startsWith('secret_like:') ||
        r.startsWith('risk_above_threshold') ||
        r === 'evidence_missing' ||
        r === 'conservative_risk_floor'
      ) {
        risk.push(r);
      } else {
        policy.push(r);
      }
    }
    return { policy, risk };
  };

  const formatReason = (r: string): string => {
    if (r === 'evidence_missing') return 'No supporting evidence provided';
    if (r.startsWith('missing_evidence:')) return `Missing required evidence: ${r.split(':')[1]}`;
    if (r.startsWith('blocked_term:')) return `Blocked term found: "${r.split(':')[1]}"`;
    if (r.startsWith('pii_denied:')) return `Contains restricted personal data: ${r.split(':')[1].replace(/_/g, ' ')}`;
    if (r.startsWith('prompt_injection:')) return `Prompt-injection pattern detected: ${r.split(':')[1].replace(/_/g, ' ')}`;
    if (r.startsWith('secret_like:')) return `Looks like a secret: ${r.split(':')[1].replace(/_/g, ' ')}`;
    if (r.startsWith('pii_like:')) return `May contain personal data: ${r.split(':')[1].replace(/_/g, ' ')}`;
    if (r.startsWith('risk_above_threshold:')) {
      const rest = r.split(':')[1] || '';
      const [lhs, rhs] = rest.split('>=');
      return `Risk score ${lhs} exceeds threshold ${rhs}`;
    }
    if (r === 'conservative_risk_floor') return 'Conservative mode: elevated risk to threshold due to indicators present';
    if (r === 'conservative_denial:any_risk_indicator') return 'Conservative mode: denied due to one or more risk indicators';
    return r;
  };

  const riskBadge = (score: number) => {
    if (score >= 67) return { label: 'High', className: 'badge bg-danger' };
    if (score >= 33) return { label: 'Medium', className: 'badge bg-warning text-dark' };
    return { label: 'Low', className: 'badge bg-success' };
  };

  return (
    <div className="container py-4">
      <h1 className="mb-3">Protect</h1>
      <p className="text-muted">
        Submit text to be evaluated against the active policy and risk engine.
      </p>

      <form onSubmit={onSubmit} className="mb-4">
        <div className="row g-3">
          <input type="hidden" id="tenantId" value={tenantId} readOnly />
          <div className="col-sm-5">
            <label htmlFor="policyId" className="form-label">
              Policy ID
            </label>
            <input
              id="policyId"
              type="number"
              min={1}
              className="form-control"
              value={policyId}
              onChange={(e) => setPolicyId(Number(e.target.value))}
              required
            />
          </div>
          {/* Advanced: hidden source inputs (developers only) */}
        </div>

        <div className="row g-3 mt-1">
          {/* Advanced controls: Evidence IDs to pass via metadata */}
          <div className="col-12">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => setShowAdvanced((v) => !v)}
              aria-expanded={showAdvanced}
              aria-controls="advanced-section"
            >
              {showAdvanced ? 'Hide advanced' : 'Show advanced'}
            </button>
          </div>
          {showAdvanced && (
            <div id="advanced-section" className="col-12 mt-2">
              <div className="card">
                <div className="card-header">Advanced</div>
                <div className="card-body">
                  <div className="mb-3">
                    <label htmlFor="evidenceIdsCsv" className="form-label">
                      Evidence IDs (CSV)
                    </label>
                    <input
                      id="evidenceIdsCsv"
                      type="text"
                      className="form-control"
                      placeholder="e.g., 12,45,78"
                      value={evidenceIdsCsv}
                      onChange={(e) => setEvidenceIdsCsv(e.target.value)}
                    />
                    <div className="form-text">
                      These IDs will be sent as metadata.evidence_ids and used to infer evidence types.
                    </div>
                  </div>
                  
                  <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <label className="form-label mb-0">Evidence Sources (for testing)</label>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => setShowEvidenceSources(!showEvidenceSources)}
                      >
                        {showEvidenceSources ? 'Hide' : 'Show'} Evidence Sources
                      </button>
                    </div>
                    {showEvidenceSources && (
                      <div className="border rounded p-3 bg-light">
                        {evidenceSources.map((source, idx) => (
                          <div key={idx} className="mb-3 pb-3 border-bottom">
                            <div className="mb-2">
                              <label className="form-label small">Source {idx + 1} - Text</label>
                              <textarea
                                className="form-control form-control-sm"
                                rows={2}
                                value={source.text}
                                onChange={(e) => {
                                  const newSources = [...evidenceSources];
                                  newSources[idx].text = e.target.value;
                                  setEvidenceSources(newSources);
                                }}
                                placeholder="Evidence text content..."
                              />
                            </div>
                            <div className="mb-2">
                              <label className="form-label small">Source {idx + 1} - URI</label>
                              <input
                                type="text"
                                className="form-control form-control-sm"
                                value={source.source_uri}
                                onChange={(e) => {
                                  const newSources = [...evidenceSources];
                                  newSources[idx].source_uri = e.target.value;
                                  setEvidenceSources(newSources);
                                }}
                                placeholder="https://example.com/source"
                              />
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => {
                                setEvidenceSources(evidenceSources.filter((_, i) => i !== idx));
                              }}
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-success"
                          onClick={() => {
                            setEvidenceSources([...evidenceSources, { text: '', source_uri: '' }]);
                          }}
                        >
                          + Add Evidence Source
                        </button>
                        <div className="form-text mt-2">
                          Evidence sources will be sent to the backend for testing evidence display in the Audit page.
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="mt-3">
          <label htmlFor="inputText" className="form-label">
            Content to evaluate
          </label>
          <textarea
            id="inputText"
            className="form-control"
            rows={6}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Paste or type the content to evaluate..."
            required
          />
        </div>

        <div className="d-flex align-items-center gap-2 mt-3">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Evaluating...' : 'Evaluate'}
          </button>
          {submitted && !loading && !error && !data && (
            <span className="text-muted">Submit to see the decision and reasons.</span>
          )}
        </div>
      </form>

      {error && (
        <div className="alert alert-danger" role="alert">
          <strong>Error:</strong> {error.message}
        </div>
      )}

      {data && (
        <div className="card">
          <div className={`card-header ${data.allowed ? 'bg-success text-white' : 'bg-danger text-white'}`}>
            Decision: {data.allowed ? 'Allowed' : 'Denied'}
          </div>
          <div className="card-body">
            <div className="d-flex align-items-center gap-2 mb-2">
              <strong>Risk score:</strong>
              <span>{data.risk_score}</span>
              <span className={riskBadge(data.risk_score).className}>{riskBadge(data.risk_score).label}</span>
            </div>

            <div className="text-muted small mb-3">
              Final decision = Policy checks passed AND Risk score below threshold. Even with a low risk score, missing required
              evidence, blocked terms, or PII rules can deny the request.
            </div>

            {!data.allowed && (
              <div className="alert alert-warning" role="alert">
                Decision denied. Risk is {riskBadge(data.risk_score).label.toLowerCase()}, but one or more policy checks failed.
                See details below.
              </div>
            )}

            {(() => {
              const parts = splitReasons(data.reasons || []);
              return (
                <div className="row g-3">
                  <div className="col-md-6">
                    <h6 className="mb-2">Policy checks</h6>
                    {parts.policy.length ? (
                      <ul className="list-group">
                        {parts.policy.map((r, idx) => (
                          <li key={`p-${idx}`} className="list-group-item">
                            {formatReason(r)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted">No policy issues found.</p>
                    )}
                  </div>
                  <div className="col-md-6">
                    <h6 className="mb-2">Risk checks</h6>
                    {parts.risk.length ? (
                      <ul className="list-group">
                        {parts.risk.map((r, idx) => (
                          <li key={`r-${idx}`} className="list-group-item">
                            {formatReason(r)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted">No risk indicators found.</p>
                    )}
                  </div>
                </div>
              );
            })()}

            <div className="mt-3 small text-muted">
              <div className="row g-3">
                <div className="col-md-4"><strong>Decision Log</strong><div>ID: {data.decision_log_id ?? '—'}</div></div>
                <div className="col-md-4"><strong>Request Log</strong><div>ID: {data.request_log_id ?? '—'}</div></div>
                <div className="col-md-4"><strong>Tip</strong><div>See Audit for full details and sources.</div></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Protect;