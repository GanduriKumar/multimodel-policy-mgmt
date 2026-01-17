"""
Compliance report renderers for CSV and HTML formats.

Provides rendering functions for EU AI Act, NIST AI RMF, and NIST Privacy Framework
compliance reports in CSV and HTML formats.
"""

from __future__ import annotations
import csv
import io
from typing import Any, Dict


def compliance_to_csv(report_dict: Dict[str, Any]) -> bytes:
    """
    Convert compliance report to CSV format.
    
    Creates a CSV with the following structure:
    - Summary row with overall metrics
    - Framework-specific rows (articles/functions/categories)
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Compliance Report'])
    writer.writerow([''])
    
    # Metadata
    writer.writerow(['Report ID', report_dict.get('report_id', '')])
    writer.writerow(['Policy ID', report_dict.get('policy_id', '')])
    writer.writerow(['Policy Name', report_dict.get('policy_name', '')])
    writer.writerow(['Framework', report_dict.get('framework', '')])
    writer.writerow(['Generated At', report_dict.get('generated_at', '')])
    writer.writerow(['Overall Status', report_dict.get('overall_status', '')])
    writer.writerow(['Compliance Score', f"{report_dict.get('compliance_score', 0):.1f}%"])
    writer.writerow([''])
    
    # Summary
    summary = report_dict.get('summary', {})
    writer.writerow(['Summary'])
    for key, value in summary.items():
        if isinstance(value, (list, dict)):
            writer.writerow([key, str(value)])
        else:
            writer.writerow([key, value])
    writer.writerow([''])
    
    # Framework-specific details
    framework = report_dict.get('framework', '')
    
    if 'EU AI Act' in framework:
        writer.writerow(['Article', 'Title', 'Status', 'Evidence Count', 'Evidence Details', 'Gaps', 'Recommendations'])
        for article in report_dict.get('articles', []):
            evidence_list = article.get('evidence', [])
            evidence_details = []
            for ev in evidence_list:
                ev_type = ev.get('type', 'unknown')
                ev_field = ev.get('field', '')
                ev_value = str(ev.get('value', ''))[:100]
                evidence_details.append(f"{ev_type}: {ev_field} = {ev_value}")
            
            writer.writerow([
                f"Article {article.get('article_number', '')}",
                article.get('article_title', ''),
                article.get('status', ''),
                len(evidence_list),
                ' | '.join(evidence_details) if evidence_details else 'No evidence',
                '; '.join(article.get('gaps', [])),
                '; '.join(article.get('recommendations', []))
            ])
    
    elif 'NIST AI RMF' in framework:
        writer.writerow(['Function', 'Description', 'Status', 'Categories', 'Category Evidence', 'Gaps', 'Recommendations'])
        for func in report_dict.get('functions', []):
            categories = func.get('categories', [])
            cat_evidence = []
            for cat in categories:
                cat_name = cat.get('name', cat.get('category', 'Unknown'))
                evidence_data = cat.get('evidence', [])
                
                # Handle different evidence formats
                if isinstance(evidence_data, list) and evidence_data:
                    for ev in evidence_data[:2]:  # Limit to 2 evidence items per category in CSV
                        if isinstance(ev, dict):
                            ev_type = ev.get('type', 'unknown')
                            ev_value = str(ev.get('value', ''))[:60]
                            cat_evidence.append(f"{cat_name}: {ev_type}={ev_value}")
                        else:
                            cat_evidence.append(f"{cat_name}: {str(ev)[:60]}")
                elif isinstance(evidence_data, str) and evidence_data:
                    cat_evidence.append(f"{cat_name}: {evidence_data[:60]}")
            
            writer.writerow([
                func.get('function_name', ''),
                func.get('function_description', ''),
                func.get('status', ''),
                len(categories),
                ' | '.join(cat_evidence) if cat_evidence else 'No evidence',
                '; '.join(func.get('gaps', [])),
                '; '.join(func.get('recommendations', []))
            ])
        writer.writerow([''])
        writer.writerow(['Trustworthiness Scorecard'])
        scorecard = report_dict.get('trustworthiness_scorecard', {})
        for key, value in scorecard.items():
            if value is not None and key != 'metrics_timestamp':
                writer.writerow([key.replace('_', ' ').title(), value])
    
    elif 'NIST Privacy' in framework:
        writer.writerow(['Function', 'Description', 'Status', 'Categories', 'Category Evidence', 'Gaps', 'Recommendations'])
        for func in report_dict.get('functions', []):
            categories = func.get('categories', [])
            cat_evidence = []
            for cat in categories:
                cat_name = cat.get('name', cat.get('category', 'Unknown'))
                evidence_data = cat.get('evidence', [])
                
                # Handle different evidence formats
                if isinstance(evidence_data, list) and evidence_data:
                    for ev in evidence_data[:2]:  # Limit to 2 evidence items per category in CSV
                        if isinstance(ev, dict):
                            ev_type = ev.get('type', 'unknown')
                            ev_value = str(ev.get('value', ''))[:60]
                            cat_evidence.append(f"{cat_name}: {ev_type}={ev_value}")
                        else:
                            cat_evidence.append(f"{cat_name}: {str(ev)[:60]}")
                elif isinstance(evidence_data, str) and evidence_data:
                    cat_evidence.append(f"{cat_name}: {evidence_data[:60]}")
            
            writer.writerow([
                func.get('function_name', ''),
                func.get('function_description', ''),
                func.get('status', ''),
                len(categories),
                ' | '.join(cat_evidence) if cat_evidence else 'No evidence',
                '; '.join(func.get('gaps', [])),
                '; '.join(func.get('recommendations', []))
            ])
        writer.writerow([''])
        writer.writerow(['Privacy Metrics'])
        metrics = report_dict.get('privacy_metrics', {})
        for key, value in metrics.items():
            if value is not None and key != 'metrics_timestamp':
                writer.writerow([key.replace('_', ' ').title(), value])
    
    # Add UTF-8 BOM for Excel compatibility
    content = output.getvalue()
    return '\ufeff'.encode('utf-8') + content.encode('utf-8')


def compliance_to_html(report_dict: Dict[str, Any]) -> str:
    """
    Convert compliance report to HTML format with styled presentation.
    """
    framework = report_dict.get('framework', '')
    policy_name = report_dict.get('policy_name', 'Unknown')
    overall_status = report_dict.get('overall_status', 'unknown')
    compliance_score = report_dict.get('compliance_score', 0)
    
    # Status color mapping
    status_colors = {
        'compliant': '#28a745',
        'partial': '#ffc107',
        'non_compliant': '#dc3545',
        'not_applicable': '#6c757d',
        'validated': '#28a745',
        'draft': '#17a2b8'
    }
    
    status_color = status_colors.get(overall_status, '#6c757d')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{framework} Compliance Report - {policy_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid {status_color};
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        .metadata-label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .metadata-value {{
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
        }}
        .status-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            color: white;
            background: {status_color};
            font-weight: 600;
            font-size: 0.9em;
        }}
        .score {{
            font-size: 2em;
            font-weight: bold;
            color: {status_color};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #dee2e6;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
            vertical-align: top;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .status-compliant {{ color: #28a745; font-weight: 600; }}
        .status-partial {{ color: #ffc107; font-weight: 600; }}
        .status-non_compliant {{ color: #dc3545; font-weight: 600; }}
        .status-not_applicable {{ color: #6c757d; font-weight: 600; }}
        .list-items {{
            margin: 0;
            padding-left: 20px;
        }}
        .list-items li {{
            margin: 4px 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-card-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        .summary-card-label {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{framework} Compliance Report</h1>
        
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Policy</div>
                <div class="metadata-value">{policy_name}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Report ID</div>
                <div class="metadata-value">{report_dict.get('report_id', 'N/A')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Generated</div>
                <div class="metadata-value">{report_dict.get('generated_at', 'N/A')[:19]}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Overall Status</div>
                <div class="metadata-value">
                    <span class="status-badge">{overall_status.replace('_', ' ').title()}</span>
                </div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Compliance Score</div>
                <div class="metadata-value">
                    <span class="score">{compliance_score:.1f}%</span>
                </div>
            </div>
        </div>
"""
    
    # Summary section
    summary = report_dict.get('summary', {})
    if summary:
        html += """
        <h2>Summary</h2>
        <div class="summary-grid">
"""
        for key, value in summary.items():
            if not isinstance(value, (list, dict)):
                label = key.replace('_', ' ').title()
                html += f"""
            <div class="summary-card">
                <div class="summary-card-value">{value}</div>
                <div class="summary-card-label">{label}</div>
            </div>
"""
        html += "        </div>\n"
    
    # Framework-specific content
    if 'EU AI Act' in framework:
        articles = report_dict.get('articles', [])
        if articles:
            html += """
        <h2>Article Assessment</h2>
        <table>
            <thead>
                <tr>
                    <th>Article</th>
                    <th>Requirement</th>
                    <th>Status</th>
                    <th>Evidence</th>
                    <th>Gaps & Recommendations</th>
                </tr>
            </thead>
            <tbody>
"""
            for article in articles:
                status_class = f"status-{article.get('status', 'unknown')}"
                evidence_list = article.get('evidence', [])
                html += f"""
                <tr>
                    <td><strong>Article {article.get('article_number', '')}</strong><br>
                        <small>{article.get('article_title', '')}</small>
                    </td>
                    <td>{article.get('requirement', 'N/A')}</td>
                    <td class="{status_class}">{article.get('status', 'unknown').replace('_', ' ').title()}</td>
                    <td>
"""
                # Display evidence details
                if evidence_list:
                    html += f"                        <strong>{len(evidence_list)} Evidence Items:</strong><ul class='list-items'>\n"
                    for ev in evidence_list:
                        ev_type = ev.get('type', 'unknown')
                        ev_field = ev.get('field', '')
                        ev_value = str(ev.get('value', ''))[:100]  # Truncate long values
                        if len(str(ev.get('value', ''))) > 100:
                            ev_value += '...'
                        html += f"                            <li><strong>{ev_type}</strong>: {ev_field} = {ev_value}</li>\n"
                    html += "                        </ul>\n"
                else:
                    html += "                        <em>No evidence found</em>\n"
                html += """
                    </td>
                    <td>
"""
                gaps = article.get('gaps', [])
                recommendations = article.get('recommendations', [])
                if gaps:
                    html += "                        <strong>Gaps:</strong><ul class='list-items'>\n"
                    for gap in gaps:
                        html += f"                            <li>{gap}</li>\n"
                    html += "                        </ul>\n"
                if recommendations:
                    html += "                        <strong>Recommendations:</strong><ul class='list-items'>\n"
                    for rec in recommendations:
                        html += f"                            <li>{rec}</li>\n"
                    html += "                        </ul>\n"
                if not gaps and not recommendations:
                    html += "                        <em>No gaps or recommendations</em>\n"
                html += """
                    </td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
    
    elif 'NIST AI RMF' in framework:
        functions = report_dict.get('functions', [])
        if functions:
            html += """
        <h2>Function Assessment</h2>
        <table>
            <thead>
                <tr>
                    <th>Function</th>
                    <th>Status</th>
                    <th>Categories</th>
                    <th>Gaps & Recommendations</th>
                </tr>
            </thead>
            <tbody>
