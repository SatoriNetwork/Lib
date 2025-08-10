from typing import List
from evrmore.core import CMutableTransaction
from evrmore.core.script import CScript, OP_0, OP_1
from satorilib.wallet import EvrmoreWallet


def simpleTimeRelease(
    *,
    wallet: EvrmoreWallet,
    tx: CMutableTransaction,
    vinIndex: int,
    redeemScript: CScript,
    sighashFlag: int = None,
    timedRelease: bool = True,
) -> List[object]:
    """
    Returns: [sig, 1] for timed release
    Returns: [sig, 0] for immediate release
    """
    sig = wallet.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
    op = OP_1 if timedRelease else OP_0
    return [sig, op]


def enhancedSimpleTimeRelease(
    *,
    wallet: EvrmoreWallet,
    tx: CMutableTransaction,
    vinIndex: int,
    redeemScript: CScript,
    sighashFlag: int = None,
    timedRelease: int = 3,
) -> List[object]:
    """
    Returns: [sig, 1, 1] for timed release 3
    Returns: [sig, 1, 0] for timed release 2
    Returns: [sig, 0, 1] for timed release 1
    Returns: [sig, 0, 0] for immediate release
    """
    sig = wallet.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
    if timedRelease == 3:
        op = [1, 1]
    elif timedRelease == 2:
        op = [1, 0]
    elif timedRelease == 1:
        op = [0, 1]
    else:
        op = [0, 0]
    return [sig, *op]


def enhancedSimpleTimeReleaseWithMultiSig(
    *,
    wallet: EvrmoreWallet,
    multi_wallet_1: EvrmoreWallet,
    multi_wallet_2: EvrmoreWallet,
    multi_wallet_3: EvrmoreWallet,
    multi_wallet_4: EvrmoreWallet,
    multi_wallet_5: EvrmoreWallet,
    tx: CMutableTransaction,
    vinIndex: int,
    redeemScript: CScript,
    sighashFlag: int = None,
    timedRelease: int = 3,
) -> List[object]:
    """
    Returns: [sig, 1, 1] for timed release 3
    Returns: [sig, 1, 0] for timed release 2
    Returns: [sig, 0, 1] for timed release 1
    Returns: [sig, 0, 0] for immediate release
    """
    sig = wallet.signatureForInput(tx, vinIndex, redeemScript, sighashFlag)
    if timedRelease == 3:
        op = [1, 1]
    elif timedRelease == 2:
        op = [1, 0]
    elif timedRelease == 1:
        op = [0, 1]
    else:
        op = [0, 0]
    return [sig, *op]
    