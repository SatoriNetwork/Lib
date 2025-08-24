from typing import List, Optional
from evrmore.core.script import CScript, OP_0, OP_TRUE, OP_FALSE


def thunderChannel(
    *,
    sender_sig: bytes,
    receiver_sig: Optional[bytes] = None,
) -> List[object]:
    """
    Returns: [sig, 1] for release (multi-sig)
    Returns: [sig, 0] for timed release (immediate)
    """
    if receiver_sig:
        return CScript([OP_0, sender_sig, receiver_sig, OP_TRUE])
    return CScript([sender_sig, OP_FALSE])


def thunderExpiring(
    *,
    sender_sig: bytes,
    receiver_sig: Optional[bytes] = None,
) -> List[object]:
    """
    Returns: [sig, 1] for release (multi-sig)
    Returns: [sig, 0] for timed release (immediate)
    """
    if receiver_sig:
        return CScript([OP_0, sender_sig, receiver_sig, OP_TRUE])
    return CScript([sender_sig, OP_FALSE])