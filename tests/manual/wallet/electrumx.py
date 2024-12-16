from satorilib.wallet import EvrmoreWallet
w = EvrmoreWallet('/Satori/Neuron/wallet/wallet-2.yaml')
x = w.electrumx.api.getBalance('42ad2f3eaa7805cf5d5f04a2a136a30bdcc7add0506497e6bb5f5a90d767cd58', True)
x
w.electrumx.responses
x = w.subscribeToScripthashActivity()
x
