import React, { useState } from 'react';
import useProtect, { type ProtectPayload, type ProtectResponse } from '../hooks/useProtect';

const Protect: React.FC = () => {
  const { protect, loading, error, data } = useProtect();

  // Basic form state
  const [tenantId, setTenantId] = useState<number>(1);
  const [policySlug, setPolicySlug] = useState<string>('content-policy');
  const [inputText, setInputText] = useState<string>('');
  const [evidenceTypesCsv, setEvidenceTypesCsv] = useState<string>('');
  const [evidenceIdsCsv, setEvidenceIdsCsv] = useState<string>(''); // optional UI only

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

    const payload: ProtectPayload = {
      tenant_id: tenantId,
      policy_slug: policySlug,
      input_text: inputText,
      evidence_types: evidence_types.length ? evidence_types : undefined,
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

  return (
    <div className="container py-4">
      <h1 className="mb-3">Protect</h1>
      <p className="text-muted">
        Submit text to be evaluated against the active policy and risk engine. Provide optional evidence types (comma
        separated) and evidence IDs for reference.
      </p>

      <form onSubmit={onSubmit} className="mb-4">
        <div className="row g-3">
          <div className="col-sm-3">
            <label htmlFor="tenantId" className="form-label">
              Tenant ID
            </label>
            <input
              id="tenantId"
              type="number"
              min={1}
              className="form-control"
              value={tenantId}
              onChange={(e) => setTenantId(Number(e.target.value))}
              required
            />
          </div>
          <div className="col-sm-5">
            <label htmlFor="policySlug" className="form-label">
              Policy Slug
            </label>
            <input
              id="policySlug"
              type="text"
              className="form-control"
              value={policySlug}
              onChange={(e) => setPolicySlug(e.target.value)}
              required
            />
          </div>
          <div className="col-sm-4">
            <label htmlFor="evidenceTypes" className="form-label">
              Evidence Types (CSV)
            </label>
            <input
              id="evidenceTypes"
              type="text"
              placeholder="e.g., url,document"
              className="form-control"
              value={evidenceTypesCsv}
              onChange={(e) => setEvidenceTypesCsv(e.target.value)}
            />
          </div>
        </div>

        <div className="row g-3 mt-1">
          <div className="col-12">
            <label htmlFor="evidenceIds" className="form-label">
              Evidence IDs (CSV, optional)
            </label>
            <input
              id="evidenceIds"
              type="text"
              placeholder="e.g., 1,2,3"
              className="form-control"
              value={evidenceIdsCsv}
              onChange={(e) => setEvidenceIdsCsv(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-3">
          <label htmlFor="inputText" className="form-label">
            Input Text
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
            <p className="mb-1">
              <strong>Risk Score:</strong> {data.risk_score}
            </p>
            <p className="mb-1">
              <strong>Request Log ID:</strong> {data.request_log_id ?? '—'}
            </p>
            <p className="mb-3">
              <strong>Decision Log ID:</strong> {data.decision_log_id ?? '—'}
            </p>

            <h6 className="mb-2">Reasons</h6>
            {data.reasons && data.reasons.length > 0 ? (
              <ul className="list-group">
                {data.reasons.map((r, idx) => (
                  <li key={`${r}-${idx}`} className="list-group-item">
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted">No reasons reported.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Protect;