from typing import Union
from ravencoin import SelectParams
from ravencoin.wallet import P2SHRavencoinAddress, CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_HASH160, OP_EQUAL, SignatureHash, SIGHASH_ALL
from ravencoin.core import b2x, lx, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from ravencoin.core.scripteval import EvalScriptError
from satoriwallet import ElectrumxAPI
from satoriwallet import ravencoin
from satoriwallet import TxUtils, AssetTransaction
from satorilib import logging
from satorilib.api.wallet.wallet import Wallet, TransactionFailure


class RavencoinP2SHWallet(Wallet):

    def __init__(
        self,
        walletPath: str,
        temporary: bool = False,
        reserve: float = .1,
        isTestnet: bool = True,
        password: Union[str, None] = None,
    ):
        super().__init__(
            walletPath,
            temporary=temporary,
            reserve=reserve,
            isTestnet=isTestnet,
            password=password)

    def connect(self):
        self.electrumx = ElectrumxAPI(
            chain=self.chain,
            address=self.address,
            scripthash=self.scripthash,
            servers=[
                'moontree.com:50002',
                '146.190.149.237:50002',
            ])

    @property
    def symbol(self) -> str:
        return 'rvn'

    @property
    def chain(self) -> str:
        return 'Ravencoin'

    @property
    def networkByte(self) -> bytes:
        return self.networkByteP2SH

    @property
    def networkByteP2SH(self) -> bytes:
        return b'\x7a'  # b'0x7a'

    def _generatePrivateKey(self):
        SelectParams('mainnet')
        return CRavencoinSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self):
        return P2SHRavencoinAddress.from_script(self._generateRedeemScript())

    @staticmethod
    def generateAddress(redeemScript: Union[bytes, str]) -> str:
        if isinstance(redeemScript, str):
            redeemScript = bytes.fromhex(redeemScript)
        return str(P2SHRavencoinAddress.from_script(redeemScript))

    def _generateRedeemScript(self):
        # Example redeem script for a 2-of-3 multisig
        # Add other public keys as needed
        publicKeys = [self._privateKeyObj.pub]
        return CScript([2] + publicKeys + [3, OP_CHECKMULTISIG])

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CRavencoinAddress(address).to_scriptPubKey()

    def sign(self, message: str):
        return ravencoin.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return ravencoin.verify(address=address or self.address, message=message, signature=sig)

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
