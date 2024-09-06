import unittest
from unittest.mock import patch, MagicMock
from base64 import b64encode, b64decode
from eth_keys import keys
from eth_account import Account
from eth_account.messages import encode_defunct
from satorilib.api.disk.wallet import WalletApi
from satorilib import secret
from satorilib.api.wallet.eth import EthereumWallet

class TestEthereumWallet(unittest.TestCase):

    def setUp(self):
        self.wallet = EthereumWallet('/Satori/Neuron/wallet/vault.yaml', 'test_password')

    def test_symbol(self):
        self.assertEqual(self.wallet.symbol, 'eth')

    def test_chain(self):
        self.assertEqual(self.wallet.chain, 'Ethereum')

    @patch('satorilib.api.disk.wallet.WalletApi.load')
    def test_initRaw(self, mock_load):
        mock_load.return_value = {'entropy': b64encode(b'test_entropy').decode('utf-8')}
        self.assertTrue(self.wallet.initRaw())
        self.assertEqual(self.wallet._entropyStr, b64encode(b'test_entropy').decode('utf-8'))
        self.assertEqual(self.wallet._entropy, b'test_entropy')

    @patch('satorilib.api.disk.wallet.WalletApi.load')
    @patch.object(EthereumWallet, 'decryptWallet')
    @patch.object(EthereumWallet, '_generateAccount')
    @patch.object(EthereumWallet, '_generatePublicKey')
    def test_load(self, mock_gen_pubkey, mock_gen_account, mock_decrypt, mock_load):
        mock_load.return_value = {'entropy': b64encode(b'test_entropy').decode('utf-8')}
        mock_decrypt.return_value = {'entropy': b64encode(b'test_entropy').decode('utf-8')}
        mock_account = MagicMock()
        mock_account.key.to_0x_hex.return_value = 'test_private_key'
        mock_account.address = 'test_address'
        mock_gen_account.return_value = mock_account
        mock_gen_pubkey.return_value = 'test_public_key'

        self.assertTrue(self.wallet.load())
        self.assertEqual(self.wallet._entropyStr, b64encode(b'test_entropy').decode('utf-8'))
        self.assertEqual(self.wallet._entropy, b'test_entropy')
        self.assertEqual(self.wallet.publicKey, 'test_public_key')
        self.assertEqual(self.wallet.privateKey, 'test_private_key')
        self.assertEqual(self.wallet.address, 'test_address')

    @patch('satorilib.secret.decryptMapValues')
    def test_decryptWallet(self, mock_decrypt):
        mock_decrypt.return_value = {'decrypted': 'data'}
        result = self.wallet.decryptWallet({'encrypted': 'data'})
        self.assertEqual(result, {'decrypted': 'data'})

    @patch('satorilib.api.disk.wallet.WalletApi.load')
    def test_getRaw(self, mock_load):
        mock_load.return_value = {'test': 'data'}
        result = self.wallet.getRaw()
        self.assertEqual(result, {'test': 'data'})

    @patch.object(EthereumWallet, 'generateAccount')
    def test_generateAccount(self, mock_gen_account):
        mock_account = MagicMock()
        mock_gen_account.return_value = mock_account
        self.wallet._entropy = b'test_entropy'
        result = self.wallet._generateAccount()
        self.assertEqual(result, mock_account)
        mock_gen_account.assert_called_once_with(b'test_entropy')

    @patch('eth_account.Account.from_key')
    def test_generateAccount_static(self, mock_from_key):
        mock_account = MagicMock()
        mock_from_key.return_value = mock_account
        result = EthereumWallet.generateAccount(b'test_entropy')
        self.assertEqual(result, mock_account)
        mock_from_key.assert_called_once_with(b'test_entropy')

    def test_generatePublicKey(self):
        self.wallet.account = MagicMock()
        self.wallet.account.key = 'test_key'
        with patch('eth_keys.keys.PrivateKey') as mock_private_key:
            mock_public_key = MagicMock()
            mock_private_key.return_value.public_key = mock_public_key
            result = self.wallet._generatePublicKey()
            self.assertEqual(result, mock_public_key)
            mock_private_key.assert_called_once_with('test_key')

    @patch('eth_account.Account.sign_message')
    def test_sign(self, mock_sign_message):
        mock_signature = MagicMock()
        mock_sign_message.return_value = mock_signature
        self.wallet.account = MagicMock()
        result = self.wallet.sign('test_message')
        self.assertEqual(result, mock_signature)
        mock_sign_message.assert_called_once()

    @patch('eth_account.Account.recover_message')
    def test_verify(self, mock_recover_message):
        mock_recover_message.return_value = 'test_address'
        self.wallet.address = 'test_address'
        result = self.wallet.verify('test_message', b'test_signature')
        self.assertTrue(result)
        mock_recover_message.assert_called_once()

if __name__ == '__main__':
    unittest.main()
