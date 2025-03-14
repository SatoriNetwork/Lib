from typing import Union
from evrmore.wallet import CEvrmoreSecret
from evrmore.signmessage import signMessage as sm
from evrmore.signmessage import EvrmoreMessage


def signMessage(key: CEvrmoreSecret, message: Union[str, EvrmoreMessage]):
    ''' returns binary signature '''
    return sm(
        key,
        EvrmoreMessage(message) if isinstance(message, str) else message)
