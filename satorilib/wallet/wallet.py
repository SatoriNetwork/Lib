from typing import Union, Callable
import os
import json
import joblib
import threading
from enum import Enum
from base64 import b64encode, b64decode
from random import randrange
import mnemonic
from decimal import Decimal
from satorilib import logging
from satorilib import config
from satorilib.utils import system
from satorilib.disk.utils import safetify
from satorilib.electrumx import Electrumx
from satorilib.wallet.concepts import authenticate
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.utils.validate import Validate
from satorilib.wallet.concepts.balance import Balance
from satorilib.wallet.concepts.transaction import TransactionResult, TransactionFailure, TransactionStruct

class TxCreationValidation(Enum):
    ready = (1, 'Initial state, ready to create')
    partialReady = (2, 'Partially ready')
    failure = (3, 'Creation failed')

    def __init__(self, code:int, description:str):
        self.code = code
        self.description = description


class WalletBase():

    def __init__(self, entropy: Union[bytes, None] = None):
        self._entropy: Union[bytes, None] = entropy
        self._entropyStr:str = ''
        self._privateKeyObj = None
        self.privateKey:str = ''
        self.words:str  = ''
        self.publicKey: str = ''
        self.address: str = ''
        self.scripthash: str = ''

    @property
    def symbol(self) -> str:
        return 'wallet'

    def close(self) -> None:
        self._entropy = None
        self._entropyStr = ''
        self._privateKeyObj = None
        self.privateKey = ''
        self.words = ''

    def loadFromYaml(self, yaml: Union[dict, None] = None):
        yaml = yaml or {}
        self._entropy = yaml.get('entropy')
        if isinstance(self._entropy, bytes):
            self._entropyStr = b64encode(self._entropy).decode('utf-8')
        if isinstance(self._entropy, str):
            self._entropyStr = self._entropy
            self._entropy = b64decode(self._entropy)
        self.words = yaml.get('words', '')
        self.privateKey = yaml.get('privateKey', '')
        self.publicKey = yaml.get('publicKey', '')
        self.address = yaml.get(self.symbol, {}).get('address')
        self.scripthash = yaml.get('scripthash', '')
        self.generateObjects(fromYaml=True)

    def verify(self) -> bool:
        if self._entropy is None and self._privateKeyObj is None:
            return False
        _entropy = self._entropy
        _entropyStr = b64encode(_entropy).decode('utf-8')
        _privateKeyObj = self._generatePrivateKey()
        if _privateKeyObj is None:
            return False
        _addressObj = self._generateAddress(pub=_privateKeyObj.pub)
        words = self._generateWords()
        privateKey = str(_privateKeyObj)
        publicKey = _privateKeyObj.pub.hex()
        address = str(_addressObj)
        # file might not have the address listed...
        if self.address is None:
            self.address = address
        scripthash = self._generateScripthash(forAddress=address)
        return (
            _entropy == self._entropy and
            _entropyStr == self._entropyStr and
            ((words == self.words) if self.privateKey == privateKey else True) and
            self.privateKey in (privateKey, ) and
            self.publicKey in (publicKey, ) and
            self.address in (address, ) and
            self.scripthash in (scripthash, ))

    def generateObjects(self, fromYaml: bool = False):
        self._entropy = self._entropy or WalletBase.generateEntropy()
        self._entropyStr = b64encode(self._entropy).decode('utf-8')
        self._privateKeyObj = self._generatePrivateKey(privkey=self.privateKey if fromYaml else None)
        self._addressObj = self._generateAddress()

    def generate(self):
        self.generateObjects()
        self.words = self.words or self._generateWords()
        if self._privateKeyObj is None:
            return False
        self.privateKey = self.privateKey or str(self._privateKeyObj)
        self.publicKey = self.publicKey or self._privateKeyObj.pub.hex()
        self.address = self.address or str(self._addressObj)
        self.scripthash = self.scripthash or self._generateScripthash()

    def _generateScripthash(self, forAddress: Union[str, None] = None):
        # possible shortcut:
        # self.scripthash = '76a914' + [s for s in self._addressObj.to_scriptPubKey().raw_iter()][2][1].hex() + '88ac'
        from base58 import b58decode_check
        from binascii import hexlify
        from hashlib import sha256
        import codecs
        OP_DUP = b'76'
        OP_HASH160 = b'a9'
        BYTES_TO_PUSH = b'14'
        OP_EQUALVERIFY = b'88'
        OP_CHECKSIG = b'ac'
        def dataToPush(address): return hexlify(b58decode_check(address)[1:])
        def sigScriptRaw(address): return b''.join(
            (OP_DUP, OP_HASH160, BYTES_TO_PUSH, dataToPush(address), OP_EQUALVERIFY, OP_CHECKSIG))
        def scripthash(address): return sha256(codecs.decode(
            sigScriptRaw(address), 'hex_codec')).digest()[::-1].hex()
        return scripthash(forAddress or self.address)

    @staticmethod
    def generateEntropy() -> bytes:
        import secrets
        # return m.to_entropy(m.generate())
        # return b64encode(x.to_seed(x.generate(strength=128))).decode('utf-8')
        # return os.urandom(32)
        return secrets.token_bytes(32)

    def _generateWords(self):
        return mnemonic.Mnemonic('english').to_mnemonic(self._entropy or b'')

    def _generatePrivateKey(self, compressed: bool = True):
        ''' returns a private key object '''

    def _generateAddress(self, pub=None):
        ''' returns an address object '''

    def _generateScriptPubKeyFromAddress(self, address: str):
        ''' returns CScript object from address '''

    def _generateUncompressedPubkey(self):
        ''' returns a private key object '''
        return self._generatePrivateKey(compressed=False).pub.hex()


