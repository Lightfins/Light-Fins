
import http.server
import socketserver
import json
import os
import sys

# Ensure we can import from the execution directory
sys.path.append(os.getcwd())

try:
    from execution.application_form import create_application
    from execution.pricing_engine import calculate_total_premium
except ImportError as e:
    print(f"Error importing application logic: {e}")
    create_application = None
    calculate_total_premium = None

PORT = 8084

class SanlamHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/submit-application':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                
                # --- MAPPING FRONTEND DATA TO BACKEND LOGIC ---
                # Frontend sends: { name, age, id, cover, plan, signature }
                
                name_parts = data.get('name', 'Unknown').split(' ')
                first_name = name_parts[0]
                surname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                applicant = {
                    'first_names': first_name,
                    'surname': surname,
                    'id_number': data.get('id', ''),
                    'date_of_birth': '1990-01-01', # Mocked for prototype if not asked
                    'cellphone': data.get('phone', 'N/A'),
                    'email': 'client@example.com', # Mocked
                }
                
                # Calculate real premium
                lives_for_calc = []
                # Principal
                lives_for_calc.append({
                    'category': 'principal',
                    'age': int(data.get('age', 30)),
                    'cover_amount': int(str(data.get('cover', '20000')).replace('R','').replace(',',''))
                })
                
                # Extended Family
                if family_data:
                    for relation, count in family_data.items():
                        for _ in range(int(count)):
                            lives_for_calc.append({
                                'category': 'wider_family' if relation in ['aunt', 'uncle', 'cousin'] else 'parent',
                                'age': 40, # Placeholder age for extended family if not provided
                                'cover_amount': 10000
                            })

                if calculate_total_premium:
                    premium_info = calculate_total_premium(lives_for_calc, plan=data.get('plan', 'value'))
                else:
                    premium_info = {
                        'total': 120, # Fallback
                        'subtotal': 120,
                        'min_applied': False
                    }
                
                # --- PREPARE DATA FOR PDF FILLER ---
                # We map the simple frontend data to the complex schema required by mapping.json
                
                # Default "N/A" for missing text fields
                def get_val(key, default=""):
                    return data.get(key, default)

                app_data = {
                    "meta": {
                        "template_version": "July 2020",
                        "created_at": "2026-01-10",
                        "reference": f"APP-{get_val('id', '000')[-4:]}"
                    },
                    "policyholder": {
                        "first_names": first_name,
                        "surname": surname,
                        "id_number": get_val('id'),
                        "cellphone": get_val('phone', '0821234567').replace(' ', ''), # Remove spaces for PDF limit
                        "email": "client@example.com",
                        "date_of_birth": "1990-01-01", 
                        "title": "Mr/Ms"
                    },
                    "payment": {
                        "monthly_premium": f"{int(premium_info['total'])}", # Remove cents for space
                        "payment_method": "DebiCheck",
                        "bank_name": data.get('bank_details', {}).get('bank', "Standard Bank"),
                        "account_number": data.get('bank_details', {}).get('accountNumber', "1234567890"),
                        "branch_code": data.get('bank_details', {}).get('branchCode', "051001"),
                        "branch_name": "Universal" 
                    },
                    "lives_covered": {
                        "principal": {
                             "first_names": first_name,
                             "surname": surname,
                             "id_number": get_val('id')
                        },
                        "spouse": {},
                        "children": [],
                        "extended": []
                    },
                    "declarations": {
                        "policyholder_signature_date": "2026-01-11",
                        "intermediary_signature_date": "2026-01-11"
                    }
                }

                # Handle Family Members for PDF
                # We map the frontend counts {aunt: 2, gogo: 1} to specific entries in the extended list
                extended_lives = []
                family_counts = data.get('family', {})
                
                # Helper to generate dummy data for testing
                import random
                def generate_dummy_id(birth_year):
                    # YYMMDD SSSS CA Z
                    y = str(birth_year)[-2:]
                    m = f"{random.randint(1,12):02d}"
                    d = f"{random.randint(1,28):02d}"
                    s = f"{random.randint(0,9999):04d}"
                    return f"{y}{m}{d}{s}081"

                counter = 1
                for relation, count in family_counts.items():
                    try:
                        count = int(count)
                    except:
                        continue
                        
                    for i in range(count):
                        relation_label = relation.capitalize()
                        # Generate dummy details
                        extended_lives.append({
                            "first_names": f"{relation_label} {i+1}",
                            "surname": surname, # Assuming same surname for demo
                            "id_number": generate_dummy_id(1960 if relation in ['gogo', 'grandpa'] else 1990),
                            "relationship": relation_label
                        })
                        counter += 1

                app_data["lives_covered"]["extended"] = extended_lives
                
                # Save to JSON for the script
                json_path = os.path.join(os.getcwd(), '.tmp', f"data_{get_val('id')}.json")
                pdf_out_path = os.path.join(os.getcwd(), 'Sanlam_application_filled.pdf') # Overwrite unique for demo
                
                # Ensure .tmp exists
                os.makedirs(os.path.join(os.getcwd(), '.tmp'), exist_ok=True)
                
                with open(json_path, 'w') as f:
                    json.dump(app_data, f)

                # Run the Filler Script
                import subprocess
                
                # python execution/fill_sanlam_pdf.py "Sanlam application.pdf" data.json execution/mapping.json output.pdf
                cmd = [
                    sys.executable,
                    os.path.join(os.getcwd(), 'execution', 'fill_sanlam_pdf.py'),
                    os.path.join(os.getcwd(), 'Sanlam application.pdf'),
                    json_path,
                    os.path.join(os.getcwd(), 'execution', 'mapping.json'),
                    pdf_out_path
                ]
                
                print(f"Running PDF Filler: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                     response_data = {
                        "status": "success",
                        "message": "Application generated successfully",
                        "path": pdf_out_path,
                        "logs": result.stdout
                    }
                else:
                    print(f"PDF Filler Error: {result.stderr}")
                    response_data = {
                        "status": "error",
                        "message": f"PDF Generation Failed: {result.stderr}"
                    }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "File not found")

print(f"Sanlam Server running at http://localhost:{PORT}")
print("Press Ctrl+C to stop")

with socketserver.TCPServer(("", PORT), SanlamHandler) as httpd:
    httpd.serve_forever()
