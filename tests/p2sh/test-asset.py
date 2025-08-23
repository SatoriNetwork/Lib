import datetime as dt
from satorilib.wallet.evrmore.wallet import EvrmoreWallet
from satorilib.wallet.evrmore.utils.multisig import MultisigUtils

test1 = EvrmoreWallet.create('/Satori/Neuron/wallet/wallet-test-1.yaml')
test2 = EvrmoreWallet.create('/Satori/Neuron/wallet/wallet-test-2.yaml')
test1.get()
test2.get()
test1
test2
test1.getReadyToSend()
test2.getReadyToSend()

wallet = EvrmoreWallet.create('/Satori/Neuron/wallet/wallet.yaml')
wallet.get()
wallet.getReadyToSend()
wallet

wallet.satoriTransaction(address=test1.address, amount=0.004)

### MINTING ###

redeem_scripts, timestamp = MultisigUtils.create(test1, test2, days=2, amount=.0001)
redeem_scripts = MultisigUtils.send(test1, redeem_scripts, timestamp)

mints = MultisigUtils.getMints('scripts-2025-08-16 15:23:51.json')
mint = mints[dt.datetime(2025, 8, 16, 16, 0, tzinfo=dt.timezone.utc)]
tx_unlock = test2.simpleTimeLockTransaction(address=test2.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'],fundingVout=mint['funding_vout'],redeemScript=mint['redeem_script'],timedRelease=True, date=mint['original_params']['locktime'])
tx_unlock

address=test2.address 
lockedAmount=mint['amount'] 
fundingTxId=mint['funding_txid']
fundingVout=mint['funding_vout']
redeemScript=mint['redeem_script']
timedRelease=True
date=mint['original_params']['locktime']

mints = MultisigUtils.getMints('scripts-2025-08-16 15:23:51.json')
mint = mints[dt.datetime(2025, 8, 16, 0, 0, tzinfo=dt.timezone.utc)]
tx_unlock = test1.simpleTimeLockTransaction(address=test1.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'],fundingVout=mint['funding_vout'],redeemScript=mint['redeem_script'],timedRelease=False, date=None)
tx_unlock

address=test1.address
lockedAmount=mint['amount']
feeOverride=250000
fundingTxId=mint['funding_txid']
fundingVout=mint['funding_vout']
redeemScript=mint['redeem_script']
timedRelease=False
date=None