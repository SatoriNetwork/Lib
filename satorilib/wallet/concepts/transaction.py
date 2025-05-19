from typing import Union
from satorilib.wallet.ethereum.valid import isValidEthereumAddress
from satorilib.utils.dict import MultiKeyDict

class TransactionStruct():

    @staticmethod
    def asSats(amount: float) -> int:
        COIN = 100000000
        return int(amount * COIN)

    def __init__(self, raw: dict, vinVoutsTxids: list[str], vinVoutsTxs: list[dict] = None):
        self.raw = raw
        self.vinVoutsTxids = vinVoutsTxids
        self.vinVoutsTxs: list[dict] = vinVoutsTxs or []
        self.txid = self.getTxid(raw)
        self.height = self.getHeight(raw)
        self.confirmations = self.getConfirmations(raw)
        self.sent = self.getSent(raw)
        self.memo = self.getMemo(raw)

    def getSupportingTransactions(self, electrumx: 'Electrumx'):
        txs = []
        for vin in self.raw.get('vin', []):
            txs.append(
                electrumx.getTransaction(vin.get('txid', '')))
        self.vinVoutsTxs: list[dict] = [t for t in txs if t is not None]

    def getAndSetReceived(self, electrumx: 'Electrumx' = None):
        if len(self.vinVoutsTxs) > 0 and electrumx:
            self.getSupportingTransactions(electrumx)
        self.received = self.getReceived(self.raw, self.vinVoutsTxs)

    def export(self) -> tuple[dict, list[str]]:
        return self.raw, self.vinVoutsTxids, self.vinVoutsTxs

    def getTxid(self, raw: dict):
        return raw.get('txid', 'unknown txid')

    def getHeight(self, raw: dict):
        return raw.get('height', 'unknown height')

    def getConfirmations(self, raw: dict):
        return raw.get('confirmations', 'unknown confirmations')

    def getSent(self, raw: dict):
        sent = MultiKeyDict()
        for vout in raw.get('vout', []):
            if 'asset' in vout:
                name = vout.get('asset', {}).get('name', 'unknown asset')
                address = vout.get('scriptPubKey', {}).get('addresses', [''])[0]
                sats = float(vout.get('asset', {}).get('amount', 0))
            else:
                name = 'EVR'
                address = vout.get('scriptPubKey', {}).get('addresses', [''])[0]
                sats = TransactionStruct.asSats(vout.get('value', 0))
            if (name, address) in sent:
                sent[name, address] = sent[name, address] + sats
            else:
                sent[name, address] = sats
        return sent

    def getReceived(self, raw: dict, vinVoutsTxs: list[dict]):
        received = {}
        for vin in raw.get('vin', []):
            position = vin.get('vout', None)
            for tx in vinVoutsTxs:
                for vout in tx.get('vout', []):
                    if position == vout.get('n', None):
                        if 'asset' in vout:
                            name = vout.get('asset', {}).get(
                                'name', 'unknown asset')
                            amount = float(
                                vout.get('asset', {}).get('amount', 0))
                        else:
                            name = 'EVR'
                            amount = float(vout.get('value', 0))
                        if name in received:
                            received[name] = received[name] + amount
                        else:
                            received[name] = amount
        return received

    def getAsset(self, raw: dict):
        return raw.get('txid', 'not implemented')

    def getMemo(self, raw: dict) -> Union[str, None]:
        '''
        vout: {
            'value': 0.0,
            'n': 502,
            'scriptPubKey': {
                'asm': 'OP_RETURN 707265646963746f7273',
                'hex': '6a0a707265646963746f7273',
                'type': 'nulldata'},
            'valueSat': 0}
        '''
        vouts = raw.get('vout', [])
        vouts.reverse()
        for vout in vouts:
            op_return = vout.get('scriptPubKey', {}).get('asm', '')
            if (
                op_return.startswith('OP_RETURN ') and
                vout.get('value', 0) == 0
            ):
                return op_return[10:]
        return None

    def hexMemo(self) -> Union[str, None]:
        return self.memo

    def bytesMemo(self) -> Union[bytes, None]:
        if self.memo == None:
            return None
        return bytes.fromhex(self.memo)

    def strMemo(self) -> Union[str, None]:
        if self.memo == None:
            return None
        return self.bytesMemo().decode('utf-8')

    def ethMemo(self) -> Union[str, None]:
        if self.memo == None:
            return None
        strMemo = self.strMemo()
        if strMemo.startswith('ethereum:') and isValidEthereumAddress(strMemo.replace('ethereum:', '')):
            address = strMemo.replace('ethereum:', '')
        elif strMemo.startswith('0x'):
            address = strMemo
        else:
            address = f'0x{strMemo}'
        if isValidEthereumAddress(address):
            return address
        return None

    @staticmethod
    def chainAddressFromMemo(strMemo:str) -> Union[dict, None]:
        if strMemo == None:
            return None
        if ':' in strMemo and len(strMemo.split(':')[1]) > 1:
            return {strMemo.split(':')[0]:strMemo.split(':')[1]}
        return None

    @staticmethod
    def validChainNames() -> Union[dict, None]:
        '''
        here we semantically encode chains with 16-bits. if only the first 11
        bits are used, we are defining the category itself, using the count
        portion we define the specific chain of that category, likewise, if all
        the count bits are used, we are not defining a specific chain, but an
        undefined chain in that category because there's no room left for it.
        0. Permissionless
        1. Permissioned
        2. UTXO-based
        3. Account-based
        4. Proof of Work
        5. Proof of Stake
        6. DAG based
        7. Smart Contract Support
        8. EVM Compatible
        9. Layer 1
        10. Native Privacy
        11. count
        12. count
        13. count
        14. count
        15. count
        '''
        return {
            'ethereum': 0b1001010111000001,
            'evrmore': 0b1010100001000001,
            #'bitcoin',
            #'base',
            #'arbitrum',
            #'polygon',
            #'ravencoin',
            #'satori',
        }

class TransactionResult():
    def __init__(
        self,
        result: str = '',
        success: bool = False,
        tx: bytes = None,
        msg: str = '',
        reportedFeeSats: int = None
    ):
        self.result = result
        self.success = success
        self.tx = tx
        self.msg = msg
        self.reportedFeeSats = reportedFeeSats


class TransactionFailure(Exception):
    '''
    unable to create a transaction for some reason
    '''

    def __init__(self, message='Transaction Failure', extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data

    def __str__(self):
        return f"{self.__class__.__name__}: {self.args[0]} {self.extra_data or ''}"


class AssetTransaction():
    evr = '657672'
    rvn = '72766e'
    t = '74'
    satoriLen = '06'
    satori = '5341544f5249'

    @staticmethod
    def satoriHex(currency: str, asset: str = 'SATORI') -> str:
        if currency.lower() == 'rvn':
            symbol = AssetTransaction.rvn
        elif currency.lower() == 'evr':
            symbol = AssetTransaction.evr
        else:
            raise Exception('invalid currency')
        asset_length_hex = f"{len(asset):02x}"
        asset_hex = asset.encode('utf-8').hex()
        return (
            symbol +
            AssetTransaction.t +
            asset_length_hex +
            asset_hex
        )

    @staticmethod
    def memoHex(memo: str) -> str:
        return memo.encode().hex()
