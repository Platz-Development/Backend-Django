from datetime import datetime, timedelta, time
import pytz

def get_next_date(day_name: str, start_time: time, tz_name="Europe/Berlin"):
    """
    Returns the next date (as a date object) for the given weekday name and time,
    considering the current time in the given timezone. Includes today only if
    the start_time is still ahead of now.
    """
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)

    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today_idx = now.weekday()
    target_idx = weekdays.index(day_name)

    # Build today's datetime with given start_time
    candidate_date = now.date()
    candidate_datetime = tz.localize(datetime.combine(candidate_date, start_time))

    if today_idx == target_idx and candidate_datetime > now:
        return candidate_date  # Today is the target and start time is still ahead

    # Otherwise find the next future weekday
    days_ahead = (target_idx - today_idx + 7) % 7
    if days_ahead == 0:  # It's today but start_time is in the past
        days_ahead = 7

    next_date = now.date() + timedelta(days=days_ahead)
    return next_date
