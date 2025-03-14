from satorilib.electrumx import Electrumx
from satorilib.wallet import EvrmoreWallet
from satorineuron import config

def a(**kwargs):
    print(kwargs)

wallet = EvrmoreWallet(
    walletPath=config.walletPath('wallet.yaml'),
    kind='wallet',
    reserve=0.25,
    isTestnet=False,
    electrumx=None,
    useElectrumx=True,
    balanceUpdatedCallback=a)

wallet.getBalances()
wallet.updateBalances()


vault = EvrmoreWallet(
    walletPath=config.walletPath('vault.yaml'),
    kind='vault',
    reserve=0.25,
    isTestnet=False,
    password='password',
    electrumx=None,
    useElectrumx=True,
    balanceUpdatedCallback=a)

vault.getBalances()
vault.updateBalances()


import threading
threading.Thread(target=vault.get).start()
threading.Thread(target=vault.getReadyToSend).start()
