from typing import Union
from evrmore.signmessage import EvrmoreMessage


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
    message = EvrmoreMessage(message) if isinstance(message, str) else message
    return message.verify(
        pubkey=publicKey,
        address=address, #or generateAddress(publicKey),
        signature=signature if isinstance(signature, bytes) else signature.encode())
