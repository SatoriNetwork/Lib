from typing import Union
from evrmore.wallet import CEvrmoreSecret
from evrmore.signmessage import EvrmoreMessage, SignMessage


def signMessage(key: CEvrmoreSecret, message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return SignMessage(
        key,
        EvrmoreMessage(message) if isinstance(message, str) else message)

def sign(privkey: Union[str, bytes], message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return SignMessage(
        CEvrmoreSecret(privkey),
        EvrmoreMessage(message) if isinstance(message, str) else message)
