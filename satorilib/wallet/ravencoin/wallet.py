from typing import Union
from ravencoin import SelectParams
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_RVN_ASSET, OP_DROP, OP_RETURN, SIGHASH_ANYONECANPAY
from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from ravencoin.core.scripteval import EvalScriptError
from satorilib.electrumx import Electrumx
from satorilib.wallet.concepts.transaction import AssetTransaction, TransactionFailure
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import Wallet
from satorilib.wallet.ravencoin.sign import signMessage
from satorilib.wallet.ravencoin.verify import verify


class RavencoinWallet(Wallet):

    def __init__(
        self,
        walletPath: str,
        temporary: bool = False,
        reserve: float = .25,
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
        self.electrumx = Electrumx(
            chain=self.chain,
            address=self.address,
            scripthash=self.scripthash,
            servers=[
                'moontree.com:50002',
                # '146.190.149.237:50002',
                # 'rvn4lyfe.com:50002', running 1.12  {"jsonrpc":"2.0","error":{"code":-32601,"message":"unknown method \"blockchain.scripthash.get_asset_balance\""},"id":1705041163840}
                # 'ravennode-01.beep.pw:50002', dead
                # 'ravennode-02.beep.pw:50002', dead
                # 'electrum-rvn.dnsalias.net:50002', dead
            ])

    @property
    def symbol(self) -> str:
        return 'rvn'

    @property
    def chain(self) -> str:
        return 'Ravencoin'

    @property
    def networkByte(self) -> bytes:
        return self.networkByteP2PKH

    @property
    def networkByteP2PKH(self) -> bytes:
        return b'\x3c'  # b'0x3c'

    @property
    def networkByteP2SH(self) -> bytes:
        return b'\x7a'  # b'0x7a'

    @property
    def satoriOriginalTxHash(self) -> str:
        return 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3'

    def _generatePrivateKey(self, compressed: bool = True):
        SelectParams('mainnet')
        return CRavencoinSecret.from_secret_bytes(self._entropy, compressed=compressed)

    def _generateAddress(self):
        return P2PKHRavencoinAddress.from_pubkey(self._privateKeyObj.pub)

    @staticmethod
    def generateAddress(pubkey: Union[bytes, str]) -> str:
        if isinstance(pubkey, str):
            pubkey = bytes.fromhex(pubkey)
        return str(P2PKHRavencoinAddress.from_pubkey(pubkey))

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CRavencoinAddress(address).to_scriptPubKey()

    def sign(self, message: str):
        return signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return verify(address=address or self.address, message=message, signature=sig)

    def _checkSatoriValue(self, output: CMutableTxOut, amount: float=None) -> bool:
        '''
        returns true if the output is a satori output of self.mundoFee
        '''
        nextOne = False
        for i, x in enumerate(output.scriptPubKey):
            if nextOne:
                # doesn't pad with 0s at the end
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05'
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05\x00\x00\x00\x00'
                return x.startswith(bytes.fromhex(
                    AssetTransaction.satoriHex(self.symbol) +
                    TxUtils.padHexStringTo8Bytes(
                        TxUtils.intToLittleEndianHex(
                            TxUtils.asSats(amount or self.mundoFee)))))
            if x == OP_RVN_ASSET:
                nextOne = True
        return False

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
        # currency vins
        txins = []
        txinScripts = []
        for utxo in (gatheredCurrencyUnspents or []):
            txin = CMutableTxIn(COutPoint(lx(
                utxo.get('tx_hash')),
                utxo.get('tx_pos')))
            txinScriptPubKey = CScript([
                OP_DUP,
                OP_HASH160,
                Hash160(self.publicKeyBytes),
                OP_EQUALVERIFY,
                OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txinScriptPubKey)
        # satori vins
        for utxo in (gatheredSatoriUnspents or []):
            txin = CMutableTxIn(COutPoint(lx(
                utxo.get('tx_hash')),
                utxo.get('tx_pos')))
            txinScriptPubKey = CScript([
                OP_DUP,
                OP_HASH160,
                Hash160(self.publicKeyBytes),
                OP_EQUALVERIFY,
                OP_CHECKSIG,
                OP_RVN_ASSET,
                bytes.fromhex(
                    AssetTransaction.satoriHex(self.symbol) +
                    TxUtils.padHexStringTo8Bytes(
                        TxUtils.intToLittleEndianHex(int(utxo.get('value'))))),
                OP_DROP,
            ])
            txins.append(txin)
            txinScripts.append(txinScriptPubKey)
        return txins, txinScripts

    def _compileSatoriOutputs(self, satsByAddress: dict[str, int] = None) -> list:
        txouts = []
        for address, sats in satsByAddress.items():
            txout = CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_RVN_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(sats))),
                    OP_DROP]))
            txouts.append(txout)
        return txouts

    def _compileCurrencyOutputs(self, currencySats: int, address: str) -> list[CMutableTxOut]:
        return [CMutableTxOut(
            currencySats,
            CRavencoinAddress(address).to_scriptPubKey()
        )]

    def _compileSatoriChangeOutput(
        self,
        satoriSats: int = 0,
        gatheredSatoriSats: int = 0,
    ) -> Union[CMutableTxOut, None]:
        satoriChange = gatheredSatoriSats - satoriSats
        if satoriChange > 0:
            return CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(self.address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_RVN_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(satoriChange))),
                    OP_DROP]))
        if satoriChange < 0:
            raise TransactionFailure('tx: not enough satori to send')
        return None

    def _compileCurrencyChangeOutput(
        self,
        currencySats: int = 0,
        gatheredCurrencySats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        scriptPubKey: CScript = None,
        returnSats: bool = False,
    ) -> Union[CMutableTxOut, None, tuple[CMutableTxOut, int]]:
        currencyChange = gatheredCurrencySats - currencySats - TxUtils.estimatedFee(
            inputCount=inputCount,
            outputCount=outputCount)
        if currencyChange > 0:
            txout = CMutableTxOut(
                currencyChange,
                scriptPubKey or self._addressObj.to_scriptPubKey())
            if returnSats:
                return txout, currencyChange
            return txout
        if currencyChange < 0:
            # go back and get more?
            raise TransactionFailure('tx: not enough currency to send')
        return None

    def _compileMemoOutput(self, memo: str) -> Union[CMutableTxOut, None]:
        if memo is not None and memo != '' and 4 < len(memo) < 80:
            return CMutableTxOut(
                0,
                CScript([
                    OP_RETURN,
                    # memo.encode().hex().encode() ->b'j\x086d656d6f' -> 3664363536643666 -> '6d656d6f'
                    # -> b'j\x04memo' -> 6d656d6f -> 'memo'
                    # bytes.fromhex(AssetTransaction.memoHex(memo))
                    # memo.encode().hex()  # ->expected a bytes-like object, str found str
                    # bytes([len(memo)]) + memo.encode()  # -> b'\x04memo' 046d656d6f
                    # '6d656d6f'.encode() # -> 3664363536643666 -> 6d656d6f
                    # 'some information'.encode()  # -> 736f6d6520696e666f726d6174696f6e -> 'some information'
                    # 'memomemo'.encode()  # -> 6d656d6f6d656d6f
                    # 'memom'.encode()  # ->6d656d6f6d
                    # 'memo'.encode()  # ->1869440365 # ?????? "hex":"6a046d656d6f"
                    # 'devs'.encode()  # ->1869440365 # ?????? "asm":"OP_RETURN 1937139044","hex":"6a0464657673"
                    # 'creators'.encode()# 63726561746f7273
                    # 'managers'.encode()  # 6d616e6167657273
                    # 'predictors'.encode()  # 707265646963746f7273
                    # 'relayers'.encode()  # 72656c6179657273
                    # 'relay'.encode()  # 72656c6179
                    # 'r'.encode()  # 114 ???
                    # it seems as though we can't do 4 or less probably because of something CScript is doing... idk why.
                    memo.encode()
                ]))
        return None

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

    def _createPartialOriginatorSimple(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        ''' simple version SIGHASH_ANYONECANPAY | SIGHASH_ALL '''
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txinScriptPubKey) in enumerate(zip(txins, txinScripts)):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ANYONECANPAY | SIGHASH_ALL)
        return tx

    def _createPartialCompleterSimple(self, txins: list, txinScripts: list, tx: CMutableTransaction) -> CMutableTransaction:
        '''
        simple version SIGHASH_ANYONECANPAY | SIGHASH_ALL
        just adds an input for the RVN fee and signs it
        '''
        # how does the final thing not have currency in?
        tx.vin.extend(txins)
        startIndex = len(tx.vin) - len(txins)
        for i, (txin, txinScriptPubKey) in (
            enumerate(zip(tx.vin[startIndex:], txinScripts), start=startIndex)
        ):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ANYONECANPAY | SIGHASH_ALL)
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
        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
        try:
            VerifyScript(
                txin.scriptSig,
                txinScriptPubKey,
                tx, i, (SCRIPT_VERIFY_P2SH,))
        except EvalScriptError as e:
            # python-ravencoinlib doesn't support OP_RVN_ASSET in txinScriptPubKey
            if str(e) != 'EvalScript: unsupported opcode 0xc0':
                raise EvalScriptError(e)

    # def _createPartialOriginator(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
    #    ''' not completed - complex version SIGHASH_ANYONECANPAY | SIGHASH_SINGLE '''
    #    tx = CMutableTransaction(txins, txouts)
    #    for i, (txin, txinScriptPubKey) in enumerate(zip(tx.vin, txinScripts)):
    #        # Use SIGHASH_SINGLE for the originator's inputs
    #        sighash_type = SIGHASH_SINGLE
    #        sighash = SignatureHash(txinScriptPubKey, tx, i, sighash_type)
    #        sig = self._privateKeyObj.sign(sighash) + bytes([sighash_type])
    #        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
    #    return tx
    #
    # def _createPartialCompleter(self, txins: list, txinScripts: list, txouts: list, tx: CMutableTransaction) -> CMutableTransaction:
    #    ''' not completed '''
    #    tx.vin.extend(txins)  # Add new inputs
    #    tx.vout.extend(txouts)  # Add new outputs
    #    # Sign new inputs with SIGHASH_ANYONECANPAY and possibly SIGHASH_SINGLE
    #    # Assuming the completer's inputs start from len(tx.vin) - len(txins)
    #    startIndex = len(tx.vin) - len(txins)
    #    for i, (txin, txinScriptPubKey) in enumerate(zip(tx.vin[startIndex:], txinScripts), start=startIndex):
    #        sighash_type = SIGHASH_ANYONECANPAY  # Or SIGHASH_ANYONECANPAY | SIGHASH_SINGLE
    #        sighash = SignatureHash(txinScriptPubKey, tx, i, sighash_type)
    #        sig = self._privateKeyObj.sign(sighash) + bytes([sighash_type])
    #        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
    #    return tx

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())

    def _serialize(self, tx: CMutableTransaction) -> bytes:
        return tx.serialize()

    def _deserialize(self, serialTx: bytes) -> CMutableTransaction:
        return CMutableTransaction.deserialize(serialTx)
