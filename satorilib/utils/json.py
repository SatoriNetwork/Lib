from typing import Union


def sanitizeJson(data: Union[dict, list, float, None]) -> Union[dict, list, float]:
    import math
    """
    This function will recursively check the structure and replace any NaN or None
    values with appropriate JSON-compatible values (e.g., None -> null, NaN -> 0).
    """
    if isinstance(data, dict):
        return {k: sanitizeJson(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitizeJson(item) for item in data]
    elif data is None:  # Replace None with JSON null
        return 0
    elif isinstance(data, float) and math.isnan(data):  # Replace NaN with 0
        return 0
    else:
        return data
