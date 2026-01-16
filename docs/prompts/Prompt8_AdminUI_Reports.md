# Prompt 8: Admin UI – Reports Section (Policy Changes)

- What it implements: Add a Reports section to the Admin page with time presets, optional custom From/To, and Generate/Download actions for Policy Changes (HTML default; CSV/NDJSON/JSON optional).
- Dependency: Prompt 7.

## Prompt
```
Write complete and executable React/TypeScript code to update the Admin page:
- Add a "Reports" section with a tab for "Policy Changes"
- Controls:
  - Preset selector (default: Last 24h; others: Last 7d, Last 30d, This month, Last month, Custom)
  - When Custom: From and To datetime pickers
  - Format selector: HTML (default), CSV, NDJSON, JSON
  - Generate (optional preview panel); Download button triggers GET /api/reports/policy-changes with selected params and downloads
- Show basic validation and error handling
- Responsive layout with Bootstrap; accessible labels

Files:
- Frontend: frontend/src/pages/Admin.tsx (extend existing page)
- Optionally add helper in frontend/src/api/reports.ts for calling the endpoint
- Tests: frontend component tests (e.g., with React Testing Library) exercising control wiring and download trigger
```
