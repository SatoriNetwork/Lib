"""
Identity Management for Cryptocurrency Wallets

This module provides the base identity management functionality for cryptocurrency wallets.
It handles three types of wallets:

1. Entropy-based wallets (highest security)
   - Generated from random entropy
   - Can derive all wallet components
   - Full transaction capabilities

2. Private key-based wallets
   - Imported from existing private key
   - Can derive public components
   - Full transaction capabilities

3. Watch-only wallets
   - Only contains public components
   - No transaction capabilities
   - Used for monitoring addresses

Interface for Wallet Implementation:
- Wallet object should combine:
  1. IdentityBase (this class) for key/address management
  2. ElectrumX connection for network interaction
  3. Additional wallet functionality (transactions, balance, etc.)

Required Implementation:
- _generatePrivateKey(compressed: bool) -> PrivateKeyObject
- _generateAddress(pub=None) -> AddressObject
- _generateScriptPubKeyFromAddress(address: str) -> CScript
"""

from typing import Union, Any
import os
import secrets
import mnemonic
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet
from satorilib import logging
from satorilib import config
from satorilib.disk.utils import safetify
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.concepts import authenticate


class IdentityBase():
    """
    Base class for wallet identity management.
    Handles the core functionality of managing wallet identity data
    with support for entropy-based, private key-based, and watch-only wallets.
    """

    def __init__(self, entropy: Union[bytes, None] = None):
        self._entropy: Union[bytes, None] = entropy
        self._entropyStr: str = ''
        self._privateKeyObj: Any = None  # Type depends on implementation
        self._addressObj: Any = None     # Type depends on implementation
        # these are only set if entropy is not provided:
        self.privateKey: str = ''
        self.passphrase: str = ''
        # these are always set if present in the yaml file and they match the entropy-derived values:
        self.publicKey: str = ''
        self.addressValue: str = ''
        self.scripthashValue: str = ''

    @property
    def symbol(self) -> str:
        """The symbol of the currency of the chain """
        return ''

    @property
    def pubkey(self) -> str:
        if self.publicKey:
            return self.publicKey
        return self._privateKeyObj.pub.hex() if self._privateKeyObj else ''
        
    @property
    def privkey(self) -> str:
        if self.privateKey:
            return self.privateKey
        return str(self._privateKeyObj) if self._privateKeyObj else ''

    @property
    def words(self) -> str:
        if self.passphrase:
            return self.passphrase
        return self._generateWords() if self._entropy else ''
    
    @property
    def address(self) -> str:
        if self.addressValue:
            return self.addressValue
        return str(self._addressObj) if self._addressObj else ''
    
    @property
    def scripthash(self) -> str:
        if self.scripthashValue:
            return self.scripthashValue
        return self._generateScripthash() if self._addressObj else ''
    
    def close(self) -> None:
        """Reset all sensitive instance variables to their initial state."""
        self._entropy = None
        self._entropyStr = ''
        self._privateKeyObj = None
        self.privateKey = ''
        self.passphrase = ''

    def loadFromYaml(self, yaml: Union[dict, None] = None):
        """Load wallet data from yaml with strict hierarchy of truth sources:
        1. Entropy (highest priority) - derives everything
        2. Private key (if no entropy) - derives public data
        3. Public data only (watch-only wallet)
        """
        yaml = yaml or {}
        
        # Case 1: Entropy is present - use it as source of truth
        self._entropy = yaml.get('entropy')
        if isinstance(self._entropy, bytes):
            self._entropyStr = base64.b64encode(self._entropy).decode('utf-8')
        elif isinstance(self._entropy, str):
            self._entropyStr = self._entropy
            self._entropy = base64.b64decode(self._entropy)
        
        if self._entropy is not None:
            # Generate everything from entropy
            self.generateObjects()
            # Store provided values for validation
            stored_private_key = yaml.get('privateKey', '')
            stored_public_key = yaml.get('publicKey', '')
            stored_address = yaml.get(self.symbol, {}).get('address')
            stored_scripthash = yaml.get('scripthash', '')
            
            # Validate if stored values match derived values
            if stored_private_key and stored_private_key != self.privkey:
                logging.warning('Stored private key does not match entropy-derived key')
            if stored_public_key and stored_public_key != self.pubkey:
                logging.warning('Stored public key does not match entropy-derived key')
            if stored_address and stored_address != self.address:
                logging.warning('Stored address does not match entropy-derived address')
            if stored_scripthash and stored_scripthash != self.scripthash:
                logging.warning('Stored scripthash does not match entropy-derived scripthash')
            return

        # Case 2: Private key is present but no entropy
        self.privateKey = yaml.get('privateKey', '')
        if self.privateKey:
            self._privateKeyObj = self._generatePrivateKey()
            if self._privateKeyObj:
                self._addressObj = self._generateAddress()
                stored_public_key = yaml.get('publicKey', '')
                stored_address = yaml.get(self.symbol, {}).get('address')
                stored_scripthash = yaml.get('scripthash', '')
                
                # Validate if stored values match derived values
                if stored_public_key and stored_public_key != self.pubkey:
                    logging.warning('Stored public key does not match private key-derived key')
                if stored_address and stored_address != self.address:
                    logging.warning('Stored address does not match private key-derived address')
                if stored_scripthash and stored_scripthash != self.scripthash:
                    logging.warning('Stored scripthash does not match private key-derived scripthash')
                return

        # Case 3: Watch-only wallet (public data only)
        self.publicKey = yaml.get('publicKey', '')
        self.addressValue = yaml.get(self.symbol, {}).get('address')
        self.scripthashValue = yaml.get('scripthash', '')
        
        # Validate we have at least some data for a watch-only wallet
        if not any([self.publicKey, self.addressValue, self.scripthashValue]):
            raise Exception('No wallet data provided - need entropy, private key, or watch-only data')

    def validateIdentity(self) -> bool:
        """
        Verify that all wallet data is consistent with its source of truth.
        Returns True if verification passes, False otherwise.
        """
        # Case 1: Verify from entropy
        if self._entropy is not None:
            _entropy = self._entropy
            _entropyStr = base64.b64encode(_entropy).decode('utf-8')
            _privateKeyObj = self._generatePrivateKey()
            if _privateKeyObj is None:
                return False
            _addressObj = self._generateAddress(pub=_privateKeyObj.pub)
            words = self._generateWords()
            privateKey = str(_privateKeyObj)
            publicKey = _privateKeyObj.pub.hex()
            address = str(_addressObj)
            if self.addressValue is None:
                self.addressValue = address
            scripthash = self._generateScripthash(forAddress=address)
            return (
                _entropy == self._entropy and
                _entropyStr == self._entropyStr and
                words == self.words and
                privateKey == self.privkey and
                publicKey == self.pubkey and
                address == self.address and
                scripthash == self.scripthash)
        
        # Case 2: Verify from private key
        if self.privateKey:
            _privateKeyObj = self._generatePrivateKey()
            if _privateKeyObj is None:
                return False
            _addressObj = self._generateAddress(pub=_privateKeyObj.pub)
            publicKey = _privateKeyObj.pub.hex()
            address = str(_addressObj)
            if self.addressValue is None:
                self.addressValue = address
            scripthash = self._generateScripthash(forAddress=address)
            return (
                publicKey == self.publicKey and
                address == self.address and
                scripthash == self.scripthash)
        
        # Case 3: Watch-only wallet - verify they are consistent
        if self.publicKey and self.addressValue and self.scripthashValue:
            return self._generateScripthash(forAddress=self.addressValue) and True # assume the address is correct...
        if self.addressValue and self.scripthashValue:
            return self._generateScripthash(forAddress=self.addressValue)
        if self.publicKey and self.addressValue:
            return True # assume the address is correct...
        return True

    def generateObjects(self):
        """
        Generate or regenerate wallet objects from the source of truth.
        This ensures all derived objects are consistent with either entropy or private key.
        
        Returns:
            bool: True if objects were generated successfully, False otherwise
        """
        try:
            # Case 1: Generate from entropy
            if self._entropy is None:
                self._entropy = IdentityBase.generateEntropy()
            self._entropyStr = base64.b64encode(self._entropy).decode('utf-8')
            self._privateKeyObj = self._generatePrivateKey()
            if self._privateKeyObj is None:
                logging.error('Failed to generate private key object')
                return False
                
            self._addressObj = self._generateAddress()
            if self._addressObj is None:
                logging.error('Failed to generate address object')
                return False
                
            return True
            
        except Exception as e:
            logging.error(f'Error generating wallet objects: {str(e)}')
            return False

    def generate(self) -> bool:
        """
        Generate all wallet data from scratch or existing entropy.
        This includes both the internal objects and the public-facing string representations.
        
        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.generateObjects():
            return False
            
        try:
            self.passphrase = self.passphrase or self._generateWords()
            if self._privateKeyObj is None:
                logging.error('Private key object not available')
                return False
                
            self.privateKey = self.privateKey or str(self._privateKeyObj)
            self.publicKey = self.publicKey or self._privateKeyObj.pub.hex()
            self.addressValue = self.addressValue or str(self._addressObj)
            self.scripthashValue = self.scripthashValue or self._generateScripthash()
            
            return True
            
        except Exception as e:
            logging.error(f'Error in generate: {str(e)}')
            return False

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
        ''' 
        Generate or load a private key object.
        
        Args:
            compressed (bool): Whether to use compressed public key format. Defaults to True.
            
        Returns:
            A private key object that must have:
            - pub attribute for public key
            - __str__ method for string representation
            - _cec_key.get_raw_privkey() method for raw bytes
        '''
        raise NotImplementedError("Subclass must implement _generatePrivateKey")

    def _generateAddress(self, pub=None):
        ''' 
        Generate an address object from a public key.
        
        Args:
            pub: Optional public key to use. If None, uses self._privateKeyObj.pub
            
        Returns:
            An address object that must have __str__ method for string representation
        '''
        raise NotImplementedError("Subclass must implement _generateAddress")

    def _generateScriptPubKeyFromAddress(self, address: str):
        ''' 
        Generate a script pubkey from an address.
        
        Args:
            address (str): The address to generate script for
            
        Returns:
            A CScript object representing the script pubkey
        '''
        raise NotImplementedError("Subclass must implement _generateScriptPubKeyFromAddress")

    def _generateUncompressedPubkey(self):
        ''' 
        Generate an uncompressed public key.
        
        Returns:
            str: Hex string of uncompressed public key
        '''
        return self._generatePrivateKey(compressed=False).pub.hex()

    ## encryption ##############################################################

    def secret(self, pubkey: str) -> None:
        """
        Derive a shared secret with another public key (hex).
        """
        # 1. Get our private key bytes from CEvrmoreSecret
        # returns 32 raw bytes
        my_priv_bytes = self._privateKeyObj._cec_key.get_raw_privkey()
        my_ec_private_key = ec.derive_private_key(
            private_value=int.from_bytes(my_priv_bytes, 'big'),
            curve=ec.SECP256K1())

        # 2. Parse the peer's public key
        peer_pubkey_bytes = bytes.fromhex(pubkey)
        peer_ec_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            curve=ec.SECP256K1(),
            data=peer_pubkey_bytes)

        # 3. Perform ECDH
        shared_secret = my_ec_private_key.exchange(
            algorithm=ec.ECDH(),
            peer_public_key=peer_ec_public_key)

        return shared_secret

    @staticmethod
    def derivedKey(shared: bytes, info: bytes = b'evrmore-ecdh') -> bytes:
        """
        Use HKDF to turn the ECDH shared secret into a 32-byte AES key.
        """
        aesKey = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=info).derive(shared)  # 32 bytes
        return aesKey

    @staticmethod
    def aesGcmEncrypt(aesKey: bytes, plaintext: bytes, aad: bytes = None) -> tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-GCM. Returns (nonce, ciphertext).
        - `aad` is "additional authenticated data" which GCM will authenticate
        but not encrypt (commonly used for e.g. message headers).
        """
        # 12-byte random nonce is typical
        nonce = os.urandom(12)
        aesgcm = AESGCM(aesKey)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        return nonce, ciphertext

    @staticmethod
    def aesGcmDecrypt(aesKey: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = None) -> bytes:
        """
        Decrypt ciphertext using AES-GCM. Returns plaintext bytes.
        """
        aesgcm = AESGCM(aesKey)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext

    @staticmethod
    def fernetEncrypt(aesKey: bytes, ciphertext: bytes) -> bytes:
        """ Encrypts a message using the ECDH-derived shared secret. """
        # Encrypt with Fernet (just an example symmetric scheme)
        fernetKey = base64.urlsafe_b64encode(aesKey)
        f = Fernet(fernetKey)
        ciphertext = f.encrypt(ciphertext)
        return ciphertext

    @staticmethod
    def fernetDecrypt(aesKey: bytes, ciphertext: bytes) -> bytes:
        """
        Decrypts a message using the ECDH-derived shared secret.
        """
        fernetKey = base64.urlsafe_b64encode(aesKey)
        f = Fernet(fernetKey)
        plaintext = f.decrypt(ciphertext)
        return plaintext

    @staticmethod
    def encrypt(
        shared: bytes,
        msg: Union[bytes, str],
        aesKey: Union[bytes, None] = None,
    ) -> bytes:
        """
        Encrypt a message using the ECDH-derived shared secret, returning a single blob:
        [12-byte nonce] + [ciphertext with GCM tag appended].
        """
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        # aesGcmEncrypt -> (nonce, ciphertext)
        nonce, ciphertext = IdentityBase.aesGcmEncrypt(
            aesKey=aesKey or IdentityBase.derivedKey(shared),
            plaintext=msg)
        # Return nonce and ciphertext together
        return nonce + ciphertext

    @staticmethod
    def decrypt(
        shared: bytes,
        blob: Union[bytes, str],
        aesKey: Union[bytes, None] = None,
    ) -> bytes:
        """
        Decrypt an AES-GCM message that was packaged as [nonce + ciphertext].
        We parse out the first 12 bytes as the nonce, and everything else is ciphertext.
        """
        if isinstance(blob, str):
            blob = blob.encode('utf-8')
        # The nonce is always 12 bytes in this pattern
        nonce = blob[:12]
        ciphertext = blob[12:]
        plaintext = IdentityBase.aesGcmDecrypt(
            aesKey=aesKey or IdentityBase.derivedKey(shared),
            nonce=nonce,
            ciphertext=ciphertext)
        return plaintext

    def validateState(self) -> bool:
        """
        Validate internal state consistency.
        This is different from verify() which checks against stored values.
        This method ensures the internal objects are in a valid state.
        
        Returns:
            bool: True if state is valid, False otherwise
        """
        try:
            # Case 1: Entropy-based wallet
            if self._entropy is not None:
                if not isinstance(self._entropy, bytes) or len(self._entropy) != 32:
                    logging.error('Invalid entropy format')
                    return False
                if not self._entropyStr:
                    logging.error('Missing entropy string representation')
                    return False
                if self._privateKeyObj is None:
                    logging.error('Missing private key object')
                    return False
                if self._addressObj is None:
                    logging.error('Missing address object')
                    return False
                return True
                
            # Case 2: Private key-based wallet
            if self.privateKey:
                if self._privateKeyObj is None:
                    logging.error('Missing private key object')
                    return False
                if self._addressObj is None:
                    logging.error('Missing address object')
                    return False
                return True
                
            # Case 3: Watch-only wallet
            if not any([self.publicKey, self.addressValue, self.scripthashValue]):
                logging.error('Watch-only wallet missing all public data')
                return False
                
            return True
            
        except Exception as e:
            logging.error(f'Error validating state: {str(e)}')
            return False


