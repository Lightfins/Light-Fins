import json
import os
import sys
import subprocess

# Mock Data simulating 'app.js' payload being processed by 'server.py'
app_data = {
    "meta": {
        "template_version": "July 2020",
        "created_at": "2026-01-10",
        "reference": "APP-TEST-001"
    },
    "policyholder": {
        "first_names": "Python",
        "surname": "Tester",
        "id_number": "9001015000087",
        "cellphone": "082 555 1234",
        "email": "test@example.com",
        "date_of_birth": "1990-01-01",
        "title": "Mr"
    },
    "payment": {
        "monthly_premium": "150.00",
        "payment_method": "DebiCheck",
        "bank_name": "Standard Bank",
        "account_number": "1234567890",
        "branch_code": "051001"
    },
    "lives_covered": {
        "principal": {
             "first_names": "Python",
             "surname": "Tester",
             "id_number": "9001015000087"
        },
        "spouse": {},
        "children": [],
        "extended": [
            {
                "first_names": "Aunt 1",
                "surname": "Tester",
                "id_number": "7001010001087"
            },
            {
                "first_names": "Aunt 2",
                "surname": "Tester",
                "id_number": "7205050001087"
            },
            {
                "first_names": "Gogo 1",
                "surname": "Tester",
                "id_number": "5001010001087"
            }
        ]
    },
    "declarations": {
        "policyholder_signature_date": "2026-01-11",
        "intermediary_signature_date": "2026-01-11"
    }
}

# Paths
json_path = os.path.join(os.getcwd(), '.tmp', "test_data.json")
pdf_template = os.path.join(os.getcwd(), 'Sanlam application.pdf')
mapping_path = os.path.join(os.getcwd(), 'execution', 'mapping.json')
pdf_out_path = os.path.join(os.getcwd(), 'Sanlam_application_filled.pdf')

# Ensure .tmp
os.makedirs(os.path.join(os.getcwd(), '.tmp'), exist_ok=True)

# Write JSON
with open(json_path, 'w') as f:
    json.dump(app_data, f)

# Run Filler
cmd = [
    sys.executable,
    os.path.join(os.getcwd(), 'execution', 'fill_sanlam_pdf.py'),
    pdf_template,
    json_path,
    mapping_path,
    pdf_out_path
]

print(f"Running command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)

if result.returncode == 0 and os.path.exists(pdf_out_path):
    print("SUCCESS: PDF Generated!")
    print(f"Size: {os.path.getsize(pdf_out_path)} bytes")
else:
    print("FAILURE: PDF Generation failed.")