class Wallet(WalletBase):

    @staticmethod
    def openSafely(
        supposedDict: Union[dict, None],
        key: str,
        default: Union[str, int, dict, list, None] = None,
    ):
        if not isinstance(supposedDict, dict):
            return default
        try:
            return supposedDict.get(key, default)
        except Exception as e:
            logging.error('openSafely err:', supposedDict, e)
            return default

    def __init__(
        self,
        walletPath: str,
        cachePath: Union[str, None] = None,
        reserve: float = .25,
        kind: str = 'wallet',
        isTestnet: bool = False,
        password: Union[str, None] = None,
        watchAssets: Union[list[str], None] = None,
        skipSave: bool = False,
        pullFullTransactions: bool = True,
        useElectrumx: bool = True,
        balanceUpdatedCallback: Union[Callable, None] = None,
    ):
        if walletPath == cachePath:
            raise Exception('wallet and cache paths cannot be the same')
        super().__init__()
        self.useElectrumx = useElectrumx
        self.skipSave = skipSave
        self.watchAssets = ['SATORI'] if watchAssets is None else watchAssets
        # at $100 SATORI this is 1 penny (for evr tx fee)
        self.mundoFee = 0.0001
        # at $100 SATORI this is 1 dollar (for risk and gas fees), by BurnBridge
        self.bridgeFee: float = 0.01
        self.bridgeAddress: str = 'EUqCW1WmT6a9Y6RBVhsxY1k4S135RPWCy7'  # TODO finish
        self.burnAddress: str = TxUtils.evrBurnMintAddressMain #'EXBurnMintXXXXXXXXXXXXXXXXXXXbdK5E'  # real
        self.maxBridgeAmount: float = 500
        #self.burnAddress: str = 'EL1BS6HmwY1KoeqBokKjUMcWbWsn5kamGv' # testing
        self.isTestnet = isTestnet
        self.password = password
        self.walletPath = walletPath
        self.cachePath = cachePath or walletPath.replace('.yaml', '.cache.joblib')
        # maintain minimum amount of currency at all times to cover fees - server only
        self.reserveAmount = reserve
        self.reserve = TxUtils.asSats(reserve)
        self.stats = {}
        self.alias = None
        self.kind = kind
        self.banner = None
        self.currency: Balance = Balance.empty('EVR')
        self.balance: Balance = Balance.empty('SATORI')
        self.divisibility = 0
        self.transactionHistory: list[dict] = []
        # TransactionStruct(*v)... {txid: (raw, vinVoutsTxs)}
        self._transactions: dict[str, tuple[dict, list[dict]]] = {}
        self.cache = {}
        self.transactions: list[TransactionStruct] = []
        self.assetTransactions = []
        self.electrumx: Electrumx = None # type: ignore
        self.unspentCurrency = None
        self.unspentAssets = None
        self.status = None
        self.pullFullTransactions = pullFullTransactions
        self.lastBalanceAmount = 0
        self.lastCurrencyAmount = 0
        self.balanceUpdatedCallback = balanceUpdatedCallback
        self.load()
        self.loadCache()

    def __call__(self):
        self.get()
        return self

    def __repr__(self):
        return (
            f'{self.chain}Wallet('
            f'\n  publicKey: {self.publicKey},'
            f'\n  privateKey: {self.privateKey},'
            f'\n  words: {self.words},'
            f'\n  address: {self.address},'
            f'\n  scripthash: {self.scripthash},'
            f'\n  currency: {self.currency},'
            f'\n  balance: {self.balance},'
            f'\n  stats: {self.stats},'
            f'\n  banner: {self.banner})')

    @property
    def chain(self) -> str:
        return ''

    @property
    def satoriOriginalTxHash(self) -> str:
        return ''

    @property
    def publicKeyBytes(self) -> bytes:
        return bytes.fromhex(self.publicKey or '')

    @property
    def isEncrypted(self) -> bool:
        return ' ' not in (self.words or '')

    @property
    def isDecrypted(self) -> bool:
        return not self.isEncrypted

    @property
    def networkByte(self) -> bytes:
        return (33).to_bytes(1, 'big') # evrmore by default

    @property
    def account(self) -> 'eth_account.Account':
        if self.isDecrypted:
            try:
                from satorilib.wallet.ethereum.wallet import EthereumWallet
                return EthereumWallet.generateAccount(self._entropy)
            except Exception as e:
                logging.error('error with eth account:', e)
        return None

    @property
    def ethAddress(self) -> str:
        return self.account.address

    def shouldPullUnspents(self) -> bool:
        return not (
            self.lastBalanceAmount == (self.balance.amount or 0) and
            self.lastCurrencyAmount == (self.currency.amount or 0))

    def updateBalances(self):
        self.lastBalanceAmount = self.balance.amount
        self.lastCurrencyAmount = self.currency.amount

    ### Loading ################################################################

    def walletFileExists(self, path: Union[str, None] = None):
        return os.path.exists(path or self.walletPath)

    def cacheFileExists(self):
        return os.path.exists(self.cachePath)

    def load(self) -> bool:
        if not self.walletFileExists():
            self.generate()
            self.save()
            return self.load()
        self.yaml = config.get(self.walletPath)
        if self.yaml == False:
            return False
        self.yaml = self.decryptWallet(self.yaml)
        self.loadFromYaml(self.yaml)
        if self.isDecrypted and not super().verify():
            raise Exception('wallet or vault file corrupt')
        return True

    def close(self) -> None:
        self.password = None
        self.yaml = None
        super().close()

    def open(self, password: Union[str, None] = None) -> None:
        self.password = password
        self.load()

    def decryptWallet(self, encrypted: dict) -> dict:
        if isinstance(self.password, str):
            from satorilib import secret
            try:
                return secret.decryptMapValues(
                    encrypted=encrypted,
                    password=self.password,
                    keys=['entropy', 'privateKey', 'words',
                          # we used to encrypt these, but we don't anymore...
                          'address' if len(encrypted.get(self.symbol, {}).get(
                              'address', '')) > 34 else '',  # == 108 else '',
                          'scripthash' if len(encrypted.get(
                              'scripthash', '')) != 64 else '',  # == 152 else '',
                          'publicKey' if len(encrypted.get(
                              'publicKey', '')) != 66 else '',  # == 152 else '',
                          ])
            except Exception as _:
                return encrypted
        return encrypted

    def encryptWallet(self, content: dict) -> dict:
        if isinstance(self.password, str):
            from satorilib import secret
            try:
                return secret.encryptMapValues(
                    content=content,
                    password=self.password,
                    keys=['entropy', 'privateKey', 'words'])
            except Exception as _:
                return content
        return content

    def save(self, path: Union[str, None] = None) -> bool:
        path = path or self.walletPath
        safetify(path)
        if self.walletFileExists(path):
            return False
        config.put(
            data={
                **(
                    self.encryptWallet(content=self.yaml)
                    if hasattr(self, 'yaml') and isinstance(self.yaml, dict)
                    else {}),
                **self.encryptWallet(
                    content={
                        'entropy': self._entropyStr,
                        'words': self.words,
                        'privateKey': self.privateKey,
                    }),
                **{
                    'publicKey': self.publicKey,
                    'scripthash': self.scripthash,
                    self.symbol: {
                        'address': self.address,
                    }
                }
            },
            path=path)
        return True

    def loadCache(self) -> bool:

        def fromJoblib(cachePath: str) -> Union[None, dict]:
            try:
                if os.path.isfile(cachePath):
                    return joblib.load(cachePath)
                return None
            except Exception as e:
                logging.debug(f'unable to load wallet cache, creating a new one: {e}')
                if os.path.isfile(cachePath):
                    os.remove(cachePath)
                return None

        if self.skipSave:
            return False
        if not self.cacheFileExists():
            return False
        try:
            if self.cachePath.endswith('.joblib'):
                self.cache = fromJoblib(self.cachePath)
                if self.cache is None:
                    return False
                self.status = self.cache['status']
                self.unspentCurrency = self.cache['unspentCurrency']
                self.unspentAssets = self.cache['unspentAssets']
                self.transactions = self.cache['transactions']
                return self.status
            return False
        except Exception as e:
            logging.error(f'issue loading transaction cache, {e}')
            return False

    def saveCache(self):
        if self.skipSave:
            return False
        try:
            safetify(self.cachePath)
            if self.cachePath.endswith('.joblib'):
                safetify(self.cachePath)
                joblib.dump({
                    'status': self.status,
                    'unspentCurrency': self.unspentCurrency,
                    'unspentAssets': self.unspentAssets,
                    'transactions': self.transactions},
                    self.cachePath)
                return True
        except Exception as e:
            logging.error("wallet transactions saveCache error", e)

    ### Electrumx ##############################################################

    def connected(self) -> bool:
        if isinstance(self.electrumx, Electrumx):
            return self.electrumx.connected()
        return False

    def subscribeToScripthashActivity(self):

        def parseNotification(notification: dict) -> str:
            return notification.get('params',['scripthash', 'status'])[-1]

        def handleNotifiation(notification: dict):
            return updateStatus(parseNotification(notification))

        def handleResponse(status: str):
            return updateStatus(status)

        def updateStatus(status: str) -> bool:
            def thenSave():
                self.getUnspentSignatures()
                self.status = status
                self.saveCache()

            if self.status == status:
                return False
            self.getBalances()
            self.getUnspents()
            self.status = status
            self.getUnspentTransactions(threaded=True, then=thenSave)
            return True

        #if self.useElectrumx and self.electrumx.ensureConnected():
        return handleResponse(
            self.electrumx.api.subscribeScripthash(
                scripthash=self.scripthash,
                callback=handleNotifiation))

    def preSend(self) -> bool:
        #if  self.useElectrumx and isinstance(self.electrumx, Electrumx):
            #if self.electrumx.ensureConnected():
            #    return True
        self.stats = {'status': 'not connected'}
        self.divisibility = self.divisibility or 8
        self.banner = 'not connected'
        self.transactionHistory = self.transactionHistory or []
        self.unspentCurrency = self.unspentCurrency or []
        self.unspentAssets = self.unspentAssets or []
        self.currency = self.currency or 0
        self.balance = self.balance or 0
        return False

    def get(self, *args, **kwargs):
        ''' gets data from the blockchain, saves to attributes '''
        try:
            self.maybeConnect()
            if self.banner is None or self.banner == 'not connected':
                self.getStats()
                self.getTransactionHistory()
            self.getBalances()
            self.updateBalances()
        except Exception as e:
            logging.debug('unable to get balances', e)

    def getStats(self):
        if not self.useElectrumx:
            return
        self.stats = self.electrumx.api.getStats()
        self.divisibility = Wallet.openSafely(self.stats, 'divisions', 8)
        self.divisibility = self.divisibility if self.divisibility is not None else 8
        self.banner = self.electrumx.api.getBanner()

    def getTransactionHistory(self):
        if not self.useElectrumx:
            return
        self.transactionHistory = self.electrumx.api.getTransactionHistory(
            scripthash=self.scripthash)

    def getBalances(self):
        if not self.useElectrumx:
            return
        self.balances = self.electrumx.api.getBalances(scripthash=self.scripthash)
        self.currency = Balance.fromBalances('EVR', self.balances or {})
        self.balance = Balance.fromBalances('SATORI', self.balances or {})
        if self.balanceUpdatedCallback is not None:
            self.balanceUpdatedCallback(kind=self.kind, evr=self.currency, satori=self.balance)

    def getReadyToSend(self, balance: bool = False, save: bool = True):
        if not self.useElectrumx:
            return
        try:
            self.maybeConnect()
            if balance:
                self.getBalances()
            self.getUnspents()
            self.getUnspentTransactions(threaded=False)
            self.getUnspentSignatures()
            if save:
                self.saveCache()
        except Exception as e:
            logging.debug('unable to get reaedy to send', e)

    def getUnspents(self):
        if not self.useElectrumx:
            return
        #import traceback
        #traceback.print_stack()
        #self.electrumx.ensureConnected()
        self.unspentCurrency = self.electrumx.api.getUnspentCurrency(scripthash=self.scripthash) or []
        self.unspentCurrency = [
            x for x in self.unspentCurrency
            if x.get('asset') == None]
        self.unspentAssets = []
        if 'SATORI' in self.watchAssets:
            # never used:
            #self.balanceOnChain = self.electrumx.api.getBalance(scripthash=self.scripthash)
            #logging.debug('self.balanceOnChain', self.balanceOnChain)
            # mempool sends all unspent transactions in currency and assets so we have to filter them here:
            self.unspentAssets = self.electrumx.api.getUnspentAssets(scripthash=self.scripthash) or []
            self.unspentAssets = [
                x for x in self.unspentAssets
                if x.get('asset') != None]
            logging.debug('self.unspentAssets', self.unspentAssets)

    def deriveBalanceFromUnspents(self):
        ''' though I like the one source of truth we don't do this anymore '''
        for x in self.unspentCurrency:
            Wallet.openSafely(x, 'value', 0)
        self.currency = sum([
            x.get('value', 0)
            for x in self.unspentCurrency
            if x.get('asset') == None])
        self.currencyAmount = TxUtils.asAmount(self.currency or 0, 8)
        if 'SATORI' in self.watchAssets:
            self.balance = sum([
                x.get('value', 0)
                for x in self.unspentAssets
                if (x.get('name', x.get('asset')) == 'SATORI' and
                    x.get('value') > 0)])
            logging.debug('self.balance', self.balance)
            self.balance.amount = TxUtils.asAmount(
                self.balance or 0,
                self.divisibility)

    def getUnspentTransactions(self, threaded: bool = True, then: callable = None) -> bool:

        def run():
            transactionIds = {tx.txid for tx in self.transactions}
            txids = [uc['tx_hash'] for uc in self.unspentCurrency] + [ua['tx_hash'] for ua in self.unspentAssets]
            for txid in txids:
                if txid not in transactionIds:
                    raw = self.electrumx.api.getTransaction(txid)
                    logging.debug('pulling transaction:', txid, color='blue')
                    if raw is not None:
                        self.transactions.append(TransactionStruct(
                            raw=raw,
                            vinVoutsTxids=[
                                vin.get('txid', '')
                                for vin in raw.get('vin', {})
                                if vin.get('txid', '') != '']))
            if callable(then):
                then()

        if not self.useElectrumx:
            return False
        if threaded:
            self.getUnspentTransactionsThread = threading.Thread(
                target=run, daemon=True)
            self.getUnspentTransactionsThread.start()
        else:
            run()
            if callable(then):
                then()
        return True



    ### Functions ##############################################################

    def appendTransaction(self, txid):
        if not self.useElectrumx:
            return
        #self.electrumx.ensureConnected()
        if txid not in self._transactions.keys():
            raw = self.electrumx.api.getTransaction(txid)
            if raw is not None:
                if self.pullFullTransactions:
                    txs = []
                    txIds = []
                    for vin in raw.get('vin', {}):
                        txId = vin.get('txid', '')
                        if txId == '':
                            continue
                        txIds.append(txId)
                        txs.append(self.electrumx.api.getTransaction(txId))
                    transaction = TransactionStruct(
                        raw=raw,
                        vinVoutsTxids=txIds,
                        vinVoutsTxs=[t for t in txs if t is not None])
                    self.transactions.append(transaction)
                    self._transactions[txid] = transaction.export()
                    return transaction.export()
                else:
                    txs = []
                    txIds = []
                    for vin in raw.get('vin', {}):
                        txId = vin.get('txid', '')
                        if txId == '':
                            continue
                        txIds.append(txId)
                        # <--- don't get the inputs to the transaction here
                    transaction = TransactionStruct(
                        raw=raw,
                        vinVoutsTxids=txIds)
                    self.transactions.append(transaction)
        else:
            raw, txids, txs = self._transactions.get(txid, ({}, []))
            self.transactions.append(
                TransactionStruct(
                    raw=raw,
                    vinVoutsTxids=txids,
                    vinVoutsTxs=txs))

    def callTransactionHistory(self):
        def getTransactions(transactionHistory: dict) -> list:
            self.transactions = []
            if not isinstance(transactionHistory, list):
                return
            new_transactions = {}  # Collect new transactions here
            for tx in transactionHistory:
                txid = tx.get('tx_hash', '')
                new_tranaction = self.appendTransaction(txid)
                if new_tranaction is not None:
                    new_transactions[txid] = new_tranaction
            # why not save self._transactions to cache? because these are incremental.
            #self.saveCache(new_transactions)

        # self.getTransactionsThread = threading.Thread(
        #    target=getTransactions, args=(self.transactionHistory,), daemon=True)
        # self.getTransactionsThread.start()

    def setAlias(self, alias: Union[str, None] = None) -> None:
        self.alias = alias

    def hash160ToAddress(self, pubKeyHash: Union[str, bytes]) -> str:
        return TxUtils.hash160ToAddress(pubKeyHash, self.networkByte)

    def showStats(self):
        ''' returns a string of stats properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        stats = (self.stats or {})
        divisions = stats.get('divisions', 8)
        circulatingCoins = TxUtils.asAmount(int(stats.get(
            'sats_in_circulation', 100000000000000)))
        # circulatingSats = stats.get(
        #    'sats_in_circulation', 100000000000000) / int('1' + ('0'*invertDivisibility(int(divisions))))
        # headTail = str(circulatingSats).split('.')
        # if headTail[1] == '0' or headTail[1] == '00000000':
        #    circulatingSats = f"{int(headTail[0]):,}"
        # else:
        #    circulatingSats = f"{int(headTail[0]):,}" + '.' + \
        #        f"{headTail[1][0:4]}" + '.' + f"{headTail[1][4:]}"
        return f'''
    Circulating Supply: {circulatingCoins}
    Decimal Points: {divisions}
    Reissuable: {stats.get('reissuable', False)}
    Issuing Transactions: {stats.get('source', {}).get('tx_hash', self.satoriOriginalTxHash)}
    '''

    def authPayload(self, asDict: bool = False, challenge: str = None) -> Union[str, dict]:
        payload = authenticate.authPayload(self, challenge)
        if asDict:
            return payload
        return json.dumps(payload)

    def registerPayload(
        self,
        asDict: bool = False,
        challenge: str = None,
        vaultInfo:dict = None,
    ) -> Union[str, dict]:
        payload = {
            **authenticate.authPayload(self, challenge),
            **system.devicePayload(asDict=True), 
            **(vaultInfo or {})}
        if asDict:
            return payload
        return json.dumps(payload)

    def sign(self, message: str):
        ''' signs a message with the private key '''

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None) -> bool:
        ''' verifies a message with the public key '''

    ### Transaction Support ####################################################

    def getUnspentSignatures(self, force: bool = False) -> bool:
        '''
        we don't need to get the scriptPubKey every time we open the wallet,
        and it requires lots of calls for individual transactions.
        we just need them available when we're creating transactions.
        '''
        if 'SATORI' in self.watchAssets:
            unspents = [
                u for u in self.unspentCurrency + self.unspentAssets
                if 'scriptPubKey' not in u]
        else:
            unspents = [
                u for u in self.unspentCurrency
                if 'scriptPubKey' not in u]
        if not force and len(unspents) == 0:
            # already have them all
            return True

        try:
            # subscription is not necessary for this
            # make sure we're connected
            # if not hasattr(self, 'electrumx') or not self.electrumx.connected():
            #    self.connect()
            # self.get()

            # get transactions, save their scriptPubKey hex to the unspents
            for uc in self.unspentCurrency:
                if uc.get('scriptPubKey', None) is not None:
                    continue
                if len([tx for tx in self.transactions if tx.txid == uc['tx_hash']]) == 0:
                    new_transactions = {}  # Collect new transactions here
                    new_tranaction = self.appendTransaction(uc['tx_hash'])
                    if new_tranaction is not None:
                        new_transactions[uc['tx_hash']] = new_tranaction
                    #self.saveCache(new_transactions)
                tx = [tx for tx in self.transactions if tx.txid == uc['tx_hash']]
                if len(tx) > 0:
                    vout = [vout for vout in tx[0].raw.get(
                        'vout', []) if vout.get('n') == uc['tx_pos']]
                    if len(vout) > 0:
                        scriptPubKey = vout[0].get(
                            'scriptPubKey', {}).get('hex', None)
                        if scriptPubKey is not None:
                            uc['scriptPubKey'] = scriptPubKey
            if 'SATORI' in self.watchAssets:
                for ua in self.unspentAssets:
                    if ua.get('scriptPubKey', None) is not None:
                        continue
                    if len([tx for tx in self.transactions if tx.txid == ua['tx_hash']]) == 0:
                        new_transactions = {}  # Collect new transactions here
                        new_tranaction = self.appendTransaction(ua['tx_hash'])
                        if new_tranaction is not None:
                            new_transactions[ua['tx_hash']] = new_tranaction
                        #self.saveCache(new_transactions)
                    tx = [tx for tx in self.transactions if tx.txid == ua['tx_hash']]
                    if len(tx) > 0:
                        vout = [vout for vout in tx[0].raw.get(
                            'vout', []) if vout.get('n') == ua['tx_pos']]
                        if len(vout) > 0:
                            scriptPubKey = vout[0].get(
                                'scriptPubKey', {}).get('hex', None)
                            if scriptPubKey is not None:
                                ua['scriptPubKey'] = scriptPubKey
        except Exception as e:
            logging.warning(
                'unable to acquire signatures of unspent transactions, maybe unable to send', e, print=True)
            return False
        return True

    def getUnspentsFromHistory(self) -> tuple[list, list]:
        '''
            get unspents from transaction history
            I have to figure out what the VOUTs are myself -
            and I have to split them into lists of currency and Satori outputs
            get history, loop through all transactions, gather all vouts
            loop through all transactions again, remove the vouts that are referenced by vins
            loop through the remaining vouts which are the unspent vouts
            and throw the ones away that are assets but not satori,
            and save the others as currency or satori outputs
            self.transactionHistory structure: [{
                "height": 215008,
                "tx_hash": "f3e1bf48975b8d6060a9de8884296abb80be618dc00ae3cb2f6cee3085e09403"
            }]
            unspents structure: [{
                "tx_pos": 0,
                "value": 45318048,
                "tx_hash": "9f2c45a12db0144909b5db269415f7319179105982ac70ed80d76ea79d923ebf",
                "height": 437146 # optional
            }]
        '''

        for txRef in self.transactionHistory:
            txRef['tx_hash']

    def _checkSatoriValue(self, output: 'CMutableTxOut', amount: float=None) -> bool:
        '''
        returns true if the output is a satori output of amount or self.mundoFee
        '''

    def _gatherReservedCurrencyUnspent(self, exactSats: int = 0):
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') == exactSats]
        if len(unspentCurrency) == 0:
            return None
        return unspentCurrency[0]

    def _gatherOneCurrencyUnspent(self, atleastSats: int = 0, claimed: dict = None) -> tuple:
        claimed = claimed or {}
        for unspentCurrency in self.unspentCurrency:
            if (
                unspentCurrency.get('value') >= atleastSats and
                unspentCurrency.get('tx_hash') not in claimed.keys()
            ):
                return unspentCurrency, unspentCurrency.get('value'), len(self.unspentCurrency)
        return None, 0, 0

    def _gatherCurrencyUnspents(
        self,
        sats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        randomly: bool = False,
    ) -> tuple[list, int]:
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') > 0]
        unspentCurrency = sorted(unspentCurrency, key=lambda x: x['value'])
        haveCurrency = sum([x.get('value') for x in unspentCurrency])
        if (haveCurrency < sats + self.reserve):
            raise TransactionFailure(
                'tx: must retain a reserve of currency to cover fees')
        gatheredCurrencySats = 0
        gatheredCurrencyUnspents = []
        encounteredDust = False
        while (
            gatheredCurrencySats < sats + TxUtils.estimatedFee(
                inputCount=inputCount + len(gatheredCurrencyUnspents),
                outputCount=outputCount)
        ):
            if randomly:
                randomUnspent = unspentCurrency.pop(
                    randrange(len(unspentCurrency)))
                gatheredCurrencyUnspents.append(randomUnspent)
                gatheredCurrencySats += randomUnspent.get('value')
            else:
                try:
                    smallestUnspent = unspentCurrency.pop(0)
                    gatheredCurrencyUnspents.append(smallestUnspent)
                    gatheredCurrencySats += smallestUnspent.get('value')
                except IndexError as _:
                    # this usually happens when people have lots of dust.
                    encounteredDust = True
                    break
        if encounteredDust:
            unspentCurrency = gatheredCurrencyUnspents
            gatheredCurrencySats = 0
            gatheredCurrencyUnspents = []
            while (
                gatheredCurrencySats < sats + TxUtils.estimatedFee(
                    inputCount=inputCount + len(gatheredCurrencyUnspents),
                    outputCount=outputCount)
            ):
                if randomly:
                    randomUnspent = unspentCurrency.pop(
                        randrange(len(unspentCurrency)))
                    gatheredCurrencyUnspents.append(randomUnspent)
                    gatheredCurrencySats += randomUnspent.get('value')
                else:
                    try:
                        largestUnspent = unspentCurrency.pop()
                        gatheredCurrencyUnspents.append(largestUnspent)
                        gatheredCurrencySats += largestUnspent.get('value')
                    except IndexError as _:
                        # they simply do not have enough currency to send
                        # it might all be dust.
                        # at least we can still try to make the transaction...
                        break
        return (gatheredCurrencyUnspents, gatheredCurrencySats)

    def _gatherSatoriUnspents(
        self,
        sats: int,
        randomly: bool = False
    ) -> tuple[list, int]:
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name', x.get('asset')) == 'SATORI' and x.get('value') > 0]
        unspentSatori = sorted(unspentSatori, key=lambda x: x['value'])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        if not (haveSatori >= sats > 0):
            raise TransactionFailure('tx: not enough satori to send')
        # gather satori utxos at random
        gatheredSatoriSats = 0
        gatheredSatoriUnspents = []
        while gatheredSatoriSats < sats:
            if randomly:
                randomUnspent = unspentSatori.pop(
                    randrange(len(unspentSatori)))
                gatheredSatoriUnspents.append(randomUnspent)
                gatheredSatoriSats += randomUnspent.get('value')
            else:
                smallestUnspent = unspentSatori.pop(0)
                gatheredSatoriUnspents.append(smallestUnspent)
                gatheredSatoriSats += smallestUnspent.get('value')
        return (gatheredSatoriUnspents, gatheredSatoriSats)

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
        ''' compile inputs '''
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py

    def _compileSatoriOutputs(self, satsByAddress: dict[str, int] = None) -> list:
        ''' compile satori outputs'''
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        # vouts
        # how do I specify an asset output? this doesn't seem right for that:
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG OP_RVN_ASSET 0c72766e6f075341544f524921 75
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 14(20 bytes length of asset information) 657672(evr) 74(t) 07(length of asset name) 5341544f524921(SATORI is asset name) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c1465767274075341544f52492100e1f5050000000075
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG ])
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG OP_EVR_ASSET 0c ])
        #
        # for asset transfer...? perfect?
        #   >>> Hash160(CRavencoinAddress(address).to_scriptPubKey())
        #   b'\xc2\x0e\xdf\x8cG\xd7\x8d\xac\x052\x03\xddC<0\xdd\x00\x91\xd9\x19'
        #   >>> Hash160(CRavencoinAddress(address))
        #   b'!\x8d"6\xcf\xe8\xf6W4\x830\x85Y\x06\x01J\x82\xc4\x87p' <- looks like what we get with self.pubkey.encode()
        # https://ravencoin.org/assets/
        # https://rvn.cryptoscope.io/api/getrawtransaction/?txid=bae95f349f15effe42e75134ee7f4560f53462ddc19c47efdd03f85ef4ab8f40&decode=1
        #
        # todo: you could generalize this to send any asset. but not necessary.

    def _compileCurrencyOutputs(self, currencySats: int, address: str) -> list['CMutableTxOut']:
        ''' compile currency outputs'''

    def _compileSatoriChangeOutput(
        self,
        satoriSats: int = 0,
        gatheredSatoriSats: int = 0,
    ) -> 'CMutableTxOut':
        ''' compile satori change output '''

    def _compileCurrencyChangeOutput(
        self,
        currencySats: int = 0,
        gatheredCurrencySats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        scriptPubKey: 'CScript' = None,
        returnSats: bool = False,
    ) -> Union['CMutableTxOut', None, tuple['CMutableTxOut', int]]:
        ''' compile currency change output '''

    def _compileMemoOutput(self, memo: str) -> 'CMutableTxOut':
        '''
        compile op_return memo output
        for example:
            {"value":0,
            "n":0,
            "scriptPubKey":{"asm":"OP_RETURN 1869440365",
            "hex":"6a046d656d6f",
            "type":"nulldata"},
            "valueSat":0},
        '''

    def _createTransaction(self, txins: list, txinScripts: list, txouts: list) -> 'CMutableTransaction':
        ''' create transaction '''

    def _createPartialOriginatorSimple(self, txins: list, txinScripts: list, txouts: list) -> 'CMutableTransaction':
        ''' originate partial '''

    def _createPartialCompleterSimple(self, txins: list, txinScripts: list, tx: 'CMutableTransaction') -> 'CMutableTransaction':
        ''' complete partial '''

    def _txToHex(self, tx: 'CMutableTransaction') -> str:
        ''' serialize '''

    def _serialize(self, tx: 'CMutableTransaction') -> bytes:
        ''' serialize '''

    def _deserialize(self, serialTx: bytes) -> 'CMutableTransaction':
        ''' serialize '''

    def broadcast(self, txHex: str) -> str:
        if not self.useElectrumx:
            return ''
        self.maybeConnect()
        return self.electrumx.api.broadcast(txHex)

    ### Transactions ###########################################################

    # for server

    def satoriDistribution(
        self,
        amountByAddress: dict[str: float],
        memo: str=None,
        broadcast: bool = True,
    ) -> str:
        ''' creates a transaction with multiple SATORI asset recipients '''
        if len(amountByAddress) == 0 or len(amountByAddress) > 1000:
            raise TransactionFailure('too many or too few recipients')
        satsByAddress: dict[str: int] = {}
        for address, amount in amountByAddress.items():
            if (
                amount <= 0 or
                # not TxUtils.isAmountDivisibilityValid(
                #    amount=amount,
                #    divisibility=self.divisibility) or
                not Validate.address(address, self.symbol)
            ):
                logging.info('amount', amount, 'divisibility', self.divisibility, 'address', address, 'address valid:', Validate.address(address, self.symbol),
                             'TxUtils.isAmountDivisibilityValid(amount=amount,divisibility=self.divisibility)', TxUtils.isAmountDivisibilityValid(amount=amount, divisibility=self.divisibility), color='green')
                raise TransactionFailure('satoriDistribution bad params')
            satsByAddress[address] = TxUtils.roundSatsDownToDivisibility(
                sats=TxUtils.asSats(amount),
                divisibility=self.divisibility)
        memoCount = 0
        if memo is not None:
            memoCount = 1
        satoriSats = sum(satsByAddress.values())
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=len(satsByAddress) + 2 + memoCount)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs(satsByAddress)
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats,
            gatheredSatoriSats=gatheredSatoriSats)
        currencyChangeOut = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(txins),
            outputCount=len(satsByAddress) + 2 + memoCount)  # satoriChange, currencyChange, memo
        memoOut = None
        if memo is not None:
            memoOut = self._compileMemoOutput(memo)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut, currencyChangeOut, memoOut]
                if x is not None])
        if broadcast:
            return self.broadcast(self._txToHex(tx))
        return self._txToHex(tx)

    # for neuron
    def currencyTransaction(self, amount: float, address: str):
        ''' creates a transaction to just send rvn '''
        ''' unused, untested '''
        if (
            amount <= 0 or
            # not TxUtils.isAmountDivisibilityValid(
            #     amount=amount,
            #     divisibility=8) or
            not Validate.address(address, self.symbol)
        ):
            raise TransactionFailure('bad params for currencyTransaction')
        currencySats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(amount),
            divisibility=8)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=0,
                outputCount=1)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents)
        currencyOuts = self._compileCurrencyOutputs(currencySats, address)
        currencyChangeOut = self._compileCurrencyChangeOutput(
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(txins),
            outputCount=2)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=currencyOuts + [
                x for x in [currencyChangeOut]
                if x is not None])
        return self.broadcast(self._txToHex(tx))

    # for neuron
    def satoriTransaction(self, amount: float, address: str):
        ''' creates a transaction to send satori to one address '''
        if (
            amount <= 0 or
            # not TxUtils.isAmountDivisibilityValid(
            #    amount=amount,
            #    divisibility=self.divisibility) or
            not Validate.address(address, self.symbol)
        ):
            raise TransactionFailure('satoriTransaction bad params')
        satoriSats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(amount),
            divisibility=self.divisibility)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        # gather currency in anticipation of fee
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=3)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs({address: satoriSats})
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats,
            gatheredSatoriSats=gatheredSatoriSats)
        currencyChangeOut = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(txins),
            outputCount=3)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut, currencyChangeOut]
                if x is not None])
        return self.broadcast(self._txToHex(tx))

    def satoriAndCurrencyTransaction(self, satoriAmount: float, currencyAmount: float, address: str):
        ''' creates a transaction to send satori and currency to one address '''
        ''' unused, untested '''
        if (
            satoriAmount <= 0 or
            currencyAmount <= 0 or
            # not TxUtils.isAmountDivisibilityValid(
            #    amount=satoriAmount,
            #    divisibility=self.divisibility) or
            # not TxUtils.isAmountDivisibilityValid(
            #    amount=currencyAmount,
            #    divisibility=8) or
            not Validate.address(address, self.symbol)
        ):
            raise TransactionFailure('satoriAndCurrencyTransaction bad params')
        satoriSats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(satoriAmount),
            divisibility=self.divisibility)
        currencySats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(currencyAmount),
            divisibility=8)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=len(gatheredSatoriUnspents),
                outputCount=4)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs({address: satoriSats})
        currencyOuts = self._compileCurrencyOutputs(currencySats, address)
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats,
            gatheredSatoriSats=gatheredSatoriSats)
        currencyChangeOut = self._compileCurrencyChangeOutput(
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=(
                len(gatheredSatoriUnspents) +
                len(gatheredCurrencyUnspents)),
            outputCount=4)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=(
                satoriOuts + currencyOuts + [
                    x for x in [satoriChangeOut, currencyChangeOut]
                    if x is not None]))
        return self.broadcast(self._txToHex(tx))

    # def satoriOnlyPartial(self, amount: int, address: str, pullFeeFromAmount: bool = False) -> str:
    #    '''
    #    if people do not have a balance of rvn, they can still send satori.
    #    they have to pay the fee in satori, so it's a higher fee, maybe twice
    #    as much on average as a normal transaction. this is because the
    #    variability of the satori price. So this function produces a partial
    #    transaction that can be sent to the server and the rest of the network
    #    to be completed. he who completes the transaction will pay the rvn fee
    #    and collect the satori fee. we will probably broadcast as a json object.
    #
    #    not completed! this generalized version needs to use SIGHASH_SINGLE
    #    which makes the transaction more complex as all inputs need to
    #    correspond to their output. see simple version for more details.
    #
    #    after having completed the simple version, I realized that the easy
    #    solution to the problem of using SIGHASH_SINGLE and needing to issue
    #    change is to simply add an additional input to be assigned to the
    #    change output (a good use of dust, actaully). The only edge case we'd
    #    need to handle is if the user has has no additional utxo to be used as
    #    and input. In that case you'd have to put the process on hold, create a
    #    separate transaction to send the user back to self in order to create
    #    the additional input. That would be a pain, but it is doable, and it
    #    would be a semi-rare case, and it would be a good use of dust, and it
    #    would allow for the general mutli-party-partial-transaction solution.
    #    '''
    #    if (
    #        amount <= 0 or
    #        not TxUtils.isAmountDivisibilityValid(
    #            amount=amount,
    #            divisibility=self.divisibility) or
    #        not Validate.address(address, self.symbol)
    #    ):
    #        raise TransactionFailure('satoriTransaction bad params')
    #    if pullFeeFromAmount:
    #        amount -= self.mundoFee
    #    satoriTotalSats = TxUtils.asSats(amount + self.mundoFee)
    #    satoriSats = TxUtils.asSats(amount)
    #    (
    #        gatheredSatoriUnspents,
    #        gatheredSatoriSats) = self._gatherSatoriUnspents(satoriTotalSats)
    #    txins, txinScripts = self._compileInputs(
    #        gatheredSatoriUnspents=gatheredSatoriUnspents)
    #    # partial transactions need to use Sighash Single so we need to create
    #    # ouputs 1-1 to inputs:
    #    satoriOuts = []
    #    outsAmount = 0
    #    change = 0
    #    for x in gatheredSatoriUnspents:
    #        logging.debug(x.get('value'), color='yellow')
    #        if TxUtils.asAmount(x.get('value'), self.divisibility) + outsAmount < amount:
    #            outAmount = x.get('value')
    #        else:
    #            outAmount = amount - outsAmount
    #            change += x.get('value') - outAmount
    #        outsAmount += outAmount
    #        if outAmount > 0:
    #            satoriOuts.append(
    #                self._compileSatoriOutputs({address: outAmount})[0])
    #    if change - self.mundoFee > 0:
    #        change -= self.mundoFee
    #    if change > 0:
    #        satoriOuts.append(self._compileSatoriOutputs(
    #            {self.address: change})[0])
    #    # needs more work
    #    # satoriOuts = self._compileSatoriOutputs({address: amount})
    #    satoriChangeOut = self._compileSatoriChangeOutput(
    #        satoriSats=satoriSats,
    #        gatheredSatoriSats=gatheredSatoriSats - TxUtils.asSats(self.mundoFee))
    #    tx = self._createPartialOriginator(
    #        txins=txins,
    #        txinScripts=txinScripts,
    #        txouts=satoriOuts + [
    #            x for x in [satoriChangeOut]
    #            if x is not None])
    #    return tx.serialize()
    #
    # def satoriOnlyCompleter(self, serialTx: bytes, address: str) -> str:
    #    '''
    #    a companion function to satoriOnlyTransaction which completes the
    #    transaction add in it's own address for the satori fee and injecting the
    #    necessary rvn inputs to cover the fee. address is the address claim
    #    satori fee address.
    #    '''
    #    tx = self._deserialize(serialTx)
    #    # add rvn fee input
    #    (
    #        gatheredCurrencyUnspents,
    #        gatheredCurrencySats) = self._gatherCurrencyUnspents(
    #            inputCount=len(tx.vin) + 2,  # fee input could potentially be 2
    #            outputCount=len(tx.vout) + 2)  # claim output, change output
    #    txins, txinScripts = self._compileInputs(
    #        gatheredCurrencyUnspents=gatheredCurrencyUnspents)
    #    # add return rvn change output to self
    #    currencyChangeOut = self._compileCurrencyChangeOutput(
    #        gatheredCurrencySats=gatheredCurrencySats,
    #        inputCount=len(tx.vin) + len(txins),
    #        outputCount=len(tx.vout) + 2)
    #    # add satori fee output to self
    #    satoriClaimOut = self._compileSatoriOutputs({address: self.mundoFee})
    #    # sign rvn fee inputs and complete the transaction
    #    tx = self._createTransaction(
    #        tx=tx,
    #        txins=txins,
    #        txinScripts=txinScripts,
    #        txouts=satoriClaimOut + [
    #            x for x in [currencyChangeOut]
    #            if x is not None])
    #    return self.broadcast(self._txToHex(tx))
    #    # return tx  # testing

    def satoriOnlyBridgePartialSimple(
        self,
        amount: int,
        ethAddress: str,
        chain: str='base',
        pullFeeFromAmount: bool = False,
        feeSatsReserved: int = 0,
        completerAddress: str = None,
        changeAddress: str = None,
    ) -> tuple[str, int, str]:
        '''
        if people do not have a balance of rvn, they can still send satori.
        they have to pay the fee in satori. So this function produces a partial
        transaction that can be sent to the server and the rest of the network
        to be completed. he who completes the transaction will pay the rvn fee
        and collect the satori fee. we will probably broadcast as a json object.

        Because the Sighash_single is too complex this simple version was
        created which allows others (ie the server) to add inputs but not
        outputs. This makes it simple because we can add the output on our side
        and keep the rest of the code basically the same while using
        SIGHASH_ANYONECANPAY | SIGHASH_ALL

        dealing with the limitations of this signature we need to provide all
        outputs on our end, includeing the rvn fee output. so that needs to be
        an input to this function. Which means we have to call the server ask it
        to reserve an input for us and ask it how much that input is going to
        be, then include the Raven output change back to the server. Then when
        the server gets this transaction it will have to inspect it to verify
        that the last output is the raven fee change and that the second to last
        output is the Satori fee for itself.
        '''
        if completerAddress is None or changeAddress is None or feeSatsReserved == 0:
            raise TransactionFailure(
                'Satori Bridge Transaction bad params: need completer details')
        if amount <= 0:
            raise TransactionFailure(
                'Satori Bridge Transaction bad params: amount <= 0')
        if amount > self.maxBridgeAmount:
            raise TransactionFailure(
                'Satori Bridge Transaction bad params: amount > 100')
        if not Validate.ethAddress(ethAddress):
            raise TransactionFailure(
                'Satori Bridge Transaction bad params: eth address')
        if isinstance(amount, Decimal):
            amount = float(amount)
        if self.balance.amount < amount + self.bridgeFee + self.mundoFee:
            raise TransactionFailure(
                f'Satori Bridge Transaction bad params: balance too low to pay for bridgeFee {self.balance.amount} < {amount} + {self.bridgeFee} + {self.mundoFee}')
        if pullFeeFromAmount:
            amount -= self.mundoFee
            amount -= self.bridgeFee
        mundoSatsFee = TxUtils.asSats(self.mundoFee)
        bridgeSatsFee = TxUtils.asSats(self.bridgeFee)
        satoriSats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(amount),
            divisibility=self.divisibility)
        satoriTotalSats = satoriSats + mundoSatsFee + bridgeSatsFee
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriTotalSats)
        txins, txinScripts = self._compileInputs(
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs({self.burnAddress: satoriSats})
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats + mundoSatsFee + bridgeSatsFee,
            gatheredSatoriSats=gatheredSatoriSats)
        # fee out to server
        mundoFeeOut = self._compileSatoriOutputs(
            {completerAddress: mundoSatsFee})[0]
        if mundoFeeOut is None:
            raise TransactionFailure('unable to generate mundo fee')
        # fee out to server
        bridgeFeeOut = self._compileSatoriOutputs(
            {self.bridgeAddress: bridgeSatsFee})[0]
        if bridgeFeeOut is None:
            raise TransactionFailure('unable to generate bridge fee')
        # change out to server
        currencyChangeOut, currencyChange = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=feeSatsReserved,
            inputCount=len(gatheredSatoriUnspents),
            # len([mundoFeeOut, bridgeFeeOut, currencyChangeOut, memoOut]) +
            outputCount=len(satoriOuts) + 4 +
            (1 if satoriChangeOut is not None else 0),
            scriptPubKey=self._generateScriptPubKeyFromAddress(changeAddress),
            returnSats=True)
        if currencyChangeOut is None:
            raise TransactionFailure('unable to generate currency change')
        memoOut = self._compileMemoOutput(f'{chain}:{ethAddress}')
        tx = self._createPartialOriginatorSimple(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut]
                if x is not None] + [mundoFeeOut, bridgeFeeOut, currencyChangeOut, memoOut])
        reportedFeeSats = feeSatsReserved - currencyChange
        return tx.serialize(), reportedFeeSats, self._txToHex(tx)

    def satoriOnlyPartialSimple(
        self,
        amount: int,
        address: str,
        pullFeeFromAmount: bool = False,
        feeSatsReserved: int = 0,
        completerAddress: str = None,
        changeAddress: str = None,
    ) -> tuple[str, int]:
        '''
        if people do not have a balance of evr, they can still send satori.
        they have to pay the fee in satori. So this function produces a partial
        transaction that can be sent to the server and the rest of the network
        to be completed. he who completes the transaction will pay the evr fee
        and collect the satori fee. we will probably broadcast as a json object.

        Because the Sighash_single is too complex this simple version was
        created which allows others (ie the server) to add inputs but not
        outputs. This makes it simple because we can add the output on our side
        and keep the rest of the code basically the same while using
        SIGHASH_ANYONECANPAY | SIGHASH_ALL

        dealing with the limitations of this signature we need to provide all
        outputs on our end, including the evr fee change output. so that needs
        to be an input to this function. Which means we have to call the server
        ask it to reserve an input for us and ask it how much that input is
        going to be, then include the evr output change back to the server. Then
        when the server gets this transaction it will have to inspect it to
        verify that the last output is the evr fee change and that the second to
        last output is the Satori fee for itself.
        '''
        if completerAddress is None or changeAddress is None or feeSatsReserved == 0:
            raise TransactionFailure('need completer details')
        if (
            amount <= 0 or
            # not TxUtils.isAmountDivisibilityValid(
            #    amount=amount,
            #    divisibility=self.divisibility) or
            not Validate.address(address, self.symbol)
        ):
            raise TransactionFailure('satoriTransaction bad params')
        if pullFeeFromAmount:
            amount -= self.mundoFee
        mundoFeeSats = TxUtils.asSats(self.mundoFee)
        satoriSats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(amount),
            divisibility=self.divisibility)
        satoriTotalSats = satoriSats + mundoFeeSats
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriTotalSats)
        txins, txinScripts = self._compileInputs(
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs({address: satoriSats})
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats,
            gatheredSatoriSats=gatheredSatoriSats - mundoFeeSats)
        # fee out to server
        mundoFeeOut = self._compileSatoriOutputs(
            {completerAddress: mundoFeeSats})[0]
        if mundoFeeOut is None:
            raise TransactionFailure('unable to generate mundo fee')
        # change out to server
        currencyChangeOut, currencyChange = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=feeSatsReserved,
            inputCount=len(gatheredSatoriUnspents),
            # len([mundoFeeOut, currencyChange]) +
            outputCount=len(satoriOuts) + 2 +
            (1 if satoriChangeOut is not None else 0),
            scriptPubKey=self._generateScriptPubKeyFromAddress(changeAddress),
            returnSats=True)
        if currencyChangeOut is None:
            raise TransactionFailure('unable to generate currency change')
        tx = self._createPartialOriginatorSimple(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut]
                if x is not None] + [mundoFeeOut, currencyChangeOut])
        reportedFeeSats = feeSatsReserved - currencyChange
        return tx.serialize(), reportedFeeSats, self._txToHex(tx)

    def satoriOnlyCompleterSimple(
        self,
        serialTx: bytes,
        feeSatsReserved: int,
        reportedFeeSats: int,
        changeAddress: Union[str, None] = None,
        completerAddress: Union[str, None] = None,
        bridgeTransaction: bool = False,
    ) -> str:
        '''
        a companion function to satoriOnlyPartialSimple which completes the
        transaction by injecting the necessary rvn inputs to cover the fee.
        address is the address claim satori fee address.
        '''
        def _verifyFee():
            '''
            notice, currency change is guaranteed:
                reportedFeeSats < TxUtils.asSats(1)
                feeSatsReserved is greater than TxUtils.asSats(1)
            '''

            if bridgeTransaction:
                return (
                    reportedFeeSats < TxUtils.asSats(1) and
                    reportedFeeSats < feeSatsReserved and
                    tx.vout[-2].nValue == feeSatsReserved - reportedFeeSats)
            return (
                reportedFeeSats < TxUtils.asSats(1) and
                reportedFeeSats < feeSatsReserved and
                tx.vout[-1].nValue == feeSatsReserved - reportedFeeSats)

        def _verifyClaim():
            if bridgeTransaction:
                # [mundoFeeOut, bridgeFeeOut, currencyChangeOut, memoOut]
                bridgePaid = False
                mundoPaid = False
                for x in tx.vout:
                    if self._checkSatoriValue(x, self.bridgeFee):
                        bridgePaid = True
                    if self._checkSatoriValue(x, self.mundoFee):
                        mundoPaid = True
                return bridgePaid and mundoPaid
            # [mundoFeeOut, currencyChangeOut]
            mundoPaid = False
            for x in tx.vout:
                if self._checkSatoriValue(x, self.mundoFee):
                    mundoPaid = True
            return mundoPaid

        def _verifyClaimAddress():
            ''' verify the claim output goes to completerAddress '''
            if bridgeTransaction:
                for i, x in enumerate(tx.vout[-4].scriptPubKey):
                    if i == 2 and isinstance(x, bytes):
                        return completerAddress == self.hash160ToAddress(x)
                return False
            for i, x in enumerate(tx.vout[-2].scriptPubKey):
                if i == 2 and isinstance(x, bytes):
                    return completerAddress == self.hash160ToAddress(x)
            return False

        def _verifyChangeAddress():
            ''' verify the change output goes to us at changeAddress '''
            if bridgeTransaction:
                for i, x in enumerate(tx.vout[-2].scriptPubKey):
                    if i == 2 and isinstance(x, bytes):
                        return changeAddress == self.hash160ToAddress(x)
                return False
            for i, x in enumerate(tx.vout[-1].scriptPubKey):
                if i == 2 and isinstance(x, bytes):
                    return changeAddress == self.hash160ToAddress(x)
            return False

        completerAddress = completerAddress or self.address
        logging.debug('completer', completerAddress)
        changeAddress = changeAddress or self.address
        logging.debug('change', changeAddress)
        tx = self._deserialize(serialTx)
        if not _verifyFee():
            raise TransactionFailure(
                f'fee mismatch, {reportedFeeSats}, {feeSatsReserved}')
        if not _verifyClaim():
            if bridgeTransaction:
                raise TransactionFailure(
                    f'bridge claim mismatch, {tx.vout[-4]}, {tx.vout[-3]}')
            raise TransactionFailure(f'claim mismatch, {tx.vout[-2]}')
        if not _verifyClaimAddress():
            raise TransactionFailure('claim mismatch, _verifyClaimAddress')
        if not _verifyChangeAddress():
            raise TransactionFailure('claim mismatch, _verifyChangeAddress')
        # add rvn fee input
        gatheredCurrencyUnspent = self._gatherReservedCurrencyUnspent(
            exactSats=feeSatsReserved)
        logging.debug('gathered', gatheredCurrencyUnspent)
        if gatheredCurrencyUnspent is None:
            raise TransactionFailure(f'unable to find sats {feeSatsReserved}')
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=[gatheredCurrencyUnspent])
        tx = self._createPartialCompleterSimple(
            tx=tx,
            txins=txins,
            txinScripts=txinScripts)
        return self.broadcast(self._txToHex(tx))

    def sendAllTransaction(self, address: str) -> str:
        '''
        sweeps all Satori and currency to the address. so it has to take the fee
        out of whatever is in the wallet rather than tacking it on at the end.
        '''
        if not Validate.address(address, self.symbol):
            raise TransactionFailure('sendAllTransaction')
        # logging.debug('currency', self.currency,
        #              'self.reserve', self.reserve, color='yellow')
        if self.currency < self.reserve:
            raise TransactionFailure(
                'sendAllTransaction: not enough currency for fee')
        # grab everything
        gatheredSatoriUnspents = [
            x for x in self.unspentAssets if x.get('name', x.get('asset')) == 'SATORI']
        gatheredCurrencyUnspents = self.unspentCurrency
        currencySats = sum([x.get('value') for x in gatheredCurrencyUnspents])
        # compile inputs
        if len(gatheredSatoriUnspents) > 0:
            txins, txinScripts = self._compileInputs(
                gatheredCurrencyUnspents=gatheredCurrencyUnspents,
                gatheredSatoriUnspents=gatheredSatoriUnspents)
        else:
            txins, txinScripts = self._compileInputs(
                gatheredCurrencyUnspents=gatheredCurrencyUnspents)
        # determin how much currency to send: take out fee
        currencySatsLessFee = currencySats - TxUtils.estimatedFee(
            inputCount=(
                len(gatheredSatoriUnspents) +
                len(gatheredCurrencyUnspents)),
            outputCount=2)
        if currencySatsLessFee < 0:
            raise TransactionFailure('tx: not enough currency to send')
        # since it's a send all, there's no change outputs
        if len(gatheredSatoriUnspents) > 0:
            txouts = (
                self._compileSatoriOutputs({
                    address: TxUtils.roundSatsDownToDivisibility(
                        sats=TxUtils.asSats(self.balance.amount),
                        divisibility=self.divisibility)}) +
                (
                    self._compileCurrencyOutputs(currencySatsLessFee, address)
                    if currencySatsLessFee > 0 else []))
        else:
            txouts = self._compileCurrencyOutputs(currencySatsLessFee, address)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=txouts)
        return self.broadcast(self._txToHex(tx))

    # not finished
    # I thought this would be worth it, but
    # SIGHASH_ANYONECANPAY | SIGHASH_SIGNLE is still too complex. particularly
    # generating outputs
    # def sendAllPartial(self, address: str) -> str:
    #    '''
    #    sweeps all Satori and currency to the address. so it has to take the fee
    #    out of whatever is in the wallet rather than tacking it on at the end.
    #
    #    this one doesn't actaully need change back, so we could use the most
    #    general solution of SIGHASH_ANYONECANPAY | SIGHASH_SIGNLE if the server
    #    knows how to handle it.
    #    '''
    #    def _generateOutputs():
    #        '''
    #        we must guarantee we have the same number of inputs to outputs.
    #        we must guarantee sum of ouputs = sum of inputs - mundoFee.
    #        that is all.
    #
    #        we could run into a situation where we need to take the fee out of
    #        multiple inputs. We could also run into the situation where we need
    #        to pair a currency output with a satori input.
    #        '''
    #        reservedFee = 0
    #        outs = []
    #        mundoFeeSats = TxUtils.asSats(self.mundoFee)
    #        for x in gatheredCurrencyUnspents:
    #            if x.get('value') > reservedFee:
    #        for x in gatheredSatoriUnspents:
    #            if reservedFee < mundoFeeSats:
    #                if x.get('value') > mundoFeeSats - reservedFee:
    #                    reservedFee += (mundoFeeSats - reservedFee)
    #                    # compile output with
    #                    mundoFeeSats x.get('value') -
    #                reservedFee = x.get('value') -
    #        return ( # not finished, combine with above
    #            self._compileSatoriOutputs({
    #                address: unspent.get('x') - self.mundoFee # on first item
    #                for unspent in gatheredSatoriUnspents
    #                }) +
    #            self._compileCurrencyOutputs(currencySats, address))
    #
    #    if not Validate.address(address, self.symbol):
    #        raise TransactionFailure('sendAllTransaction')
    #    logging.debug('currency', self.currency,
    #                'self.reserve', self.reserve, color='yellow')
    #    if self.balance.amount <= self.mundoFee*2:
    #        # what if they have 2 satoris in 2 different utxos?
    #        # one goes to the destination, and what about the other?
    #        # server supplies the fee claim so... we can't create this
    #        # transaction unless we supply the fee claim, and the server detects
    #        # it.
    #        raise TransactionFailure(
    #            'sendAllTransaction: not enough Satori for fee')
    #    # grab everything
    #    gatheredSatoriUnspents = [
    #        x for x in self.unspentAssets if x.get('name', x.get('asset')) == 'SATORI']
    #    gatheredCurrencyUnspents = self.unspentCurrency
    #    currencySats = sum([x.get('value') for x in gatheredCurrencyUnspents])
    #    # compile inputs
    #    txins, txinScripts = self._compileInputs(
    #        gatheredCurrencyUnspents=gatheredCurrencyUnspents,
    #        gatheredSatoriUnspents=gatheredSatoriUnspents)
    #    # since it's a send all, there's no change outputs
    #    tx = self._createPartialOriginator(
    #        txins=txins,
    #        txinScripts=txinScripts,
    #        txouts=_generateOutputs())
    #    return tx.serialize()

    def sendAllPartialSimple(
        self,
        address: str,
        feeSatsReserved: int = 0,
        completerAddress: str = None,
        changeAddress: str = None,
        **kwargs
    ) -> tuple[str, int]:
        '''
        sweeps all Satori and currency to the address. so it has to take the fee
        out of whatever is in the wallet rather than tacking it on at the end.

        this one doesn't actaully need change back, so we could use the most
        general solution of SIGHASH_ANYONECANPAY | SIGHASH_SIGNLE if the server
        knows how to handle it.
        '''
        if completerAddress is None or changeAddress is None or feeSatsReserved == 0:
            raise TransactionFailure('need completer details')
        if not Validate.address(address, self.symbol):
            raise TransactionFailure('sendAllTransaction')
        # logging.debug('currency', self.currency,
        #              'self.reserve', self.reserve, color='yellow')
        if self.balance.amount < self.mundoFee:
            raise TransactionFailure(
                'sendAllTransaction: not enough Satori for fee')
        # grab everything
        gatheredSatoriUnspents = [
            x for x in self.unspentAssets if x.get('name', x.get('asset')) == 'SATORI']
        gatheredCurrencyUnspents = self.unspentCurrency
        currencySats = sum([x.get('value') for x in gatheredCurrencyUnspents])
        # compile inputs
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        sweepOuts = (
            (
                self._compileCurrencyOutputs(currencySats, address)
                if currencySats > 0 else []) +
            self._compileSatoriOutputs(
                {address:
                    TxUtils.roundSatsDownToDivisibility(
                        sats=TxUtils.asSats(
                            self.balance.amount) - TxUtils.asSats(self.mundoFee),
                        divisibility=self.divisibility)}))
        mundoFeeOut = self._compileSatoriOutputs(
            {completerAddress: TxUtils.asSats(self.mundoFee)})[0]
        # change out to server
        currencyChangeOut, currencyChange = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=feeSatsReserved,
            inputCount=len(gatheredSatoriUnspents) +
            len(gatheredCurrencyUnspents),
            outputCount=len(sweepOuts) + 2,
            scriptPubKey=self._generateScriptPubKeyFromAddress(changeAddress),
            returnSats=True)
        # since it's a send all, there's no change outputs
        tx = self._createPartialOriginatorSimple(
            txins=txins,
            txinScripts=txinScripts,
            txouts=sweepOuts + [mundoFeeOut, currencyChangeOut])
        reportedFeeSats = feeSatsReserved - currencyChange
        return tx.serialize(), reportedFeeSats, self._txToHex(tx)

    def typicalNeuronTransaction(
        self,
        amount: float,
        address: str,
        sweep: bool = False,
        requestSimplePartialFn: callable = None, # they provide send all if sweep
        broadcastBridgeSimplePartialFn: callable = None,
    ) -> TransactionResult:

        def sendDirect():
            if sweep:
                txid = self.sendAllTransaction(address)
            else:
                txid = self.satoriTransaction(amount=amount, address=address)
            if isinstance(txid, str) and len(txid) == 64:
                return TransactionResult(
                    result=None,
                    success=True,
                    msg=txid)
            return TransactionResult(
                result=None,
                success=False,
                msg=f'Send Failed: {txid}')

        def sendIndirect():
            responseJson = requestSimplePartialFn(network='main')
            changeAddress = responseJson.get('changeAddress')
            feeSatsReserved = responseJson.get('feeSatsReserved')
            completerAddress = responseJson.get('completerAddress')
            if feeSatsReserved == 0 or completerAddress is None:
                return TransactionResult(
                    result='try again',
                    success=True,
                    tx=None,
                    msg='creating partial, need feeSatsReserved.')
            sendPartialFunction = self.satoriOnlyPartialSimple
            if sweep:
                sendPartialFunction = self.sendAllPartialSimple
            tx, reportedFeeSats, txhex = sendPartialFunction(
                amount=float(amount),
                address=address,
                changeAddress=changeAddress,
                feeSatsReserved=feeSatsReserved,
                completerAddress=completerAddress,
                pullFeeFromAmount=float(amount) + self.mundoFee > self.balance.amount)
            if ( # checking any on of these should suffice in theory...
                tx is not None and
                reportedFeeSats is not None and
                reportedFeeSats > 0
            ):
                r = broadcastBridgeSimplePartialFn(
                    tx=tx,
                    reportedFeeSats=reportedFeeSats,
                    feeSatsReserved=feeSatsReserved,
                    walletId=responseJson.get('partialId'),
                    network='evrmore')
                if r.text.startswith('{"code":1,"message":'):
                    return TransactionResult(
                        result=None,
                        success=False,
                        msg=f'Send Failed: {r.json().get("message")}')
                elif r.text != '':
                    return TransactionResult(
                        result=TxUtils.txhexToTxid(txhex),
                        success=True,
                        msg=r.text)
                else:
                    return TransactionResult(
                        result=None,
                        success=False,
                        msg='Send Failed: and try again in a few minutes.')
            return TransactionResult(
                result=None,
                success=False,
                msg='unable to generate transaction')

        ready, partialReady, msg = self.validateForTypicalNeuronTransaction(
            amount=amount,
            address=address)
        if ready:
            return sendDirect()
        elif partialReady:
            return sendIndirect()
        return TransactionResult(
            result=None,
            success=False,
            msg=f'Send Failed: {msg}')

    def typicalNeuronBridgeTransaction(
        self,
        amount: float,
        ethAddress: str,
        chain: str = 'base',
        requestSimplePartialFn: callable = None,
        ofacReportedFn: callable = None,
        broadcastBridgeSimplePartialFn: callable = None,
    ) -> TransactionResult:

        def sendDirect():
            txhex = self.satoriDistribution(
                amountByAddress={
                    self.bridgeAddress: self.bridgeFee,
                    self.burnAddress: amount},
                memo=f'{chain}:{ethAddress}',
                broadcast=False)
            if not ofacReportedFn(txid=TxUtils.txhexToTxid(txhex)):
                return TransactionResult(
                    result=None,
                    success=False,
                    msg='Send Failed: OFAC on Report')
            txid = self.broadcast(txhex)
            if len(txid) == 64:
                return TransactionResult(
                    result=None,
                    success=True,
                    msg=txid)
            return TransactionResult(
                result=None,
                success=False,
                msg=f'Send Failed: {txid}')

        def sendIndirect():
            responseJson = requestSimplePartialFn(network='main')
            changeAddress = responseJson.get('changeAddress')
            feeSatsReserved = responseJson.get('feeSatsReserved')
            completerAddress = responseJson.get('completerAddress')
            if feeSatsReserved == 0 or completerAddress is None:
                return TransactionResult(
                    result='try again',
                    success=True,
                    tx=None,
                    msg='creating partial, need feeSatsReserved.')
            tx, reportedFeeSats, txhex = self.satoriOnlyBridgePartialSimple(
                amount=amount,
                ethAddress=ethAddress,
                changeAddress=changeAddress,
                feeSatsReserved=feeSatsReserved,
                completerAddress=completerAddress)
            if ( # checking any on of these should suffice in theory...
                tx is not None and
                reportedFeeSats is not None and
                reportedFeeSats > 0
            ):
                txid = TxUtils.txhexToTxid(txhex)
                if not ofacReportedFn(txid):
                    return TransactionResult(
                        result=None,
                        success=False,
                        msg='Send Failed: OFAC on Report')
                r = broadcastBridgeSimplePartialFn(
                    tx=tx,
                    reportedFeeSats=reportedFeeSats,
                    feeSatsReserved=feeSatsReserved,
                    walletId=responseJson.get('partialId'),
                    network='evrmore')
                if r.text.startswith('{"code":1,"message":'):
                    return TransactionResult(
                        result=None,
                        success=False,
                        msg=f'Send Failed: {r.json().get("message")}')
                elif r.text != '':
                    return TransactionResult(
                        result=txid,
                        success=True,
                        msg=r.text)
                else:
                    return TransactionResult(
                        result=None,
                        success=False,
                        msg='Send Failed: and try again in a few minutes.')
            return TransactionResult(
                result=None,
                success=False,
                msg='unable to generate transaction')

        ready, partialReady, msg = self.validateForTypicalNeuronBridgeTransaction(
            amount=amount,
            ethAddress=ethAddress,
            chain=chain)
        if ready:
            return sendDirect()
        elif partialReady:
            return sendIndirect()
        return TransactionResult(
            result=None,
            success=False,
            msg=f'Send Failed: {msg}')



    def validateForTypicalNeuronTransaction(
        self,
        amount: float,
        address: str,
    ) -> TransactionResult:
        if isinstance(amount, Decimal):
            amount = float(amount)
        if amount <= 0:
            return False, False, f'Satori Transaction bad params: unable to send amount: {amount}'
        if amount > self.balance.amount:
            return False, False, f'Satori Transaction bad params: {amount} > {self.balance.amount} '
        if not Validate.address(address, self.symbol):
            return False, False, f'Satori Transaction bad params: address: {address}'
        if self.currency < self.reserve:
            if amount > self.balance.amount + self.mundoFee:
                return False, False, f'Satori Transaction bad params: not enough for transaction fees: {amount} > {self.balance.amount} + {self.mundoFee}'
            return False, True, 'currency < reserve'
        return True, False, ''

    def validateForTypicalNeuronBridgeTransaction(
        self,
        amount: float,
        ethAddress: str,
        chain: str = 'base',
    ) -> tuple[bool, bool, str]: # success, partial-ready, msg
        if isinstance(amount, Decimal):
            amount = float(amount)
        if chain != 'base':
            return False, False, 'can only bridge to base'
        if amount <= 0:
            return False, False, f'Satori Bridge Transaction bad params: unable to send amount: {amount}'
        if amount > self.maxBridgeAmount:
            return False, False, 'Satori Bridge Transaction bad params: amount > 100'
        if not Validate.ethAddress(ethAddress):
            return False, False, f'Satori Bridge Transaction bad params: eth address: {ethAddress}'
        if self.balance.amount < amount + self.bridgeFee:
            return False, False, f'Satori Bridge Transaction bad params: balance too low to pay for bridgeFee {self.balance.amount} < {amount} + {self.bridgeFee}'
        if self.currency < self.reserve:
            return False, True, 'currency < reserve'
        return True, False, ''
