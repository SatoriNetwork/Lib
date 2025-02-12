from typing import Union
import os
import secrets
from base64 import b64encode, b64decode
import mnemonic
from satorilib import logging
from satorilib import config


class IdentityBase():

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
        self.generateObjects()

    def verify(self) -> bool:
        if self._entropy is None:
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
            words == self.words and
            privateKey == self.privateKey and
            publicKey == self.publicKey and
            address == self.address and
            scripthash == self.scripthash)

    def generateObjects(self):
        self._entropy = self._entropy or IdentityBase.generateEntropy()
        self._entropyStr = b64encode(self._entropy).decode('utf-8')
        self._privateKeyObj = self._generatePrivateKey()
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


class Idenity(IdentityBase):

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
        password: Union[str, None] = None,
    ):
        if walletPath == cachePath:
            raise Exception('wallet and cache paths cannot be the same')
        super().__init__()
        self.password = password
        self.walletPath = walletPath
        self.alias = None
        self.challenges: dict[str, str] = {}
        self.load()

    def __call__(self, password: Union[str, None] = None):
        self.open(password)
        return self

    def __repr__(self):
        return (
            f'{self.chain}Wallet('
            f'\n  publicKey: {self.publicKey},'
            f'\n  privateKey: {self.privateKey},'
            f'\n  words: {self.words},'
            f'\n  address: {self.address},'
            f'\n  scripthash: {self.scripthash})')

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


    ### Loading ################################################################

    def walletFileExists(self, path: Union[str, None] = None):
        return os.path.exists(path or self.walletPath)

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

    def setAlias(self, alias: Union[str, None] = None) -> None:
        self.alias = alias

    def challenge(self, identifier: Union[str, None] = None) -> str:
        self.challenges[identifier] = secrets.token_hex(32)
        return self.challenges[identifier]

    def sign(self, msg: str) -> bytes:
        ''' signs a message with the private key '''

    def verify(self,
        msg: str,
        sig: bytes,
        address: Union[str, None] = None,
        pubkey: Union[str, bytes, None] = None,
    ) -> bool:
        ''' verifies a message with the public key '''
