
import unittest
from unittest.mock import patch, MagicMock
from evrmore.core import CMutableTxOut, CScript
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET, OP_DROP
from satorilib.api.wallet.evr import EvrmoreWallet
from satorilib.api.wallet.wallet import Wallet,TransactionFailure, TransactionResult

class TestEvrmoreWallet(unittest.TestCase):

    @patch('satorilib.api.wallet.wallet.WalletApi.config', new_callable=MagicMock)
    @patch('satorilib.api.wallet.wallet.Wallet.loadRaw', return_value=True)
    def setUp(self, mock_loadRaw,mock_config):
        # Mock the configuration to return a valid dictionary
        mock_config.get.return_value = {'some_key': 'some_value'}
        self.wallet = EvrmoreWallet(walletPath='/Satori/Neuron/wallet/wallet.yaml')
        self.wallet._entropy = b'test_entropy'

    def test_symbol(self):
        self.assertEqual(self.wallet.symbol, 'evr')

    def test_chain(self):
        self.assertEqual(self.wallet.chain, 'Evrmore')

    def test_networkByte(self):
        self.assertEqual(self.wallet.networkByte, b'\x21')

    def test_networkByteP2PKH(self):
        self.assertEqual(self.wallet.networkByteP2PKH, b'\x21')

    def test_networkByteP2SH(self):
        self.assertEqual(self.wallet.networkByteP2SH, b'\x5c')

    def test_satoriOriginalTxHash(self):
        self.assertEqual(self.wallet.satoriOriginalTxHash, 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188')

    @patch('evrmore.wallet.CEvrmoreSecret.from_secret_bytes')
    def test_generatePrivateKey(self, mock_from_secret_bytes):
        mock_private_key = MagicMock()
        mock_from_secret_bytes.return_value = mock_private_key
        self.wallet._entropy = b'test_entropy'
        result = self.wallet._generatePrivateKey()
        # print(type(result))
        # print(type(mock_private_key))
        mock_from_secret_bytes.assert_called_once_with(b'test_entropy')
        self.assertEqual(result, mock_private_key)
        

    @patch('evrmore.wallet.P2PKHEvrmoreAddress.from_pubkey')
    def test_generateAddress(self, mock_from_pubkey):
        mock_address = MagicMock()
        mock_from_pubkey.return_value = mock_address
        self.wallet._privateKeyObj = MagicMock()
        self.wallet._privateKeyObj.pub = b'test_pubkey'
        result = self.wallet._generateAddress()
        mock_from_pubkey.assert_called_once_with(b'test_pubkey')
        self.assertEqual(result, mock_address)

    @patch('evrmore.wallet.P2PKHEvrmoreAddress.from_pubkey')
    def test_generateAddress_static(self, mock_from_pubkey):
        mock_address = MagicMock()
        mock_from_pubkey.return_value = mock_address
        mock_address.__str__.return_value = 'test_address'
        result = EvrmoreWallet.generateAddress(b'test_pubkey')
        mock_from_pubkey.assert_called_once_with(b'test_pubkey')
        self.assertEqual(result, 'test_address')

    # @patch('evrmore.wallet.CEvrmoreAddress')
    # def test_generateScriptPubKeyFromAddress(self, mock_CEvrmoreAddress):
    #     mock_address = MagicMock()
    #     mock_CEvrmoreAddress.return_value = mock_address
    #     mock_scriptPubKey = MagicMock()
    #     mock_address.to_scriptPubKey.return_value = mock_scriptPubKey
    #     result = self.wallet._generateScriptPubKeyFromAddress('mock_address')
    #     mock_CEvrmoreAddress.assert_called_once_with('mock_address')
    #     mock_address.to_scriptPubKey.assert_called_once()
    #     self.assertEqual(result, mock_scriptPubKey)

    @patch('satorilib.api.wallet.evr.CEvrmoreAddress')
    def test_generateScriptPubKeyFromAddress(self, mock_CEvrmoreAddress):
        test_address = "EXAMPLEEvrmoreAddressXYZ123"
        expected_script_pubkey = b'example_script_pubkey'
        
        mock_address = MagicMock()
        mock_address.to_scriptPubKey.return_value = expected_script_pubkey
        mock_CEvrmoreAddress.return_value = mock_address
        
        result = self.wallet._generateScriptPubKeyFromAddress(test_address)
        
        mock_CEvrmoreAddress.assert_called_once_with(test_address)
        mock_address.to_scriptPubKey.assert_called_once()
        self.assertEqual(result, expected_script_pubkey)

    @patch('satorilib.api.wallet.evr.evrmore.signMessage')
    def test_sign(self, mock_signMessage):
        mock_signMessage.return_value = b'test_signature'
        self.wallet._privateKeyObj = MagicMock()
        result = self.wallet.sign('test_message')
        mock_signMessage.assert_called_once_with(self.wallet._privateKeyObj, 'test_message')
        self.assertEqual(result, b'test_signature')

    @patch('satorilib.api.wallet.evr.evrmore.verify')
    def test_verify(self, mock_verify):
        mock_verify.return_value = True
        self.wallet.address = 'test_address'
        result = self.wallet.verify('test_message', b'test_signature')
        mock_verify.assert_called_once_with(address='test_address', message='test_message', signature=b'test_signature')
        self.assertTrue(result)


    @patch('satorilib.api.wallet.wallet.WalletApi.config', new_callable=MagicMock)
    @patch('satorilib.api.wallet.evr.AssetTransaction.satoriHex', return_value='')  # 'satori' in hex
    @patch('satorilib.api.wallet.evr.TxUtils.padHexStringTo8Bytes', return_value='')
    @patch('satorilib.api.wallet.evr.TxUtils.intToLittleEndianHex', return_value='')
    @patch('satorilib.api.wallet.evr.TxUtils.asSats', return_value=100000)  # 0.001 EVR in satoshis
    def test_checkSatoriValue(self, mock_asSats, mock_intToLittleEndianHex, mock_padHexStringTo8Bytes, mock_satoriHex, mock_config):
        # Setup
        mock_config.get.return_value = {'some_key': 'some_value'}
        self.wallet = EvrmoreWallet(walletPath='/Satori/Neuron/wallet/wallet.yaml')
        self.wallet._entropy = b'test_entropy'
        self.wallet.satoriFee = 0.001
        # self.wallet.symbol = 'EVR'  # Ensure the symbol is set
        # print(f"Wallet symbol: {self.wallet.symbol}")
        # Construct the expected Satori asset bytes
        expected_satori_bytes = bytes.fromhex('')

        # Test case 1: Valid Satori output
        valid_script = CScript([
            OP_DUP, OP_HASH160, b'\x00'*20, OP_EQUALVERIFY, OP_CHECKSIG,
            OP_EVR_ASSET,
            int.from_bytes(expected_satori_bytes, 'big'),  # Expected Satori asset bytes
            OP_DROP
        ])
        valid_output = CMutableTxOut(0, valid_script)
        result = self.wallet._checkSatoriValue(valid_output)
        # print(f"_checkSatoriValue result: {result}")
        self.assertTrue(result)
    

    def test_compileSatoriChangeOutput(self):
        self.wallet.address = 'test_address'
        with patch('satorilib.api.wallet.evr.TxUtils.addressToH160Bytes') as mock_addressToH160Bytes, \
             patch('satorilib.api.wallet.evr.AssetTransaction.satoriHex') as mock_satoriHex, \
             patch('satorilib.api.wallet.evr.TxUtils.padHexStringTo8Bytes') as mock_padHexStringTo8Bytes, \
             patch('satorilib.api.wallet.evr.TxUtils.intToLittleEndianHex') as mock_intToLittleEndianHex:
            
            mock_addressToH160Bytes.return_value = b'\x00' * 20
            mock_satoriHex.return_value = '7361746f72695f686578'
            mock_padHexStringTo8Bytes.return_value = '00000000'
            mock_intToLittleEndianHex.return_value = '00000000'
            
            result = self.wallet._compileSatoriChangeOutput(100, 200)
            
            self.assertIsInstance(result, CMutableTxOut)
            self.assertEqual(result.nValue, 0)
            self.assertIsInstance(result.scriptPubKey, CScript)

    def test_compileSatoriChangeOutput_no_change(self):
        result = self.wallet._compileSatoriChangeOutput(100, 100)
        self.assertIsNone(result)

    def test_compileSatoriChangeOutput_negative_change(self):
        with self.assertRaises(TransactionFailure):
            self.wallet._compileSatoriChangeOutput(200, 100)

if __name__ == '__main__':
    unittest.main()