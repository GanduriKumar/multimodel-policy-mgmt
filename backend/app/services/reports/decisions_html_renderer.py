from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

import html
import json

from app.services.reports.decisions import DecisionEvent


def _group_by_day_outcome(events: List[DecisionEvent]) -> Dict[str, Dict[str, int]]:
    buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in events:
        day = (e.decided_at_local or "").split("T")[0] or (e.decided_at_utc or "").split("T")[0]
        outcome = "allow" if e.allowed else "deny"
        buckets[day][outcome] += 1
    return {d: dict(cts) for d, cts in buckets.items()}


def _group_by_policy_outcome(events: List[DecisionEvent]) -> Dict[str, Dict[str, int]]:
    buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in events:
        pname = e.policy_name or (str(e.policy_id) if e.policy_id is not None else "unknown")
        outcome = "allow" if e.allowed else "deny"
        buckets[pname][outcome] += 1
    return {p: dict(cts) for p, cts in buckets.items()}


def _risk_histogram(events: List[DecisionEvent], bucket: int = 10) -> Dict[str, int]:
    hist: Dict[str, int] = defaultdict(int)
    for e in events:
        if e.risk_score is None:
            continue
        v = max(0, min(100, int(e.risk_score)))
        start = (v // bucket) * bucket
        end = start + bucket - (0 if start < 100 else 0)
        label = f"{start}-{min(100, start + bucket - 1)}"
        if start == 100:
            label = "100"
        hist[label] += 1
    # Ensure all buckets 0-9,10-19,...,100 exist (optional)
    labels = [f"{i}-{i+bucket-1}" for i in range(0, 100, bucket)] + ["100"]
    return {lbl: hist.get(lbl, 0) for lbl in labels}


def _top_reasons(events: List[DecisionEvent], top_n: int = 10) -> List[tuple[str, int]]:
    c: Counter[str] = Counter()
    for e in events:
        for r in (e.reasons or []):
            if isinstance(r, str) and r:
                c[r] += 1
    return c.most_common(top_n)


def render_decisions_html(
    *,
    tenant_id: int,
    tz: str,
    range_meta: Dict[str, str],  # { preset, from_utc, to_utc }
    events: List[DecisionEvent],
) -> str:
    title = f"Decisions Report — Tenant {tenant_id}"

    by_day = _group_by_day_outcome(events)
    day_labels = sorted(by_day.keys())
    outcomes = ["allow", "deny"]
    day_datasets = []
    for name in outcomes:
        data = [by_day.get(day, {}).get(name, 0) for day in day_labels]
        day_datasets.append({"label": name, "data": data})

    by_policy = _group_by_policy_outcome(events)
    # top 10 policies by total activity
    pol_counts = [(p, sum(cts.values())) for p, cts in by_policy.items()]
    pol_counts.sort(key=lambda x: x[1], reverse=True)
    top_policies = [p for p, _ in pol_counts[:10]]
    pol_labels = top_policies
    pol_allow = [by_policy.get(p, {}).get("allow", 0) for p in top_policies]
    pol_deny = [by_policy.get(p, {}).get("deny", 0) for p in top_policies]

    risk_hist = _risk_histogram(events, bucket=10)
    risk_labels = list(risk_hist.keys())
    risk_values = [risk_hist[k] for k in risk_labels]

    reasons = _top_reasons(events, top_n=10)
    reasons_labels = [r for r, _ in reasons]
    reasons_values = [n for _, n in reasons]

    # Table rows
    def row(e: DecisionEvent) -> str:
        return (
            f"<tr>"
            f"<td>{e.request_log_id}</td>"
            f"<td>{e.decision_log_id}</td>"
            f"<td>{'' if e.policy_id is None else e.policy_id}</td>"
            f"<td>{html.escape(e.policy_name or '')}</td>"
            f"<td>{'ALLOW' if e.allowed else 'DENY'}</td>"
            f"<td>{'' if e.risk_score is None else e.risk_score}</td>"
            f"<td>{html.escape(e.decided_at_local)}</td>"
            f"<td>{html.escape(', '.join(e.reasons or []))}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(row(e) for e in events)

    payload_day = json.dumps({"labels": day_labels, "datasets": day_datasets})
    payload_policy = json.dumps({"labels": pol_labels, "allow": pol_allow, "deny": pol_deny})
    payload_risk = json.dumps({"labels": risk_labels, "data": risk_values})
    payload_reasons = json.dumps({"labels": reasons_labels, "data": reasons_values})

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
            <div class=\"card-header\">Decisions per day (stacked)</div>
            <div class=\"card-body\">
              <canvas id=\"chartDay\" height=\"120\"></canvas>
            </div>
          </div>
        </div>
        <div class=\"col-12 col-lg-5\">
          <div class=\"card\">
            <div class=\"card-header\">By policy (top 10, stacked)</div>
            <div class=\"card-body\">
              <canvas id=\"chartPolicy\" height=\"120\"></canvas>
            </div>
          </div>
        </div>
      </div>

      <div class=\"row g-3 mt-1\">
        <div class=\"col-12 col-lg-6\">
          <div class=\"card\">
            <div class=\"card-header\">Risk score distribution</div>
            <div class=\"card-body\">
              <canvas id=\"chartRisk\" height=\"120\"></canvas>
            </div>
          </div>
        </div>
        <div class=\"col-12 col-lg-6\">
          <div class=\"card\">
            <div class=\"card-header\">Top reasons</div>
            <div class=\"card-body\">
              <canvas id=\"chartReasons\" height=\"120\"></canvas>
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
                <th>request_log_id</th><th>decision_log_id</th><th>policy_id</th><th>policy_name</th><th>outcome</th><th>risk</th><th>decided_at_local</th><th>reasons</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <script>
      (function() {{
        const day = {payload_day};
        const ctx1 = document.getElementById('chartDay');
        if (ctx1 && window.Chart) {{
          const colors = ['#198754', '#dc3545']; // allow, deny
          const ds = day.datasets.map((d, i) => ({{
            label: d.label,
            data: d.data,
            backgroundColor: colors[i % colors.length],
            borderColor: colors[i % colors.length],
            stack: 'day',
          }}));
          new Chart(ctx1, {{ type: 'bar', data: {{ labels: day.labels, datasets: ds }}, options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true, ticks: {{ precision: 0 }} }} }} }} }});
        }}

        const pol = {payload_policy};
        const ctx2 = document.getElementById('chartPolicy');
        if (ctx2 && window.Chart) {{
          new Chart(ctx2, {{ type: 'bar', data: {{ labels: pol.labels, datasets: [{{ label: 'allow', data: pol.allow, backgroundColor: '#198754', stack: 'pol' }}, {{ label: 'deny', data: pol.deny, backgroundColor: '#dc3545', stack: 'pol' }}] }}, options: {{ indexAxis: 'y', responsive: true, scales: {{ x: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}, y: {{ stacked: true }} }} }} }});
        }}

        const risk = {payload_risk};
        const ctx3 = document.getElementById('chartRisk');
        if (ctx3 && window.Chart) {{
          new Chart(ctx3, {{ type: 'bar', data: {{ labels: risk.labels, datasets: [{{ label: 'count', data: risk.data, backgroundColor: '#0d6efd' }}] }}, options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }} }} }});
        }}

        const reasons = {payload_reasons};
        const ctx4 = document.getElementById('chartReasons');
        if (ctx4 && window.Chart) {{
          new Chart(ctx4, {{ type: 'bar', data: {{ labels: reasons.labels, datasets: [{{ label: 'count', data: reasons.data, backgroundColor: '#6f42c1' }}] }}, options: {{ indexAxis: 'y', responsive: true, scales: {{ x: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }} }} }});
        }}
      }})();
    </script>
    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
  </body>
</html>
"""
    return html_doc
