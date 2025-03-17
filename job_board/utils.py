from datetime import datetime, timedelta, timezone


def parse_relative_time(relative_str: str | None) -> datetime | None:
    if relative_str is None:
        return

    value, unit = relative_str.replace(" ago", "").split(" ")
    value = int(value)

    now = datetime.now(timezone.utc)

    match unit:
        case "day" | "days":
            return now - timedelta(days=value)
        case "hour" | "hours":
            return now - timedelta(hours=value)
        case "minute" | "minutes":
            return now - timedelta(minutes=value)
        case "second" | "seconds":
            return now - timedelta(seconds=value)
        case "month" | "months":
            # although this might be a little inaccurate
            # don't want to use another library dateutil
            # for just this one case.
            return now - timedelta(days=30 * value)
        case _:
            raise ValueError(f"Unsupported time unit: {unit}")
