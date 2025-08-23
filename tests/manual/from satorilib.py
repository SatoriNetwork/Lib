from satorilib.wallet import EvrmoreWallet
from satorilib.electrumx import Electrumx
w = EvrmoreWallet.create(hostPort='electrumx.satorinet.ie')
w
from satorilib import logging
logging.setup(level=logging.DEBUG)
w = EvrmoreWallet.create(hostPort='electrumx.satorinet.ie')
