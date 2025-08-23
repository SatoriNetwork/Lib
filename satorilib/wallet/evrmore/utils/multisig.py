import re
import json
import datetime as dt
from typing import Optional, Union
from itertools import islice
from evrmore.core import CScript
from evrmore.core import CMutableTransaction
from satorilib.wallet import EvrmoreWallet
from satorilib.wallet.evrmore.scripts import mining
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


class MultisigUtils():

    ### DATES ########################################################################
    
    UTC = dt.timezone.utc

    @staticmethod
    def now() -> dt.datetime:
        return dt.datetime.now(MultisigUtils.UTC)

    @staticmethod
    def today() -> dt.datetime:
        return dt.datetime.now(MultisigUtils.UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def tomorrow(d: Optional[dt.datetime] = None) -> dt.datetime:
        d = d or MultisigUtils.today()
        return d + dt.timedelta(days=1)

    ### SERIALIZATION ########################################################################
    
    @staticmethod
    def utcIso(d: dt.datetime) -> str:
        if d.tzinfo is None:
            d = d.replace(tzinfo=MultisigUtils.UTC)  # treat naive as MultisigUtils.UTC
        else:
            d = d.astimezone(MultisigUtils.UTC)
        return d.isoformat().replace("+00:00", "Z")

    @staticmethod
    def fromUtcIso(s: str) -> dt.datetime:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return dt.datetime.fromisoformat(s).astimezone(MultisigUtils.UTC)

    @staticmethod
    def _cleanHex(s: str) -> str:
        return re.sub(r'[^0-9A-Fa-f]', '', s.removeprefix("0x"))

    @staticmethod
    def toHex(tx: Union[CMutableTransaction, CMutableTxIn]) -> str:
        # Evrmore: no witness section
        return tx.serialize(
            params={"include_witness": False} if isinstance(tx, CMutableTransaction) else {}
        ).hex()

    @staticmethod
    def sigToHex(sig: bytes) -> str:
        """bytes -> hex string (lowercase)"""
        if not isinstance(sig, (bytes, bytearray, memoryview)):
            raise TypeError("sig must be bytes-like")
        return bytes(sig).hex()
    
    @staticmethod
    def _hexToBytes(hex: str) -> bytes:
        """hex string -> bytes"""
        return bytes.fromhex(MultisigUtils._cleanHex(hex))

    @staticmethod
    def hexToSig(hex: str) -> bytes:
        return MultisigUtils._hexToBytes(hex)
    
    @staticmethod
    def hexToCScript(hex: str) -> CScript:
        return CScript(MultisigUtils._hexToBytes(hex)) 
    
    @staticmethod
    def hexToTxin(hex: str) -> CMutableTxIn:
        return CMutableTxIn.deserialize(MultisigUtils._hexToBytes(hex))

    @staticmethod
    def hexToTx(hex: str) -> CMutableTransaction:
        tx = CMutableTransaction.deserialize(MultisigUtils._hexToBytes(hex))
        if tx.has_witness():
            raise ValueError("Witness data present, but Evrmore is non-SegWit.")
        # deep-mutable copy: vin->CMutableTxIn, vout->CMutableTxOut
        return CMutableTransaction.from_tx(tx)
    

    ### LOAD ########################################################################

    @staticmethod
    def loadScripts(path: str) -> dict[dt.datetime, dict]:
        with open(path) as f:
            raw = json.load(f)
        scripts = {}
        for iso, payload in raw.items():
            when = iso # should be string
            p = dict(payload)
            rs = CScript(bytes.fromhex(p["redeem_script_hex"]))
            p["redeem_script"] = rs
            assert p["redeem_script_size"] == len(rs) # int
            if "original_params" in p:
                p["original_params"] = dict(p["original_params"])
                for k, v in p["original_params"].items():
                    if k.startswith("locktime_"):
                        lp = p["original_params"].get(k)
                        if isinstance(lp, str):
                            p["original_params"][k] = MultisigUtils.fromUtcIso(lp)
            scripts[when] = p
        return scripts
    
    @staticmethod
    def getMints(filename: str = 'mints.json') -> dict[dt.datetime, dict]:
        return MultisigUtils.loadScripts(filename)

    @staticmethod
    def multisigMap(redeemScript: dict, signatureMap: Optional[dict[str, str]] = None) -> dict[str, dict]:
        ''' the value is to be replaced with the signature '''
        # get the dictionary of the multisig pubkeys and their ordering values
        unordered = {
            v: k
            for k, v in redeemScript.get('original_params', {}).items()
            if k.startswith('multi_key_')}
        # order the dictionary by the value alphabetically
        ordered = dict(sorted(unordered.items(), key=lambda x: x[0]))
        # update value to be signature if provided
        signatureMap = signatureMap or {}
        return {
            k: signatureMap.get(k, v)
            for k, v in ordered.items()}

    # sparta = 03399d0d369fe0f675b7a0f1415502c8721d939251b8e26f8b6a67508d57e67e2e
    # wilqsl = 03785beb5ff5318dec78823d8df30a8acbae44fde12c0110996717e46b405c5d1d
    # deadhead = 025fbcba83ee2d4f23b54cef6d340972b1821a8dbfce67c8b800fd88c3582e7390
    # krishna = 
    # cerebus = 

    @staticmethod
    def createMultisigScript(
        immediate: EvrmoreWallet, 
        delayed: EvrmoreWallet, 
        specific_date: dt.datetime, 
        amount: int,
    ) -> dict:
        early_date = specific_date - dt.timedelta(days=1)
        function = mining.lock.multiTimeMultisig
        redeem_script = function(
            immediate_key=immediate.pubkey,
            multi_key_1=immediate.pubkey,
            multi_key_2=delayed.pubkey,
            multi_key_3=delayed.pubkey,
            multi_key_4=delayed.pubkey,
            multi_key_5=delayed.pubkey,
            delayed_key_1=delayed.pubkey,
            delayed_key_2=delayed.pubkey,
            locktime_1=early_date,
            locktime_2=specific_date,
            use_blocks=False)
        return {
                'redeem_script': str(redeem_script),
                'redeem_script_hex': redeem_script.hex(),
                'redeem_script_size': len(redeem_script),
                'p2sh_address': immediate.generateP2SHAddress(redeem_script),
                'amount': amount,
                'function': function.__name__,
                'funding_vout': None, # added during send
                'currency_sats': None, # added during send
                'funding_txid': None, # added during send
                'original_params': {
                    'immediate_key': immediate.pubkey,
                    'multi_key_1': immediate.pubkey,
                    'multi_key_2': delayed.pubkey,
                    'multi_key_3': delayed.pubkey,
                    'multi_key_4': delayed.pubkey,
                    'multi_key_5': delayed.pubkey,
                    'delayed_key_1': delayed.pubkey,
                    'delayed_key_2': delayed.pubkey,
                    'locktime_1': MultisigUtils.utcIso(early_date),
                    'locktime_2': MultisigUtils.utcIso(specific_date),
                    'use_blocks': False}}

    @staticmethod
    def sendFunds(sender: EvrmoreWallet, redeemScripts: dict):
        def chunkDict(d, size=90):
            it = iter(d.items())
            while batch := dict(islice(it, size)):
                yield batch

        newScripts = {}
        for batch in chunkDict(redeemScripts, 90):
            #_txhex, _funding_txid, scripts_batch = sender.simpleTimeLockTransactionCurrency(batch, broadcast=True)
            #_txhex, _funding_txid, scripts_batch = sender.produceMultiTimeMultisigCurrency(batch, broadcast=True)
            _txhex, _funding_txid, scripts_batch = sender.produceMultiTimeMultisig(batch, broadcast=True)
            print(_funding_txid)
            print(_txhex)
            newScripts.update(scripts_batch)
        return newScripts

    @staticmethod
    def saveScripts(path: str, redeemScripts: dict[dt.datetime, dict]) -> None:
        with open(path, "w") as f:
            json.dump(redeemScripts, f, separators=(",", ":"), sort_keys=True)

    def create(immediate: EvrmoreWallet, delayed: EvrmoreWallet, days: int = 2, amount: int = 1):
        timestamp = dt.datetime.now(MultisigUtils.UTC).strftime("%Y-%m-%d %H:%M:%S")
        td = MultisigUtils.today()
        date_amounts = {
            td + dt.timedelta(days=i): amount
            for i in range(days)}
        print(date_amounts)
        redeemScripts = {
            MultisigUtils.utcIso(specific_date): MultisigUtils.createMultisigScript(
                immediate,
                delayed,
                specific_date,
                amount)
            for specific_date, amount in date_amounts.items()}
        MultisigUtils.saveScripts(f'unsent_scripts-{timestamp}.json', redeemScripts)
        return redeemScripts, timestamp


    def send(immediate: EvrmoreWallet, redeemScripts: dict, timestamp: str):
        redeemScripts = MultisigUtils.sendFunds(immediate, redeemScripts)
        print(timestamp)
        print(redeemScripts)
        MultisigUtils.saveScripts(f'scripts-{timestamp}.json', redeemScripts)
        return redeemScripts


    def main(immediate: EvrmoreWallet, delayed: EvrmoreWallet, days: int = 2, amount: int = 1):
        redeemScripts, timestamp = MultisigUtils.create(immediate, delayed, days, amount)
        MultisigUtils.send(immediate, redeemScripts, timestamp)
