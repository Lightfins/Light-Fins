from pypdf import PdfReader
from pypdf.generic import NameObject
import json
import sys

def extract_widgets(pdf_path: str):
    """
    Extract all form fields from PDF with their properties.
    Returns both field tree and widget annotations.
    """
    r = PdfReader(pdf_path)

    # Field tree (hierarchical field structure)
    field_tree = r.get_fields() or {}
    field_tree_out = []
    for k, v in field_tree.items():
        field_tree_out.append({
            "name": k,
            "ft": str(v.get("/FT")) if v else None,
            "tu": str(v.get("/TU")) if v else None,
            "ff": int(v.get("/Ff")) if v and v.get("/Ff") is not None else None
        })

    # Widget annotations (actual form fields on pages)
    widgets = []
    for pi, page in enumerate(r.pages):
        annots = page.get("/Annots")
        if not annots:
            continue
        for a in annots:
            obj = a.get_object()
            if obj.get("/Subtype") != NameObject("/Widget"):
                continue

            name = obj.get("/T")
            if name is None:
                continue

            ft = obj.get("/FT")
            rect = obj.get("/Rect")
            tu = obj.get("/TU")

            widgets.append({
                "name": str(name),
                "type": str(ft) if ft else None,
                "tooltip": str(tu) if tu else None,
                "page": pi + 1,
                "rect": [float(x) for x in rect] if rect else None
            })

    return {
        "pdf": pdf_path,
        "pages": len(r.pages),
        "field_tree_count": len(field_tree_out),
        "widget_count": len(widgets),
        "field_tree": sorted(field_tree_out, key=lambda x: x["name"]),
        "widgets": sorted(widgets, key=lambda x: (x["page"], x["name"]))
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_fields.py 'Sanlam application.pdf'")
        sys.exit(1)

    pdf_path = sys.argv[1]
    out = extract_widgets(pdf_path)

    with open("sanlam_pdf_fields_inventory.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✓ Wrote: sanlam_pdf_fields_inventory.json")
    print(f"  Pages: {out['pages']}")
    print(f"  Field tree entries: {out['field_tree_count']}")
    print(f"  Widget fields: {out['widget_count']}")
    print("\nNext steps:")
    print("1. Open sanlam_pdf_fields_inventory.json")
    print("2. Use the 'widgets' array to map fields by page and position")
    print("3. Update mapping.json with correct field names")
