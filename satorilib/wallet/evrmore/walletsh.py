import json
import logging
from typing import List, Tuple, Union
from base64 import b64encode, b64decode
import os
import random
from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.script import CreateMultisigRedeemScript
from evrmore.wallet import P2SHEvrmoreAddress
from evrmore.wallet import CEvrmoreSecret, CEvrmoreAddress
from evrmore.core import CMutableTransaction, CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.transaction import CMultiSigTransaction
from evrmore.core.script import OP_HASH160, OP_EQUAL, OP_CHECKMULTISIG, OP_CHECKSIG
from satorilib.electrumx import Electrumx
from satorilib.wallet.wallet import WalletBase  # Import WalletBase

class EvrmoreP2SHWallet(WalletBase):

    electrumxServers: list[str] = [
        '128.199.1.149:50002',
        '146.190.149.237:50002',
        '146.190.38.120:50002',
        'electrum1-mainnet.evrmorecoin.org:50002',
        'electrum2-mainnet.evrmorecoin.org:50002',
    ]

    electrumxServersWithoutSSL: list[str] = [
        '128.199.1.149:50001',
        '146.190.149.237:50001',
        '146.190.38.120:50001',
        'electrum1-mainnet.evrmorecoin.org:50001',
        'electrum2-mainnet.evrmorecoin.org:50001',
    ]


    @staticmethod
    def createElectrumxConnection(hostPort: str = None, persistent: bool = False) -> Electrumx:
        hostPort = hostPort or random.choice(EvrmoreP2SHWallet.electrumxServers)
        return Electrumx(
            persistent=persistent,
            host=hostPort.split(':')[0],
            port=int(hostPort.split(':')[1]))

    def __init__(
        self,
        wallet_path: str,
        is_testnet: bool = True,
        electrumx: Electrumx = None,
        required_signatures: int = 2
    ):
        super().__init__()
        self.wallet_path = wallet_path
        self.is_testnet = is_testnet
        self.required_signatures = required_signatures
        self.private_keys = []
        self.public_keys = []
        self.redeem_script = None
        self.p2sh_address = None
        self.electrumx = electrumx or EvrmoreP2SHWallet.createElectrumxConnection()
        self.generateObjects()


    def _generatePrivateKey(self, compressed: bool = True):
        ''' returns a private key object '''
        return CEvrmoreSecret.from_secret_bytes(os.urandom(32), compressed=compressed)

    def _generateAddress(self, pub=None):
        ''' returns an address object '''
        # return CEvrmoreAddress.from_pubkey(pub)

    def generate_multi_party_p2sh_address(self, public_keys: List[bytes], required_signatures: int) -> Tuple[P2SHEvrmoreAddress, CScript]:
        '''Generates a multi-party P2SH address.'''
        try:
            assert len(public_keys) >= required_signatures, "Number of public keys must be >= required signatures."

            self.redeem_script = CreateMultisigRedeemScript(required_signatures, public_keys)

            if not self.redeem_script:
                raise ValueError("Failed to generate the redeem script.")
            print(self.redeem_script.hex())
            self.p2sh_address = P2SHEvrmoreAddress.from_redeemScript(self.redeem_script)

            if not self.p2sh_address:
                raise ValueError("Failed to generate the P2SH address.")

            return self.p2sh_address, self.redeem_script

        except Exception as e:
            logging.error(f"Error in generate_multi_party_p2sh_address: {e}", exc_info=True)
            return None, None


    def generate_single_party_p2sh_address(self, num_keys: int = 3, required_signatures: int = 2) -> Tuple[P2SHEvrmoreAddress, CScript]:
        '''Generates a single-party P2SH address using internal private keys.'''
        try:
            self.private_keys = [self._generatePrivateKey() for _ in range(num_keys)]
            self.public_keys = [key.pub for key in self.private_keys]
            if not self.public_keys:
                raise ValueError("Failed to generate public keys.")

            address, redeem_script = self.generate_multi_party_p2sh_address(self.public_keys, required_signatures)
            if not address or not redeem_script:
                raise ValueError("Failed to generate single-party P2SH address.")

            return address, redeem_script

        except Exception as e:
            logging.error(f"Error in generate_single_party_p2sh_address: {e}", exc_info=True)
            return None, None

    def sign_transaction(self, tx: CMultiSigTransaction, private_keys: List[CEvrmoreSecret]) -> CMultiSigTransaction:
        '''Signs a transaction with multiple signatures.'''
        try:
            if not self.redeem_script:
                raise ValueError("Cannot sign transaction. Redeem script is not set.")
            signatures = tx.sign_with_multiple_keys(private_keys, self.redeem_script)
            tx.apply_multisig_signatures(signatures, self.redeem_script)
            return tx

        except Exception as e:
            logging.error(f"Error in sign_transaction: {e}", exc_info=True)
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


    def broadcast_transaction(self, signed_tx: CMultiSigTransaction) -> str:
        '''
        Broadcasts a signed transaction to the Evrmore network using Electrumx.

        Parameters:
        - signed_tx (CMultiSigTransaction): The signed transaction object to be broadcasted.

        Returns:
        - str: The transaction ID if successfully broadcasted.
        '''
        try:
            if not self.electrumx:
                raise ValueError("Electrumx connection is not established.")

            # Convert the signed transaction to hexadecimal format
            tx_hex = signed_tx.serialize().hex()

            # Broadcast the transaction to the network
            txid = self.electrumx.api.broadcast(tx_hex)

            if txid:
                logging.info(f"Transaction successfully broadcasted with txid: {txid}")
                return txid
            else:
                raise ValueError("Failed to broadcast the transaction.")

        except Exception as e:
            logging.error(f"Error broadcasting transaction: {e}", exc_info=True)
            return ""

    def add_public_key(self, public_key: bytes) -> None:
        '''Adds a public key to the wallet's list of known public keys.'''
        if public_key not in self.public_keys:
            self.public_keys.append(public_key)
