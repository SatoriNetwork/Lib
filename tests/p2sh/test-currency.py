from satorilib.wallet.evrmore.wallet import EvrmoreWallet
test1 = EvrmoreWallet.create('/Satori/Neuron/wallet/wallet-test-1.yaml')
test2 = EvrmoreWallet.create('/Satori/Neuron/wallet/wallet-test-2.yaml')
test1.get()
test2.get()
test1
test2
test1.getReadyToSend()
test2.getReadyToSend()

### CURRENCY TRANSACTIONS ###

# to self
test1.currencyTransaction(address=test1.address, amount=1)

# to other
test1.currencyTransaction(address=test2.address, amount=1)


### SATORI TRANSACTIONS ###

# to self
test1.satoriTransaction(amount=1, address=test1.address)

# to other
test1.satoriTransaction(amount=1, address=test2.address)

### MINTING ###

# copy 1-code
redeem_scripts, timestamp = create(test1, test2, days=2, amount=1)
redeem_scripts = send(test1, redeem_scripts, timestamp)

# to self
test1.mintingTransactionCurrency(address=test1.address, amount=1)

# to other
test1.mintingTransactionCurrency(address=test2.address, amount=1)



#........ COPY MINTS .................


mints = get_mints('scripts-2025-08-15 02:07:44.json')
mint = mints[dt.datetime(2025, 8, 15, 3, 0, tzinfo=dt.timezone.utc)]

address=test2.address 
lockedAmount=mint['amount'] 
fundingTxId=mint['funding_txid']
fundingVout=mint['funding_vout']
redeemScript=mint['redeem_script']
timedRelease=True
date=mint['original_params']['locktime']

tx_unlock = test2.simpleTimeLockCurrencyTransaction(address=test2.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'],fundingVout=mint['funding_vout'],redeemScript=mint['redeem_script'],timedRelease=True, date=mint['original_params']['locktime'])
tx_unlock

mint = mints[dt.datetime(2025, 8, 15, 0, 0, tzinfo=dt.timezone.utc)]
tx_unlock = test1.simpleTimeLockCurrencyTransaction(address=test1.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'],fundingVout=mint['funding_vout'],redeemScript=mint['redeem_script'],timedRelease=False, date=None)