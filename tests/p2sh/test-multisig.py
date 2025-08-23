exit()
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

redeem_scripts, timestamp = MultisigUtils.create(test1, test2, days=2, amount=1)
redeem_scripts
timestamp

redeem_scripts = MultisigUtils.send(test1, redeem_scripts, timestamp)
redeem_scripts

mints = MultisigUtils.getMints('scripts-2025-08-21 03:42:56.json')
mint = mints[MultisigUtils.utcIso(dt.datetime(2025, 8, 21, 0, 0, tzinfo=dt.timezone.utc))]
tx_unlock = test2.multiTimeMultisigCurrencyTransaction(address=test2.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'],fundingVout=mint['funding_vout'],redeemScript=mint['redeem_script'], timedRelease=3, date=mint['original_params']['locktime_2'])
tx_unlock

from typing import Union, Callable, Optional, Sequence
import os
import json
import threading
import datetime as dt
from functools import partial
from enum import Enum
from random import randrange
from decimal import Decimal
import joblib
from satorilib import logging
from satorilib.utils import system
from satorilib.disk.utils import safetify
from satorilib.electrumx import Electrumx
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.utils.validate import Validate
from satorilib.wallet.concepts.balance import Balance
from satorilib.wallet.concepts.transaction import TransactionResult, TransactionFailure, TransactionStruct
from satorilib.wallet.identity import Identity, IdentityBase
from typing import Union, Callable, Dict, Sequence, Optional
import datetime as dt
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import (
    CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, 
    OP_EVR_ASSET, OP_DROP, OP_RETURN, SIGHASH_ANYONECANPAY, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY)
from evrmore.core import b2lx, b2x, lx, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from evrmore.core.scripteval import EvalScriptError
from satorilib import logging
from satorilib.electrumx import Electrumx
from satorilib.wallet.concepts.transaction import AssetTransaction, TransactionFailure
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import Wallet
from satorilib.wallet.evrmore.utils.sign import signMessage
from satorilib.wallet.evrmore.utils.verify import verify
from satorilib.wallet.evrmore.utils.valid import isValidEvrmoreAddress
from satorilib.wallet.identity import Identity
from satorilib.wallet.evrmore.identity import EvrmoreIdentity


address=test2.address
lockedAmount=mint['amount']
feeOverride=250000
fundingTxId=mint['funding_txid']
fundingVout=mint['funding_vout']
redeemScript=mint['redeem_script']
timedRelease=True
date=mint['original_params']['locktime_2']
memo = None 
satoriSats = 0
extraVins = None
extraVouts = None
extraVinsTxinScripts=None
broadcast=True





mints = MultisigUtils.getMints('scripts-2025-08-17 19:15:14.json')
mint = mints[MultisigUtils.utcIso(dt.datetime(2025, 8, 17, 0, 0, tzinfo=dt.timezone.utc))]
tx_unlock_immediate = test1.multiTimeMultisigCurrencyTransaction(address=test1.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'], fundingVout=mint['funding_vout'], redeemScript=mint['redeem_script'], timedRelease=0)
tx_unlock_immediate

address=test1.address
lockedAmount=mint['amount']
feeOverride=250000
fundingTxId=mint['funding_txid']
fundingVout=mint['funding_vout']
redeemScript=mint['redeem_script']
timedRelease=False
date=None


mint = mints[MultisigUtils.utcIso(dt.datetime(2025, 8, 17, 0, 0, tzinfo=dt.timezone.utc))]
tx_unlock_immediate = test1.multiTimeMultisigCurrencyTransaction(address=test1.address, lockedAmount=mint['amount'], feeOverride=250000, fundingTxId=mint['funding_txid'], fundingVout=mint['funding_vout'], redeemScript=mint['redeem_script'], timedRelease=0)
tx_unlock_immediate




### MULTISIG ###

redeem_scripts, timestamp = MultisigUtils.create(test1, test2, days=3, amount=.00010000)
redeem_scripts
timestamp

redeem_scripts = MultisigUtils.send(test1, redeem_scripts, timestamp)
redeem_scripts

mints = MultisigUtils.getMints('scripts-2025-08-17 20:17:12.json')
mint = mints[MultisigUtils.utcIso(dt.datetime(2025, 8, 17, 21, 0, tzinfo=dt.timezone.utc))]

tx = test2.multiTimeMultisigCurrencyTransaction(
    address=test2.address,
    lockedAmount=mint['amount'],
    feeOverride=833800,
    fundingTxId=mint['funding_txid'],
    fundingVout=mint['funding_vout'],
    redeemScript=mint['redeem_script'],
    timedRelease=1,
    multisigMap=MultisigUtils.multisigMap(mint))

tx

tx1 = MultisigUtils.toHex(tx)
tx2 = MultisigUtils.hexToTx(tx1)
sig2 = test2.multiTimeMultisigCurrencyTransactionMiddle(
    tx=tx2,
    redeemScript=mint['redeem_script'],
    vinIndex=0,
    sighashFlag=None)
sig3 = sig2
sig4 = sig2
sig5 = sig2
sig1 = test1.multiTimeMultisigCurrencyTransactionMiddle(
    tx=tx2,
    redeemScript=mint['redeem_script'],
    vinIndex=0,
    sighashFlag=None)


#sigMap = MultisigUtils.multisigMap(mint, {
#    test1.pubkey: sig1,
#    test2.pubkey: sig2,
#    test2.pubkey: sig3,
#    test2.pubkey: sig4,
#    test2.pubkey: sig5,
#})
#sigMap  

txid_multisig = test2.multiTimeMultisigCurrencyTransactionEnd(
    tx=tx2,
    signatures=[sig1, sig2, sig3, sig4, sig5],
    extraVinsTxinScripts=[],
    broadcast=True,
    feeOverride=833800,
    redeemScript=mint['redeem_script'],
    timedRelease=1,
    #multisigMap=sigMap
    )
txid_multisig


### MULTISIG --- SATORI ###

mints = MultisigUtils.getMints('scripts-2025-08-21 03:56:15.json')
mint = mints[MultisigUtils.utcIso(dt.datetime(2025, 8, 24, 0, 0, tzinfo=dt.timezone.utc))]

tx, extraVinsTxinScripts = test2.multiTimeMultisigTransaction(
    address=test2.address,
    lockedAmount=mint['amount'],
    feeOverride=1058200,
    fundingTxId=mint['funding_txid'],
    fundingVout=mint['funding_vout'],
    redeemScript=mint['redeem_script'],
    timedRelease=1,
    multisigMap=MultisigUtils.multisigMap(mint))

tx

tx1 = MultisigUtils.toHex(tx)
tx2 = MultisigUtils.hexToTx(tx1)
sig2 = test2.multiTimeMultisigTransactionMiddle(
    tx=tx2,
    redeemScript=mint['redeem_script'],
    vinIndex=0,
    sighashFlag=None)
sig3 = sig2
sig4 = sig2
sig5 = sig2
sig1 = test1.multiTimeMultisigTransactionMiddle(
    tx=tx2,
    redeemScript=mint['redeem_script'],
    vinIndex=0,
    sighashFlag=None)


#sigMap = MultisigUtils.multisigMap(mint, {
#    test1.pubkey: sig1,
#    test2.pubkey: sig2,
#    test2.pubkey: sig3,
#    test2.pubkey: sig4,
#    test2.pubkey: sig5,
#})
#sigMap  

txid_multisig = test2.multiTimeMultisigTransactionEnd(
    tx=tx2,
    signatures=[sig1, sig2, sig3, sig4, sig5],
    extraVinsTxinScripts=extraVinsTxinScripts,
    broadcast=True,
    feeOverride=1058200,
    redeemScript=mint['redeem_script'],
    timedRelease=1,
    #multisigMap=sigMap
    )
txid_multisig
