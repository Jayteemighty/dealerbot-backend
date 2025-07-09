import re
from typing import Dict, List

def manual_parse_vehicle_name(vehicle_name: str) -> Dict[str, str]:
    """Manually parse a Ford vehicle name into its components."""
    # Remove special characters
    clean_name = vehicle_name.replace('®', '').replace('™', '').strip()
    parts = clean_name.split()
    
    # Default values
    year = ''
    make = 'Ford'
    model = ''
    trim = ''
    vehicle_type = ''

    # Try to extract year (first 4-digit number)
    if parts and re.match(r'^\d{4}$', parts[0]):
        year = parts[0]
        parts = parts[1:]

    # Known models and their types
    model_types = {
        'Escape': 'SUV',
        'Bronco': 'SUV',
        'Ranger': 'Truck',
        'E-Series': 'Van',
        'Cutaway': 'Van',
        'F-150': 'Truck',
        'Super Duty': 'Truck',
        'Transit': 'Van',
        'Mustang': 'Performance',
        'Mach-E': 'Electric',
        'Lightning': 'Electric',
        'Active': 'SUV',
        'Badlands': 'SUV',
        'LARIAT': 'Truck',
        'SRW': 'Van',
    }

    # Try to find model and trim
    # For E-Series Cutaway, model is 'E-Series Cutaway'
    if 'E-Series Cutaway' in clean_name:
        model = 'E-Series Cutaway'
        rest = clean_name.split('E-Series Cutaway', 1)[1].strip()
        trim = rest
        vehicle_type = 'Van'
    else:
        # Model is first capitalized word after year
        if parts:
            model = parts[0]
            trim = ' '.join(parts[1:])
            vehicle_type = model_types.get(model, '')
            # If trim is a known type, use that
            if not vehicle_type and trim:
                vehicle_type = model_types.get(trim.split()[0], '')

    return {
        'year': year,
        'make': make,
        'model': model,
        'trim': trim,
        'vehicle_type': vehicle_type
    }

if __name__ == "__main__":
    vehicle_names = [
        "2024 Bronco\u00ae Wildtrak\u2122",
        "2025 Explorer\u00ae Platinum",
        "2025 F-150\u00ae Lariat",
        "2024 Mustang\u00ae GT Premium Fastback",
    ]
    for name in vehicle_names:
        parsed = manual_parse_vehicle_name(name)
        print(f"{name} => {parsed}") 