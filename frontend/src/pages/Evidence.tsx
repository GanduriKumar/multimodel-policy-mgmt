import React, { useCallback, useMemo, useState } from 'react';
import useEvidence, { type EvidenceCreate, type EvidenceOut } from '../hooks/useEvidence';

const EvidencePage: React.FC = () => {
  const { ingestEvidence, fetchEvidence, loading, error, item, resetError } = useEvidence();

  // Ingest form state
  const [tenantId, setTenantId] = useState<number>(1);
  const [evidenceType, setEvidenceType] = useState<string>('url');
  const [source, setSource] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [content, setContent] = useState<string>('');
  const [policyId, setPolicyId] = useState<string>('');
  const [policyVersionId, setPolicyVersionId] = useState<string>('');
  const [metadataText, setMetadataText] = useState<string>('');

  // Fetch form state
  const [fetchId, setFetchId] = useState<string>('');

  const parseJson = useCallback((text: string): Record<string, unknown> | null => {
    const trimmed = (text || '').trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed);
    } catch (e: any) {
      throw new Error(`Invalid metadata JSON: ${e?.message ?? 'parse error'}`);
    }
  }, []);

  const onIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    try {
      const payload: EvidenceCreate = {
        evidence_type: evidenceType,
        policy_id: policyId ? Number(policyId) : undefined,
        policy_version_id: policyVersionId ? Number(policyVersionId) : undefined,
        source: source || undefined,
        description: description || undefined,
        content: content || undefined,
        metadata: parseJson(metadataText) ?? undefined,
      };
      await ingestEvidence(tenantId, payload);
    } catch {
      // error surfaced via hook state
    }
  };

  const onFetch = async (e: React.FormEvent) => {
    e.preventDefault();
    resetError();
    const id = Number(fetchId);
    if (!id || id < 1) return;
    try {
      await fetchEvidence(id);
    } catch {
      // handled by hook
    }
  };

  const fmt = (iso?: string | null) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return isNaN(d.getTime()) ? String(iso) : d.toLocaleString();
    } catch {
      return String(iso);
    }
  };

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h1 className="mb-0">Evidence</h1>
        <a className="btn btn-outline-secondary" href="/">Home</a>
      </div>

      <section className="mb-4">
        <div className="card">
          <div className="card-header">Ingest Evidence</div>
          <div className="card-body">
            <form onSubmit={onIngest} className="row g-3">
              <div className="col-sm-2">
                <label htmlFor="tenantId" className="form-label">Tenant ID</label>
                <input id="tenantId" type="number" min={1} className="form-control" value={tenantId} onChange={(e) => setTenantId(Number(e.target.value))} required />
              </div>
              <div className="col-sm-3">
                <label htmlFor="etype" className="form-label">Evidence Type</label>
                <input id="etype" className="form-control" value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)} required />
              </div>
              <div className="col-sm-7">
                <label htmlFor="source" className="form-label">Source (URL or ref)</label>
                <input id="source" className="form-control" value={source} onChange={(e) => setSource(e.target.value)} placeholder="https://example.com/resource" />
              </div>

              <div className="col-12">
                <label htmlFor="desc" className="form-label">Description</label>
                <input id="desc" className="form-control" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>

              <div className="col-12">
                <label htmlFor="content" className="form-label">Content (optional, used to compute hash)</label>
                <textarea id="content" className="form-control" rows={4} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Paste content here..." />
              </div>

              <div className="col-sm-3">
                <label htmlFor="policyId" className="form-label">Policy ID</label>
                <input id="policyId" className="form-control" value={policyId} onChange={(e) => setPolicyId(e.target.value)} placeholder="e.g., 10" />
              </div>
              <div className="col-sm-3">
                <label htmlFor="policyVersionId" className="form-label">Policy Version ID</label>
                <input id="policyVersionId" className="form-control" value={policyVersionId} onChange={(e) => setPolicyVersionId(e.target.value)} placeholder="e.g., 3" />
              </div>
              <div className="col-sm-6">
                <label htmlFor="metadata" className="form-label">Metadata (JSON)</label>
                <textarea id="metadata" className="form-control" rows={3} value={metadataText} onChange={(e) => setMetadataText(e.target.value)} placeholder='{"k":"v"}' />
              </div>

              <div className="col-12">
                <button className="btn btn-success" disabled={loading}>
                  {loading ? 'Submitting…' : 'Ingest Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      <section className="mb-4">
        <div className="card">
          <div className="card-header">Fetch Evidence</div>
          <div className="card-body">
            <form onSubmit={onFetch} className="row g-3 align-items-end">
              <div className="col-sm-3">
                <label htmlFor="fetchId" className="form-label">Evidence ID</label>
                <input id="fetchId" className="form-control" value={fetchId} onChange={(e) => setFetchId(e.target.value)} placeholder="e.g., 1" />
              </div>
              <div className="col-sm-3">
                <button className="btn btn-primary" disabled={loading || !fetchId}>Fetch</button>
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

      {item && (
        <section>
          <div className="card">
            <div className="card-header">Evidence Details</div>
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-3"><strong>ID:</strong> {item.id}</div>
                <div className="col-sm-3"><strong>Tenant:</strong> {item.tenant_id}</div>
                <div className="col-sm-3"><strong>Type:</strong> {item.evidence_type}</div>
                <div className="col-sm-3"><strong>Hash:</strong> <code>{item.content_hash ?? '—'}</code></div>
              </div>
              <div className="mb-2"><strong>Source:</strong> {item.source || '—'}</div>
              <div className="mb-2"><strong>Description:</strong> {item.description || '—'}</div>
              <div className="row mb-2">
                <div className="col-sm-3"><strong>Policy ID:</strong> {item.policy_id ?? '—'}</div>
                <div className="col-sm-3"><strong>Version ID:</strong> {item.policy_version_id ?? '—'}</div>
                <div className="col-sm-3"><strong>Created:</strong> {fmt(item.created_at)}</div>
                <div className="col-sm-3"><strong>Updated:</strong> {fmt(item.updated_at)}</div>
              </div>
              <div>
                <strong>Metadata:</strong>
                <pre className="mt-2 bg-light p-2 rounded" style={{ whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(item.metadata ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default EvidencePage;