"""
            for func in functions:
                status_class = f"status-{func.get('status', 'unknown')}"
                categories = func.get('categories', [])
                html += f"""
                <tr>
                    <td><strong>{func.get('function_name', '')}</strong><br>
                        <small>{func.get('function_description', '')}</small>
                    </td>
                    <td class="{status_class}">{func.get('status', 'unknown').replace('_', ' ').title()}</td>
                    <td>
"""
                # Display category details with evidence
                if categories:
                    html += f"                        <strong>{len(categories)} Categories:</strong><ul class='list-items'>\n"
                    for cat in categories:
                        cat_name = cat.get('name', cat.get('category', 'Unknown'))
                        cat_status = cat.get('status', 'unknown')
                        evidence_data = cat.get('evidence', [])
                        
                        html += f"                            <li><strong>{cat_name}</strong> ({cat_status})<br>\n"
                        
                        # Handle different evidence formats
                        if isinstance(evidence_data, list):
                            # List of evidence dictionaries
                            if evidence_data:
                                html += "                                <small>Evidence:</small><ul>\n"
                                for ev in evidence_data[:3]:  # Limit to first 3 evidence items per category
                                    if isinstance(ev, dict):
                                        ev_type = ev.get('type', 'unknown')
                                        ev_value = str(ev.get('value', ''))[:80]
                                        if len(str(ev.get('value', ''))) > 80:
                                            ev_value += '...'
                                        html += f"                                    <li>{ev_type}: {ev_value}</li>\n"
                                    else:
                                        html += f"                                    <li>{str(ev)[:80]}</li>\n"
                                if len(evidence_data) > 3:
                                    html += f"                                    <li><em>...and {len(evidence_data) - 3} more</em></li>\n"
                                html += "                                </ul>\n"
                            else:
                                html += "                                <small><em>No evidence</em></small>\n"
                        elif isinstance(evidence_data, str) and evidence_data:
                            # String evidence
                            html += f"                                <small>Evidence: {evidence_data[:100]}</small>\n"
                        else:
                            html += "                                <small><em>No evidence</em></small>\n"
                        
                        html += "                            </li>\n"
                    html += "                        </ul>\n"
                else:
                    html += "                        <em>No categories assessed</em>\n"
                html += """
                    </td>
                    <td>
