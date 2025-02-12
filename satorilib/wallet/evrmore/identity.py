from typing import Union
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret
from satorilib.wallet.identity import Identity
from satorilib.wallet.evrmore.sign import signMessage
from satorilib.wallet.evrmore.verify import verify


class EvrmoreIdentity(Identity):

    def __init__(self, walletPath: str, password: Union[str, None] = None):
        super().__init__(walletPath=walletPath, password=password)

    @property
    def symbol(self) -> str:
        return 'evr'

    @property
    def chain(self) -> str:
        return 'Evrmore'

    @property
    def networkByte(self) -> bytes:
        return self.networkByteP2PKH

    @property
    def networkByteP2PKH(self) -> bytes:
        # evrmore.params.BASE58_PREFIXES['PUBKEY_ADDR']
        # BASE58_PREFIXES = {'PUBKEY_ADDR': 33,
        #                   'SCRIPT_ADDR': 92,
        #                   'SECRET_KEY': 128}
        # RVN = return b'\x3c'  # b'0x3c'
        return (33).to_bytes(1, 'big')

    @property
    def networkByteP2SH(self) -> bytes:
        return (92).to_bytes(1, 'big')

    @property
    def satoriOriginalTxHash(self) -> str:
        # SATORI/TEST 15dd33886452c02d58b500903441b81128ef0d21dd22502aa684c002b37880fe
        return 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188'

    # generation ##############################################################

    @staticmethod
    def generateAddress(pubkey: Union[bytes, str]) -> str:
        if isinstance(pubkey, str):
            pubkey = bytes.fromhex(pubkey)
        return str(P2PKHEvrmoreAddress.from_pubkey(pubkey))

    def _generatePrivateKey(self, compressed: bool = True):
        SelectParams('mainnet')
        return CEvrmoreSecret.from_secret_bytes(self._entropy, compressed=compressed)

    def _generateAddress(self, pub=None):
        return P2PKHEvrmoreAddress.from_pubkey(pub or self._privateKeyObj.pub)

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CEvrmoreAddress(address).to_scriptPubKey()

    # signature ###############################################################

    def sign(self, msg: str) -> bytes:
        return signMessage(self._privateKeyObj, msg)

    def verify(self,
        msg: str,
        sig: bytes,
        pubkey: Union[str, bytes, None] = None,
        address: Union[str, None] = None,
    ) -> bool:
        return verify(
            message=msg,
            signature=sig,
            publicKey=pubkey or self.publicKey,
            address=address or self.address)
