
from satorilib.api.disk import Cache  # Disk
from satorilib.api.wallet import RavencoinWallet
from satorineuron import config
Cache.setConfig(config)
vault = RavencoinWallet(
    config.walletPath('vault.yaml'),
    reserve=0.01, isTestnet=True, password='123456789')
wallet = RavencoinWallet(
    config.walletPath('wallet.yaml'),
    reserve=0.01, isTestnet=True)
vault()
wallet.address
vault.address
wallet()
