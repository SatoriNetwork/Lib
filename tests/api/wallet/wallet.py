'''
testing notes:

wallet code has basically 4 typtes of functionality:
    1. init wallet process
        - load
        - crete
        - encrypt
    2. signing / verification
    3. connect process
        - connects to electrumx servers to get data, or broadcast data
        - saves data to wallet object
    4. generating a transaction
        - various nuanced types of transactions
            - evrmore only (EVR)
            - SATORI only (asset)
            - both
            - etc...
'''
# import unittest
# from unittest.mock import MagicMock, patch
# from satoriwallet.lib import connection
# from satoriwallet import TxUtils, Validate
# from satorilib.api import system
# from satorilib.api.disk.wallet import WalletApi
# # from tests.api.wallet.wallet import Wallet, TransactionResult, TransactionFailure

# class TransactionResult:
#     def __init__(self, success, result=None, tx=None, msg=None):
#         self.success = success
#         self.result = result
#         self.tx = tx
#         self.msg = msg

# class TransactionFailure(Exception):
#     pass

# class Wallet:
#     def __init__(self, walletPath):
#         self.walletPath = walletPath
#         self.currency = 0
#         self.reserve = 0
#         self._entropyStr = ''
#         self.words = ''
#         self.privateKey = ''
#         self.publicKey = ''
#         self.scripthash = ''
#         self.address = ''

#     def authPayload(self):
#         return connection.authPayload()

#     def registerPayload(self):
#         auth_payload = connection.authPayload()
#         device_payload = system.devicePayload()
#         return {**auth_payload, **device_payload}

#     def loadRaw(self):
#         data = WalletApi.load(self.walletPath)
#         if data:
#             self._entropyStr = data['entropy']
#             self.words = data['words']
#             self.publicKey = data['publicKey']
#             self.privateKey = data['privateKey']
#             self.address = data['wallet']['address']
#             self.scripthash = data['scripthash']
#             return True
#         return False

#     def save(self):
#         data = {
#             'entropy': self._entropyStr,
#             'words': self.words,
#             'publicKey': self.publicKey,
#             'privateKey': self.privateKey,
#             'wallet': {'address': self.address},
#             'scripthash': self.scripthash
#         }
#         WalletApi.save(self.walletPath, data)

#     def typicalNeuronTransaction(self, amount, address, sweep=False):
#         if sweep:
#             if self.currency > self.reserve:
#                 return TransactionResult(True, self.sendAllTransaction())
#             elif self.currency < self.reserve:
#                 return TransactionResult(True, 'try again', None, 'creating partial, need feeSatsReserved.')
#         else:
#             try:
#                 return TransactionResult(True, self.satoriTransaction(amount, address))
#             except TransactionFailure as e:
#                 return TransactionResult(False, None, None, f'Send Failed: {str(e)}')

#     def sendAllTransaction(self):
#         # Placeholder for sendAllTransaction method
#         return 'test_tx_hash'
    
#     def satoriTransaction(self, amount, address):
#         # Placeholder for satoriTransaction method
#         return 'test_tx_hash'
    
# class TestWallet(unittest.TestCase):

#     def setUp(self):
#         self.wallet = Wallet(walletPath="test_wallet.json")

#     @patch('satoriwallet.lib.connection.authPayload')
#     def test_authPayload(self, mock_authPayload):
#         mock_authPayload.return_value = {"test": "payload"}
#         result = self.wallet.authPayload()
#         self.assertEqual(result, {"test": "payload"})  # Changed from string to dict

#     @patch('satoriwallet.lib.connection.authPayload')
#     @patch('satorilib.api.system.devicePayload')
#     def test_registerPayload(self, mock_devicePayload, mock_authPayload):
#         mock_authPayload.return_value = {"auth": "payload"}
#         mock_devicePayload.return_value = {"device": "payload"}
#         result = self.wallet.registerPayload()
#         self.assertEqual(result, {"auth": "payload", "device": "payload"})  # Changed from string to dict

#     @patch('satorilib.api.disk.wallet.WalletApi.load')
#     def test_loadRaw(self, mock_load):
#         mock_load.return_value = {
#             'entropy': 'test_entropy',
#             'words': 'test words',
#             'publicKey': 'test_public_key',
#             'privateKey': 'test_private_key',
#             'wallet': {'address': 'test_address'},
#             'scripthash': 'test_scripthash'
#         }
#         result = self.wallet.loadRaw()
#         self.assertTrue(result)
#         self.assertEqual(self.wallet._entropyStr, 'test_entropy')

#     @patch('satorilib.api.disk.wallet.WalletApi.save')
#     def test_save(self, mock_save):
#         self.wallet._entropyStr = 'test_entropy'
#         self.wallet.words = 'test words'
#         self.wallet.privateKey = 'test_private_key'
#         self.wallet.publicKey = 'test_public_key'
#         self.wallet.scripthash = 'test_scripthash'
#         self.wallet.address = 'test_address'
#         self.wallet.save()
#         mock_save.assert_called_once()

#     def test_typicalNeuronTransaction_sweep(self):
#         self.wallet.currency = 100000000  # 1 EVR
#         self.wallet.reserve = 10000000  # 0.1 EVR
#         self.wallet.sendAllTransaction = MagicMock(return_value='test_tx_hash')
#         result = self.wallet.typicalNeuronTransaction(0, 'test_address', sweep=True)
#         self.assertEqual(result.result, 'test_tx_hash')
#         self.assertTrue(result.success)

#     def test_typicalNeuronTransaction_partial(self):
#         self.wallet.currency = 1000000  # 0.01 EVR
#         self.wallet.reserve = 10000000  # 0.1 EVR
#         result = self.wallet.typicalNeuronTransaction(0, 'test_address', sweep=True)
#         self.assertEqual(result.result, 'try again')
#         self.assertTrue(result.success)
#         self.assertIsNone(result.tx)
#         self.assertEqual(result.msg, 'creating partial, need feeSatsReserved.')

#     def test_typicalNeuronTransaction_normal(self):
#         self.wallet.currency = 100000000  # 1 EVR
#         self.wallet.reserve = 10000000  # 0.1 EVR
#         self.wallet.satoriTransaction = MagicMock(return_value='test_tx_hash')
#         result = self.wallet.typicalNeuronTransaction(1000000, 'test_address')
#         self.assertEqual(result.result, 'test_tx_hash')
#         self.assertTrue(result.success)

#     def test_typicalNeuronTransaction_failure(self):
#         self.wallet.currency = 100000000  # 1 EVR
#         self.wallet.reserve = 10000000  # 0.1 EVR
#         self.wallet.satoriTransaction = MagicMock(side_effect=TransactionFailure('Test failure'))
#         result = self.wallet.typicalNeuronTransaction(1000000, 'test_address')
#         self.assertIsNone(result.result)
#         self.assertFalse(result.success)
#         self.assertEqual(result.msg, 'Send Failed: Test failure')

# if __name__ == '__main__':
#     unittest.main()
