from datetime import timedelta


def format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return f"-{format_duration(-td)}"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}m"