class Identity(IdentityBase):

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

    def __init__(self, walletPath: str, password: Union[str, None] = None):
        if walletPath == '':
            raise Exception('wallet paths must be provided')
        super().__init__()
        self.walletPath = walletPath
        self.password = password
        self.alias = None
        self.challenges: dict[str, str] = {}
        self.load()

    def __call__(self, password: Union[str, None] = None):
        self.open(password)
        return self

    def __repr__(self):
        return (
            f'{self.chain}Wallet('
            f'\n  encrypted: {self.isEncrypted},'
            f'\n  publicKey: {self.publicKey},'
            #f'\n  privateKey: {self.privateKey},'
            #f'\n  words: {self.words},'
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
        if self.isDecrypted and not super().validateIdentity():
            raise Exception('wallet or vault file corrupt')
        return True

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

    def authenticationPayload(
        self,
        challengeId: Union[str, None] = None,
        challenged:Union[str, None] = None,
        signature:Union[bytes, None] = None,
    ) -> dict[str, str]:
        return {
            'pubkey': self.pubkey,
            'address': self.address,
            **({'challenge': self.challenge(challengeId) if challengeId else {}}),
            **({'signature': self.sign(challenged)} if challenged else {}), # TODO: "and not signature"? to avoid calling self.sign() if already provided
            **({'signature': signature} if signature else {})}

    def hash160ToAddress(self, pubKeyHash: Union[str, bytes]) -> str:
        return TxUtils.hash160ToAddress(pubKeyHash, self.networkByte)

    def authPayload(self, asDict: bool = False, challenge: str = None) -> Union[str, dict]:
        payload = authenticate.authPayload(self, challenge)
        if asDict:
            return payload
        return json.dumps(payload)