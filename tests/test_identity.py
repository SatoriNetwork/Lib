import unittest
from unittest.mock import Mock, patch
import base64
from satorilib.wallet.identity import IdentityBase


class MockIdentity(IdentityBase):
    """Mock implementation of IdentityBase for testing"""
    
    def _generatePrivateKey(self, compressed=True):
        mock_priv = Mock()
        mock_priv.pub = Mock()
        mock_priv.pub.hex.return_value = 'mock_pubkey_hex'
        mock_priv._cec_key = Mock()
        mock_priv._cec_key.get_raw_privkey.return_value = b'mock_privkey_bytes'
        mock_priv.__str__ = lambda _: 'mock_privkey_str'
        return mock_priv

    def _generateAddress(self, pub=None):
        mock_addr = Mock()
        mock_addr.__str__ = lambda _: 'mock_address'
        return mock_addr

    def _generateScriptPubKeyFromAddress(self, address):
        return 'mock_script'


class TestIdentityBase(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_entropy = b'0' * 32
        self.identity = MockIdentity(entropy=self.test_entropy)

    def test_init_with_entropy(self):
        """Test initialization with entropy"""
        self.assertEqual(self.identity._entropy, self.test_entropy)
        self.assertEqual(self.identity._entropyStr, '')
        self.assertIsNone(self.identity._privateKeyObj)
        self.assertEqual(self.identity.privateKey, '')
        self.assertEqual(self.identity.passphrase, '')
        self.assertEqual(self.identity.publicKey, '')
        self.assertEqual(self.identity.addressValue, '')
        self.assertEqual(self.identity.scripthashValue, '')

    def test_init_without_entropy(self):
        """Test initialization without entropy"""
        identity = MockIdentity()
        self.assertIsNone(identity._entropy)
        self.assertEqual(identity._entropyStr, '')
        self.assertIsNone(identity._privateKeyObj)
        self.assertEqual(identity.privateKey, '')
        self.assertEqual(identity.passphrase, '')
        self.assertEqual(identity.publicKey, '')
        self.assertEqual(identity.addressValue, '')
        self.assertEqual(identity.scripthashValue, '')

    def test_generate_objects_from_entropy(self):
        """Test generating objects from entropy"""
        result = self.identity.generateObjects()
        self.assertTrue(result)
        self.assertIsNotNone(self.identity._privateKeyObj)
        self.assertIsNotNone(self.identity._addressObj)
        self.assertEqual(
            self.identity._entropyStr,
            base64.b64encode(self.test_entropy).decode('utf-8'))

    def test_generate_objects_without_entropy(self):
        """Test generating objects without entropy"""
        identity = MockIdentity()
        result = identity.generateObjects()
        self.assertTrue(result)
        self.assertIsNotNone(identity._entropy)
        self.assertEqual(len(identity._entropy), 32)

    def test_generate_full_wallet(self):
        """Test generating all wallet components"""
        result = self.identity.generate()
        self.assertTrue(result)
        self.assertNotEqual(self.identity.passphrase, '')
        self.assertNotEqual(self.identity.privateKey, '')
        self.assertNotEqual(self.identity.publicKey, '')
        self.assertNotEqual(self.identity.addressValue, '')
        self.assertNotEqual(self.identity.scripthashValue, '')

    def test_load_from_yaml_entropy(self):
        """Test loading wallet from yaml with entropy"""
        yaml_data = {
            'entropy': base64.b64encode(self.test_entropy).decode('utf-8'),
            'privateKey': 'stored_privkey',
            'publicKey': 'stored_pubkey',
            'wallet': {'address': 'stored_address'},
            'scripthash': 'stored_scripthash'
        }
        self.identity.loadFromYaml(yaml_data)
        self.assertEqual(self.identity._entropy, self.test_entropy)
        # Values should be derived from entropy, not stored values
        self.assertEqual(self.identity.privkey, 'mock_privkey_str')
        self.assertEqual(self.identity.pubkey, 'mock_pubkey_hex')
        self.assertEqual(self.identity.address, 'mock_address')

    def test_load_from_yaml_private_key(self):
        """Test loading wallet from yaml with private key only"""
        yaml_data = {
            'privateKey': 'stored_privkey',
            'publicKey': 'stored_pubkey',
            'wallet': {'address': 'stored_address'},
            'scripthash': 'stored_scripthash'
        }
        self.identity.loadFromYaml(yaml_data)
        self.assertIsNone(self.identity._entropy)
        self.assertEqual(self.identity.privateKey, 'stored_privkey')
        # Public data should be derived from private key
        self.assertEqual(self.identity.pubkey, 'mock_pubkey_hex')
        self.assertEqual(self.identity.address, 'mock_address')

    def test_load_from_yaml_watch_only(self):
        """Test loading wallet from yaml with public data only"""
        yaml_data = {
            'publicKey': 'watch_pubkey',
            'wallet': {'address': 'watch_address'},
            'scripthash': 'watch_scripthash'
        }
        self.identity.loadFromYaml(yaml_data)
        self.assertIsNone(self.identity._entropy)
        self.assertEqual(self.identity.privateKey, '')
        self.assertEqual(self.identity.publicKey, 'watch_pubkey')
        self.assertEqual(self.identity.addressValue, 'watch_address')
        self.assertEqual(self.identity.scripthashValue, 'watch_scripthash')

    def test_validate_state_entropy_based(self):
        """Test state validation for entropy-based wallet"""
        self.identity.generateObjects()
        self.assertTrue(self.identity.validateState())

    def test_validate_state_private_key_based(self):
        """Test state validation for private key-based wallet"""
        identity = MockIdentity()
        identity.privateKey = 'test_privkey'
        identity._privateKeyObj = identity._generatePrivateKey()
        identity._addressObj = identity._generateAddress()
        self.assertTrue(identity.validateState())

    def test_validate_state_watch_only(self):
        """Test state validation for watch-only wallet"""
        identity = MockIdentity()
        identity.publicKey = 'test_pubkey'
        identity.addressValue = 'test_address'
        identity.scripthashValue = 'test_scripthash'
        self.assertTrue(identity.validateState())

    def test_verify_entropy_based(self):
        """Test verification for entropy-based wallet"""
        self.identity.generate()
        self.assertTrue(self.identity.verify())

    def test_verify_private_key_based(self):
        """Test verification for private key-based wallet"""
        identity = MockIdentity()
        identity.privateKey = 'test_privkey'
        identity._privateKeyObj = identity._generatePrivateKey()
        identity._addressObj = identity._generateAddress()
        identity.publicKey = 'mock_pubkey_hex'
        identity.addressValue = 'mock_address'
        self.assertTrue(identity.verify())

    def test_verify_watch_only(self):
        """Test verification for watch-only wallet"""
        identity = MockIdentity()
        identity.publicKey = 'test_pubkey'
        identity.addressValue = 'test_address'
        identity.scripthashValue = 'test_scripthash'
        self.assertTrue(identity.verify())

    def test_close(self):
        """Test closing wallet and clearing sensitive data"""
        self.identity.generate()
        self.identity.close()
        self.assertIsNone(self.identity._entropy)
        self.assertEqual(self.identity._entropyStr, '')
        self.assertIsNone(self.identity._privateKeyObj)
        self.assertEqual(self.identity.privateKey, '')
        self.assertEqual(self.identity.passphrase, '')

    @patch('secrets.token_bytes')
    def test_generate_entropy(self, mock_token_bytes):
        """Test entropy generation"""
        mock_token_bytes.return_value = b'test_entropy' * 4
        entropy = IdentityBase.generateEntropy()
        self.assertEqual(len(entropy), 32)
        mock_token_bytes.assert_called_once_with(32)

    def test_encryption_methods(self):
        """Test the encryption/decryption methods"""
        self.identity.generateObjects()
        test_pubkey = 'mock_pubkey_hex'
        test_message = b'test message'
        
        # Test secret derivation
        secret = self.identity.secret(test_pubkey)
        self.assertIsNotNone(secret)
        
        # Test key derivation
        key = self.identity.derivedKey(secret)
        self.assertEqual(len(key), 32)
        
        # Test AES-GCM encryption/decryption
        nonce, ciphertext = self.identity.aesGcmEncrypt(key, test_message)
        decrypted = self.identity.aesGcmDecrypt(key, nonce, ciphertext)
        self.assertEqual(decrypted, test_message)
        
        # Test Fernet encryption/decryption
        encrypted = self.identity.fernetEncrypt(key, test_message)
        decrypted = self.identity.fernetDecrypt(key, encrypted)
        self.assertEqual(decrypted, test_message)
        
        # Test combined encrypt/decrypt
        encrypted = self.identity.encrypt(secret, test_message)
        decrypted = self.identity.decrypt(secret, encrypted)
        self.assertEqual(decrypted, test_message)

    def test_load_from_yaml_invalid_entropy(self):
        """Test loading wallet with invalid entropy format"""
        yaml_data = {
            'entropy': 'invalid_base64_encoding',
        }
        with self.assertRaises(Exception):
            self.identity.loadFromYaml(yaml_data)

    def test_load_from_yaml_empty(self):
        """Test loading wallet with empty yaml"""
        with self.assertRaises(Exception):
            self.identity.loadFromYaml({})

    def test_validate_state_invalid_entropy(self):
        """Test state validation with invalid entropy"""
        self.identity._entropy = b'too_short'
        self.assertFalse(self.identity.validateState())

    def test_validate_state_missing_objects(self):
        """Test state validation with missing required objects"""
        self.identity._entropy = b'0' * 32
        self.identity._privateKeyObj = None
        self.assertFalse(self.identity.validateState())

    def test_encryption_with_invalid_key(self):
        """Test encryption with invalid key"""
        with self.assertRaises(Exception):
            self.identity.aesGcmEncrypt(b'short_key', b'message')

    def test_decryption_with_invalid_data(self):
        """Test decryption with invalid data"""
        with self.assertRaises(Exception):
            self.identity.aesGcmDecrypt(b'0'*32, b'nonce', b'invalid_ciphertext')

    def test_verify_mismatched_data(self):
        """Test verification with mismatched data"""
        self.identity.generate()
        self.identity.publicKey = 'mismatched_pubkey'
        self.assertFalse(self.identity.verify())


if __name__ == '__main__':
    unittest.main() 