from typing import Union
import datetime as dt
from evrmore.core.script import (CScript, OP_CHECKMULTISIG)


def basicMultisig(pubkeys: list[Union[bytes, str]], signatures: int) -> CScript:
    """Create a multi-signature redeem script.
    
    Args:
        pubkeys: List of public keys in bytes or hex strings
        signatures: Number of signatures required (M of N)
        
    Returns:
        CScript containing the redeem script
    """
    if not 1 <= signatures <= len(pubkeys):
        raise ValueError("Required signatures must be between 1 and number of public keys")
    
    # Convert hex strings to bytes if needed
    byteKeys = []
    for key in pubkeys:
        if isinstance(key, str):
            byteKeys.append(bytes.fromhex(key))
        elif isinstance(key, bytes):
            byteKeys.append(key)
        else:
            raise TypeError(f"Public key must be bytes or hex string, got {type(key)}")
    
    return CScript([signatures] + byteKeys + [len(byteKeys), OP_CHECKMULTISIG])
