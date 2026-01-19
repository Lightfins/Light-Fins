from pypdf import PdfReader
import sys
import json

def discover_per_page(path):
    reader = PdfReader(path)
    res = {}
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        res[i] = []
        if "/Annots" in page:
            for annot in page["/Annots"]:
                obj = annot.get_object()
                if "/T" in obj:
                    res[i].append({
                        "name": str(obj["/T"]),
                        "alt": str(obj.get("/TU", ""))
                    })
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    discover_per_page(sys.argv[1])
