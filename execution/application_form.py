"""
Sanlam Application Form - Google Docs Integration

Auto-fills the electronic application form and stores in Google Docs.

Setup:
1. Place Google OAuth credentials.json in the Agents folder
2. Run this script once to authorize
3. Token will be saved as token.json

Usage:
    from execution.application_form import create_application
    
    application = create_application(
        applicant_data={...},
        lives_assured=[...],
        premium_info={...}
    )
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# Try to import Google APIs (may not be installed)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client")


# Google Docs API scopes
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

# Paths
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


# ============================================================================
# APPLICATION FORM FIELD MAPPING
# ============================================================================

# Maps chat responses to application form fields
FIELD_MAPPING = {
    # Policyholder details
    'first_names': 'Policyholder First Names',
    'surname': 'Policyholder Surname',
    'id_number': 'SA ID Number',
    'date_of_birth': 'Date of Birth',
    'gender': 'Gender',
    'marital_status': 'Marital Status',
    'cellphone': 'Cellphone Number',
    'email': 'Email Address',
    'address_street': 'Physical Address - Street',
    'address_suburb': 'Physical Address - Suburb',
    'address_city': 'Physical Address - City',
    'address_postal_code': 'Postal Code',
    'employment_status': 'Employment Status',
    'source_of_income': 'Source of Income',
    
    # Cover details
    'cover_amount_principal': 'Principal Cover Amount',
    'cover_amount_spouse': 'Spouse Cover Amount',
    'cover_amount_children': 'Children Cover Amount',
    'cover_amount_parents': 'Parents Cover Amount',
    
    # Previous cover
    'has_previous_cover': 'Previous Funeral Cover (Y/N)',
    'previous_insurer': 'Previous Insurer Name',
    'previous_policy_number': 'Previous Policy Number',
    
    # Premium
    'total_premium': 'Total Monthly Premium',
    'premium_frequency': 'Premium Frequency',
    
    # Beneficiaries
    'beneficiary_1_name': 'Beneficiary 1 Name',
    'beneficiary_1_id': 'Beneficiary 1 ID',
    'beneficiary_1_relationship': 'Beneficiary 1 Relationship',
    'beneficiary_1_percentage': 'Beneficiary 1 Percentage',
}


# ============================================================================
# GOOGLE DOCS INTEGRATION
# ============================================================================

def get_google_credentials():
    """Get or refresh Google API credentials."""
    if not GOOGLE_AVAILABLE:
        raise ImportError("Google API libraries not installed")
    
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Missing {CREDENTIALS_FILE}. Download from Google Cloud Console:\n"
                    "1. Go to console.cloud.google.com\n"
                    "2. Create project & enable Docs/Drive APIs\n"
                    "3. Create OAuth credentials\n"
                    "4. Download as credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def create_google_doc(title: str, content: str) -> str:
    """
    Create a new Google Doc with the given content.
    
    Returns:
        Document ID (can be used to construct URL)
    """
    creds = get_google_credentials()
    
    # Create document
    docs_service = build('docs', 'v1', credentials=creds)
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']
    
    # Insert content
    requests = [
        {
            'insertText': {
                'location': {'index': 1},
                'text': content
            }
        }
    ]
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()
    
    return doc_id


# ============================================================================
# APPLICATION FORM GENERATION
# ============================================================================

def format_application_form(
    applicant: Dict,
    lives_assured: List[Dict],
    premium_info: Dict,
    beneficiaries: Optional[List[Dict]] = None
) -> str:
    """
    Format the application data into a text form.
    
    Args:
        applicant: Policyholder details
        lives_assured: List of covered lives with premiums
        premium_info: Total premium breakdown
        beneficiaries: Optional list of beneficiaries
    
    Returns:
        Formatted application text
    """
    now = datetime.now()
    
    lines = [
        "=" * 70,
        "SANLAM INDIVIDUAL VALUE FUNERAL PLAN - APPLICATION FORM",
        "=" * 70,
        f"Application Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "-" * 70,
        "SECTION A: POLICYHOLDER DETAILS",
        "-" * 70,
    ]
    
    # Policyholder details
    for key, label in FIELD_MAPPING.items():
        if key in applicant:
            lines.append(f"{label}: {applicant[key]}")
    
    lines.extend([
        "",
        "-" * 70,
        "SECTION B: LIVES ASSURED",
        "-" * 70,
    ])
    
    # Lives assured
    for i, life in enumerate(lives_assured, 1):
        lines.append(f"\nLife {i}:")
        lines.append(f"  Category: {life.get('category', 'N/A')}")
        lines.append(f"  Name: {life.get('name', 'N/A')}")
        lines.append(f"  ID Number: {life.get('id_number', 'N/A')}")
        lines.append(f"  Age: {life.get('age', 'N/A')}")
        lines.append(f"  Gender: {life.get('gender', 'N/A')}")
        lines.append(f"  Cover Amount: R{life.get('cover_amount', 0):,}")
        lines.append(f"  Monthly Premium: R{life.get('premium', 0):,}")
    
    lines.extend([
        "",
        "-" * 70,
        "SECTION C: PREMIUM SUMMARY",
        "-" * 70,
        f"Subtotal: R{premium_info.get('subtotal', 0):,}",
        f"Minimum Applied: {'Yes' if premium_info.get('min_applied') else 'No'}",
        f"Total Monthly Premium: R{premium_info.get('total', 0):,}",
    ])
    
    # Beneficiaries
    if beneficiaries:
        lines.extend([
            "",
            "-" * 70,
            "SECTION D: BENEFICIARIES",
            "-" * 70,
        ])
        for i, ben in enumerate(beneficiaries, 1):
            lines.append(f"\nBeneficiary {i}:")
            lines.append(f"  Name: {ben.get('name', 'N/A')}")
            lines.append(f"  ID: {ben.get('id_number', 'N/A')}")
            lines.append(f"  Relationship: {ben.get('relationship', 'N/A')}")
            lines.append(f"  Percentage: {ben.get('percentage', 0)}%")
    
    lines.extend([
        "",
        "-" * 70,
        "SECTION E: DECLARATIONS",
        "-" * 70,
        "[ ] I confirm the information provided is true and correct",
        "[ ] I consent to POPIA data processing",
        "[ ] I understand the waiting period conditions",
        "[ ] I have read and accept the policy terms",
        "",
        "-" * 70,
        "SIGNATURE",
        "-" * 70,
        "Policyholder Signature: ________________________",
        f"Date: {now.strftime('%Y-%m-%d')}",
        "",
        "=" * 70,
        "FOR OFFICE USE ONLY",
        "=" * 70,
        "Application Status: PENDING REVIEW",
        f"Submitted: {now.strftime('%Y-%m-%d %H:%M:%S')}",
    ])
    
    return "\n".join(lines)


def create_application(
    applicant: Dict,
    lives_assured: List[Dict],
    premium_info: Dict,
    beneficiaries: Optional[List[Dict]] = None,
    save_to_google: bool = True,
    save_local: bool = True
) -> Dict:
    """
    Create and save the application form.
    
    Args:
        applicant: Policyholder details
        lives_assured: List of covered lives
        premium_info: Premium breakdown
        beneficiaries: Optional beneficiaries
        save_to_google: Whether to save to Google Docs
        save_local: Whether to save locally
    
    Returns:
        Dict with file paths and URLs
    """
    # Format the application
    content = format_application_form(applicant, lives_assured, premium_info, beneficiaries)
    
    now = datetime.now()
    filename = f"Sanlam_Application_{applicant.get('surname', 'Unknown')}_{now.strftime('%Y%m%d_%H%M%S')}"
    
    result = {
        'content': content,
        'local_path': None,
        'google_doc_id': None,
        'google_doc_url': None,
    }
    
    # Save locally
    if save_local:
        local_path = os.path.join('.tmp', f'{filename}.txt')
        os.makedirs('.tmp', exist_ok=True)
        with open(local_path, 'w') as f:
            f.write(content)
        result['local_path'] = local_path
        print(f"Saved locally: {local_path}")
    
    # Save to Google Docs
    if save_to_google and GOOGLE_AVAILABLE:
        try:
            doc_id = create_google_doc(filename, content)
            result['google_doc_id'] = doc_id
            result['google_doc_url'] = f"https://docs.google.com/document/d/{doc_id}/edit"
            print(f"Saved to Google Docs: {result['google_doc_url']}")
        except Exception as e:
            print(f"Failed to save to Google Docs: {e}")
    
    return result


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    # Demo application
    demo_applicant = {
        'first_names': 'John',
        'surname': 'Smith',
        'id_number': '9001015800087',
        'date_of_birth': '1990-01-01',
        'gender': 'Male',
        'marital_status': 'Married',
        'cellphone': '0821234567',
        'email': 'john.smith@email.com',
        'address_street': '123 Main Street',
        'address_suburb': 'Sandton',
        'address_city': 'Johannesburg',
        'address_postal_code': '2196',
        'employment_status': 'Employed',
        'source_of_income': 'Salary',
    }
    
    demo_lives = [
        {'category': 'principal', 'name': 'John Smith', 'id_number': '9001015800087', 'age': 34, 'gender': 'Male', 'cover_amount': 50000, 'premium': 122},
        {'category': 'spouse', 'name': 'Jane Smith', 'id_number': '9201025800088', 'age': 32, 'gender': 'Female', 'cover_amount': 50000, 'premium': 122},
    ]
    
    demo_premium = {'subtotal': 244, 'total': 244, 'min_applied': False}
    
    demo_beneficiaries = [
        {'name': 'Sarah Smith', 'id_number': '8501015800089', 'relationship': 'Sister', 'percentage': 100}
    ]
    
    print("Creating demo application...")
    result = create_application(
        applicant=demo_applicant,
        lives_assured=demo_lives,
        premium_info=demo_premium,
        beneficiaries=demo_beneficiaries,
        save_to_google=False,  # Set to True once Google credentials are set up
        save_local=True
    )
    
    print("\n" + "=" * 60)
    print("APPLICATION PREVIEW:")
    print("=" * 60)
    print(result['content'][:1500] + "...")
