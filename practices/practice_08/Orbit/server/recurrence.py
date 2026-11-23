from datetime import date, timedelta


def occurrences(row, start, end):
    """Yield inclusive start/end dates of instances intersecting the requested window."""
    birthday = row["kind"] == "birthday"
    frequency = "yearly" if birthday else row["frequency"]
    anchor = date(1, 1, 1) if birthday else date.fromisoformat(row["startDate"])
    duration = 0 if birthday else (date.fromisoformat(row["endDate"]) - anchor).days
    lower = date.fromordinal(max(1, start.toordinal() - duration))
    lower = max(lower, anchor)
    if row["active_from"]:
        lower = max(lower, date.fromisoformat(row["active_from"]))
    if row["active_until"]:
        end = min(end, date.fromisoformat(row["active_until"]))
    end = date.fromordinal(min(end.toordinal(), date.max.toordinal() - duration))
    if lower > end:
        return

    if frequency in ("daily", "weekly"):
        stride = 1 if frequency == "daily" else 7
        offset = (anchor.toordinal() - lower.toordinal()) % stride
        begins = (date.fromordinal(day) for day in range(lower.toordinal() + offset, end.toordinal() + 1, stride))
    else:
        first = lower.year * 12 + lower.month - 1
        last = end.year * 12 + end.month - 1
        month = row["birthMonth"] if birthday else anchor.month
        day = row["birthDay"] if birthday else anchor.day
        if frequency == "yearly":
            first += (month - 1 - first) % 12
        begins = month_dates(first, last, day, 12 if frequency == "yearly" else 1)

    for begin in begins:
        if lower <= begin <= end:
            yield begin, begin + timedelta(days=duration)


def month_dates(first, last, day, stride):
    for number in range(first, last + 1, stride):
        year, month = divmod(number, 12)
        try:
            yield date(year, month + 1, day)
        except ValueError:
            continue
