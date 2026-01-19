from pypdf import PdfReader
import sys
import json

def get_fields_for_pages(path, pages):
    reader = PdfReader(path)
    res = {}
    for p_idx in pages:
        page = reader.pages[p_idx]
        res[p_idx] = []
        annots = page.get('/Annots')
        if annots:
            for a in annots:
                obj = a.get_object()
                if "/T" in obj:
                    res[p_idx].append({
                        "name": str(obj["/T"]),
                        "alt": str(obj.get("/TU", ""))
                    })
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    get_fields_for_pages(sys.argv[1], [3, 4, 5, 6, 7])
