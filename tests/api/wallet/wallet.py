import unittest
from unittest.mock import patch, mock_open
from satorilib.api.wallet.wallet import Wallet
from satorilib.api.wallet import RavencoinWallet, EvrmoreWallet
from satorilib import logging

# Test Cases for satori wallet base class
class TestWallet(unittest.TestCase):
    def setUp(self):
        self.test_password = "test_password"

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

    def test_create_vault(self):
        logging.info("Create Vault Testing", color="green")
        vaultObject = EvrmoreWallet(
                "/Satori/Lib/tests/api/wallet/vault.yaml",
                reserve=0.25,
                isTestnet=False)
        self.assertIsNotNone(vaultObject.address)
        self.assertIsNotNone(vaultObject.privateKey)
        self.assertIsNotNone(vaultObject.publicKey)

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

if __name__ == '__main__':
    unittest.main()