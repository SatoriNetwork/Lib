from typing import Union
from base64 import b64encode, b64decode
from eth_keys import keys
from eth_account import Account
from eth_account.messages import encode_defunct
from satorilib.disk.wallet import WalletApi
from satorilib.wallet.ethereum.valid import isValidEthereumAddress

class EthereumWallet():
    '''
    instead of inheriting from Wallet like RavencoinWallet and EvrmoreWallet
    we'll just use this class to generate a wallet details for ethereum on the
    fly. Our only need right now is to generate an address and private key,
    (and as a stretch goal, a pubkey for signing and verifying messages) so that
    we can inform the server of what address to associate with the user's
    account so that when we wrap tokens for them we can send the wrapped tokens
    to the right address. we should also key this off the vault rather than the
    wallet. alternatively we could just ask the user to provide an address...
    If they're wrapping tokens to trade they'll probably know how to use
    metamask already...
    '''

    @staticmethod
    def addressIsValid(address: str) -> bool:
        return isValidEthereumAddress(address)

    def __init__(
        self,
        vaultPath: str,
        password: Union[str, None] = None,
    ):
        self.vaultPath = vaultPath
        self.password = password
        self._entropy = None
        self.account = None
        self.publicKey = None
        self.privateKey = None
        self.address = None
        self.initRaw()

    def __call__(self):
        self.init()
        return self

    @property
    def symbol(self) -> str:
        return 'eth'

    @property
    def chain(self) -> str:
        return 'Ethereum'

    def initRaw(self):
        self.loadRaw()

    def init(self):
        self.load()

    def decryptWallet(self, encrypted: dict) -> dict:
        if isinstance(self.password, str):
            from satorilib import secret
            try:
                return secret.decryptMapValues(
                    encrypted=encrypted,
                    password=self.password,
                    keys=['entropy', 'privateKey', 'words',
                          'address' if len(encrypted.get(self.symbol, {}).get(
                              'address', '')) != 34 else '',  # == 108 else '',
                          'scripthash' if len(encrypted.get(
                              'scripthash', '')) != 64 else '',  # == 152 else '',
                          'publicKey' if len(encrypted.get(
                              'publicKey', '')) != 66 else '',  # == 152 else '',
                          ])
            except Exception as _:
                return encrypted
        return encrypted

    def getRaw(self):
        return WalletApi.load(walletPath=self.vaultPath)

    def loadRaw(self):
        self.yaml = self.getRaw()
        if self.yaml == False:
            return False
        self._entropy = self.yaml.get('entropy')
        if isinstance(self._entropy, bytes):
            self._entropyStr = b64encode(self._entropy).decode('utf-8')
        if isinstance(self._entropy, str):
            self._entropyStr = self._entropy
            self._entropy = b64decode(self._entropy)
        return True

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
        self.account = self._generateAccount()
        self.publicKey = str(self._generatePublicKey())
        self.privateKey = self.account.key.to_0x_hex()
        self.address = self.account.address
        return True

    def _generateAccount(self):
        return EthereumWallet.generateAccount(self._entropy)

    @staticmethod
    def generateAccount(entropy: bytes):
        account = Account.from_key(entropy)
        try:
            from web3 import Web3
            account.checksum_address = Web3.to_checksum_address(account.address)
        except Exception as _:
            account.checksum_address = None
        return account

    def _generatePublicKey(self):
        '''
        In Ethereum, the eth-account library's Account class does not directly
        provide the public key. However, you can derive the public key from the
        private key using the eth_keys library, which is internally used by
        eth-account.
        '''
        return keys.PrivateKey(self.account.key).public_key

    def sign(self, message: str):
        return Account.sign_message(
            encode_defunct(text=message),
            private_key=self.account.key)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return Account.recover_message(
            encode_defunct(text=message),
            signature=sig) == (address or self.address)