"""
                gaps = func.get('gaps', [])
                recommendations = func.get('recommendations', [])
                if gaps:
                    html += "                        <strong>Gaps:</strong><ul class='list-items'>\n"
                    for gap in gaps:
                        html += f"                            <li>{gap}</li>\n"
                    html += "                        </ul>\n"
                if recommendations:
                    html += "                        <strong>Recommendations:</strong><ul class='list-items'>\n"
                    for rec in recommendations:
                        html += f"                            <li>{rec}</li>\n"
                    html += "                        </ul>\n"
                if not gaps and not recommendations:
                    html += "                        <em>No gaps or recommendations</em>\n"
                html += """
                    </td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        # Trustworthiness scorecard
        scorecard = report_dict.get('trustworthiness_scorecard', {})
        if scorecard:
            html += """
        <h2>Trustworthiness Scorecard</h2>
        <div class="summary-grid">
"""
            for key, value in scorecard.items():
                if value is not None and key != 'metrics_timestamp':
                    label = key.replace('_', ' ').title()
                    html += f"""
            <div class="summary-card">
                <div class="summary-card-value">{value if isinstance(value, (int, float)) else 'N/A'}</div>
                <div class="summary-card-label">{label}</div>
            </div>
"""
            html += "        </div>\n"
    
    elif 'NIST Privacy' in framework:
        functions = report_dict.get('functions', [])
        if functions:
            html += """
        <h2>Function Assessment</h2>
        <table>
            <thead>
                <tr>
                    <th>Function</th>
                    <th>Status</th>
                    <th>Categories</th>
                    <th>Gaps & Recommendations</th>
                </tr>
            </thead>
            <tbody>
"""
            for func in functions:
                status_class = f"status-{func.get('status', 'unknown')}"
                categories = func.get('categories', [])
                html += f"""
                <tr>
                    <td><strong>{func.get('function_name', '')}</strong><br>
                        <small>{func.get('function_description', '')}</small>
                    </td>
                    <td class="{status_class}">{func.get('status', 'unknown').replace('_', ' ').title()}</td>
                    <td>
"""
                # Display category details with evidence
                if categories:
                    html += f"                        <strong>{len(categories)} Categories:</strong><ul class='list-items'>\n"
                    for cat in categories:
                        cat_name = cat.get('name', cat.get('category', 'Unknown'))
                        cat_status = cat.get('status', 'unknown')
                        evidence_data = cat.get('evidence', [])
                        
                        html += f"                            <li><strong>{cat_name}</strong> ({cat_status})<br>\n"
                        
                        # Handle different evidence formats
                        if isinstance(evidence_data, list):
                            # List of evidence dictionaries
                            if evidence_data:
                                html += "                                <small>Evidence:</small><ul>\n"
                                for ev in evidence_data[:3]:  # Limit to first 3 evidence items per category
                                    if isinstance(ev, dict):
                                        ev_type = ev.get('type', 'unknown')
                                        ev_value = str(ev.get('value', ''))[:80]
                                        if len(str(ev.get('value', ''))) > 80:
                                            ev_value += '...'
                                        html += f"                                    <li>{ev_type}: {ev_value}</li>\n"
                                    else:
                                        html += f"                                    <li>{str(ev)[:80]}</li>\n"
                                if len(evidence_data) > 3:
                                    html += f"                                    <li><em>...and {len(evidence_data) - 3} more</em></li>\n"
                                html += "                                </ul>\n"
                            else:
                                html += "                                <small><em>No evidence</em></small>\n"
                        elif isinstance(evidence_data, str) and evidence_data:
                            # String evidence
                            html += f"                                <small>Evidence: {evidence_data[:100]}</small>\n"
                        else:
                            html += "                                <small><em>No evidence</em></small>\n"
                        
                        html += "                            </li>\n"
                    html += "                        </ul>\n"
                else:
                    html += "                        <em>No categories assessed</em>\n"
                html += """
                    </td>
                    <td>
"""
                gaps = func.get('gaps', [])
                recommendations = func.get('recommendations', [])
                if gaps:
                    html += "                        <strong>Gaps:</strong><ul class='list-items'>\n"
                    for gap in gaps:
                        html += f"                            <li>{gap}</li>\n"
                    html += "                        </ul>\n"
                if recommendations:
                    html += "                        <strong>Recommendations:</strong><ul class='list-items'>\n"
                    for rec in recommendations:
                        html += f"                            <li>{rec}</li>\n"
                    html += "                        </ul>\n"
                if not gaps and not recommendations:
                    html += "                        <em>No gaps or recommendations</em>\n"
                html += """
                    </td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        # Privacy metrics
        metrics = report_dict.get('privacy_metrics', {})
        if metrics:
            html += """
        <h2>Privacy Metrics</h2>
        <div class="summary-grid">
"""
            for key, value in metrics.items():
                if value is not None and key != 'metrics_timestamp':
                    label = key.replace('_', ' ').title()
                    html += f"""
            <div class="summary-card">
                <div class="summary-card-value">{value if isinstance(value, (int, float)) else 'N/A'}</div>
                <div class="summary-card-label">{label}</div>
            </div>
"""
            html += "        </div>\n"
    
    # Report hash for verification
    report_hash = report_dict.get('report_sha256', '')
    if report_hash:
        html += f"""
        <div style="margin-top: 40px; padding: 15px; background: #f8f9fa; border-radius: 6px; font-size: 0.85em; color: #666;">
            <strong>Report Hash (SHA-256):</strong> <code style="font-size: 0.9em;">{report_hash}</code><br>
            This immutable hash can be used to verify report integrity.
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html
