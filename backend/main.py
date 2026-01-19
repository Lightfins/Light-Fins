from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from fastapi.responses import FileResponse
from pdf_service import PDFService

app = FastAPI(title="Sanlam 16-Page PDF Engine")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "assets", "TR4407-SDM-MP40-SANLAM-INDIVIDUAL-VALUE-FUNERAL-PLA-ELECTRONIC upd.pdf")
MAPPING_PATH = os.path.join(BASE_DIR, "pdf_fill", "mapping.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

pdf_service = PDFService(TEMPLATE_PATH, MAPPING_PATH)

# CORS setup for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    policyholder: Dict
    livesCovered: Dict
    beneficiaries: List
    complianceChecklist: Optional[Dict]
    # Add other fields as per default_formData.json

@app.post("/api/generate-pdf")
async def generate_pdf(data: Dict):
    try:
        output_filename = f"Sanlam_App_{data.get('policyholder', {}).get('surname', 'New')}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        pdf_service.fill_pdf(data, output_path)
        
        return FileResponse(output_path, media_type='application/pdf', filename=output_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug-sample-pdf")
async def debug_sample_pdf():
    try:
        output_path = os.path.join(OUTPUT_DIR, "debug_grid.pdf")
        pdf_service.generate_debug_pdf(output_path)
        return FileResponse(output_path, media_type='application/pdf', filename="debug_grid.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8084))
    uvicorn.run(app, host="0.0.0.0", port=port)
