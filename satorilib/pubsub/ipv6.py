
def to4(ipv6Address):
    ''' alternative to:
    import ipaddress
    try:
        ip = ipaddress.ip_address(remote_address)
        if ip.version == 6 and ip.ipv4_mapped:
            ip_address = ip.ipv4_mapped.exploded
        else:
            ip_address = ip.exploded
    except ValueError:
        ip_address = None
    # Example usage
    ipv6Address = "0000:0000:0000:0000:0000:ffff:db85:aeb3"
    ipv4Address = to4(ipv6Address)
    print(ipv4Address)  # Output: 219.133.174.179
    '''

    # Check if the IPv6 address is an IPv4-mapped IPv6 address
    if ipv6Address.startswith("0000:0000:0000:0000:0000:ffff:"):
        # Handle the form 0000:0000:0000:0000:0000:ffff:xxxx:xxxx
        ipv4Hex = ipv6Address.split(':')[-2:]
        ipv4Decimal = []
        for hexPart in ipv4Hex:
            ipv4Decimal.append(str(int(hexPart[:2], 16)))
            ipv4Decimal.append(str(int(hexPart[2:], 16)))
        return '.'.join(ipv4Decimal)
    elif ipv6Address.startswith("::ffff:"):
        # Handle the form ::ffff:xxx.xxx.xxx.xxx or ::ffff:xxxx:xxxx
        ipv4Part = ipv6Address[7:]
        if '.' in ipv4Part:
            return ipv4Part  # Already in IPv4 format
        else:
            # Convert the hex representation to a dotted decimal format
            high, low = ipv4Part.split(':')
            return f"{int(high, 16)}.{int(low, 16)}"
    return ipv6Address


def run_tests():
    # Test IPv4-mapped IPv6 addresses
    # assert to4("::ffff:192.0.2.128") == "192.0.2.128", "Test case 1 failed"
    # assert to4("::ffff:7f00:1") == "127.0.0.1", "Test case 3 failed"
    ipv6Address = "0000:0000:0000:0000:0000:ffff:db85:aeb3"
    ipv4Address = to4(ipv6Address)
    print(ipv4Address)  # Output: 219.133.174.179
    assert to4(
        "0000:0000:0000:0000:0000:ffff:c000:0280") == "192.0.2.128", "Test case 2 failed"
    assert to4(
        "0000:0000:0000:0000:0000:ffff:7f00:0001") == "127.0.0.1", "Test case 4 failed"
    assert to4(
        "0000:0000:0000:0000:0000:ffff:db85:aeb3") == "219.133.174.179", "Test case 5 failed"
    # Test regular IPv6 addresses (should return the same address)
    assert to4(
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "2001:0db8:85a3:0000:0000:8a2e:0370:7334", "Test case 6 failed"
    assert to4(
        "fe80::1ff:fe23:4567:890a") == "fe80::1ff:fe23:4567:890a", "Test case 7 failed"
    # Test invalid input (should return the same input)
    assert to4(
        "invalid:address") == "invalid:address", "Test case 8 failed"
    assert to4("") == "", "Test case 9 failed"
    print("All test cases passed!")
