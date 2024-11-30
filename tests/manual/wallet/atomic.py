from ravencoin.core import CMutableTransaction
from satorineuron import config
from satorilib.wallet import RavencoinWallet
from satorilib.disk import Cache  # Disk
Cache.setConfig(config)

VERSION = '0.0.5'
MOTO = 'Let your workings remain a mystery, just show people the results.'

wallet = RavencoinWallet(
    config.walletPath('wallet.yaml'),
    reserve=0.01, isTestnet=True)()
# wallet.get()
wallet.balance
tx = wallet.satoriOnlyTransaction(1, 'RX4FbdramqY6qu7twwGCLsX6NyVwkwCevY')

print(tx)
# serialTx = tx.serialize()
# print(serialTx)
deserialTx = CMutableTransaction.deserialize(tx)
# print(deserialTx)
# print(tx == deserialTx)
# print(wallet._txToHex(tx))
# print(wallet._txToHex(deserialTx))
# print(wallet._txToHex(tx) == wallet._txToHex(deserialTx))
#
t = wallet.satoriOnlyTransactionCompleted(
    tx, 'RX4FbdramqY6qu7twwGCLsX6NyVwkwCevY')
