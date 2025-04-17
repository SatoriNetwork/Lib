def isIpv4Simple(ip: str) -> bool:
    if ip is None:
        return False
    try:
        return isinstance(ip, str) and len(ip.split('.')) == 4 and all([
            -1 < int(x) < 256 for x in ip.split('.')
        ])
    except ValueError:
        return False


def isIpv4(ip: str) -> bool:
    if ip is None:
        return False
    import ipaddress
    try:
        return isinstance(ipaddress.IPv4Address(ip), ipaddress.IPv4Address)
    except ValueError:
        return False