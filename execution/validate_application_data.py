#!/usr/bin/env python3
"""
Validation Script for Sanlam Application Data

Validates application data before PDF generation to catch errors early.
Part of the 3-layer architecture (Layer 3: Execution).

Usage:
    python execution/validate_application_data.py <data.json>

Returns:
    0 - Validation passed
    1 - Validation failed
"""

import json
import sys
import re
from datetime import datetime


def validate_id_number(id_num):
    """
    Validate South African ID number.
    Format: YYMMDD SSSS C A Z
    """
    if not id_num or not isinstance(id_num, str):
        return False, "ID number is required"
    
    # Remove spaces
    id_num = id_num.replace(" ", "")
    
    # Check length
    if len(id_num) != 13:
        return False, f"ID must be 13 digits, got {len(id_num)}"
    
    # Check all digits
    if not id_num.isdigit():
        return False, "ID must contain only digits"
    
    # Validate date portion (YYMMDD)
    try:
        year = int(id_num[0:2])
        month = int(id_num[2:4])
        day = int(id_num[4:6])
        
        if month < 1 or month > 12:
            return False, f"Invalid month in ID: {month}"
        if day < 1 or day > 31:
            return False, f"Invalid day in ID: {day}"
    except ValueError:
        return False, "Invalid date in ID number"
    
    return True, "Valid"


def validate_age(age, min_age=18, max_age=74):
    """Validate age is within acceptable range."""
    try:
        age = int(age)
        if age < min_age or age > max_age:
            return False, f"Age must be between {min_age} and {max_age}"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, "Age must be a number"


def validate_cover_amount(amount, max_amount=100000):
    """Validate cover amount."""
    try:
        amount = int(str(amount).replace("R", "").replace(",", ""))
        if amount <= 0:
            return False, "Cover amount must be positive"
        if amount > max_amount:
            return False, f"Cover amount exceeds maximum of R{max_amount:,}"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, "Invalid cover amount"


def validate_phone(phone):
    """Validate phone number."""
    if not phone:
        return False, "Phone number is required"
    
    # Remove spaces and common separators
    phone = str(phone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Check length (SA numbers are typically 10 digits)
    if len(phone) != 10:
        return False, f"Phone must be 10 digits, got {len(phone)}"
    
    if not phone.isdigit():
        return False, "Phone must contain only digits"
    
    return True, "Valid"


def validate_email(email):
    """Validate email format."""
    if not email:
        return True, "Valid (optional)"  # Email is optional
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "Valid"
    return False, "Invalid email format"


def validate_application_data(data):
    """
    Main validation function.
    Returns: (is_valid, errors_list)
    """
    errors = []
    
    # Validate policyholder data
    policyholder = data.get("policyholder", {})
    
    if not policyholder.get("first_names"):
        errors.append("Policyholder first name is required")
    
    if not policyholder.get("surname"):
        errors.append("Policyholder surname is required")
    
    # ID validation
    valid, msg = validate_id_number(policyholder.get("id_number"))
    if not valid:
        errors.append(f"Policyholder ID: {msg}")
    
    # Phone validation
    valid, msg = validate_phone(policyholder.get("cellphone"))
    if not valid:
        errors.append(f"Policyholder phone: {msg}")
    
    # Email validation
    valid, msg = validate_email(policyholder.get("email"))
    if not valid:
        errors.append(f"Policyholder email: {msg}")
    
    # Validate principal life
    principal = data.get("lives_covered", {}).get("principal", {})
    if principal:
        valid, msg = validate_id_number(principal.get("id_number"))
        if not valid:
            errors.append(f"Principal life ID: {msg}")
    
    # Validate payment data
    payment = data.get("payment", {})
    if not payment.get("monthly_premium"):
        errors.append("Monthly premium is required")
    
    if not payment.get("bank_name"):
        errors.append("Bank name is required")
    
    if not payment.get("account_number"):
        errors.append("Account number is required")
    
    # Validate extended family members
    extended = data.get("lives_covered", {}).get("extended", [])
    for i, member in enumerate(extended):
        valid, msg = validate_id_number(member.get("id_number"))
        if not valid:
            errors.append(f"Extended family member {i+1} ID: {msg}")
    
    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_application_data.py <data.json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(1)
    
    is_valid, errors = validate_application_data(data)
    
    if is_valid:
        print("OK - Validation passed")
        print(f"  Policyholder: {data.get('policyholder', {}).get('first_names')} {data.get('policyholder', {}).get('surname')}")
        print(f"  Premium: R{data.get('payment', {}).get('monthly_premium')}")
        sys.exit(0)
    else:
        print("ERROR - Validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
