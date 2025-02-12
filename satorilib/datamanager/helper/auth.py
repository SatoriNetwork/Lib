from typing import Union
import datetime as dt
from satorilib.wallet.evrmore.valid_evr import validEvrmoreAddress
from satorilib.wallet import evrmore

def auth(msg: str, sig: str, pub: Union[str, bytes]=None, address: str=None) -> bool:
    return evrmore.verify(
        message=msg,
        signature=sig,
        publicKey=pub,
        address=address,
        #address=validEvrmoreAddress(payload.get('address', ''))
    )
