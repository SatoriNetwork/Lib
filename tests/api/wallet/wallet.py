import unittest
from unittest.mock import patch, mock_open
from satorilib.api.wallet.wallet import Wallet
from satorilib.api.wallet import RavencoinWallet, EvrmoreWallet
from satorilib import logging
from unittest.mock import patch, MagicMock
from satorineuron import config
from satorilib.api.disk import Disk
Disk.setConfig(config)

# Test Cases for satori wallet base class
class TestWallet(unittest.TestCase):
    # setup method
    def setUp(self):
        self.test_password = "test_password"

    # Test case to load the wallet yaml file from wallet.yaml
    def test_wallet_load(self):
        logging.info("Load Wallet Testing", color="green")
        walletObject = EvrmoreWallet(
                "/Satori/Lib/tests/api/wallet/wallet.yaml",
                reserve=0.25,
                isTestnet=False)
        self.assertIsNotNone(walletObject.address)
        self.assertIsNotNone(walletObject.privateKey)
        self.assertIsNotNone(walletObject.publicKey)
        self.assertEqual(walletObject.address, "EWMY8wPX7pgHJ37KBTiYYKZK5MBShogEtF")

    # Test case to create the vault yaml file in case we do not have one
    def test_create_vault(self):
        logging.info("Create Vault Testing", color="green")
        vaultObject = EvrmoreWallet(
                "/Satori/Lib/tests/api/wallet/vault.yaml",
                reserve=0.25,
                isTestnet=False)
        self.assertIsNotNone(vaultObject.address)
        self.assertIsNotNone(vaultObject.privateKey)
        self.assertIsNotNone(vaultObject.publicKey)

    # Test case to encrypt the wallet using the password
    def test_encrypt_wallet(self):
        logging.info("Testing wallet encryption", color="green")
        vaultObject = EvrmoreWallet(
            "/Satori/Lib/tests/api/wallet/vault.yaml",
            reserve=0.25,
            isTestnet=False,
            password=self.test_password)
        encrypted = vaultObject.encryptWallet({
            'privateKey': vaultObject.privateKey,
            'words': vaultObject.words,
            'entropy': vaultObject._entropy
        })

        self.assertIsNotNone(encrypted)
        self.assertNotEqual(vaultObject, encrypted)
        for key in ['entropy', 'privateKey', 'words']:
            self.assertIn(key, encrypted)
    
    # Test case to decrypt the wallet using the same password
    def test_decrypt_wallet(self):
        logging.info("Testing wallet decryption", color="green")
        vaultObject = EvrmoreWallet(
            "/Satori/Lib/tests/api/wallet/vault.yaml",
            reserve=0.25,
            isTestnet=False,
            password=self.test_password)
        encrypted = vaultObject.encryptWallet({
            'privateKey': vaultObject.privateKey,
            'words': vaultObject.words,
            'entropy': vaultObject._entropy
        })
        decrypted = vaultObject.decryptWallet(encrypted)
        self.assertIsNotNone(decrypted['privateKey'])
        self.assertEqual(decrypted['privateKey'], vaultObject.privateKey) 

    # Test case to sign the message using wallet sign method
    def test_sign_message(self):
        logging.info("Testing message signing", color="green")
        message = "This is a test message"
        walletObject = EvrmoreWallet(
            "/Satori/Lib/tests/api/wallet/wallet.yaml",
            reserve=0.25,
            isTestnet=False)
        signature = walletObject.sign(message)
        
        self.assertIsNotNone(signature)
        self.assertIsInstance(signature, bytes)
        logging.info(f"Signature: {signature.hex()}", color="blue")

    # Test case verify signature for the wallet base class
    def test_verify_signature(self):
        logging.info("Testing signature verification", color="green")
        message = "This is a test message"
        wrongMessage = "Wrong Message"
        walletObject = EvrmoreWallet(
            "/Satori/Lib/tests/api/wallet/wallet.yaml",
            reserve=0.25,
            isTestnet=False)
        signature = walletObject.sign(message)
        
        # Verify with wallet's own address
        is_valid = walletObject.verify(message, signature)
        self.assertTrue(is_valid)
        logging.info("Signature verified successfully with wallet's address", color="blue")
        
        # Verify with explicitly provided address
        is_valid = walletObject.verify(message, signature, walletObject.address)
        self.assertTrue(is_valid)
        logging.info("Signature verified successfully with provided address", color="blue")
        
        # Test with incorrect message
        is_valid = walletObject.verify(wrongMessage, signature)
        self.assertFalse(is_valid)
        logging.info("Incorrect message verification failed as expected", color="blue")
        
        # Test with incorrect signature
        wrongSignature = walletObject.sign(wrongMessage)
        is_valid = walletObject.verify(message, wrongSignature)
        self.assertFalse(is_valid)
        logging.info("Incorrect signature verification failed as expected", color="blue")

    # Test case to connect method and handshake method
    @patch('satorilib.api.wallet.evr.ElectrumXAPI')
    def test_connect_to_electrumx(self, mock_electrumx_api):
        logging.info("Testing connection to ElectrumX server", color="green")

        # Mock the ElectrumXAPI instance
        mock_api_instance = MagicMock()
        mock_electrumx_api.return_value = mock_api_instance
        mock_api_instance.handshake.return_value = None

        walletObject = EvrmoreWallet(
            "/Satori/Lib/tests/api/wallet/wallet.yaml",
            reserve=0.25,
            isTestnet=False)
        walletObject.connect()

        # Assertions calls
        mock_electrumx_api.assert_called_once_with(
            chain=walletObject.chain,
            address=walletObject.address,
            scripthash=walletObject.scripthash,
            servers=[
                '146.190.149.237:50002',
                '146.190.38.120:50002',
                'electrum1-mainnet.evrmorecoin.org:50002',
                'electrum2-mainnet.evrmorecoin.org:50002',
            ]
        )
        mock_api_instance.handshake.assert_called_once()
        self.assertIsNotNone(walletObject.electrumx)
        self.assertEqual(walletObject.electrumx, mock_api_instance)

        logging.info("Connection test completed successfully", color="green")

if __name__ == '__main__':
    unittest.main()
