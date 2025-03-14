from typing import Union
from evrmore.signmessage import EvrmoreMessage


def generateAddress(publicKey: Union[bytes, str]) -> str:
    ''' returns address from pubkey '''
    from evrmore.wallet import P2PKHEvrmoreAddress
    from evrmore.core.key import CPubKey
    if isinstance(publicKey, str):
        #publicKey = bytes.fromhex(publicKey)
        publicKey = bytearray.fromhex(publicKey)
    return str(P2PKHEvrmoreAddress.from_pubkey(CPubKey(publicKey)))


def verify(
    message: Union[str, EvrmoreMessage],
    signature: Union[bytes, str],
    publicKey: Union[bytes, str, None] = None,
    address: Union[str, None] = None
):
    ''' returns bool success '''
    if (
        message is None or
        signature is None or
        (publicKey is None and address is None)
    ):
        return False
    #return VerifyMessage(
    #    address or generateAddress(publicKey),
    #    EvrmoreMessage(message) if isinstance(message, str) else message,
    #    signature if isinstance(signature, bytes) else signature.encode())
    message = EvrmoreMessage(message) if isinstance(message, str) else message
    return message.verify(
        pubkey=publicKey,
        address=address, #or generateAddress(publicKey),
        signature=signature if isinstance(signature, bytes) else signature.encode())

