from typing import Union
import hashlib
import base58


def isValidEvrmoreAddressBasic(address: str) -> bool:
    '''Evrmore addresses typically start with 'E' and are 34 characters long'''
    import re
    pattern = r'^[E][a-zA-Z0-9]{33}$'
    return bool(re.match(pattern, address))


def base58_check_decode(address: Union[str, bytes]) -> tuple[bool, Union[int, None]]:
    ''' Decode Base58Check address and return the payload and version byte. '''
    try:
        decoded = base58.b58decode(address)
        version = decoded[0]
        checksum = decoded[-4:]
        payload = decoded[:-4]
        # Calculate checksum of the payload
        checksum_check = hashlib.sha256(
            hashlib.sha256(payload).digest()).digest()[:4]
        if checksum != checksum_check:
            return False, None  # Checksum does not match
        return True, version  # Return payload and version byte
    except Exception:
        return False, None


def isValidEvrmoreAddress(address: str) -> bool:
    ''' Validate Evrmore address using Base58Check. '''
    try:
        from evrmore.wallet import CEvrmoreAddress
        CEvrmoreAddress(address)
        if not isValidEvrmoreAddressBasic(address):
            return False
        is_valid, version = base58_check_decode(address)
        if not is_valid:
            return False
        # Evrmore P2PKH (starts with 'E'), adjust the version byte accordingly
        if version == 0x21:  # Example for Evrmore P2PKH (adjust if necessary)
            return True
        elif version == 0x5a:  # Example for Evrmore P2SH (adjust if necessary)
            return True
        else:
            return False  # Invalid version byte
    except Exception:
        return False




def validEvrmoreAddress(address: str) -> Union[str, None]:
    ''' Validate Evrmore address using Base58Check. '''
    if not isValidEvrmoreAddress(address):
        return None
    return address
