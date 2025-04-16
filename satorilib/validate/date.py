def isDate(date_string: str) -> bool:
    import datetime as dt
    try:
        # Try to parse the string into a date with the specified format
        dt.datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        # If parsing fails, it's not a valid date in the specified format
        return False