import unittest
import os
import json
from unittest.mock import patch, MagicMock
from evrmore.wallet import CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core import CMutableTransaction, CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.script import OP_HASH160, OP_EQUAL
from evrmore.core.scripteval import EvalScriptError
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
        address, redeem_script = self.wallet.generate_multi_party_p2sh_address(public_keys, required_signatures=2)
        self.assertIsInstance(address, P2SHEvrmoreAddress)
        self.assertIsInstance(redeem_script, CScript)
    
    def test_add_public_key(self):
        """ Test adding a public key to the wallet. """
        public_key = CEvrmoreSecret.from_secret_bytes(os.urandom(32)).pub
        self.wallet.add_public_key(public_key)
        self.assertIn(public_key, self.wallet.public_keys)
    
if __name__ == '__main__':
    unittest.main()
