from pypdf import PdfReader
import sys

def check_pdf(path):
    try:
        reader = PdfReader(path)
        print(f"PDF: {path}")
        print(f"Pages: {len(reader.pages)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pdf(sys.argv[1])
