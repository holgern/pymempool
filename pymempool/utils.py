from datetime import datetime


def median(a):
    n = len(a)
    a.sort()

    if n % 2 == 0:
        median1 = a[n // 2]
        median2 = a[n // 2 - 1]
        median = (median1 + median2) / 2
    else:
        median = a[n // 2]
    return median


def time_until(target_datetime: datetime, short: bool = False) -> str:
    now = datetime.now(target_datetime.tzinfo)
    delta = target_datetime - now

    # If target time is in the past
    if delta.total_seconds() < 0:
        delta = abs(delta)
        past = True
    else:
        past = False

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60

    if short:
        result = f"{days}d {hours}h {minutes}min"
    else:
        day_str = "day" if days == 1 else "days"
        hour_str = "hour" if hours == 1 else "hours"
        minute_str = "minute" if minutes == 1 else "minutes"
        result = f"{days} {day_str} {hours} {hour_str} {minutes} {minute_str}"

    return f"{result} ago" if past else result
