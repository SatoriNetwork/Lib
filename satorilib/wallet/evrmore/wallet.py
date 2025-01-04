from typing import Union
import random
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_EVR_ASSET, OP_DROP, OP_RETURN, SIGHASH_ANYONECANPAY
from evrmore.core import b2x, lx, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from evrmore.core.scripteval import EvalScriptError
from satorilib import logging
from satorilib.electrumx import Electrumx
from satorilib.wallet.concepts.transaction import AssetTransaction, TransactionFailure
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import Wallet
from satorilib.wallet.evrmore.sign import signMessage
from satorilib.wallet.evrmore.verify import verify


class EvrmoreWallet(Wallet):

    electrumxServers: list[str] = [
        '128.199.1.149:50002',
        '146.190.149.237:50002',
        '146.190.38.120:50002',
        'electrum1-mainnet.evrmorecoin.org:50002',
        'electrum2-mainnet.evrmorecoin.org:50002',
        '1-electrum.satorinet.ie:50002', #WilQSL
        'evr-electrum.wutup.io:50002', #Kasvot Växt
    ]

    electrumxServersWithoutSSL: list[str] = [
        '128.199.1.149:50001',
        '146.190.149.237:50001',
        '146.190.38.120:50001',
        'electrum1-mainnet.evrmorecoin.org:50001',
        'electrum2-mainnet.evrmorecoin.org:50001',
        #'135.181.212.189:50001', #WilQSL
        #'evr-electrum.wutup.io:50001', #Kasvot Växt
    ]

    @staticmethod
    def createElectrumxConnection(
        persistent: bool = False,
        hostPort: str = None,
        hostPorts: list[str] = None
    ) -> Electrumx:
        hostPort = hostPort or random.choice(
            hostPorts or EvrmoreWallet.electrumxServers)
        return Electrumx(
            persistent=persistent,
            host=hostPort.split(':')[0],
            port=int(hostPort.split(':')[1]))

    def __init__(
        self,
        walletPath: str,
        reserve: float = .25,
        isTestnet: bool = False,
        password: Union[str, None] = None,
        electrumx: Electrumx = None,
        type: str = 'wallet',
        watchAssets: list[str] = None,
        skipSave: bool = False,
        pullFullTransactions: bool = True,
    ):
        super().__init__(
            walletPath,
            reserve=reserve,
            isTestnet=isTestnet,
            password=password,
            watchAssets=watchAssets,
            skipSave=skipSave,
            pullFullTransactions=pullFullTransactions)
        self.electrumx = electrumx or EvrmoreWallet.createElectrumxConnection()
        self.type = type

    @property
    def symbol(self) -> str:
        return 'evr'

    @property
    def chain(self) -> str:
        return 'Evrmore'

    @property
    def networkByte(self) -> bytes:
        return self.networkByteP2PKH

    @property
    def networkByteP2PKH(self) -> bytes:
        # evrmore.params.BASE58_PREFIXES['PUBKEY_ADDR']
        # BASE58_PREFIXES = {'PUBKEY_ADDR': 33,
        #                   'SCRIPT_ADDR': 92,
        #                   'SECRET_KEY': 128}
        # RVN = return b'\x3c'  # b'0x3c'
        return (33).to_bytes(1, 'big')

    @property
    def networkByteP2SH(self) -> bytes:
        return (92).to_bytes(1, 'big')

    @property
    def satoriOriginalTxHash(self) -> str:
        # SATORI/TEST 15dd33886452c02d58b500903441b81128ef0d21dd22502aa684c002b37880fe
        return 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188'

    # signature ###############################################################

    def sign(self, message: str):
        return signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return verify(
            message=message,
            signature=sig,
            address=address or self.address)

    # generation ##############################################################

    @staticmethod
    def generateAddress(pubkey: Union[bytes, str]) -> str:
        if isinstance(pubkey, str):
            pubkey = bytes.fromhex(pubkey)
        return str(P2PKHEvrmoreAddress.from_pubkey(pubkey))

    def _generatePrivateKey(self):
        SelectParams('mainnet')
        return CEvrmoreSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self, pub=None):
        return P2PKHEvrmoreAddress.from_pubkey(pub or self._privateKeyObj.pub)

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CEvrmoreAddress(address).to_scriptPubKey()

    # transaction creation ####################################################

    def _checkSatoriValue(self, output: CMutableTxOut) -> bool:
        '''
        returns true if the output is a satori output of self.mundoFee
        '''
        nextOne = False
        for i, x in enumerate(output.scriptPubKey):
            if nextOne:
                # doesn't padd with 0s at the end
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05'
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05\x00\x00\x00\x00'
                if not x.startswith(bytes.fromhex(
                    AssetTransaction.satoriHex(self.symbol) +
                    TxUtils.padHexStringTo8Bytes(
                        TxUtils.intToLittleEndianHex(
                            TxUtils.asSats(self.mundoFee))))):
                    if not x.startswith(bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol))):
                        logging.debug('failed to even validate mundo asset')
                    else:
                        logging.debug('validated asset, failed valid amount')
                    return False
                return True
            if x == OP_EVR_ASSET:
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
            if 'scriptPubKey' in utxo:
                txinScriptPubKey = CScript(
                    bytes.fromhex(utxo.get('scriptPubKey')))
            else:
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
            if 'scriptPubKey' in utxo:
                txinScriptPubKey = CScript(
                    bytes.fromhex(utxo.get('scriptPubKey')))
            else:
                txinScriptPubKey = CScript([
                    OP_DUP,
                    OP_HASH160,
                    Hash160(self.publicKeyBytes),
                    OP_EQUALVERIFY,
                    OP_CHECKSIG,
                    OP_EVR_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(int(utxo.get('value'))))),
                    OP_DROP])
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
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
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
            CEvrmoreAddress(address).to_scriptPubKey()
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
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
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
                    # it seems as though we can't do 4 or less
                    # probably because of something CScript is doing... idk why.
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
        # logging.debug('txins', txins)
        # logging.debug('txouts', txouts)
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
        # todo, verify the last two outputs at somepoint before this
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
