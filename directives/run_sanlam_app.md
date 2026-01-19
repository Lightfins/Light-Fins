# Running the Sanlam Application

## Goal
Start and run the complete Sanlam funeral policy application (frontend + backend).

## Prerequisites
- Python 3.8+ installed
- Node.js 16+ installed
- All dependencies installed (see below)

## Setup (First Time Only)

### 1. Install Python Dependencies
```bash
cd C:/Users/yolan/Documents/SanlamApp
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Step 1: Start Backend Server
Open a terminal and run:
```bash
python server.py
```

**Expected output:**
```
Sanlam Server running at http://localhost:8084
Press Ctrl+C to stop
```

**Port:** 8084  
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

Generated PDF saved to:
```
C:/Users/yolan/Documents/SanlamApp/Sanlam_application_filled.pdf
```

Intermediate data saved to:
```
C:/Users/yolan/Documents/SanlamApp/.tmp/data_<ID>.json
```

## Troubleshooting

### Backend won't start
**Error:** `Address already in use`  
**Fix:** Port 8084 is taken. Kill the process or change port in `server.py` (line 17)

**Error:** `ModuleNotFoundError: No module named 'pypdf'`  
**Fix:** Run `pip install -r requirements.txt`

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

### 2026-01-18
- React frontend is primary UI (better UX, maintainability)
- Simple HTML prototype kept for quick testing
- Both frontends use same backend API
