import os
import json
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

class PDFService:
    def __init__(self, template_path, mapping_path):
        self.template_path = template_path
        self.mapping_path = mapping_path
        self.mapping = self._load_mapping()

    def _load_mapping(self):
        if os.path.exists(self.mapping_path):
            with open(self.mapping_path, 'r') as f:
                return json.load(f)
        return {}

    def generate_overlay(self, data):
        packet = BytesIO()
        # Create a new PDF with Reportlab
        can = canvas.Canvas(packet, pagesize=A4)
        
        # Iterating through all mapped fields
        # structure of mapping.json: { "field_key": { "page": 0, "x": 100, "y": 200, "type": "text" } }
        for key, field in self.mapping.items():
            page_num = field.get('page', 0)
            x = field.get('x', 0)
            y = field.get('y', 0)
            field_type = field.get('type', 'text')
            
            # Resolve data value using dotted notation if necessary
            val = self._get_value(data, key)
            if not val:
                continue

            # Switch to correct page in overlay if needed
            # (Note: simpler to create one overlay page per template page and merge)
            # For now, we'll assume the mapping includes page index and we draw only if active page
            
        can.save()
        packet.seek(0)
        return packet

    def _get_value(self, data, path):
        keys = path.split('.')
        rv = data
        for key in keys:
            if isinstance(rv, dict):
                rv = rv.get(key)
            elif isinstance(rv, list) and key.isdigit():
                rv = rv[int(key)]
            else:
                return None
        return rv

    def fill_pdf(self, data, output_path):
        existing_pdf = PdfReader(self.template_path)
        output = PdfWriter()

        # Group mapping by type: field vs coordinate
        field_mappings = {}
        coord_mappings = {}

        for key, field in self.mapping.items():
            if 'pypdf_name' in field:
                field_mappings[field['pypdf_name']] = str(self._get_value(data, key) or "")
            else:
                p = field.get('page', 0)
                if p not in coord_mappings:
                    coord_mappings[p] = []
                coord_mappings[p].append((key, field))

        # First, fill all form fields globally (pypdf does this well)
        output.append_pages_from_reader(existing_pdf)
        output.update_page_form_field_values(output.pages[0], field_mappings) # Note: pypdf filling is often global but can be page-specific. 
        # Actually, for complex forms, it's better to update the fields in the writer.
        
        # Second, apply coordinate overlays page-by-page
        for i in range(len(output.pages)):
            if i in coord_mappings:
                page = output.pages[i]
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=A4)
                for key, field in coord_mappings[i]:
                    val = str(self._get_value(data, key) or "")
                    if val:
                        can.drawString(field['x'], field['y'], val)
                can.save()
                packet.seek(0)
                overlay_pdf = PdfReader(packet)
                page.merge_page(overlay_pdf.pages[0])

        with open(output_path, "wb") as outputStream:
            output.write(outputStream)

    def generate_debug_pdf(self, output_path):
        """Generates a PDF showing coordinates for alignment."""
        existing_pdf = PdfReader(open(self.template_path, "rb"))
        output = PdfWriter()

        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)
            can.setFont("Helvetica", 8)
            can.setStrokeColorRGB(1, 0, 0) # Red
            
            # Draw a grid
            for x in range(0, 600, 50):
                can.line(x, 0, x, 842)
                can.drawString(x, 10, str(x))
            for y in range(0, 850, 50):
                can.line(0, y, 595, y)
                can.drawString(10, y, str(y))
                
            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

        with open(output_path, "wb") as outputStream:
            output.write(outputStream)
