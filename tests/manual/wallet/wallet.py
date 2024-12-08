from ravencoin.wallet import CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL
from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from satorilib import logging
from satorineuron import config
from satorilib.disk import Disk
from satorilib.wallet import RavencoinWallet
from satorilib.wallet import EvrmoreWallet
Disk.setConfig(config)
r = RavencoinWallet('/Satori/Neuron/wallet/wallet.yaml')
r()
e = EvrmoreWallet('/Satori/Neuron/wallet/wallet-value.yaml')
e()
x = EvrmoreWallet('/tmp/testwallet.yaml')
x()
a = RavencoinWallet('/tmp/testwalletRVN.yaml')
a()
