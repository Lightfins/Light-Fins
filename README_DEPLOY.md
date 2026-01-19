# Sanlam Application Deployment Guide

This guide provides instructions for deploying the overhauled Sanlam 16-Page Application.

## Local Development Setup

### 1. Backend (FastAPI)
The backend handles the PDF generation and coordinates mapping.
- **Python Version**: 3.14 recommended.
- **Dependencies**: `pip install fastapi uvicorn pypdf reportlab`
- **Run**: 
  ```powershell
  python backend/main.py
  ```
- **Port**: Runs on `http://localhost:8084`

### 2. Frontend (React + Vite)
The frontend is a multi-step wizard using Sanlam's corporate identity.
- **Dependencies**: `npm install` inside the `frontend` directory.
- **Run**:
  ```powershell
  npm run dev
  ```
- **Proxy**: Vite is pre-configured to proxy `/api` requests to port 8084.

## Cloud Deployment

### 1. Backend (e.g., Render, Railway, AWS)
- Deploy the `backend/` directory as a FastAPI service.
- Set the `TEMPLATE_PATH` environment variable if your hosting differs from local paths.
- Ensure `assets/TR4407-SDM-MP40-SANLAM-INDIVIDUAL-VALUE-FUNERAL-PLA-ELECTRONIC upd.pdf` is included in the build.

### 2. Frontend (e.g., Netlify, Vercel)
- Deploy the `frontend/` directory.
- Set the `VITE_API_URL` (if configured) or update the `vite.config.js` proxy for production environments.
- Note: If using Netlify, ensure the backend URL is accessible to the client or use a serverless function proxy.

## Troubleshooting
- **PDF Page Count**: The engine enforces exactly 16 pages. If the template is modified, ensure the page index in `mapping.json` is updated.
- **Missing Fields**: Use `GET /api/debug-sample-pdf` to see the coordinate grid for fine-tuning text placement.
