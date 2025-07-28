import re
from django.core.exceptions import ValidationError
import logging

utils_logger = logging.getLogger("Utils")

ZIP_CODE_PATTERNS = {
    'DE': r'^\d{5}$',                       # Germany
    'US': r'^\d{5}(-\d{4})?$',              # USA
    'GB': r'^[A-Z]{1,2}\d[A-Z\d]? \d[ABD-HJLNP-UW-Z]{2}$',  # UK
    'IN': r'^\d{6}$',                       # India
    # Add more patterns as needed
}

def validate_zip_code(value, country_code):
    pattern = ZIP_CODE_PATTERNS.get(country_code)
    if pattern and not re.match(pattern, value):
        utils_logger.error(f"Invalid Zip Code Format For Country: {country_code}")
        raise ValidationError(f"Invalid Zip Code Format For Country: {country_code}")
