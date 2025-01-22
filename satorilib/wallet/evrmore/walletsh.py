import json
import logging
import os
import random
from typing import List, Tuple, Union
from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core.script import CreateMultisigRedeemScript, OP_HASH160, OP_EQUAL, OP_EVR_ASSET, OP_DUP, OP_EQUALVERIFY, OP_CHECKSIG, OP_DROP
from evrmore.core import CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.transaction import CMultiSigTransaction
from satorilib.electrumx import Electrumx
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import WalletBase  # Import WalletBase
from satorilib.wallet.evrmore.wallet import AssetTransaction

class EvrmoreP2SHWallet(WalletBase):
    electrumx_servers: list[str] = [
        '128.199.1.149:50002',
        '146.190.149.237:50002',
        '146.190.38.120:50002',
        'electrum1-mainnet.evrmorecoin.org:50002',
        'electrum2-mainnet.evrmorecoin.org:50002',
    ]

    @staticmethod
    def create_electrumx_connection(hostPort: str = None, persistent: bool = False) -> Electrumx:
        """Create a connection to an ElectrumX server."""
        hostPort = hostPort or random.choice(EvrmoreP2SHWallet.electrumx_servers)
        return Electrumx(
            persistent=persistent,
            host=hostPort.split(':')[0],
            port=int(hostPort.split(':')[1])
        )

    def __init__(self, wallet_path: str, is_testnet: bool = True, electrumx: Electrumx = None, required_signatures: int = 2):
        super().__init__()
        self.wallet_path = wallet_path
        self.is_testnet = is_testnet
        self.required_signatures = required_signatures
        self.public_keys = []
        self.redeem_script = None
        self.p2sh_address = None
        self.electrumx = electrumx or EvrmoreP2SHWallet.create_electrumx_connection()

    def generate_multi_party_p2sh_address(self, public_keys: List[bytes], required_signatures: int) -> Tuple[P2SHEvrmoreAddress, CScript]:
        """Generate a secure multi-party P2SH address with public keys only."""
        try:
            if len(public_keys) < required_signatures:
                raise ValueError("Number of public keys must be >= required signatures.")
            
            self.redeem_script = CreateMultisigRedeemScript(required_signatures, public_keys)
            self.p2sh_address = P2SHEvrmoreAddress.from_redeemScript(self.redeem_script)
            return self.p2sh_address, self.redeem_script
        except Exception as e:
            logging.error(f"Error generating P2SH address: {e}", exc_info=True)
            return None, None

    def fetch_utxos(self, asset: str = None) -> List[dict]:
        """Fetch UTXOs for the asset."""
        try:
            if not self.p2sh_address:
                raise ValueError("P2SH address not generated yet.")
            all_utxos = self.electrumx.api.getUnspentCurrency(self.p2sh_address.to_scripthash(), extraParam=True)
            
            for utxo in all_utxos:
                if utxo.get('asset') is None:
                    utxo['asset'] = 'EVR'
            
            return [utxo for utxo in all_utxos if utxo['asset'] == asset]
        except Exception as e:
            logging.error(f"Error fetching UTXOs: {e}", exc_info=True)
            return []

    def generate_sighash(self, tx: CMultiSigTransaction, input_index: int) -> bytes:
        """Generate the sighash for a transaction (for all participants)."""
        if not self.redeem_script:
            raise ValueError("Redeem script not set.")
        return tx.generate_sighash(self.redeem_script, input_index)

    @staticmethod
    def sign_independently(tx: CMultiSigTransaction, private_key: CEvrmoreSecret, sighash: bytes) -> bytes:
        """Sign the transaction independently with a private key."""
        try:
            return tx.sign_independently(private_key, sighash)
        except Exception as e:
            logging.error(f"Error signing transaction: {e}", exc_info=True)
            return b''

    def apply_signatures(self, tx: CMultiSigTransaction, signatures_list: List[List[bytes]]) -> CMultiSigTransaction:
        """Apply multiple signatures to a multisig transaction."""
        try:
            tx.apply_multisig_signatures(signatures_list, self.redeem_script)
            return tx
        except Exception as e:
            logging.error(f"Error applying signatures: {e}", exc_info=True)
            return None

    def compileInputs(self, utxos_by_asset, required_amounts, fee_rate):
        txins = []
        total_input_by_asset = {}
        for asset, utxos in utxos_by_asset.items():
            total_input_by_asset[asset] = 0
            required_amount = required_amounts.get(asset, 0)
            if asset == 'EVR':
                estimated_size = TxUtils.estimateTransactionSize(len(txins), len(required_amounts) + 1) 
                fee = fee_rate * estimated_size
                required_amount += fee

            for utxo in utxos:
                if utxo["value"] < 546:
                    continue
                if total_input_by_asset[asset] >= required_amount:
                    break
                outpoint = COutPoint(lx(utxo["tx_hash"]), utxo["tx_pos"])
                txin = CMutableTxIn(prevout=outpoint)
                txins.append(txin)
                total_input_by_asset[asset] += utxo["value"]

        return txins, total_input_by_asset

    def compileOutputs(self, recipients, change_value_by_asset, change_address):
        txouts = []
        total_outs_by_asset = {}
        for recipient in recipients:
            asset = recipient.get('asset', 'EVR').upper()
            recipient_script_pubkey = CEvrmoreAddress(recipient["address"]).to_scriptPubKey()
            if recipient["amount"] < 546:
                raise ValueError(f"Output amount for {recipient['address']} is below the dust threshold.")
            
            if asset != 'EVR':
                asset_script = CScript([
                    *recipient_script_pubkey,
                    OP_EVR_ASSET,
                    bytes.fromhex(AssetTransaction.satoriHex(currency="evr", asset=asset) +
                                    TxUtils.padHexStringTo8Bytes(
                                        TxUtils.intToLittleEndianHex(recipient["amount"]))),
                    OP_DROP
                ])
                txout = CMutableTxOut(nValue=0, scriptPubKey=asset_script)
            else:
                txout = CMutableTxOut(nValue=recipient["amount"], scriptPubKey=recipient_script_pubkey)
            
            txouts.append(txout)
            total_outs_by_asset[asset] = total_outs_by_asset.get(asset, 0) + recipient["amount"]

        # Add change outputs if necessary
        for asset, change_value in change_value_by_asset.items():
            if change_value > 546 and change_address is not None:
                change_script_pubkey = CEvrmoreAddress(change_address).to_scriptPubKey()
                if asset != 'EVR':
                    change_script = CScript([
                        *change_script_pubkey,
                        OP_EVR_ASSET,
                        bytes.fromhex(AssetTransaction.satoriHex(currency="evr", asset=asset) +
                                        TxUtils.padHexStringTo8Bytes(
                                            TxUtils.intToLittleEndianHex(change_value))),
                        OP_DROP
                    ])
                    change_txout = CMutableTxOut(nValue=0, scriptPubKey=change_script)
                else:
                    change_txout = CMutableTxOut(nValue=change_value, scriptPubKey=change_script_pubkey)
                txouts.append(change_txout)

        return txouts

    def create_unsigned_transaction_multi(
        self,
        recipients: List[dict],
        fee_rate: int,
        change_address: Union[str, None] = None
    ) -> CMultiSigTransaction:
        """
        Create an unsigned multi-input, multi-output transaction automatically.

        :param recipients: List of outputs, each a dict with:
            {
                "address": "<string base58/Bech32>",
                "amount": <int in satoshis>,
                "asset": "SATORI" (optional, defaults to "EVR")
            }
        :param fee_rate: Fee rate in satoshis per byte.
        :param change_address: Address to send leftover change to, if any.

        :return: A CMultiSigTransaction object with all specified inputs/outputs but no signatures.
        """
        try:
            if not recipients:
                raise ValueError("No recipients provided.")

            utxos_by_asset = {}
            for recipient in recipients:
                asset = recipient.get('asset', 'EVR').upper()
                if asset not in utxos_by_asset:
                    utxos_by_asset[asset] = self.fetch_utxos(asset)

            if 'EVR' not in utxos_by_asset:
                utxos_by_asset['EVR'] = self.fetch_utxos('EVR')

            required_amounts = {r.get('asset', 'EVR').upper(): r['amount'] for r in recipients}
            txins, total_input_by_asset = self.compileInputs(utxos_by_asset, required_amounts, fee_rate)
            change_value_by_asset = {}
            for asset, total_input_amount in total_input_by_asset.items():
                total_output_amount = sum(r['amount'] for r in recipients if r.get('asset', 'EVR').upper() == asset)
                if asset == 'EVR':
                    estimated_size = TxUtils.estimateTransactionSize(len(txins), len(recipients) + 1)
                    fee = fee_rate * estimated_size
                    total_output_amount += fee
                change_value = total_input_amount - total_output_amount
                if change_value < 0:
                    raise ValueError(f"Not enough input to cover outputs + fee for asset {asset}.")
                change_value_by_asset[asset] = change_value

            txouts = self.compileOutputs(recipients, change_value_by_asset, change_address)

            tx = CMultiSigTransaction(vin=txins, vout=txouts)
            return tx

        except Exception as e:
            logging.error(f"Error in create_unsigned_transaction_multi: {e}", exc_info=True)
            return None

    def broadcast_transaction(self, signed_tx: CMultiSigTransaction) -> str:
        """Broadcast a signed transaction."""
        try:
            tx_hex = signed_tx.serialize().hex()
            txid = self.electrumx.api.broadcast(tx_hex)
            return txid if txid else ""
        except Exception as e:
            logging.error(f"Error broadcasting transaction: {e}", exc_info=True)
            return ""

    def add_public_key(self, public_key: bytes) -> None:
        """Add a public key to the wallet's list of known public keys."""
        if public_key not in self.public_keys:
            self.public_keys.append(public_key)
