from pypdf import PdfReader
import sys
import json

def list_fields(path):
    reader = PdfReader(path)
    fields = reader.get_fields()
    if fields:
        print(json.dumps(list(fields.keys()), indent=2))
    else:
        print("No fields found.")

if __name__ == "__main__":
    list_fields(sys.argv[1])
