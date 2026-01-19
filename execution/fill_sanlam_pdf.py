from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, DictionaryObject
import json
import sys
from typing import Any, Dict

def get_by_path(data: Dict[str, Any], path: str) -> Any:
    """
    Get value from nested dict using dot notation.
    Supports: 'policyholder.surname' and 'beneficiaries.0.first_names'
    """
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                idx = int(part)
                cur = cur[idx] if idx < len(cur) else None
            except (ValueError, TypeError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        
        if cur is None:
            return None
    return cur

def set_need_appearances(reader: PdfReader):
    """
    Set NeedAppearances flag to help PDF viewers render filled values.
    Critical for displaying filled text in many viewers.
    """
    if "/AcroForm" not in reader.trailer["/Root"]:
        reader.trailer["/Root"]["/AcroForm"] = {}
    acro = reader.trailer["/Root"]["/AcroForm"]
    acro.update({"/NeedAppearances": True})

def main(template_pdf: str, data_json: str, mapping_json: str, out_pdf: str):
    # Load data
    with open(data_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Compute convenience values
    if "policyholder" in data:
        ph = data["policyholder"]
        full_name = " ".join([
            x for x in [
                ph.get("first_names", ""), 
                ph.get("surname", "")
            ] if x
        ]).strip()
        data.setdefault("policyholder", {})["full_name"] = full_name

    # Load mapping
    with open(mapping_json, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Read template and clone to writer (preserves form structure)
    try:
        writer = PdfWriter(clone_from=template_pdf)
    except Exception as e:
        # Fallback for older pypdf versions or if clone fails
        print(f"Clone failed: {e}, attempting manual copy")
        reader = PdfReader(template_pdf)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        # Copy AcroForm if present
        if "/AcroForm" in reader.trailer["/Root"]:
            writer._root_object.update({
                NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
            })

    # Set NeedAppearances
    try:
        if "/AcroForm" not in writer.root_object:
            writer.root_object.update({
                NameObject("/AcroForm"): DictionaryObject()
            })
        writer.root_object["/AcroForm"].update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })
    except Exception as e:
        print(f"Warning setting NeedAppearances: {e}")

    # Build PDF field values dict
    pdf_values: Dict[str, Any] = {}
    skipped = []
    
    for backend_key, pdf_field in mapping.items():
        if backend_key.startswith("_"):  # Skip comments
            continue
            
        val = get_by_path(data, backend_key)
        if val is None:
            continue
        
        # Skip complex types (dicts, lists)
        if isinstance(val, (dict, list)):
            skipped.append(backend_key)
            continue
        
        # Convert to string for PDF text fields
        pdf_values[pdf_field] = str(val)

    # Fill the form fields
    for i in range(len(writer.pages)):
        writer.update_page_form_field_values(
            writer.pages[i], 
            pdf_values,
            auto_regenerate=False
        )

    # Write output
    with open(out_pdf, "wb") as f:
        writer.write(f)

    # Report
    print(f"Verified Wrote: {out_pdf}")
    print(f"  Filled fields: {len(pdf_values)}")
    if skipped:
        print(f"  Skipped complex types: {len(skipped)}")
    
    # Check for unmapped but available data
    all_keys = set()
    def collect_keys(d, prefix=""):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                collect_keys(v, path)
            elif isinstance(v, list):
                for idx, item in enumerate(v):
                    if isinstance(item, dict):
                        collect_keys(item, f"{path}.{idx}")
            else:
                all_keys.add(path)
    
    collect_keys(data)
    mapped_keys = {k for k in mapping.keys() if not k.startswith("_")}
    unmapped = all_keys - mapped_keys
    
    if unmapped and len(unmapped) < 20:  # Don't spam if many unmapped
        print(f"\n  [INFO] Unmapped data keys ({len(unmapped)}):")
        for k in sorted(unmapped)[:10]:
            print(f"    - {k}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python fill_sanlam_pdf.py <template.pdf> <data.json> <mapping.json> <output.pdf>")
        sys.exit(1)

    template_pdf = sys.argv[1]
    data_json = sys.argv[2]
    mapping_json = sys.argv[3]
    out_pdf = sys.argv[4]
    
    main(template_pdf, data_json, mapping_json, out_pdf)
