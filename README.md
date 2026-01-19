# Sanlam Funeral Policy Application

> **3-Layer Architecture**: This application follows a strict separation between directives (what to do), orchestration (decision-making), and execution (deterministic scripts).

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: DIRECTIVES (What to do)                        │
│ └─ directives/*.md - SOPs and instructions              │
├─────────────────────────────────────────────────────────┤
│ Layer 2: ORCHESTRATION (Decision-making)                │
│ └─ server.py - Routes requests to execution scripts     │
├─────────────────────────────────────────────────────────┤
│ Layer 3: EXECUTION (Deterministic work)                 │
│ └─ execution/*.py - PDF filling, pricing, validation    │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for React frontend)

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 3. Start the Backend Server
```bash
python server.py
```
Server runs on `http://localhost:8084`

### 4. Start the Frontend (in a new terminal)
```bash
cd frontend
npm run dev
```
Frontend runs on `http://localhost:5173`

### 5. Access the Application
Open your browser to `http://localhost:5173`

## 📁 Project Structure

```
C:\Users\yolan\Documents\SanlamApp\
├── directives/              # Layer 1: Instructions
│   ├── sanlam_funeral_policy.md
│   ├── sanlam_all_in_one.md
│   ├── run_sanlam_app.md
│   └── generate_pdf_application.md
├── execution/               # Layer 3: Deterministic scripts
│   ├── pricing_engine.py
│   ├── fill_sanlam_pdf.py
│   ├── extract_pdf_fields.py
│   ├── application_form.py
│   ├── validate_application_data.py
│   └── mapping.json
├── frontend/                # UI (React + Vite)
│   ├── src/
│   └── package.json
├── .tmp/                    # Intermediate files (gitignored)
├── server.py                # Layer 2: Orchestration
├── index.html               # Simple prototype (optional)
├── app.js                   # Simple prototype (optional)
└── README.md                # This file
```

## 🔧 How It Works

1. **User interacts** with React frontend
2. **Frontend sends** application data to `server.py` via API
3. **Server orchestrates** by calling execution scripts
4. **Execution scripts** generate PDF using deterministic logic
5. **PDF returned** to user

## 📋 Available Scripts

### Test PDF Generation
```bash
python test_pdf_gen.py
```

### Extract PDF Fields (for debugging)
```bash
python execution/extract_pdf_fields.py "Sanlam application.pdf"
```

### Validate Application Data
```bash
python execution/validate_application_data.py .tmp/data.json
```

## 🎯 Key Features

- ✅ AI-driven chat interface
- ✅ Real-time premium calculation
- ✅ Family member selection with visual UI
- ✅ Digital signature capture
- ✅ Automatic PDF form filling
- ✅ POPIA compliance built-in

## 🐛 Troubleshooting

**Server won't start:**
- Check if port 8084 is available
- Ensure Python dependencies are installed

**Frontend won't start:**
- Run `npm install` in `frontend/` directory
- Check if port 5173 is available

**PDF generation fails:**
- Verify `Sanlam application.pdf` exists in root
- Check `execution/mapping.json` is valid
- Review logs in `.tmp/` directory

## 📚 Documentation

See `directives/` folder for detailed SOPs on:
- Running the application
- PDF generation workflow
- Product specifications

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure:
```bash
# Currently no external APIs required
# Add keys here as needed
```

## 🧪 Testing

The application uses a self-annealing approach:
1. Run the workflow
2. If errors occur, fix the execution script
3. Update the directive with learnings
4. System becomes more robust

## 📝 License

Internal use only - Sanlam funeral policy application.
