
import unittest
# from unittest.mock import patch, MagicMock
from evrmore.wallet import CEvrmoreSecret, P2PKHEvrmoreAddress
from evrmore.core import CMutableTxOut, CScript
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET, OP_DROP
from satorilib.api.wallet.evr import EvrmoreWallet
from satorilib.api.wallet.wallet import  TransactionFailure
from satoriwallet import TxUtils, AssetTransaction
from satorilib.api.disk.wallet import WalletApi

class TestEvrmoreWallet(unittest.TestCase):

    def setUp(self):
        # Set up mock wallet configuration
        WalletApi.config = {
            '/Satori/Lib/tests/api/wallet/artifacts/wallet.yaml': {
                'entropy': '',
                'address': '',
                'privateKey': '',
                'publicKey': '',
                'scripthash': '',
                'words': ''
            }
        }
        # Initialize wallet for testing
        self.wallet = EvrmoreWallet(walletPath='/Satori/Lib/tests/api/wallet/artifacts/wallet.yaml')
        # Set up test wallet values
        self.wallet_values = {
            'entropy': '',
            'address': 'EXybyoeyn7uHWArTJA1iVddBKcAeF99kjb',
            'privateKey': '',
            'publicKey': '027aebc5ad86be6f9c0005809d1431388f09c3a2d0708f40f5f22ec82b4aaac4ae',
            'scripthash': '',
            'words': ''}
        self.vault = ''' TODO: an encrypted wallet '''
        self.vault_values = {}

    def test_symbol(self):
        # Verify wallet symbol is 'evr'
        self.assertEqual(self.wallet.symbol, 'evr')

    def test_chain(self):
        # Verify wallet chain is 'Evrmore'
        self.assertEqual(self.wallet.chain, 'Evrmore')

    def test_networkByte(self):
        # Verify network byte is correct
        self.assertEqual(self.wallet.networkByte, b'\x21')

    def test_networkByteP2PKH(self):
        # Verify P2PKH network byte is correct
        self.assertEqual(self.wallet.networkByteP2PKH, b'\x21')

    def test_networkByteP2SH(self):
        # Verify P2SH network byte is correct
        self.assertEqual(self.wallet.networkByteP2SH, b'\x5c')

    def test_satoriOriginalTxHash(self):
        # Verify Satori original transaction hash
        self.assertEqual(self.wallet.satoriOriginalTxHash, 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188')

    def test_generatePrivateKey(self):
        # Test private key generation
        private_key = self.wallet._generatePrivateKey()
        self.assertIsInstance(private_key, CEvrmoreSecret)
        wif = str(private_key)
        self.assertEqual(len(private_key), 33)
        self.assertIn(wif[0], ['L', 'K'])

    def test_generateAddress(self):
        # Test address generation
        address = self.wallet._generateAddress()
        self.assertIsInstance(address, P2PKHEvrmoreAddress)
        wif = str(address)
        self.assertEqual(len(address), 20)
        self.assertEqual(wif[0], 'E')

    def test_generateAddress_static(self):
        # Test static address generation
        result = self.wallet.generateAddress(self.wallet_values["publicKey"])
        self.assertEqual(result, self.wallet_values["address"])
  
    def test_generateScriptPubKeyFromAddress(self):
        # Test script public key generation from address
        script_pubkey = self.wallet._generateScriptPubKeyFromAddress(self.wallet_values["address"])
        self.assertIsInstance(script_pubkey, CScript)
        script_ops = list(script_pubkey)
        # Check the structure of the script
        self.assertEqual(script_ops[0], OP_DUP)
        self.assertEqual(script_ops[1], OP_HASH160)
        self.assertEqual(len(script_ops[2]), 20)  # 20-byte pubkey hash
        self.assertEqual(script_ops[3], OP_EQUALVERIFY)
        self.assertEqual(script_ops[4], OP_CHECKSIG)
        # Verify the script starts with the expected OP_DUP and OP_HASH160 bytes
        self.assertTrue(bytes(script_pubkey).startswith(b'\x76\xa9\x14'))
        
        # Verify the script ends with the expected OP_EQUALVERIFY and OP_CHECKSIG bytes
        self.assertTrue(bytes(script_pubkey).endswith(b'\x88\xac'))

    def test_sign(self):
        # Test signing functionality
        result = self.wallet.sign(self.wallet_values["words"])
        self.assertEqual(len(result),88)
        self.assertTrue(bytes(result).startswith(b'I') or bytes(result).startswith(b'H') )

    def test_verify(self):
        # Test signature verification
        result = self.wallet.verify(self.wallet_values["words"],self.wallet.sign(self.wallet_values["words"]))
        self.assertTrue(result)

    def test_checkSatoriValue(self):
        # Test Satori value checking
        Script =CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(self.wallet_values["address"]),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.wallet.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(1))),
                    OP_DROP])
        txt_out = CMutableTxOut(0,Script)
        result = self.wallet._checkSatoriValue(txt_out)
        self.assertTrue(result)

    def test_compileSatoriChangeOutput(self):
        # Test Satori change output compilation
        result = self.wallet._compileSatoriChangeOutput(100, 150)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)
        self.assertIsInstance(result.scriptPubKey, CScript)
        
        # Verify script structure
        script = result.scriptPubKey
        self.assertEqual(script[0], OP_DUP)
        self.assertEqual(script[1], OP_HASH160)
        self.assertEqual(script[23], OP_EQUALVERIFY)
        self.assertEqual(script[24], OP_CHECKSIG)
        self.assertEqual(script[25], OP_EVR_ASSET)
        self.assertEqual(script[-1], OP_DROP)

        # Test case: Large change value
        result = self.wallet._compileSatoriChangeOutput(1000000, 2000000)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)

        # Test case: Minimum change value
        result = self.wallet._compileSatoriChangeOutput(100, 101)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)

    def test_compileSatoriChangeOutput_no_change(self):
        # Test compilation with no change
        result = self.wallet._compileSatoriChangeOutput(100, 100)
        self.assertIsNone(result)

    def test_compileSatoriChangeOutput_negative_change(self):
        # Test compilation with negative change (should raise exception)
        with self.assertRaises(TransactionFailure):
            self.wallet._compileSatoriChangeOutput(200, 100)

if __name__ == '__main__':
    unittest.main()
