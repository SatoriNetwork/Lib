import unittest
import os
import json
from unittest.mock import patch, MagicMock
from evrmore.wallet import CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core import CMutableTransaction, CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.script import OP_HASH160, OP_EQUAL
from evrmore.core.transaction import CMultiSigTransaction
from satorilib.wallet.evrmore.walletsh import EvrmoreP2SHWallet  # Replace with the actual import path

class TestEvrmoreP2SHWallet(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """ Set up class-level resources. """
        cls.wallet_path = 'test_wallet.json'
    
    def setUp(self):
        """ Create a new instance of the EvrmoreP2SHWallet before each test. """
        self.wallet = EvrmoreP2SHWallet(wallet_path=self.wallet_path, is_testnet=True,)
    
    def tearDown(self):
        """ Clean up after each test. """
        if os.path.exists(self.wallet_path):
            os.remove(self.wallet_path)
    
    def test_wallet_initialization(self):
        """ Test wallet is initialized properly. """
        self.assertIsInstance(self.wallet, EvrmoreP2SHWallet)
        self.assertTrue(self.wallet.is_testnet)
        # self.assertEqual(self.wallet.mode, 'single')
    
    def test_generate_single_party_p2sh_address(self):
        """ Test single-party P2SH address generation. """
        address, redeem_script = self.wallet.generate_single_party_p2sh_address(num_keys=3, required_signatures=2)
        self.assertIsInstance(address, P2SHEvrmoreAddress)
        self.assertIsInstance(redeem_script, CScript)
        self.assertEqual(len(self.wallet.private_keys), 3)
        self.assertEqual(len(self.wallet.public_keys), 3)
    
    def test_generate_multi_party_p2sh_address(self):
        """ Test multi-party P2SH address generation. """
        public_keys = [CEvrmoreSecret.from_secret_bytes(os.urandom(32)).pub for _ in range(3)]
        # print(public_keys)
        address, redeem_script = self.wallet.generate_multi_party_p2sh_address(public_keys, required_signatures=2)
        self.assertIsInstance(address, P2SHEvrmoreAddress)
        self.assertIsInstance(redeem_script, CScript)
    
    def test_add_public_key(self):
        """ Test adding a public key to the wallet. """
        public_key = CEvrmoreSecret.from_secret_bytes(os.urandom(32)).pub
        self.wallet.add_public_key(public_key)
        self.assertIn(public_key, self.wallet.public_keys)
        
    # def test_create_unsigned_transaction(self):
    #     """ Test creating an unsigned transaction. """
    #     txid = "e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5"
    #     vout_index = 0
    #     amount = 1000000  # 0.01 EVR
    #     redeem_script_hex = "522102abcdef2102fedcba2103aabbcc2103aabbcc2103aabbcc53ae"
    #     redeem_script = CScript(bytes.fromhex(redeem_script_hex))
        
    #     tx = self.wallet.create_unsigned_transaction(txid, vout_index, amount, redeem_script)
        
    #     self.assertIsNotNone(tx)
    #     self.assertIsInstance(tx, CMutableTransaction)
    #     self.assertEqual(len(tx.vin), 1)
    #     self.assertEqual(len(tx.vout), 1)
    #     self.assertEqual(tx.vout[0].nValue, amount)
    #     self.assertTrue(tx.vout[0].scriptPubKey.is_p2sh())

    # def test_sign_transaction(self):
    #     """ Test signing a transaction. """
    #     txid = "e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5"
    #     vout_index = 0
    #     amount = 1000000  # 0.01 EVR
    #     redeem_script_hex = "522102abcdef2102fedcba2103aabbcc2103aabbcc2103aabbcc53ae"
    #     redeem_script = CScript(bytes.fromhex(redeem_script_hex))
        
    #     # Create unsigned transaction
    #     tx = self.wallet.create_unsigned_transaction(txid, vout_index, amount, redeem_script)
        
    #     # Sign transaction
    #     signed_tx = self.wallet.sign_transaction(tx)
        
    #     self.assertIsNotNone(signed_tx)
    #     self.assertIsInstance(signed_tx, CMultiSigTransaction)
    #     self.assertIsNotNone(signed_tx.vin[0].scriptSig)

    # def test_invalid_redeem_script(self):
    #     """ Test create unsigned transaction with an invalid redeem script. """
    #     txid = "e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5"
    #     vout_index = 0
    #     amount = 1000000  # 0.01 EVR
    #     redeem_script = "INVALID_SCRIPT"

    #     with self.assertRaises(ValueError):
    #         self.wallet.create_unsigned_transaction(txid, vout_index, amount, redeem_script)

    # def test_large_redeem_script(self):
    #     """ Test create unsigned transaction with large redeem script (> 520 bytes). """
    #     txid = "e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5"
    #     vout_index = 0
    #     amount = 1000000  # 0.01 EVR
    #     large_redeem_script = CScript(os.urandom(600))  # 600-byte redeem script

    #     with self.assertRaises(ValueError):
    #         self.wallet.create_unsigned_transaction(txid, vout_index, amount, large_redeem_script)

    # def test_missing_redeem_script(self):
    #     """ Test signing a transaction without a redeem script. """
    #     txid = "e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5e3c8d5f5b91e7f30f6c4c3c2d9e5b8d5"
    #     vout_index = 0
    #     amount = 1000000  # 0.01 EVR
    #     redeem_script_hex = "522102abcdef2102fedcba2103aabbcc2103aabbcc2103aabbcc53ae"
    #     redeem_script = CScript(bytes.fromhex(redeem_script_hex))
        
    #     tx = self.wallet.create_unsigned_transaction(txid, vout_index, amount, redeem_script)
        
    #     self.wallet.redeem_script = None  # Simulate missing redeem script
    #     with self.assertRaises(ValueError):
    #         self.wallet.sign_transaction(tx)
        
    
if __name__ == '__main__':
    unittest.main()
