from typing import Union
from evrmore.wallet import CEvrmoreSecret
from evrmore.signmessage import EvrmoreMessage, signMessage


def signMessage(key: CEvrmoreSecret, message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return signMessage(
        key,
        EvrmoreMessage(message) if isinstance(message, str) else message)
