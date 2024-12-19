import json
import logging
from typing import List, Tuple, Union
from base64 import b64encode, b64decode
import os
from evrmore.wallet import CEvrmoreSecret
from evrmore.core.script import CreateMultisigRedeemScript
from evrmore.wallet import P2SHEvrmoreAddress
from evrmore.core import CMutableTransaction, CMutableTxOut, CMutableTxIn, COutPoint, lx, CScript
from evrmore.core.script import OP_HASH160, OP_EQUAL, OP_CHECKMULTISIG, OP_CHECKSIG
from satorilib.wallet.wallet import WalletBase  # Import WalletBase

class EvrmoreP2SHWallet(WalletBase):

    def __init__(self, wallet_path: str, is_testnet: bool = True, required_signatures: int = 2):
        super().__init__()
        self.wallet_path = wallet_path
        self.is_testnet = is_testnet
        self.required_signatures = required_signatures
        self.private_keys = []
        self.public_keys = []
        self.redeem_script = None
        self.p2sh_address = None
        self.generateObjects()
    
    def generate_multi_party_p2sh_address(self, public_keys: List[bytes], required_signatures: int) -> Tuple[P2SHEvrmoreAddress, CScript]:
        """Generates a multi-party P2SH address."""
        try:
            assert len(public_keys) >= required_signatures, "Number of public keys must be >= required signatures."
            
            self.redeem_script = CreateMultisigRedeemScript(required_signatures, public_keys)
            
            if not self.redeem_script:
                raise ValueError("Failed to generate the redeem script.")
            
            self.p2sh_address = P2SHEvrmoreAddress.from_redeemScript(self.redeem_script)
            
            if not self.p2sh_address:
                raise ValueError("Failed to generate the P2SH address.")
            
            return self.p2sh_address, self.redeem_script
        
        except Exception as e:
            logging.error(f"Error in generate_multi_party_p2sh_address: {e}", exc_info=True)
            return None, None


    def generate_single_party_p2sh_address(self, num_keys: int = 3, required_signatures: int = 2) -> Tuple[P2SHEvrmoreAddress, CScript]:
        """Generates a single-party P2SH address using internal private keys."""
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
    
    def sign_transaction(self, tx: CMutableTransaction, private_keys: List[CEvrmoreSecret]) -> CMutableTransaction:
        """Signs a transaction with multiple signatures."""
        from evrmore.core import SignatureHash, SIGHASH_ALL
        
        for i, txin in enumerate(tx.vin):
            sighash = SignatureHash(self.redeem_script, tx, i, SIGHASH_ALL)
            for priv_key in private_keys:
                signature = priv_key.sign(sighash) + bytes([SIGHASH_ALL])
                txin.scriptSig = CScript([signature, self.redeem_script])
        
        return tx
    
    def add_public_key(self, public_key: bytes) -> None:
        """Adds a public key to the wallet's list of known public keys."""
        if public_key not in self.public_keys:
            self.public_keys.append(public_key)
    