import json
import logging
import os
import random
from typing import List, Tuple, Union
from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core.script import CreateMultisigRedeemScript
from evrmore.core import CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.transaction import CMultiSigTransaction
from satorilib.electrumx import Electrumx
<<<<<<< Updated upstream
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import WalletBase  # Import WalletBase
=======
from satorilib.wallet.wallet import WalletBase

>>>>>>> Stashed changes

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
            return [utxo for utxo in all_utxos if utxo['asset'] == asset]
        except Exception as e:
            logging.error(f"Error fetching UTXOs: {e}", exc_info=True)
            return []

    def generate_sighash(self, tx: CMultiSigTransaction) -> bytes:
        """Generate the sighash for a transaction (for all participants)."""
        if not self.redeem_script:
            raise ValueError("Redeem script not set.")
        return tx.generate_sighash(self.redeem_script)

    @staticmethod
    def sign_independently(tx: CMultiSigTransaction, private_key: CEvrmoreSecret, sighash: bytes) -> bytes:
        """Sign the transaction independently with a private key."""
        try:
            return tx.sign_independently(private_key, sighash)
        except Exception as e:
            logging.error(f"Error signing transaction: {e}", exc_info=True)
            return b''

    def apply_signatures(self, tx: CMultiSigTransaction, signatures: List[bytes]) -> CMultiSigTransaction:
        """Apply multiple signatures to a multisig transaction."""
        try:
            tx.apply_multisig_signatures(signatures, self.redeem_script)
            return tx
        except Exception as e:
            logging.error(f"Error applying signatures: {e}", exc_info=True)
            return None

    def create_unsigned_transaction(self, txid: str, vout_index: int, amount: int, recipient_address: str) -> CMultiSigTransaction:
        '''
        Creates an unsigned transaction to send funds from a P2SH address to a recipient address.

        Parameters:
        - txid (str): Transaction ID of the UTXO being spent.
        - vout_index (int): Index of the output in the UTXO being spent.
        - amount (int): Amount to send (in satoshis).
        - recipient_address (str): Recipient's address.
        - redeem_script (CScript): Redeem script for the P2SH address.

        Returns:
        - CMultiSigTransaction: The unsigned transaction.
        '''
        try:
            # Create the input (vin) referencing the UTXO
            outpoint = COutPoint(lx(txid), vout_index)
            txin = CMutableTxIn(prevout=outpoint)

            # Create the scriptPubKey for the recipient address
            recipient_script_pubkey = CEvrmoreAddress(recipient_address).to_scriptPubKey()
            if not isinstance(recipient_script_pubkey, CScript):
                raise ValueError("Failed to generate recipient scriptPubKey.")

            # Create the output (vout) with the specified amount and recipient address
            txout = CMutableTxOut(nValue=amount, scriptPubKey=recipient_script_pubkey)

            # Create the unsigned transaction
            tx = CMultiSigTransaction(vin=[txin], vout=[txout])

            return tx

        except Exception as e:
            logging.error(f"Error in create_unsigned_transaction: {e}", exc_info=True)
            return None

    def create_unsigned_transaction_multi(
        self,
        inputs: List[dict],
        recipients: List[dict],
        change_address: Union[str, None] = None,
        fee: Union[int, None] = None,
    ) -> CMultiSigTransaction:
        """
        Create an unsigned multi-input, multi-output transaction.

        :param inputs: List of UTXOs, each a dict with:
            {
                "txid": "<hex-string>",
                "vout": <int>,
                "amount": <int in satoshis>,
                "asset": "SATORI" (optional, defaults to "EVR" or null)
                "redeem_script": <CScript> (optional if the same redeem_script is stored in the wallet)
            }
            - 'redeem_script' might be omitted if the wallet assumes a single script in self.redeem_script.
        :param recipients: List of outputs, each a dict with:
            {
                "address": "<string base58/Bech32>",
                "amount": <int in satoshis>
                "asset": "SATORI" (optional, defaults to "EVR" or null)
            }
        :param change_address: Address to send leftover change to, if any.
        :param fee: The transaction fee in satoshis.

        :return: A CMultiSigTransaction object with all specified inputs/outputs but no signatures.
        """
        try:
            if not recipients:
                raise ValueError("No recipients provided.")

            # 1) Build the list of TxIn
            txins = []
            total_input_by_asset: dict[str, int] = {'EVR': 0}
            for utxo in inputs:
                if "txid" not in utxo or "vout" not in utxo or "amount" not in utxo:
                    raise ValueError("Each UTXO dict must contain 'txid', 'vout', and 'amount'.")

                # TODO: what if the input is not a multisig output, but just a standard vout (sent from a p2pkh address)? maybe this is already handled?

                if utxo.get('asset', 'EVR').upper() == 'EVR':
                    outpoint = COutPoint(lx(utxo["txid"]), utxo["vout"])
                    txin = CMutableTxIn(prevout=outpoint)
                    txins.append(txin)
                    total_input_by_asset['EVR'] = total_input_by_asset.get('EVR', 0) + utxo["amount"]
                else:
                    # this would typically be the case for
                    # if utxo.get('asset', 'EVR').upper() == 'SATORI':
                    # TODO: handle including asset input?
                    total_input_by_asset[utxo['asset']] = total_input_by_asset.get(utxo['asset'], 0) + utxo["amount"]

            # 2) Build the list of TxOut
            txouts = []
            total_outs_by_asset: dict[str, int] = {'EVR': 0}
            for recipient in recipients:
                if "address" not in recipient or "amount" not in recipient:
                    raise ValueError("Each recipient dict must contain 'address' and 'amount'.")

                # TODO: what if the output is going to a standard vout (sent to a p2pkh address)? maybe this is already handled?

                if recipient.get('asset', 'EVR').upper() == 'EVR':
                    recipient_script_pubkey = CEvrmoreAddress(recipient["address"]).to_scriptPubKey()
                    txout = CMutableTxOut(nValue=recipient["amount"], scriptPubKey=recipient_script_pubkey)
                    txouts.append(txout)
                    total_outs_by_asset['EVR'] = (
                        total_outs_by_asset.get('EVR', 0) + recipient["amount"])
                else:
                    # this would typically be the case for
                    # if utxo.get('asset', 'EVR').upper() == 'SATORI':
                    # TODO: handle including asset output?
                    #       I think we just need to add OP_EVR_ASSET <asset data> like so:
                    #       OP_HASH160 <redeemScriptHash> OP_EQUAL OP_EVR_ASSET <asset data> OP_DROP
                    #       and <asset data> is:
                    #           bytes.fromhex(
                    #               AssetTransaction.satoriHex(recipient["asset"]) +
                    #                   TxUtils.padHexStringTo8Bytes(
                    #                       TxUtils.intToLittleEndianHex(sats)))
                    total_outs_by_asset[recipient["asset"]] = (
                        total_outs_by_asset.get(recipient["asset"], 0) +
                        recipient["amount"])

            # 3) Calculate fee:
            fee = fee or TxUtils.estimateMultisigFee(
                inputCount=len(txins),
                outputCount=len(txouts),
                signatureCount=len(txins) * 3)

            # 4) Calculate change each asset, if any
            #    total_input_amount - (total_output_amount + fee)
            change_value_by_asset: dict[str, int] = {'EVR': 0}
            for asset, total_input_amount in total_input_by_asset.items():
                total_output_amount = total_outs_by_asset.get(asset, 0)
                if asset == 'EVR':
                    total_output_amount += fee
                change_value = total_input_amount - total_output_amount
                if change_value < 0:
                    raise ValueError(f"Not enough input to cover outputs + fee for asset {asset}.")
                change_value_by_asset[asset] = change_value

            # 5) If there is leftover, add a change output for each asset
            for asset, change_value in change_value_by_asset.items():
                if change_value > 0 and change_address is not None:
                    if asset == 'EVR':
                        change_script_pubkey = CEvrmoreAddress(change_address).to_scriptPubKey()
                        change_txout = CMutableTxOut(nValue=change_value, scriptPubKey=change_script_pubkey)
                        txouts.append(change_txout)
                    else:
                        # TODO: handle including asset output?
                        pass

            # 6) Construct the transaction
            tx = CMultiSigTransaction(vin=txins, vout=txouts)
            return tx

        except Exception as e:
            logging.error(f"Error in create_unsigned_transaction: {e}", exc_info=True)
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
