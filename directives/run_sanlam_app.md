# Running the Sanlam Application

## Goal
Start and run the complete Sanlam funeral policy application (frontend + backend).

## Prerequisites
- Python 3.8+ installed
- Node.js 16+ installed
- All dependencies installed (see below)

## Setup (First Time Only)

### 1. Install Python Dependencies
From the repo root:
```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Step 1: Start the Backend That Matches the UI
Both backends listen on port 8084. Run one of them:

| UI | Calls | Start |
|----|-------|-------|
| Wizard (`components/Wizard`, rendered by `App.tsx`) | `POST /api/generate-pdf` | `python backend/main.py` (needs `pip install -r backend/requirements.txt`) |
| Chat (`hooks/useChatFlow.js`) and the `index.html` prototype | `POST /api/submit-application` | `python server.py` |

**Purpose:** Handles API requests, orchestrates execution scripts

### Step 2: Start Frontend (New Terminal)
Open a **second terminal** and run:
```bash
cd frontend
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**Port:** 5173  
**Purpose:** Serves React UI

### Step 3: Access Application
Open browser to: `http://localhost:5173`

## User Flow

1. **Select Plan**: Choose "Value Funeral Plan" or "All-in-One"
2. **Chat Interface**: Answer questions one at a time
3. **Premium Display**: See real-time pricing as you answer
4. **Family Selection**: (All-in-One only) Add family members visually
5. **Signature**: Sign digitally on canvas
6. **Submit**: Application generates PDF automatically

## Output

- `server.py` → `Sanlam_application_filled.pdf` in the repo root; intermediate data in `.tmp/data_<ID>.json`
- `backend/main.py` → `backend/output/Sanlam_App_<surname>.pdf`, returned as a download

## Troubleshooting

### Backend won't start
**Error:** `Address already in use`  
**Fix:** Port 8084 is taken, usually by the other backend. Stop it, or change `PORT` in `server.py` / the `PORT` env var for `backend/main.py`.

**Error:** `ModuleNotFoundError: No module named 'pypdf'`  
**Fix:** Run `pip install -r requirements.txt`

### Submit returns 404
**Cause:** The running backend does not serve the UI's endpoint (see the Step 1 table).
**Fix:** Start the other backend.

### Frontend won't start
**Error:** `Cannot find module`  
**Fix:** Run `npm install` in `frontend/` directory

**Error:** `Port 5173 already in use`  
**Fix:** Kill existing Vite process or change port in `vite.config.js`

### PDF generation fails
**Error:** `FileNotFoundError: Sanlam application.pdf`  
**Fix:** Ensure template PDF exists in root directory

**Error:** `Field not found in PDF`  
**Fix:** Check `execution/mapping.json` - field names may have changed

## Stopping the Application

1. Press `Ctrl+C` in backend terminal
2. Press `Ctrl+C` in frontend terminal

## Alternative: Simple Prototype

For quick demos without React:
```bash
python server.py
```
Then open `index.html` directly in browser (uses simple HTML/CSS/JS)

## Learnings

### 2026-09-29
- The two backends serve different endpoints on the same port. Pick the backend by the UI's endpoint (Step 1 table).
- Paths are repo-relative. The original author's Windows paths were removed.

### 2026-01-18
- React frontend is primary UI (better UX, maintainability)
- Simple HTML prototype kept for quick testing
- Both frontends use same backend API
