def getPublicIpv4():
    return getPublicIpv4UsingCurl()

def getPublicIpv4UsingCurl():
    import os
    x = os.popen("curl -4 https://checkip.amazonaws.com").read().strip()
    if x == "":
        x = os.popen("curl -4 ifconfig.me").read().strip()
    return x

def getPublicIpv4UsingRequests():

    import socket
    import requests

    # Save the real getaddrinfo
    _real_getaddrinfo = socket.getaddrinfo

    def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Force AF_INET (IPv4 only)
        return _real_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    def getPublicIpv4():
        # Monkey-patch to force IPv4
        socket.getaddrinfo = _ipv4_only_getaddrinfo
        try:
            for url in ["https://checkip.amazonaws.com", "https://ifconfig.me"]:
                try:
                    r = requests.get(url, timeout=2)
                    r.raise_for_status()
                    return r.text.strip()
                except requests.RequestException:
                    pass
            return ""
        finally:
            # Restore original getaddrinfo
            socket.getaddrinfo = _real_getaddrinfo

    return getPublicIpv4()
