from typing import Union
from evrmore.wallet import CEvrmoreSecret
from evrmore.signmessage import signMessage as sm
from evrmore.signmessage import EvrmoreMessage
from evrmore.core.script import SignatureHash, CScript
from evrmore.core import CMutableTransaction

def signMessage(key: CEvrmoreSecret, message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return sm(
        key,
        EvrmoreMessage(message) if isinstance(message, str) else message)

def sign(privkey: Union[str, bytes], message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return SignMessage(
        CEvrmoreSecret(privkey),
        EvrmoreMessage(message) if isinstance(message, str) else message)

def signForPubkey(
    privkeyObj: CEvrmoreSecret,
    tx: CMutableTransaction,
    vin_index: int,
    script_code: CScript,
    sighash_flag: int,
) -> bytes:
    """Return DER signature + sighash byte for this input and script_code."""
    sighash = SignatureHash(script_code, tx, vin_index, sighash_flag)
    return privkeyObj.sign(sighash) + bytes([sighash_flag])
