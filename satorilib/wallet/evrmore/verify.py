from typing import Union
from evrmore.signmessage import EvrmoreMessage, VerifyMessage


def generateAddress(publicKey: str):
    ''' returns address from pubkey '''
    from evrmore.wallet import P2PKHEvrmoreAddress
    from evrmore.core.key import CPubKey
    return str(
        P2PKHEvrmoreAddress.from_pubkey(
            CPubKey(
                bytearray.fromhex(
                    publicKey))))


def verify(
    message: Union[str, EvrmoreMessage],
    signature: Union[bytes, str],
    publicKey: str = None,
    address: str = None
):
    ''' returns bool success '''
    return VerifyMessage(
        address or generateAddress(publicKey),
        EvrmoreMessage(message) if isinstance(message, str) else message,
        signature if isinstance(signature, bytes) else signature.encode())
