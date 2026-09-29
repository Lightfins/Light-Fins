---
name: run-sanlam-app
description: Start the Sanlam app locally. Use when asked to run, start, demo, or screenshot the app, or when a submit request returns 404.
---
Pick the backend by the UI's endpoint. Both listen on port 8084, so run exactly one:

| UI | Endpoint | Backend |
|----|----------|---------|
| Wizard (rendered by `App.tsx`) | `POST /api/generate-pdf` | `python backend/main.py` |
| Chat (`useChatFlow.js`), `index.html` prototype | `POST /api/submit-application` | `python server.py` |

Frontend: `cd frontend && npm install && npm run dev` → http://localhost:5173. Vite proxies `/api` to 8084.

Full runbook and troubleshooting: `directives/run_sanlam_app.md`.
