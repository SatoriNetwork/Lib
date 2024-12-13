import json
import os
from typing import Tuple, Union, List
from evrmore import SelectParams
from evrmore.wallet import P2SHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import CScript, OP_HASH160, OP_EQUAL, SignatureHash, CreateMultisigRedeemScript, OP_CHECKMULTISIG, SIGHASH_ALL
from evrmore.core import b2x, lx, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from evrmore.core.scripteval import EvalScriptError
from satorilib.electrumx import Electrumx
from satorilib.wallet.wallet import Wallet
from satorilib.wallet.evrmore.sign import signMessage
from satorilib.wallet.evrmore.verify import verify

class EvrmoreP2SHWallet(Wallet):

    def __init__(
        self,
        walletPath: str,
        temporary: bool = False,
        reserve: float = .1,
        isTestnet: bool = False,
        password: Union[str, None] = None,
        mode: str = 'single',
        public_keys: List[bytes] = None
    ):
        """
        Initialize the P2SH wallet.

        Args:
            walletPath (str): Path to the wallet file.
            temporary (bool): Whether the wallet is temporary.
            reserve (float): Reserve balance.
            isTestnet (bool): True if testnet should be used.
            password (str, optional): Password for encrypted wallets.
            mode (str): Mode of operation, either 'single' or 'multi'.
            public_keys (List[bytes], optional): List of public keys for multi-party mode.
        """
        super().__init__(
            walletPath,
            temporary=temporary,
            reserve=reserve,
            isTestnet=isTestnet,
            password=password
        )
        
        self.mode = mode
        self.private_keys: List[CEvrmoreSecret] = []
        self.public_keys: List[bytes] = public_keys if public_keys else []
        
        self.redeem_script: CScript = None
        
        # Load existing wallet data if available
        if os.path.exists(self.walletPath):
            self.load_wallet()

    def _initialize_network(self):
        SelectParams('mainnet' if not self.isTestnet else 'testnet')

    def connect(self):
        self.electrumx = Electrumx(
            chain=self.chain,
            address=self.address,
            scripthash=self.scripthash,
            servers=[
                'moontree.com:50022',  # mainnet ssl evr
                # '146.190.149.237:50022',  # mainnet ssl evr
            ])

    @property
    def symbol(self) -> str:
        return 'evr'

    @property
    def chain(self) -> str:
        return 'Evrmore'

    @property
    def networkByte(self) -> bytes:
        return self.networkByteP2SH

    @property
    def networkByteP2SH(self) -> bytes:
        return (92).to_bytes(1, 'big')
    
    def _generatePrivateKey(self) -> CEvrmoreSecret:
        return CEvrmoreSecret.from_secret_bytes(self._entropy)
    
    def _generateRedeemScript(self, publicKeys: List[bytes], required: int):        
        return CreateMultisigRedeemScript(required, publicKeys)
    
    def _generateAddress(self, redeemScript: CScript):
        return P2SHEvrmoreAddress.from_redeemScript(redeemScript)
    
    def _generateScriptPubKeyFromAddress(self, address):
        return CScript.to_p2sh_scriptPubKey(address)

    def generateSinglePartyP2shAddress(self, num_keys: int = 3, required_signatures: int = 2) -> Tuple[str, CScript]:
        """Generate a single-party P2SH address where one person controls all private keys."""
        for _ in range(num_keys):
            private_key = self._generatePrivateKey()
            self.private_keys.append(private_key)
            self.public_keys.append(private_key.pub)
        
        redeem_script = self._generateRedeemScript(self.public_keys, required_signatures)
        p2sh_address = self._generateAddress(redeem_script)
        
        self.redeem_script = redeem_script
        
        self.save_wallet()  # Save the wallet data after generating the address
        
        return str(p2sh_address), redeem_script
    
    def generateMultiPartyP2shAddress(self, public_keys: List[bytes], required_signatures: int) -> Tuple[str, CScript]:
        """Generate a multi-party P2SH address using public keys from multiple participants."""
        if required_signatures > len(public_keys):
            raise ValueError("Required signatures cannot exceed the number of public keys")
        
        redeem_script = self._generateRedeemScript(public_keys, required_signatures)
        p2sh_address = self._generateAddress(redeem_script)
        
        self.redeem_script = redeem_script
        
        return str(p2sh_address), redeem_script
    
    def addPublicKey(self, public_key: bytes) -> None:
        """Add a public key for multi-party P2SH creation."""
        self.public_keys.append(public_key)
        
    def loadPrivateKeys(self, private_keys_wif: List[str]) -> None:
        """Load private keys from WIF (Wallet Import Format) into the wallet."""
        for wif in private_keys_wif:
            private_key = CEvrmoreSecret(wif)
            self.private_keys.append(private_key)
            self.public_keys.append(private_key.pub)
            
    def save_wallet(self):
        """Save the wallet data to the specified wallet path."""
        wallet_data = {
            'p2sh_address': str(self._generateAddress(self.redeem_script)),
            'private_keys': [key.to_wif() for key in self.private_keys],
            'public_keys': [key.hex() for key in self.public_keys],
            'redeem_script': self.redeem_script.hex() if self.redeem_script else None
        }
        
        with open(self.walletPath, 'w') as f:
            json.dump(wallet_data, f, indent=4)

    def load_wallet(self):
        """Load the wallet data from the specified wallet path."""
        with open(self.walletPath, 'r') as f:
            wallet_data = json.load(f)
        
        self.private_keys = [CEvrmoreSecret(wif) for wif in wallet_data['private_keys']]
        self.public_keys = [bytes.fromhex(pub) for pub in wallet_data['public_keys']]
        self.redeem_script = CScript(bytes.fromhex(wallet_data['redeem_script']))
            
    def signTransaction(self, tx: CMutableTransaction, private_keys: List[CEvrmoreSecret]) -> CMutableTransaction:
        """Sign a transaction using the provided private keys."""
        for i, txin in enumerate(tx.vin):
            sighash = SignatureHash(self.redeem_script, tx, i, SIGHASH_ALL)
            signatures = []
            
            for private_key in private_keys:
                sig = private_key.sign(sighash) + bytes([SIGHASH_ALL])
                signatures.append(sig)
            
            txin.scriptSig = CScript([b''] + signatures + [self.redeem_script])
            VerifyScript(txin.scriptSig, self.redeem_script, tx, i, (SCRIPT_VERIFY_P2SH,))
        
        return tx

    def sign(self, message: str):
        return signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return verify(address=address or self.address, message=message, signature=sig)

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
        txins = []
        txinScripts = []
        for utxo in (gatheredCurrencyUnspents or []):
            txin = CMutableTxIn(COutPoint(lx(
                utxo.get('tx_hash')),
                utxo.get('tx_pos')))
            txinScriptPubKey = self._generateRedeemScript()
            txins.append(txin)
            txinScripts.append(txinScriptPubKey)
        return txins, txinScripts

    def _createTransaction(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txinScriptPubKey) in enumerate(zip(txins, txinScripts)):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ALL)
        return tx

    def _signInput(
        self,
        tx: CMutableTransaction,
        i: int,
        txin: CMutableTxIn,
        txinScriptPubKey: CScript,
        sighashFlag: int
    ):
        sighash = SignatureHash(txinScriptPubKey, tx, i, sighashFlag)
        sig = self._privateKeyObj.sign(sighash) + bytes([sighashFlag])
        txin.scriptSig = CScript([sig, self._generateRedeemScript()])
        try:
            VerifyScript(
                txin.scriptSig,
                txinScriptPubKey,
                tx, i, (SCRIPT_VERIFY_P2SH,))
        except EvalScriptError as e:
            raise EvalScriptError(e)

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())

    def _serialize(self, tx: CMutableTransaction) -> bytes:
        return tx.serialize()

    def _deserialize(self, serialTx: bytes) -> CMutableTransaction:
        return CMutableTransaction.deserialize(serialTx)
