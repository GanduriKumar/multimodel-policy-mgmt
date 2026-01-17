import { useCallback } from 'react';

export type ComplianceFramework = 'eu-ai-act' | 'nist-ai-rmf' | 'nist-privacy';
export type ReportFormat = 'json' | 'csv' | 'html';

function parseFilename(contentDisposition: string | null | undefined, fallback: string): string {
  if (!contentDisposition) return fallback;
  const match = /filename\s*=\s*"?([^";]+)"?/i.exec(contentDisposition);
  return match && match[1] ? match[1] : fallback;
}

function getApiBase(): string {
  const envBase = (import.meta as any).env?.VITE_API_BASE_URL || '';
  const base = envBase || 'http://localhost:8000/api';
  return String(base).replace(/\/$/, '');
}

export function useReports() {
  const downloadComplianceReport = useCallback(
    async (policyId: number, framework: ComplianceFramework, tenantId: number = 1, format: ReportFormat = 'json'): Promise<void> => {
      const base = getApiBase();
      const baseNorm = String(base).replace(/\/$/, '');
      const hasApiSuffix = baseNorm.toLowerCase().endsWith('/api');
      const usp = new URLSearchParams({ tenant_id: String(tenantId), format: format });
      const path = `${hasApiSuffix ? '' : '/api'}/reports/compliance/${framework}/${policyId}`;
      const reqUrl = `${baseNorm}${path}?${usp.toString()}`;
      
      // Set Accept header based on format
      const acceptMap: Record<ReportFormat, string> = {
        json: 'application/json',
        csv: 'text/csv',
        html: 'text/html',
      };
      const acceptHeader = acceptMap[format] || 'application/json';
      
      const res = await fetch(reqUrl, { method: 'GET', headers: { Accept: acceptHeader }, credentials: 'include' });
      if (!res.ok) {
        const msg = await res.text().catch(() => 'Request failed');
        throw new Error(msg);
      }
      const blob = await res.blob();
      const ct = res.headers.get('content-type') || acceptHeader;
      const cd = res.headers.get('content-disposition');
      const fallback = `${framework}_p${policyId}.${format}`;
      const filename = parseFilename(cd, fallback);
      const blobUrl = URL.createObjectURL(blob);
      try {
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.rel = 'noopener';
        // For some browsers, setting type helps
        (a as any).type = ct;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } finally {
        setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
      }
    },
    []
  );

  return { downloadComplianceReport };
}

export default useReports;
