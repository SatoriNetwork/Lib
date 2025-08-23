''' unused '''
from typing import List
from evrmore.wallet import CEvrmoreSecret
from satorilib.wallet.evrmore.utils.sign import signForPubkey


def p2pkh(priv: CEvrmoreSecret, tx, vin_index, script_code, sighash_flag) -> List[object]:
    sig = signForPubkey(priv, tx, vin_index, script_code, sighash_flag)
    pub = priv.pub
    return [sig, pub]
