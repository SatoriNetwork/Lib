import json

def coerce(item, native):
    if item is None:
        return item
    if isinstance(item, native):
        return item
    if native == list:
        return ([item] if isinstance(item, str) else [*item])
    if native == tuple:
        return ((item,) if isinstance(item, str) else (*item,))
    if native == set:
        return ({item} if isinstance(item, str) else {*item})
    if native == dict:
        if isinstance(item, (list, tuple, set)):
            return {k: v for k, v in item}
        else:
            return json.loads(item) if isinstance(item, str) else dict(item)
    if native == 'json':
        if isinstance(item, dict):
            return json.dumps(item)
        if isinstance(item, str):
            try:
                return json.loads(item)
            except Exception:
                pass
        return item
    return native(item)