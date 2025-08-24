from typing import List, Optional
from evrmore.core.script import CScript, OP_0, OP_1, OP_TRUE, OP_FALSE


def simpleTime(
    *,
    sig: bytes,
    timedRelease: bool = True,
) -> List[object]:
    """
    Returns: [sig, 1] for timed release
    Returns: [sig, 0] for immediate release
    """
    params = OP_1 if timedRelease else OP_0
    return CScript([sig, params])


def multiTime(
    *,
    sig: bytes,
    timedRelease: int = 3,
) -> List[object]:
    """
    Returns: [sig, 1, 1] for timed release 3
    Returns: [sig, 1, 0] for timed release 2
    Returns: [sig, 0, 1] for timed release 1
    Returns: [sig, 0, 0] for timed release 0 (immediate)
    """
    if timedRelease == 3:
        params = [OP_TRUE, OP_TRUE]
    elif timedRelease == 2:
        params = [OP_FALSE, OP_TRUE]
    elif timedRelease == 1:
        params = [OP_TRUE, OP_FALSE]
    else:
        params = [OP_FALSE, OP_FALSE]
    return CScript([sig, *params])


def multiTimeMultisig(
    *,
    sig: bytes,
    sig2: Optional[bytes] = None,
    sig3: Optional[bytes] = None,
    sig4: Optional[bytes] = None,
    sig5: Optional[bytes] = None,
    timedRelease: int = 3,
) -> List[object]:
    """
    Returns: [sig, 1, 1] for timed release 3
    Returns: [sig, 0, 1] for timed release 2
    Returns: [sig, 1, 0] for timed release 1 (multi-sig, immediate)
    Returns: [sig, 0, 0] for timed release 0 (immediate)
    """
    if timedRelease == 3:
        params = [sig, OP_TRUE, OP_TRUE]
    elif timedRelease == 2:
        params = [sig, OP_FALSE, OP_TRUE]
    elif timedRelease == 1:
        #sig2 = sig2.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
        #sig3 = sig3.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
        #sig4 = sig4.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
        #sig5 = sig5.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
        params = [OP_0, sig, sig2, sig3, sig4, sig5, OP_TRUE, OP_FALSE]
    else:
        params = [sig, OP_FALSE, OP_FALSE]
    return CScript(params)
    