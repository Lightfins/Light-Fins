"""
Sanlam Value Funeral Plan - Pricing Engine

Deterministic pricing calculator using official Sanlam rate tables.
No estimates - exact premiums only.

Usage:
    from execution.pricing_engine import calculate_premium, calculate_total_premium
    
    # Single life
    premium = calculate_premium(age=30, category='principal', cover_amount=50000)
    
    # Multiple lives
    total = calculate_total_premium([
        {'age': 30, 'category': 'principal', 'cover_amount': 50000},
        {'age': 28, 'category': 'spouse', 'cover_amount': 50000},
        {'age': 5, 'category': 'child', 'cover_amount': 20000},
    ])
"""

from typing import Literal, List, Dict, Optional, Tuple

# ============================================================================
# RATE TABLES (extracted from Sanlam Value Funeral Plan documents)
# ============================================================================

# Principal / Spouse rates by age band and cover amount
PRINCIPAL_RATES = {
    # Age range: {cover_amount: premium}
    (18, 25): {5000: 23, 10000: 35, 15000: 45, 20000: 55, 30000: 67, 50000: 93, 70000: 117, 100000: 141},
    (26, 35): {5000: 28, 10000: 46, 15000: 59, 20000: 71, 30000: 86, 50000: 122, 70000: 159, 100000: 214},
    (36, 45): {5000: 33, 10000: 62, 15000: 76, 20000: 88, 30000: 101, 50000: 138, 70000: 174, 100000: 239},
    (46, 55): {5000: 61, 10000: 81, 15000: 100, 20000: 120, 30000: 146, 50000: 221, 70000: 284, 100000: 369},
    (56, 65): {5000: 76, 10000: 116, 15000: 155, 20000: 195, 30000: 242, 50000: 346, 70000: 442, 100000: 614},
    (66, 74): {5000: 113, 10000: 153, 15000: 199, 20000: 240, 30000: 242, 50000: 346, 70000: 442, 100000: 614},
}

# Children rates by age band and cover amount
CHILD_RATES = {
    (0, 5): {5000: 15, 10000: 24, 20000: 31, 40000: 38, 60000: 40},
    (6, 13): {5000: 16, 10000: 25, 20000: 33, 40000: 40, 60000: 45},
    (14, 15): {5000: 17, 10000: 25, 20000: 39, 40000: 51, 60000: 61},
    (16, 25): {5000: 30, 10000: 42, 20000: 54, 40000: 81, 60000: 105},
}

# Parents / Wider Family rates by age band and cover amount
PARENT_RATES = {
    (26, 30): {5000: 34, 10000: 49, 20000: 81, 40000: 118, 50000: 136},
    (31, 35): {5000: 36, 10000: 52, 20000: 86, 40000: 128, 50000: 148},
    (36, 40): {5000: 38, 10000: 56, 20000: 92, 40000: 140, 50000: 162},
    (41, 45): {5000: 42, 10000: 64, 20000: 102, 40000: 156, 50000: 182},
    (46, 50): {5000: 47, 10000: 75, 20000: 115, 40000: 177, 50000: 210},
    (51, 55): {5000: 55, 10000: 88, 20000: 138, 40000: 212, 50000: 248},
    (56, 60): {5000: 64, 10000: 102, 20000: 159, 40000: 242, 50000: 280},
    (61, 65): {5000: 73, 10000: 118, 20000: 183, 40000: 278, 50000: 320},
    (66, 70): {5000: 95, 10000: 156, 20000: 248, 40000: 370, 50000: 420},
    (71, 75): {5000: 125, 10000: 208, 20000: 336, 40000: 450, 50000: 510},
    (76, 80): {5000: 166, 10000: 278, 20000: 451, 40000: 560},  # No R50k for 76+
    (81, 85): {5000: 240, 10000: 398, 20000: 584, 40000: 710},  # No R50k for 81+
}

# Cover limits per category
COVER_LIMITS = {
    'principal': 100000,
    'spouse': 100000,
    'child': 60000,  # Legal limits apply for younger children
    'parent': 50000,
    'wider_family': 50000,
}

# Age limits per category
AGE_LIMITS = {
    'principal': (18, 74),
    'spouse': (18, 74),
    'child': (0, 25),
    'parent': (26, 85),
    'wider_family': (0, 85),
}

# Minimum total monthly premium by plan type
MIN_PREMIUMS = {
    'value': 80,
    'all_in_one': 250
}

# Max lives allowed
MAX_LIVES = {
    'value': 10,  # Assumption for simple plan
    'all_in_one': 30
}

Category = Literal['principal', 'spouse', 'child', 'parent', 'wider_family']
PlanType = Literal['value', 'all_in_one']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_age_band(age: int, rate_table: dict) -> Optional[Tuple[int, int]]:
    """Find the age band for a given age in the rate table."""
    for (min_age, max_age) in rate_table.keys():
        if min_age <= age <= max_age:
            return (min_age, max_age)
    return None


