# PDF Application Generation Workflow

## Goal
Generate a filled Sanlam funeral policy PDF application from user data.

## Inputs
- **Application data** (JSON file in `.tmp/`)
- **Template PDF** (`Sanlam application.pdf`)
- **Field mapping** (`execution/mapping.json`)

## Tools / Scripts

### `execution/fill_sanlam_pdf.py`
Fills PDF form fields with application data.

**Usage:**
```bash
python execution/fill_sanlam_pdf.py <template.pdf> <data.json> <mapping.json> <output.pdf>
```

**Example:**
```bash
python execution/fill_sanlam_pdf.py \
  "Sanlam application.pdf" \
  ".tmp/data_9001015000087.json" \
  "execution/mapping.json" \
  "Sanlam_application_filled.pdf"
```

### `execution/extract_pdf_fields.py`
Extracts all form fields from PDF (for debugging/mapping).

**Usage:**
```bash
python execution/extract_pdf_fields.py "Sanlam application.pdf"
```

**Output:** `sanlam_pdf_fields_inventory.json`

### `execution/validate_application_data.py`
Validates application data before PDF generation.

**Usage:**
```bash
python execution/validate_application_data.py ".tmp/data.json"
```

## Data Flow

```
User Input (Frontend)
    ↓
server.py (Orchestration)
    ↓
Validation (validate_application_data.py)
    ↓
PDF Filling (fill_sanlam_pdf.py)
    ↓
Output PDF
```

**Status:** `server.py` calls `fill_sanlam_pdf.py` directly today. Run `validate_application_data.py` yourself before filling until the server wires it in.

**Second pipeline:** the Wizard UI uses `backend/main.py` → `backend/pdf_service.py`, with template `backend/assets/TR4407-…ELECTRONIC upd.pdf` and mapping `backend/pdf_fill/mapping.json` (`{"key": {"pypdf_name": …}}` format). Edit the mapping that belongs to the pipeline you are changing.

## Field Mapping

The `mapping.json` file maps application data to PDF field names:

```json
{
  "policyholder.first_names": "Text1",
  "policyholder.surname": "Text2",
  "policyholder.id_number": "Text3"
}
```

**Key format:** JSONPath to data  
**Value:** PDF field name (from template)

## Outputs

### Success
- PDF file created at specified output path
- Console log: "✓ PDF generated successfully"
- Return code: 0

### Failure
- Error message printed to stderr
- Return code: 1
- Common errors:
  - Template PDF not found
  - Invalid JSON data
  - Field not found in PDF
  - Permission denied (file locked)

## Edge Cases

### Missing Optional Fields
**Behavior:** Skip field, continue processing  
**Example:** Spouse data empty → spouse fields left blank

### Invalid ID Number
**Behavior:** Validation fails, escalate to manual review  
**Fix:** Check ID format (13 digits, valid checksum)

### PDF Field Name Changed
**Behavior:** Field not found error  
**Fix:** Re-run `extract_pdf_fields.py` and update `mapping.json`

### File Locked (PDF open in viewer)
**Behavior:** Permission denied error  
**Fix:** Close PDF viewer, retry

## Testing

### Test with Mock Data
```bash
python test_pdf_gen.py
```

This creates test data and generates a PDF to verify the workflow.

### Manual Verification
1. Open generated PDF
2. Check all fields populated correctly
3. Verify formatting (no truncation)
4. Check signatures/dates

## Learnings

### 2026-01-10
- PDF field names are case-sensitive
- Some fields have character limits (e.g., phone: 10 chars)
- Extended family members require dynamic field mapping

### 2026-01-18
- Validation should happen before PDF generation
- Better error messages needed for field mapping failures
- Consider adding field length validation

### 2026-09-29
- Neither backend runs the validator yet, and `server.py` fills missing bank details with placeholder values. A PDF can look complete while its data is missing.
- Re-extracting fields overwrites the committed `sanlam_pdf_fields_inventory.json` (~100 KB). Use the manual `/remap-pdf-fields` skill.
