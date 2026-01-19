from pypdf import PdfReader
import sys
import json

def list_fields_ext(path):
    reader = PdfReader(path)
    fields = reader.get_fields()
    res = {}
    if fields:
        for name, field in fields.items():
            res[name] = {
                "type": str(field.get('/FT', 'Unknown')),
                "value": str(field.get('/V', '')),
                "alt": str(field.get('/TU', ''))
            }
        print(json.dumps(res, indent=2))
    else:
        print("No fields found.")

if __name__ == "__main__":
    list_fields_ext(sys.argv[1])