def _get_rate_table(category: Category) -> dict:
    """Get the appropriate rate table for the category."""
    if category in ('principal', 'spouse'):
        return PRINCIPAL_RATES
    elif category == 'child':
        return CHILD_RATES
    elif category in ('parent', 'wider_family'):
        return PARENT_RATES
    else:
        raise ValueError(f"Unknown category: {category}")


def _find_nearest_cover(cover_amount: int, available_covers: list) -> int:
    """Find the nearest available cover amount (rounds up)."""
    for cover in sorted(available_covers):
        if cover >= cover_amount:
            return cover
    return max(available_covers)


# ============================================================================
# PUBLIC API
# ============================================================================

def validate_eligibility(age: int, category: Category, cover_amount: int) -> Tuple[bool, str]:
    """
    Validate if a person is eligible for cover.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check age limits
    min_age, max_age = AGE_LIMITS.get(category, (0, 100))
    if age < min_age or age > max_age:
        return False, f"Age {age} outside valid range ({min_age}-{max_age}) for {category}"
    
    # Check cover limits
    max_cover = COVER_LIMITS.get(category, 100000)
    if cover_amount > max_cover:
        return False, f"Cover R{cover_amount:,} exceeds maximum R{max_cover:,} for {category}"
    
    # Check if age band exists in rate table
    rate_table = _get_rate_table(category)
    age_band = _get_age_band(age, rate_table)
    if age_band is None:
        return False, f"No rates available for age {age} in {category} category"
    
    return True, ""


def calculate_premium(
    age: int,
    category: Category,
    cover_amount: int,
    validate: bool = True
) -> int:
    """
    Calculate the monthly premium for a single life assured.
    
    Args:
        age: Age of the person
        category: 'principal', 'spouse', 'child', 'parent', or 'wider_family'
        cover_amount: Desired cover amount in Rand
        validate: Whether to validate eligibility first
    
    Returns:
        Monthly premium in Rand (integer)
    
    Raises:
        ValueError: If validation fails or no rate found
    """
    if validate:
        is_valid, error = validate_eligibility(age, category, cover_amount)
        if not is_valid:
            raise ValueError(error)
    
    rate_table = _get_rate_table(category)
    age_band = _get_age_band(age, rate_table)
    
    if age_band is None:
        raise ValueError(f"No age band found for age {age}")
    
    rates = rate_table[age_band]
    
    # Find the cover amount in available rates
    if cover_amount in rates:
        return rates[cover_amount]
    
    # If exact cover not available, find nearest
    nearest_cover = _find_nearest_cover(cover_amount, list(rates.keys()))
    return rates[nearest_cover]


def calculate_total_premium(lives: List[Dict], plan: PlanType = 'value') -> Dict:
    """
    Calculate total monthly premium for multiple lives.
    
    Args:
        lives: List of dicts with keys: age, category, cover_amount
        plan: 'value' or 'all_in_one'
        
    Returns:
        Dict with:
            - premiums: list of individual premiums
            - subtotal: sum before minimum applied
            - total: final premium (minimum applied)
            - min_applied: whether minimum was applied
    """
    premiums = []
    
    for life in lives:
        # For All-in-One, check if compulsory R10k Funeral exists for PLA
        if plan == 'all_in_one' and life['category'] == 'principal' and life['cover_amount'] < 10000:
            life['cover_amount'] = 10000 # Enforce min R10k cover
            
        premium = calculate_premium(
            age=life['age'],
            category=life['category'],
            cover_amount=life['cover_amount']
        )
        premiums.append({
            **life,
            'premium': premium
        })
    
    subtotal = sum(p['premium'] for p in premiums)
    min_req = MIN_PREMIUMS.get(plan, 80)
    total = max(subtotal, min_req)
    
    return {
        'premiums': premiums,
        'subtotal': subtotal,
        'total': total,
        'min_applied': subtotal < min_req,
        'plan': plan
    }


def get_available_covers(category: Category) -> List[int]:
    """Get available cover amounts for a category."""
    rate_table = _get_rate_table(category)
    # Get covers from first age band (they're the same for all bands in category)
    first_band = list(rate_table.keys())[0]
    return sorted(rate_table[first_band].keys())


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("SANLAM VALUE FUNERAL PLAN - PRICING ENGINE")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        (22, 'principal', 10000, 35),
        (30, 'principal', 50000, 122),
        (50, 'principal', 100000, 369),
        (10, 'child', 20000, 33),
        (65, 'parent', 20000, 183),
    ]
    
    print("\nRunning test cases...")
    all_passed = True
    
    for age, category, cover, expected in test_cases:
        result = calculate_premium(age, category, cover)
        status = "PASS" if result == expected else f"FAIL (got {result})"
        if result != expected:
            all_passed = False
        print(f"  Age {age}, {category}, R{cover:,}: R{result} {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! Pricing engine ready.")
    else:
        print("Some tests failed - review rate tables.")
    print("=" * 60)
