# utils/datetime_formatting.py

import logging
from datetime import datetime
from django.utils.timezone import is_aware, is_naive, make_aware, localtime
import pytz

# Setup logger for debugging (optional but recommended)
datetime_formatting_logger = logging.getLogger("DatetimeFormatting")

# Define the desired display timezone
DISPLAY_TIMEZONE = pytz.timezone("Europe/Berlin")

# Default display format: "30 June 2025 – 04:00 PM"
DEFAULT_DATETIME_FORMAT = "%d %B %Y – %I:%M %p"

def localize_and_format_datetime(dt: datetime,format_str: str = DEFAULT_DATETIME_FORMAT,fallback_to_raw: bool = True) -> str:
    """
    Convert a datetime to Europe/Berlin timezone and format it for display.

    Args:
        dt (datetime): A timezone-aware or naive datetime.
        format_str (str): Desired format string.
        fallback_to_raw (bool): Whether to return raw string if formatting fails.

    Returns:
        str: Formatted datetime string, or empty string if input is None.
    """

    if dt is None:
        return ""

    try:
        # If naive, make aware in UTC (assuming stored that way)
        if is_naive(dt):
            dt = make_aware(dt, timezone=pytz.UTC)

        # Convert to Europe/Berlin
        dt_local = localtime(dt, timezone=DISPLAY_TIMEZONE)

        # Format and return
        return dt_local.strftime(format_str)

    except Exception as e:
        datetime_formatting_logger.error(f"Failed To Format Datetime: {e}")
        return str(dt) if fallback_to_raw else ""
