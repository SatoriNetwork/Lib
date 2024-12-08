from typing import Union
from ravencoin.wallet import CRavencoinSecret
from ravencoin.signmessage import RavencoinMessage, SignMessage


def signMessage(key: CRavencoinSecret, message: Union[str, RavencoinMessage]):
    ''' returns binary signature '''
    return SignMessage(
        key,
        RavencoinMessage(message) if isinstance(message, str) else message)
