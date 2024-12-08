import re
from eth_utils import is_checksum_address#, to_checksum_address


def isValidEthereumAddress(address: str) -> bool:
    # address = "0x32Be343B94f860124dC4fEe278FDCBD38C102D88"
    # Check if it starts with '0x' and is 40 hexadecimal characters long
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        # Optional: Verify checksum if it's a mixed-case address
        if address == address.lower() or address == address.upper():
            return True  # Not a checksummed address, but valid
        else:
            return is_checksum_address(address)  # Validate checksum
    return False
