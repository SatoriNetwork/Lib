from typing import Union
import os
import json
from base64 import b64encode, b64decode
from random import randrange
import mnemonic
from satoriwallet.lib import connection
from satoriwallet import TxUtils, Validate
from satorilib import logging
from satorilib.api import system
from satorilib.api.disk.wallet import WalletApi


class TransactionResult():
    def __init__(self, result: str = '', success: bool = False, tx: bytes = None, msg: str = '', reportedFeeSats: int = None):
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


class Wallet():

    def __init__(
        self,
        walletPath: str,
        temporary: bool = False,
        reserve: float = .01,
        isTestnet: bool = False,
        password: str = None,
        use: 'Wallet' = None,
    ):
        self.satoriFee = .01  # ~50 cents
        self.isTestnet = isTestnet
        self.password = password
        self._entropy = None
        self._privateKeyObj = None
        self.privateKey = None
        self.words = None
        self._addressObj = None if use is None else use._addressObj
        self.publicKey = None if use is None else use.publicKey
        self.address = None if use is None else use.address
        self.scripthash = None if use is None else use.scripthash
        self.stats = {} if use is None else use.stats
        self.alias = None if use is None else use.alias
        self.banner = None if use is None else use.banner
        self.currency = None if use is None else use.currency
        self.balance = None if use is None else use.balance
        self.currencyAmount = 0 if use is None else use.currencyAmount
        self.balanceAmount = 0 if use is None else use.balanceAmount
        self.divisibility = 0 if use is None else use.divisibility
        self.transactionHistory: list[dict] = None if use is None else use.transactionHistory
        self.transactions = [] if use is None else use.transactions  # TransactionStruct
        self.assetTransactions = [] if use is None else use.assetTransactions
        self.electrumx = None if use is None else use.electrumx
        self.currencyOnChain = None if use is None else use.currencyOnChain
        self.balanceOnChain = None if use is None else use.balanceOnChain
        self.unspentCurrency = None if use is None else use.unspentCurrency
        self.unspentAssets = None if use is None else use.unspentAssets
        self.walletPath = walletPath
        self.temporary = temporary
        # maintain minimum amount of currency at all times to cover fees - server only
        self.reserveAmount = reserve
        self.reserve = TxUtils.asSats(reserve)
        self.initRaw()

    def __call__(self):
        x = 0
        while x < 5:
            try:
                self.init()
                break
            except TimeoutError:
                logging.error('init wallet connection attempts', x)
                x += 1
        return self

    def __repr__(self):
        return (
            f'{self.chain}Wallet('
            f'\n\tpublicKey: {self.publicKey},'
            f'\n\tprivateKey: {self.privateKey},'
            f'\n\twords: {self.words},'
            f'\n\taddress: {self.address},'
            f'\n\tscripthash: {self.scripthash},'
            f'\n\tbalance: {self.balance},'
            f'\n\tstats: {self.stats},'
            f'\n\tbanner: {self.banner})')

    @property
    def symbol(self) -> str:
        return 'wallet'

    @property
    def chain(self) -> str:
        return ''

    @property
    def satoriOriginalTxHash(self) -> str:
        return ''

    @property
    def publicKeyBytes(self) -> bytes:
        return bytes.fromhex(self.publicKey)

    @property
    def isEncrypted(self) -> bool:
        return ' ' not in self.words

    @property
    def isDecrypted(self) -> bool:
        return not self.isEncrypted

    def close(self) -> None:
        # if self.password is not None:
        self.password = None
        self._entropy = None
        self._entropyStr = ''
        self._privateKeyObj = None
        self.privateKey = ''
        self.words = ''

    def open(self, password: str = None) -> None:
        # if self.password is not None:
        self.password = password
        self.initRaw()
        self.regenerate()

    def setAlias(self, alias: Union[str, None] = None) -> None:
        self.alias = alias

    def hash160ToAddress(self, pubKeyHash: Union[str, bytes]) -> str:
        return TxUtils.hash160ToAddress(pubKeyHash, self.networkByte)

    def showStats(self):
        ''' returns a string of stats properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        divisions = self.stats.get('divisions', 8)
        circulatingCoins = TxUtils.asAmount(int(self.stats.get(
            'sats_in_circulation', 100000000000000)))
        # circulatingSats = self.stats.get(
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
    Reissuable: {self.stats.get('reissuable', False)}
    Issuing Transactions: {self.stats.get('source', {}).get('tx_hash', self.satoriOriginalTxHash)}
    '''

    def authPayload(self, asDict: bool = False, challenge: str = None) -> Union[str, dict]:
        payload = connection.authPayload(self, challenge)
        if asDict:
            return payload
        return json.dumps(payload)

    def registerPayload(self, asDict: bool = False, challenge: str = None) -> Union[str, dict]:
        payload = {
            **connection.authPayload(self, challenge),
            **system.devicePayload(asDict=True)}
        if asDict:
            return payload
        return json.dumps(payload)

    def init(self):
        ''' try to load, else generate and save '''
        if self.load():
            self.regenerate()
        else:
            self.generate()
            self.save()
        if not self.temporary:
            self.connect()
            self.get()

    def initRaw(self):
        ''' try to load, else generate and save '''
        if isinstance(self.password, str):
            if not self.load():
                if not self.loadRaw():
                    self.generate()
                    self.save()
        else:
            if not self.loadRaw():
                self.generate()
                self.save()
        if self.address is None:
            self.regenerate()

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

    def getRaw(self):
        return WalletApi.load(walletPath=self.walletPath)

    def loadRaw(self):
        self.yaml = self.getRaw()
        if self.yaml == False:
            return False
        # leave this in for a few months then you can remove it.
        self.cleanYaml()
        self._entropy = self.yaml.get('entropy')
        if isinstance(self._entropy, bytes):
            self._entropyStr = b64encode(self._entropy).decode('utf-8')
        if isinstance(self._entropy, str):
            self._entropyStr = self._entropy
            self._entropy = b64decode(self._entropy)
        self.words = self.yaml.get('words')
        self.publicKey = self.yaml.get('publicKey')
        self.privateKey = self.yaml.get('privateKey')
        thisWallet = self.yaml.get(self.symbol, {})
        self.address = thisWallet.get('address')
        self.scripthash = self.yaml.get('scripthash')
        if self._entropy is None:
            return False
        logging.info('load', self.publicKey, self.walletPath)
        return True

    def cleanYaml(self):
        ''' here we clean the yaml file such that the entropy is a string '''
        self.yaml = self.getRaw()
        if isinstance(self.yaml.get('entropy'), bytes):
            self.yaml['entropy'] = b64encode(
                self.yaml.get('entropy')).decode('utf-8')
            self._entropyStr = self.yaml.get('entropy')
            WalletApi.save(
                wallet={
                    **(
                        self.yaml
                        if hasattr(self, 'yaml') and isinstance(self.yaml, dict)
                        else {}),
                    **(self.encryptWallet(
                        content={
                            'entropy': self._entropyStr,
                        }) if self.password is not None else {})
                },
                walletPath=self.walletPath)

    def load(self):
        self.yaml = self.getRaw()
        if self.yaml == False:
            return False
        self.yaml = self.decryptWallet(self.yaml)

        self._entropy = self.yaml.get('entropy')
        if isinstance(self._entropy, bytes):
            self._entropyStr = b64encode(self._entropy).decode('utf-8')
        if isinstance(self._entropy, str):
            self._entropyStr = self._entropy
            self._entropy = b64decode(self._entropy)

        # # these are regenerated from entropy in every case
        self.words = self.yaml.get('words')
        self.publicKey = self.yaml.get('publicKey')
        self.privateKey = self.yaml.get('privateKey')
        self.address = self.yaml.get(self.symbol, {}).get(
            'address')
        self.scripthash = self.yaml.get('scripthash')
        if self._entropy is None:
            return False
        logging.info('load', self.publicKey, self.walletPath)
        return True

    def save(self):
        WalletApi.save(
            wallet={
                **(
                    self.encryptWallet(self.yaml)
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
            walletPath=self.walletPath)

    def regenerate(self):
        saveIt = False
        if not hasattr(self, 'privateKey') or self.privateKey is None:
            saveIt = True
        # entire file is encrypted (only part is supposed to be encrypted)
        elif self.isDecrypted and (self.getRaw() or {}).get('publicKey') != self.publicKey:
            saveIt = True
        self.generate()
        if saveIt:
            self.save()

    def generate(self):
        self._entropy = self._entropy or self._generateEntropy()
        self._entropyStr = b64encode(self._entropy).decode('utf-8')
        self._privateKeyObj = self._generatePrivateKey()
        self._addressObj = self._generateAddress()
        self.words = self.words or self._generateWords()
        self.privateKey = self.privateKey or str(self._privateKeyObj)
        self.publicKey = self.publicKey or self._privateKeyObj.pub.hex()
        self.address = self.address or str(self._addressObj)
        self.scripthash = self.scripthash or self._generateScripthash()

    def _generateScripthash(self, forAddress: str = None):
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
        def DATA_TO_PUSH(address): return hexlify(b58decode_check(address)[1:])

        def sig_script_raw(address): return b''.join(
            (OP_DUP, OP_HASH160, BYTES_TO_PUSH, DATA_TO_PUSH(address), OP_EQUALVERIFY, OP_CHECKSIG))
        def scripthash(address): return sha256(codecs.decode(
            sig_script_raw(address), 'hex_codec')).digest()[::-1].hex()
        return scripthash(forAddress or self.address)

    def _generateEntropy(self):
        # return m.to_entropy(m.generate())
        # return b64encode(x.to_seed(x.generate(strength=128))).decode('utf-8')
        return os.urandom(32)

    def _generateWords(self):
        return mnemonic.Mnemonic('english').to_mnemonic(self._entropy)

    def _generatePrivateKey(self):
        ''' returns a private key object '''

    def _generateAddress(self):
        ''' returns an address object '''

    def _generateScriptPubKeyFromAddress(self, address: str):
        ''' returns CScript object from address '''

    def getUnspentSignatures(self) -> bool:
        '''
        we don't need to get the scriptPubKey every time we open the wallet,
        and it requires lots of calls for individual transactions.
        we just need them available when we're creating transactions.

        '''
        if (
            len([
                u for u in self.unspentCurrency + self.unspentAssets
                if 'scriptPubKey' not in u]) == 0
        ):
            # already have them all
            return True

        try:
            # make sure we're connected
            if not hasattr(self, 'electrumx'):
                self.connect()
                self.get()
            elif not self.electrumx.connected():
                self.connect()

            # get transactions, save their scriptPubKey hex to the unspents
            for uc in self.unspentCurrency:
                if len([tx for tx in self.transactions if tx['txid'] == uc['tx_hash']]) == 0:
                    self.transactions.append(
                        self.electrumx.getTransaction(uc['tx_hash']))
                tx = [tx for tx in self.transactions if tx['txid'] == uc['tx_hash']]
                if len(tx) > 0:
                    vout = [vout for vout in tx[0].get(
                        'vout', []) if vout.get('n') == uc['tx_pos']]
                    if len(vout) > 0:
                        scriptPubKey = vout[0].get(
                            'scriptPubKey', {}).get('hex', None)
                        if scriptPubKey is not None:
                            uc['scriptPubKey'] = scriptPubKey
            for ua in self.unspentAssets:
                if len([tx for tx in self.transactions if tx['txid'] == ua['tx_hash']]) == 0:
                    self.transactions.append(
                        self.electrumx.getTransaction(ua['tx_hash']))
                tx = [tx for tx in self.transactions if tx['txid'] == ua['tx_hash']]
                if len(tx) > 0:
                    vout = [vout for vout in tx[0].get(
                        'vout', []) if vout.get('n') == ua['tx_pos']]
                    if len(vout) > 0:
                        scriptPubKey = vout[0].get(
                            'scriptPubKey', {}).get('hex', None)
                        if scriptPubKey is not None:
                            ua['scriptPubKey'] = scriptPubKey
        except Exception as e:
            logging.warning(
                'unable to acquire signatures of unspent transactions, maybe unable to send', e)
            return False
        return True

    def get(self, allWalletInfo=False):
        ''' gets data from the blockchain, saves to attributes '''

        def openSafely(supposedDict: dict, key: str, default: Union[str, int, dict, list] = None):
            try:
                return supposedDict.get(key, default)
            except Exception as e:
                logging.error('openSafely err:', supposedDict, e)
                return None

        def getBalanceTheHardWay() -> int:
            '''
            using unspents get all transactions
            cycle through the vouts to find the asset you want and that was sent to your address:
            'vout': [{
                'n': 0,
                'scriptPubKey': {
                    'type': 'transfer_asset',
                    'asset': {
                        'name': 'KINKAJOU/GROOMER1',
                        'amount': 1.0},
                    'addresses': ['Eevy1hooby2SmCMZHcGbFVArPMYUY8EThs']}}]
            OR you could get a list of all addresses that hold the asset and find your address in the list:
            e.send('blockchain.asset.list_addresses_by_asset', 'SATORI')
            {
                'Eagq7rNFUEnR7kciQafV38kzpocef74J44': 1.0,
                'EbdsuYpb3URjafVLaSCzfnjGAc9gzH8gwg': 136.0,
                'EdLRYNrPVJLqXz9Pxp6fwD4gNdvk4dZNnP': 1.0
            }
            '''
            return self.electrumx.getAssetHolders(self.address).get(self.address, 0)

        # x = Evrmore(self.address, self.scripthash, config.electrumxServers())
        # todo: this list of servers should be parameterized from configuration

        # todo:
        # on connect ask for peers, add each to our list of electrumxServers
        # if unable to connect, remove that server from our list
        if not hasattr(self, 'electrumx') or not self.electrumx.connected():
            self.connect()
        self.electrumx.get(allWalletInfo)
        self.currencyOnChain = self.electrumx.currency
        self.balanceOnChain = self.electrumx.balance
        self.stats = self.electrumx.stats
        # self.divisibility = self.stats.get('divisions', 8)
        self.divisibility = openSafely(self.stats, 'divisions', 8)
        self.divisibility = self.divisibility if self.divisibility is not None else 8
        # self.assetTransactions = self.electrumx.assetTransactions
        self.banner = self.electrumx.banner
        self.transactionHistory = self.electrumx.transactionHistory
        self.transactions = self.electrumx.transactions or []
        self.unspentCurrency = self.electrumx.unspentCurrency
        self.unspentAssets = self.electrumx.unspentAssets
        # get mempool balance
        # for logging purposes
        for x in self.unspentCurrency:
            openSafely(x, 'value')
        self.currency = sum([
            x.get('value')for x in self.unspentCurrency
            if x.get('asset') == None])
        # for logging purposes
        # for x in self.unspentAssets:
        #    openSafely(x, 'value')
        #    openSafely(x, 'name')
        # don't need this anymore because we're getting it from the server correctly
        # if (
        #    isinstance(self.unspentAssets, dict)
        #    and self.unspentAssets.get('message') == 'unknown method "blockchain.scripthash.listassets"'
        # ):
        #    self.balance = getBalanceTheHardWay()
        #    unspents, assetUnspents = self.getUnspentsFromHistory()
        #    if sum([x.get('value', 0) for x in unspents]) == sum([x.get('value', 0) for x in self.unspentCurrency]):
        #        self.unspentAssets = assetUnspents
        # else:
        self.balance = sum([
            x.get('value') for x in self.unspentAssets
            if x.get('name', x.get('asset')) == 'SATORI' and x.get('value') > 0])
        self.currencyAmount = TxUtils.asAmount(self.currency or 0, 8)
        self.balanceAmount = TxUtils.asAmount(
            self.balance or 0, self.divisibility)
        # self.currencyVouts = self.electrumx.evrVouts
        # self.assetVouts = self.electrumx.assetVouts

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

    def sign(self, message: str):
        ''' signs a message with the private key '''

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None) -> bool:
        ''' verifies a message with the public key '''

    def _checkSatoriValue(self, output: 'CMutableTxOut') -> bool:
        '''
        returns true if the output is a satori output of self.satoriFee
        '''

    def shouldAutosecure(self):
        return (
            self.password is None and
            self.balanceAmount > self.satoriFee and
            self.autosecured())

    def getAutosecureEntry(self):
        for k, v in WalletApi.config.get('autosecure').items():
            if k == self.address or v.get('address') == self.address:
                return v

    def autosecured(self) -> bool:
        ''' verifies a message with the public key '''
        config = WalletApi.config
        entry = self.getAutosecureEntry()
        if entry is None:
            return False
        # {'message': self.getRaw().get('publicKey'),
        # 'pubkey': self.publicKey,
        # 'address': self.address,
        # 'signature': wallet.sign(challenge).decode()}
        vault = config.get(config.walletPath('vault.yaml'))
        return (
            entry.get('message').startswith(entry.get('address')) and
            entry.get('message').endswith(entry.get('pubkey')) and
            entry.get('address') == vault.get(self.symbol).get('address') and
            entry.get('pubkey') == vault.get('publicKey') and
            self.verify(
                address=entry.get('address'),
                message=entry.get('message'),
                sig=entry.get('signature')))

    def _gatherReservedCurrencyUnspent(self, exactSats: int = 0):
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') == exactSats]
        if len(unspentCurrency) == 0:
            return False
        return unspentCurrency[0]

    def _gatherOneCurrencyUnspent(self, atleastSats: int = 0) -> tuple:
        for unspentCurrency in self.unspentCurrency:
            if unspentCurrency.get('value') >= atleastSats:
                return unspentCurrency, unspentCurrency.get('value')
        return None, 0

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
                smallestUnspent = unspentCurrency.pop(0)
                gatheredCurrencyUnspents.append(smallestUnspent)
                gatheredCurrencySats += smallestUnspent.get('value')
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
            logging.debug('not enough', haveSatori, sats, color='magenta')
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

    def _broadcast(self, txHex: str) -> str:
        if self.electrumx.connected():
            return self.electrumx.broadcast(txHex)
        return self.electrumx.broadcast(txHex)

    # for server
    def satoriDistribution(self, amountByAddress: dict[str: float], memo: str) -> str:
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
                print('amount', amount, 'divisibility', self.divisibility, 'address', address, 'address valid:', Validate.address(address, self.symbol),
                      'TxUtils.isAmountDivisibilityValid(amount=amount,divisibility=self.divisibility)', TxUtils.isAmountDivisibilityValid(amount=amount, divisibility=self.divisibility))
                raise TransactionFailure('satoriDistribution bad params')
            satsByAddress[address] = TxUtils.roundSatsDownToDivisibility(
                sats=TxUtils.asSats(amount),
                divisibility=self.divisibility)
        satoriSats = sum(satsByAddress.values())
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=len(satsByAddress) + 3)
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
            outputCount=len(satsByAddress) + 3)  # satoriChange, currencyChange, memo
        memoOut = self._compileMemoOutput(memo)
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut, currencyChangeOut, memoOut]
                if x is not None])
        return self._broadcast(self._txToHex(tx))

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
        return self._broadcast(self._txToHex(tx))

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
        return self._broadcast(self._txToHex(tx))

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
        return self._broadcast(self._txToHex(tx))

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
    #        amount -= self.satoriFee
    #    satoriTotalSats = TxUtils.asSats(amount + self.satoriFee)
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
    #    if change - self.satoriFee > 0:
    #        change -= self.satoriFee
    #    if change > 0:
    #        satoriOuts.append(self._compileSatoriOutputs(
    #            {self.address: change})[0])
    #    # needs more work
    #    # satoriOuts = self._compileSatoriOutputs({address: amount})
    #    satoriChangeOut = self._compileSatoriChangeOutput(
    #        satoriSats=satoriSats,
    #        gatheredSatoriSats=gatheredSatoriSats - TxUtils.asSats(self.satoriFee))
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
    #    satoriClaimOut = self._compileSatoriOutputs({address: self.satoriFee})
    #    # sign rvn fee inputs and complete the transaction
    #    tx = self._createTransaction(
    #        tx=tx,
    #        txins=txins,
    #        txinScripts=txinScripts,
    #        txouts=satoriClaimOut + [
    #            x for x in [currencyChangeOut]
    #            if x is not None])
    #    return self._broadcast(self._txToHex(tx))
    #    # return tx  # testing

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
            amount -= self.satoriFee
        satoriTotalSats = TxUtils.asSats(
            amount) + TxUtils.asSats(self.satoriFee)
        satoriSats = TxUtils.roundSatsDownToDivisibility(
            sats=TxUtils.asSats(amount),
            divisibility=self.divisibility)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriTotalSats)
        txins, txinScripts = self._compileInputs(
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        satoriOuts = self._compileSatoriOutputs({address: satoriSats})
        satoriChangeOut = self._compileSatoriChangeOutput(
            satoriSats=satoriSats,
            gatheredSatoriSats=gatheredSatoriSats - TxUtils.asSats(self.satoriFee))
        # fee out to server
        satoriFeeOut = self._compileSatoriOutputs(
            {completerAddress: TxUtils.asSats(self.satoriFee)})[0]
        if satoriFeeOut is None:
            raise TransactionFailure('unable to generate satori fee')
        # change out to server
        currencyChangeOut, currencyChange = self._compileCurrencyChangeOutput(
            gatheredCurrencySats=feeSatsReserved,
            inputCount=len(gatheredSatoriUnspents),
            outputCount=len(satoriOuts) + 2 +
            (1 if satoriChangeOut is not None else 0),
            scriptPubKey=self._generateScriptPubKeyFromAddress(changeAddress),
            returnSats=True)
        if currencyChangeOut is None:
            raise TransactionFailure('unable to generate currency change')
        # logging.debug('txins', txins, color='magenta')
        # logging.debug('txinScripts', txinScripts, color='magenta')
        # logging.debug('satoriOuts', satoriOuts, color='magenta')
        # logging.debug('satoriChangeOut', satoriChangeOut, color='magenta')
        # logging.debug('satoriFeeOut', satoriFeeOut, color='magenta')
        # logging.debug('currencyChangeOut', currencyChangeOut, color='magenta')
        tx = self._createPartialOriginatorSimple(
            txins=txins,
            txinScripts=txinScripts,
            txouts=satoriOuts + [
                x for x in [satoriChangeOut]
                if x is not None] + [satoriFeeOut, currencyChangeOut])
        reportedFeeSats = feeSatsReserved - currencyChange
        # logging.debug('reportedFeeSats', reportedFeeSats, color='magenta')
        # logging.debug('reportedFeeSats', reportedFeeSats, color='magenta')
        return tx.serialize(), reportedFeeSats

    def satoriOnlyCompleterSimple(
        self,
        serialTx: bytes,
        feeSatsReserved: int,
        reportedFeeSats: int,
        changeAddress: Union[str, None] = None,
        completerAddress: Union[str, None] = None,
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
            return (
                reportedFeeSats < TxUtils.asSats(1) and
                reportedFeeSats < feeSatsReserved and
                tx.vout[-1].nValue == feeSatsReserved - reportedFeeSats)

        def _verifyClaim():
            return self._checkSatoriValue(tx.vout[-2])

        def _verifyClaimAddress():
            ''' verify the claim output goes to completerAddress '''
            for i, x in enumerate(tx.vout[-2].scriptPubKey):
                if i == 2 and isinstance(x, bytes):
                    return completerAddress == self.hash160ToAddress(x)
            return False

        def _verifyChangeAddress():
            ''' verify the change output goes to us at changeAddress '''
            for i, x in enumerate(tx.vout[-1].scriptPubKey):
                if i == 2 and isinstance(x, bytes):
                    return changeAddress == self.hash160ToAddress(x)
            return False

        completerAddress = completerAddress or self.address
        changeAddress = changeAddress or self.address
        tx = self._deserialize(serialTx)
        if not _verifyFee():
            raise TransactionFailure(
                f'fee mismatch, {reportedFeeSats}, {feeSatsReserved}')
        if not _verifyClaim():
            raise TransactionFailure(f'claim mismatch, {tx.vout[-2].value}')
        if not _verifyClaimAddress():
            raise TransactionFailure('claim mismatch, _verifyClaimAddress')
        if not _verifyChangeAddress():
            raise TransactionFailure('claim mismatch, _verifyChangeAddress')
        # add rvn fee input
        gatheredCurrencyUnspent = self._gatherReservedCurrencyUnspent(
            exactSats=feeSatsReserved)
        if gatheredCurrencyUnspent is None:
            raise TransactionFailure(f'unable to find sats {feeSatsReserved}')
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=[gatheredCurrencyUnspent])
        tx = self._createPartialCompleterSimple(
            tx=tx,
            txins=txins,
            txinScripts=txinScripts)
        return self._broadcast(self._txToHex(tx))

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
                        sats=TxUtils.asSats(self.balanceAmount),
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
        return self._broadcast(self._txToHex(tx))

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
    #        we must guarantee sum of ouputs = sum of inputs - satoriFee.
    #        that is all.
    #
    #        we could run into a situation where we need to take the fee out of
    #        multiple inputs. We could also run into the situation where we need
    #        to pair a currency output with a satori input.
    #        '''
    #        reservedFee = 0
    #        outs = []
    #        satoriFeeSats = TxUtils.asSats(self.satoriFee)
    #        for x in gatheredCurrencyUnspents:
    #            if x.get('value') > reservedFee:
    #        for x in gatheredSatoriUnspents:
    #            if reservedFee < satoriFeeSats:
    #                if x.get('value') > satoriFeeSats - reservedFee:
    #                    reservedFee += (satoriFeeSats - reservedFee)
    #                    # compile output with
    #                    satoriFeeSats x.get('value') -
    #                reservedFee = x.get('value') -
    #        return ( # not finished, combine with above
    #            self._compileSatoriOutputs({
    #                address: unspent.get('x') - self.satoriFee # on first item
    #                for unspent in gatheredSatoriUnspents
    #                }) +
    #            self._compileCurrencyOutputs(currencySats, address))
    #
    #    if not Validate.address(address, self.symbol):
    #        raise TransactionFailure('sendAllTransaction')
    #    logging.debug('currency', self.currency,
    #                'self.reserve', self.reserve, color='yellow')
    #    if self.balanceAmount <= self.satoriFee*2:
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
        if self.balanceAmount < self.satoriFee:
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
                            self.balanceAmount) - TxUtils.asSats(self.satoriFee),
                        divisibility=self.divisibility)}))
        satoriFeeOut = self._compileSatoriOutputs(
            {completerAddress: TxUtils.asSats(self.satoriFee)})[0]
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
            txouts=sweepOuts + [satoriFeeOut, currencyChangeOut])
        reportedFeeSats = feeSatsReserved - currencyChange
        return tx.serialize(), reportedFeeSats

    def typicalNeuronTransaction(
        self,
        amount: float,
        address: str,
        sweep: bool = False,
        pullFeeFromAmount: bool = False,
        completerAddress: str = None,
        changeAddress: str = None,
        feeSatsReserved: int = 0
    ) -> TransactionResult:
        if sweep:
            try:
                if self.currency < self.reserve:
                    if feeSatsReserved == 0 or completerAddress is None or changeAddress is None:
                        return TransactionResult(
                            result='try again',
                            success=True,
                            tx=None,
                            msg='creating partial, need feeSatsReserved.')
                    # logging.debug('a', color='magenta')
                    result = self.sendAllPartialSimple(
                        address=address,
                        feeSatsReserved=feeSatsReserved,
                        completerAddress=completerAddress,
                        changeAddress=changeAddress,
                    )
                    # #logging.debug('result of sendAllPartialSimple',
                    #               result, color='yellow')
                    # logging.debug('b', result, color='magenta')
                    if result is None:
                        # logging.debug('c', color='magenta')
                        return TransactionResult(
                            result=None,
                            success=False,
                            msg='Send Failed: try again in a few minutes.')
                    # logging.debug('d', color='magenta')
                    return TransactionResult(
                        result=result,
                        success=True,
                        tx=result[0],
                        reportedFeeSats=result[1],
                        msg='send transaction requires fee.')
                # logging.debug('e', color='magenta')
                result = self.sendAllTransaction(address)
                # logging.debug('f', result, color='magenta')
                if result is None:
                    # logging.debug('g', color='magenta')
                    return TransactionResult(
                        result=result,
                        success=False,
                        msg='Send Failed: try again in a few minutes.')
                # logging.debug('h', result, color='magenta')
                return TransactionResult(result=str(result), success=True)
            except TransactionFailure as e:
                # logging.debug('i', color='magenta')
                return TransactionResult(
                    result=None,
                    success=False,
                    msg=f'Send Failed: {e}')
        else:
            # logging.debug('j', color='magenta')
            try:
                if self.currency < self.reserve:
                    # if we have to make a partial we need more data so we need
                    # to return, telling them we need more data, asking for more
                    # information, and then if we get more data we can do this:
                    # logging.debug('k', color='magenta')
                    if feeSatsReserved == 0 or completerAddress is None:
                        # logging.debug('l', color='magenta')
                        return TransactionResult(
                            result='try again',
                            success=True,
                            tx=None,
                            msg='creating partial, need feeSatsReserved.')
                    result = self.satoriOnlyPartialSimple(
                        amount=amount,
                        address=address,
                        pullFeeFromAmount=pullFeeFromAmount,
                        feeSatsReserved=feeSatsReserved,
                        completerAddress=completerAddress,
                        changeAddress=changeAddress)
                    # logging.debug('n', color='magenta')
                    if result is None:
                        # logging.debug('o', color='magenta')
                        return TransactionResult(
                            result=None,
                            success=False,
                            msg='Send Failed: try again in a few minutes.')
                    # logging.debug('p', color='magenta')
                    return TransactionResult(
                        result=result,
                        success=True,
                        tx=result[0],
                        reportedFeeSats=result[1],
                        msg='send transaction requires fee.')
                # logging.debug('q', color='magenta')
                result = self.satoriTransaction(amount=amount, address=address)
                # logging.debug('r', result,  color='magenta')
                if result is None:
                    # logging.debug('s', color='magenta')
                    return TransactionResult(
                        result=result,
                        success=False,
                        msg='Send Failed: try again in a few minutes.')
                # logging.debug('t', color='magenta')
                return TransactionResult(result=str(result), success=True)
            except TransactionFailure as e:
                # logging.debug('v', color='magenta')
                return TransactionResult(
                    result=None,
                    success=False,
                    msg=f'Send Failed: {e}')
