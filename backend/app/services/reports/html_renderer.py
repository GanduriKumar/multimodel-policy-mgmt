from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import html
import json

from app.services.reports.policy_changes import PolicyChangeEvent


def _group_by_day_and_type(events: List[PolicyChangeEvent]) -> Dict[str, Dict[str, int]]:
    buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in events:
        # Use local date from changed_at_local (YYYY-MM-DD)
        day = (e.changed_at_local or "").split("T")[0]
        if not day:
            # Fallback to UTC date
            day = (e.changed_at_utc or "").split("T")[0]
        buckets[day][e.change_type] += 1
    return {d: dict(cts) for d, cts in buckets.items()}


def _top_policies(events: List[PolicyChangeEvent], top_n: int = 10) -> List[tuple[int, str, int]]:
    counts: Counter[int] = Counter()
    names: Dict[int, str] = {}
    for e in events:
        counts[e.policy_id] += 1
        names.setdefault(e.policy_id, e.policy_name)
    top = counts.most_common(top_n)
    return [(pid, names.get(pid, str(pid)), cnt) for pid, cnt in top]


def render_policy_changes_html(
    *,
    tenant_id: int,
    tz: str,
    range_meta: Dict[str, str],  # { preset, from_utc, to_utc }
    events: List[PolicyChangeEvent],
    no_change_policies_recent: List[Dict[str, str]],  # [{policy_id, policy_name}]
    older_no_change_count: int = 0,
) -> str:
    """
    Render a responsive HTML report for Policy Changes using Bootstrap 5 and Chart.js.
    Returns a complete HTML string (self-contained via CDN assets).
    """
    title = f"Policy Changes Report — Tenant {tenant_id}"

    # Prepare chart data
    by_day = _group_by_day_and_type(events)
    day_labels = sorted(by_day.keys())
    all_types = sorted({t for m in by_day.values() for t in m.keys()})
    datasets = []
    for tname in all_types:
        data = [by_day.get(day, {}).get(tname, 0) for day in day_labels]
        datasets.append({"label": tname, "data": data})

    top_pol = _top_policies(events, top_n=10)
    pol_labels = [f"{pid}: {pname}" for pid, pname, _ in top_pol]
    pol_data = [cnt for _, _, cnt in top_pol]

    # HTML encode table rows
    def row(e: PolicyChangeEvent) -> str:
        return (
            f"<tr>"
            f"<td>{e.policy_id}</td>"
            f"<td>{html.escape(e.policy_name or '')}</td>"
            f"<td>{'' if e.version_id is None else e.version_id}</td>"
            f"<td>{'' if e.version is None else e.version}</td>"
            f"<td>{'' if e.is_active is None else ('Yes' if e.is_active else 'No')}</td>"
            f"<td>{html.escape(e.change_type)}</td>"
            f"<td>{html.escape(e.changed_at_local)}</td>"
            f"<td>{html.escape(e.changed_by)}</td>"
            f"<td>{html.escape(e.diff_summary or '')}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(row(e) for e in events)

    no_change_rows = "\n".join(
        f"<tr><td>{p.get('policy_id')}</td><td>{html.escape(p.get('policy_name',''))}</td><td>No change</td></tr>"
        for p in no_change_policies_recent
    )

    older_note = (
        f"<p class=\"text-muted\">+ {older_no_change_count} policies had no changes earlier than the recent window.</p>"
        if older_no_change_count > 0 else ""
    )

    # Serialize chart payloads
    chart_changes_payload = json.dumps({"labels": day_labels, "datasets": datasets})
    chart_policies_payload = json.dumps({"labels": pol_labels, "data": pol_data})

    html_doc = f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{html.escape(title)}</title>
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
    <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>
  </head>
  <body>
    <div class=\"container py-4\">
      <div class=\"d-flex justify-content-between align-items-center mb-3\">
        <h1 class=\"h3 mb-0\">{html.escape(title)}</h1>
        <span class=\"badge bg-secondary\">Timezone: {html.escape(tz)}</span>
      </div>
      <p class=\"text-muted\">Range: preset={html.escape(range_meta.get('preset',''))}, UTC {html.escape(range_meta.get('from_utc',''))} to {html.escape(range_meta.get('to_utc',''))}</p>

      <div class=\"row g-3\">
        <div class=\"col-12 col-lg-7\">
          <div class=\"card\">
            <div class=\"card-header\">Changes per day</div>
            <div class=\"card-body\">
              <canvas id=\"chartChanges\" height=\"120\"></canvas>
            </div>
          </div>
        </div>
        <div class=\"col-12 col-lg-5\">
          <div class=\"card\">
            <div class=\"card-header\">Changes by policy (top 10)</div>
            <div class=\"card-body\">
              <canvas id=\"chartPolicies\" height=\"120\"></canvas>
            </div>
          </div>
        </div>
      </div>

      <div class=\"card mt-4\">
        <div class=\"card-header\">Events</div>
        <div class=\"table-responsive\">
          <table class=\"table table-sm table-striped mb-0\">
            <thead>
              <tr>
                <th>policy_id</th><th>policy_name</th><th>version_id</th><th>version</th><th>is_active</th><th>change_type</th><th>changed_at_local</th><th>changed_by</th><th>diff_summary</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
      </div>

      <div class=\"card mt-4\">
        <div class=\"card-header\">Policies with no change (recent)</div>
        <div class=\"table-responsive\">
          <table class=\"table table-sm table-striped mb-0\">
            <thead>
              <tr>
                <th>policy_id</th><th>policy_name</th><th>status</th>
              </tr>
            </thead>
            <tbody>
              {no_change_rows if no_change_rows else '<tr><td colspan=3 class=\'text-muted\'>No changes in range</td></tr>'}
            </tbody>
          </table>
        </div>
        <div class=\"card-body\">
          {older_note}
        </div>
      </div>

    </div>

    <script>
      (function() {{
        const changes = {chart_changes_payload};
        const ctx1 = document.getElementById('chartChanges');
        if (ctx1 && window.Chart) {{
          const colors = ['#0d6efd','#198754','#dc3545','#6f42c1','#fd7e14','#20c997'];
          const ds = changes.datasets.map((d, i) => ({{
            label: d.label,
            data: d.data,
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '88',
            stack: 'changes',
          }}));
          new Chart(ctx1, {{ type: 'bar', data: {{ labels: changes.labels, datasets: ds }}, options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }} }});
        }}

        const pol = {chart_policies_payload};
        const ctx2 = document.getElementById('chartPolicies');
        if (ctx2 && window.Chart) {{
          new Chart(ctx2, {{ type: 'bar', data: {{ labels: pol.labels, datasets: [{{ label: 'Events', data: pol.data, backgroundColor: '#0d6efd' }}] }}, options: {{ indexAxis: 'y', responsive: true }} }});
        }}
      }})();
    </script>
    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
  </body>
</html>
"""
    return html_doc
