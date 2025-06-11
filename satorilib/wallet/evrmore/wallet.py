from typing import Union, Callable, Dict
import datetime as dt
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret, P2SHEvrmoreAddress
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import (
    CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, 
    OP_EVR_ASSET, OP_DROP, OP_RETURN, SIGHASH_ANYONECANPAY, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY)
from evrmore.core import b2x, lx, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from evrmore.core.scripteval import EvalScriptError
from satorilib import logging
from satorilib.electrumx import Electrumx
from satorilib.wallet.concepts.transaction import AssetTransaction, TransactionFailure
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.wallet import Wallet
from satorilib.wallet.evrmore.sign import signMessage
from satorilib.wallet.evrmore.verify import verify
from satorilib.wallet.evrmore.valid import isValidEvrmoreAddress
from satorilib.wallet.evrmore.scripts import P2SHRedeemScripts
from satorilib.wallet.identity import Identity
from satorilib.wallet.evrmore.identity import EvrmoreIdentity

class EvrmoreWallet(Wallet):

    @staticmethod
    def addressIsValid(address: str) -> bool:
        return isValidEvrmoreAddress(address)

    @staticmethod
    def create(
        walletPath: Union[str,None] = None,
        cachePath: Union[str,None] = None,
        password: Union[str,None] = None,
        identity: Union[Identity, None] = None,
        reserve: float = 0,
        watchAssets: list[str] = None,
        skipSave: bool = False,
        pullFullTransactions: bool = True,
        balanceUpdatedCallback: Union[Callable, None] = None,
        electrumx: Electrumx = None,
        hostPort: str = None,
        persistent: bool = False,
        cachedPeersFile: Union[str, None] = None,
    ) -> 'EvrmoreWallet':
        return EvrmoreWallet(
            identity=identity or EvrmoreIdentity(walletPath=walletPath, password=password),
            electrumx=electrumx or Electrumx.create(
                hostPort=hostPort, 
                persistent=persistent,
                cachedPeersFile=cachedPeersFile),
            cachePath=cachePath,
            reserve=reserve,
            watchAssets=watchAssets,
            skipSave=skipSave,
            pullFullTransactions=pullFullTransactions,
            hostPort=hostPort,
            persistent=persistent,
            balanceUpdatedCallback=balanceUpdatedCallback,
            cachedPeersFile=cachedPeersFile)

    def __init__(
        self,
        identity: EvrmoreIdentity,
        electrumx: Union[Electrumx, None] = None,
        cachePath: Union[str, None] = None,
        reserve: float = 0,
        watchAssets: list[str] = None,
        skipSave: bool = False,
        pullFullTransactions: bool = True,
        balanceUpdatedCallback: Union[Callable, None] = None,
        **kwargs
    ):
        super().__init__(
            identity=identity,
            cachePath=cachePath,
            electrumx=electrumx,
            reserve=reserve,
            watchAssets=watchAssets,
            skipSave=skipSave,
            pullFullTransactions=pullFullTransactions,
            balanceUpdatedCallback=balanceUpdatedCallback)
        self.scripts = P2SHRedeemScripts()

    def maybeConnect(self, electrumx = None):
        if self.electrumx is None:
            self.electrumx = Electrumx.create(
                    hostPort=self.hostPort, 
                    persistent= self.persistent,
                    cachedPeersFile=self.cachedPeersFile)
            return self.electrumx is not None
        elif self.electrumx.isConnected:
            return True
        else:
            if self.electrumx.reconnect():
                return True
            else:
                self.electrumx = None
                return self.maybeConnect(electrumx)

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

    @property
    def ethaddress(self) -> Union[str, None]:
        try:
            account = self.account
            return (
                account.checksum_address
                if hasattr(account, 'checksum_address') else None
            ) or account.address
        except Exception as e:
            logging.error(e)
            return None

    # signature ###############################################################

    def sign(self, message: str):
        return signMessage(self.identity._privateKeyObj, message)

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

    @staticmethod
    def generateP2SHAddress(redeem_script: CScript) -> str:
        """Generate a P2SH address from a redeem script."""
        return str(P2SHEvrmoreAddress.from_redeemScript(redeem_script))

    def _generatePrivateKey(self, compressed: bool = True, privkey: Union[str, bytes, None] = None):
        SelectParams('mainnet')
        if not self._entropy:
            privkey = privkey or self.privateKey
        if privkey:
            if isinstance(privkey, str):
                #return CEvrmoreSecret.from_secret_bytes(bytes.fromhex(privkey), compressed=compressed) # bytes below
                #return CEvrmoreSecret.from_hex(privkey) # probably not hex
                return CEvrmoreSecret(privkey)
            elif isinstance(privkey, bytes):
                return CEvrmoreSecret.from_secret_bytes(privkey, compressed=compressed)
            else:
                raise ValueError('privkey must be a string or bytes')
        return CEvrmoreSecret.from_secret_bytes(self._entropy, compressed=compressed)

    def _generateAddress(self, pub=None):
        return P2PKHEvrmoreAddress.from_pubkey(pub or self._privateKeyObj.pub)

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CEvrmoreAddress(address).to_scriptPubKey()

    # transaction creation ####################################################

    def _checkSatoriValue(self, output: CMutableTxOut, amount: float=None) -> bool:
        '''
        returns true if the output is a satori output of amount or self.mundoFee
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
                            TxUtils.asSats(amount or self.mundoFee))))):
                    # logging not necessary since we call this many times, and
                    # it only needs to succeed once...
                    #if not x.startswith(bytes.fromhex(
                    #    AssetTransaction.satoriHex(self.symbol))):
                    #    logging.debug('failed to even validate mundo asset')
                    #else:
                    #    logging.debug('validated asset, failed valid amount')
                    return False
                return True
            if x == OP_EVR_ASSET:
                nextOne = True
        return False

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
        redeem_scripts: dict[str, CScript] = None,  # Map of tx_hash:pos to redeem script
    ) -> tuple[list, list]:
        # currency vins
        txins = []
        txinScripts = []
        for utxo in (gatheredCurrencyUnspents or []):
            tx_hash = utxo.get('tx_hash')
            tx_pos = utxo.get('tx_pos')
            txin = CMutableTxIn(COutPoint(lx(tx_hash), tx_pos))
            
            # If we have a scriptPubKey in the UTXO, use it directly
            if 'scriptPubKey' in utxo:
                txinScriptPubKey = CScript(bytes.fromhex(utxo.get('scriptPubKey')))
            else:
                # No scriptPubKey provided, we need to construct one
                utxo_key = f"{tx_hash}:{tx_pos}"
                if redeem_scripts and utxo_key in redeem_scripts:
                    # Construct P2SH scriptPubKey from redeem script
                    redeem_script = redeem_scripts[utxo_key]
                    txinScriptPubKey = P2SHEvrmoreAddress.from_redeemScript(redeem_script).to_scriptPubKey()
                else:
                    # Construct standard P2PKH scriptPubKey
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
            tx_hash = utxo.get('tx_hash')
            tx_pos = utxo.get('tx_pos')
            txin = CMutableTxIn(COutPoint(lx(tx_hash), tx_pos))
            
            # If we have a scriptPubKey in the UTXO, use it directly
            if 'scriptPubKey' in utxo:
                txinScriptPubKey = CScript(bytes.fromhex(utxo.get('scriptPubKey')))
            else:
                # No scriptPubKey provided, we need to construct one
                utxo_key = f"{tx_hash}:{tx_pos}"
                if redeem_scripts and utxo_key in redeem_scripts:
                    # Construct P2SH scriptPubKey from redeem script and add asset data
                    redeem_script = redeem_scripts[utxo_key]
                    base_script = P2SHEvrmoreAddress.from_redeemScript(redeem_script).to_scriptPubKey()
                    txinScriptPubKey = CScript([
                        *base_script,
                        OP_EVR_ASSET,
                        bytes.fromhex(
                            AssetTransaction.satoriHex(self.symbol) +
                            TxUtils.padHexStringTo8Bytes(
                                TxUtils.intToLittleEndianHex(int(utxo.get('value'))))),
                        OP_DROP])
                else:
                    # Construct standard P2PKH scriptPubKey with asset data
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
                    *CEvrmoreAddress(address).to_scriptPubKey(),
                    OP_EVR_ASSET,
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
                    *CEvrmoreAddress(self.address).to_scriptPubKey(),
                    OP_EVR_ASSET,
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
            if str(CEvrmoreAddress(self.address)) != self.address:
                raise TransactionFailure('tx: address mismatch')
            # allow for overrirde, should probably allow for override as address str:
            #if str(CEvrmoreAddress(self.address)).to_scriptPubKey() != scriptPubKey:
            #    raise TransactionFailure('tx: scriptPubKey mismatch')
            if CEvrmoreAddress(self.address).to_scriptPubKey() != self._addressObj.to_scriptPubKey():
                raise TransactionFailure('tx: scriptPubKey mismatch')
            txout = CMutableTxOut(
                currencyChange,
                scriptPubKey or CEvrmoreAddress(self.address).to_scriptPubKey()) # self._addressObj.to_scriptPubKey())
            # use *CEvrmoreAddress(self.address).to_scriptPubKey()? # supports P2SH automatically
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

    def _createTransaction(
        self,
        txins: list,
        txinScripts: list,
        txouts: list,
        redeem_scripts: dict[str, CScript] = None,
        signatures: dict[str, list[bytes]] = None,  # Map of tx_hash:pos to list of signatures
    ) -> CMutableTransaction:
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txinScriptPubKey) in enumerate(zip(txins, txinScripts)):
            utxo_key = f"{b2x(txin.prevout.hash)}:{txin.prevout.n}"
            redeem_script = redeem_scripts.get(utxo_key) if redeem_scripts else None
            other_sigs = signatures.get(utxo_key) if signatures else None
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ALL,
                redeem_script=redeem_script,
                signatures=other_sigs)
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
        sighashFlag: int,
        redeem_script: CScript = None,
        signatures: list[bytes] = None,  # For multi-sig, list of signatures from other signers
    ):
        """Sign a transaction input.
        
        Args:
            tx: The transaction to sign
            i: Input index
            txin: The transaction input
            txinScriptPubKey: The scriptPubKey of the input
            sighashFlag: The sighash flag to use
            redeem_script: For P2SH inputs, the redeem script
            signatures: For multi-sig, list of signatures from other signers
        """
        if redeem_script:
            # This is a P2SH input
            sighash = SignatureHash(redeem_script, tx, i, sighashFlag)
            sig = self._privateKeyObj.sign(sighash) + bytes([sighashFlag])
            
            if signatures:
                # Multi-sig case
                # Combine our signature with other signatures
                all_sigs = signatures + [sig]
                # Sort signatures by public key (required by Bitcoin)
                all_sigs.sort()
                # Create scriptSig: [sig1, sig2, ..., redeem_script]
                txin.scriptSig = CScript(all_sigs + [redeem_script])
            else:
                # Single-sig P2SH case
                txin.scriptSig = CScript([sig, redeem_script])
        else:
            # Regular P2PKH input
            sighash = SignatureHash(txinScriptPubKey, tx, i, sighashFlag)
            sig = self._privateKeyObj.sign(sighash) + bytes([sighashFlag])
            txin.scriptSig = CScript([sig, self._privateKeyObj.pub])

        try:
            # For P2SH, we need to verify against the redeem script
            script_to_verify = redeem_script if redeem_script else txinScriptPubKey
            VerifyScript(
                txin.scriptSig,
                script_to_verify,
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

    def createP2SHTransaction(
        self,
        outputs: list[tuple[str, float]],  # List of (address, amount) tuples
        redeem_scripts: dict[str, CScript],  # Map of tx_hash:pos to redeem script
        utxos: list = None,  # Optional list of UTXOs to use
        signatures: dict[str, list[bytes]] = None,  # Optional map of tx_hash:pos to list of signatures
        memo: str = None,
    ) -> str:
        """Create and sign a P2SH transaction.

        *** NOTE ***
            this is unused, it's an example, and it doesn't handle fees or change correctly so don't use it.
        
        Args:
            outputs: List of (address, amount) tuples for the outputs
            redeem_scripts: Map of tx_hash:pos to redeem script for each P2SH input
            utxos: Optional list of UTXOs to use. If not provided, will select from available UTXOs
            signatures: Optional map of tx_hash:pos to list of signatures for multi-sig inputs
            memo: Optional memo to include in the transaction
            
        Returns:
            Hex string of the signed transaction
        """
        # Gather UTXOs if not provided
        utxos = utxos or self.gatherUnspents()
            
        # Compile inputs
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=utxos,
            redeem_scripts=redeem_scripts
        )
        
        # Calculate total output amount
        total_output = sum(amount for _, amount in outputs)
        
        # Compile outputs
        txouts = []
        for address, amount in outputs:
            txouts.extend(self._compileCurrencyOutputs(
                TxUtils.asSats(amount),
                address
            ))
            
        # Add memo output if provided
        if memo:
            memo_output = self._compileMemoOutput(memo)
            if memo_output:
                txouts.append(memo_output)
                
        # Create and sign transaction
        tx = self._createTransaction(
            txins=txins,
            txinScripts=txinScripts,
            txouts=txouts,
            redeem_scripts=redeem_scripts,
            signatures=signatures)
        
        raise Exception("this function is an example, and it doesn't handle fees or change correctly so don't use it.")
    
        return self._txToHex(tx)


    def p2shFlow(self):
        '''
        # Let's say we have 3 participants in a 2-of-3 multi-sig
        from evrmore import CEvrmoreSecret  # For private keys
        from evrmore.core import SignatureHash, SIGHASH_ALL

        # Each participant has their own private/public key pair
        privkey1 = CEvrmoreSecret.from_secret_bytes(b'participant1_secret', compressed=True)
        privkey2 = CEvrmoreSecret.from_secret_bytes(b'participant2_secret', compressed=True)
        privkey3 = CEvrmoreSecret.from_secret_bytes(b'participant3_secret', compressed=True)

        pubkey1 = privkey1.pub
        pubkey2 = privkey2.pub
        pubkey3 = privkey3.pub

        # Create the 2-of-3 redeem script
        redeem_script = wallet.scripts.multiSig([pubkey1, pubkey2, pubkey3], 2)

        # Create the P2SH address
        p2sh_address = wallet.generateP2SHAddress(redeem_script)

        # Later, when spending...
        # First, create the transaction without signatures
        tx = CMutableTransaction(txins, txouts)

        # Each participant signs the transaction
        # Participant 1 signs
        sighash1 = SignatureHash(redeem_script, tx, 0, SIGHASH_ALL)
        sig1 = privkey1.sign(sighash1) + bytes([SIGHASH_ALL])

        # Participant 2 signs
        sighash2 = SignatureHash(redeem_script, tx, 0, SIGHASH_ALL)
        sig2 = privkey2.sign(sighash2) + bytes([SIGHASH_ALL])

        # Now we have both signatures needed
        signatures = {
            'tx_hash:tx_pos': [sig1, sig2]  # These are the actual signatures from participants 1 and 2
        }

        # Create the final transaction with these signatures
        tx_hex = wallet.createP2SHTransaction(
            outputs=[(destination_address, amount)],
            redeem_scripts={'tx_hash:tx_pos': redeem_script},
            signatures=signatures
        )    
        '''
        # example
        #In a real-world scenario:
        #Each participant would have their own wallet with their private key
        #They would each sign the transaction independently
        #The signatures would be shared between participants (often through some secure channel)
        #Once you have enough signatures (2 in this case), you can broadcast the transaction
        #The actual process might look more like this in practice:
        '''
        # Participant 1's wallet
        def sign_transaction(tx_hex, redeem_script):
            tx = CMutableTransaction.deserialize(bytes.fromhex(tx_hex))
            sighash = SignatureHash(redeem_script, tx, 0, SIGHASH_ALL)
            sig = my_privkey.sign(sighash) + bytes([SIGHASH_ALL])
            return sig.hex()

        # Participant 2's wallet
        def sign_transaction(tx_hex, redeem_script):
            # Same process, but with their private key
            ...

        # Coordinator's wallet
        # 1. Create unsigned transaction
        tx_hex = wallet.createP2SHTransaction(
            outputs=[(destination_address, amount)],
            redeem_scripts={'tx_hash:tx_pos': redeem_script},
            signatures=None  # No signatures yet
        )

        # 2. Send tx_hex to participants
        # 3. Collect signatures from participants
        sig1_hex = participant1.sign_transaction(tx_hex, redeem_script)
        sig2_hex = participant2.sign_transaction(tx_hex, redeem_script)

        # 4. Create final transaction with signatures
        signatures = {
            'tx_hash:tx_pos': [
                bytes.fromhex(sig1_hex),
                bytes.fromhex(sig2_hex)
            ]
        }

        final_tx_hex = wallet.createP2SHTransaction(
            outputs=[(destination_address, amount)],
            redeem_scripts={'tx_hash:tx_pos': redeem_script},
            signatures=signatures
        )
        '''

    # 1. redeem-script generator  ───────────────────────────────────────────────────
    # see self.scripts
    
    # 2. funding (opens the channel)  ───────────────────────────────────────────────
    def generatePaymentChannel(
        self, 
        redeemScript: CScript,
        amount: float, 
    ) -> tuple[CScript, str, str]:
        """
        
        Returns (redeem_script, p2sh_address, funding_tx_hex)

        Example Usage:
        ```
        redeem_script, p2sh_address, funding_tx_hex = wallet.generatePaymentChannel(
            amount=24,
            redeemScript=wallet.scripts.renewable_light_channel(
                sender=wallet.publicKeyBytes,
                receiver=other.pubkey,
                blocks=60*60*24))
        tx = wallet.broadcast(funding_tx_hex)
        reported = wallet.thunder.reportChannelOpened(
            sender=wallet.address,
            receiver=other.address,
            redeem=redeem_script,
            address=p2sh_address,
            fundingTx=funding_tx_hex,
            tx=tx)
        wallet.remember(reported)
        ```
        """
        sats = TxUtils.asSats(amount)
        p2shAddress = self.generateP2SHAddress(redeemScript)

        # choose inputs
        if utxos is None:
            utxos = self.gatherUnspents()
        txins, txinScripts = self._compileInputs(gatheredCurrencyUnspents=utxos)
        # output = lock <amount_sats> into channel P2SH
        txouts = [CMutableTxOut(sats, CEvrmoreAddress(p2shAddress).to_scriptPubKey())]

        # add change + fee optimisation as usual
        change = self._compileCurrencyChangeOutput(
            currencySats=sats,
            gatheredCurrencySats=sum(u['value'] for u in utxos),
            inputCount=len(txins),
            outputCount=len(txouts))
        
        if change:
            txouts.append(change)

        tx = self._createTransaction(txins, txinScripts, txouts)
        return redeemScript, p2shAddress, self._txToHex(tx)


    # 3. Alice creates a one-sig "commitment" tx  ───────────────────────────────────
    def generateCommitmentTx(
        self, 
        funding_txid: str, 
        vout: int,
        funding_value: int,
        redeem_script: CScript,
        pay_to_receiver_sats: int, 
        receiver_addr: str,
        tx_fee_sats: int = 12000,  # Default fee of 0.00012 EVR (12000 satoshis)
        dust_threshold_multiple: int = 3,  # Multiple of tx fee considered dust
        respect_dust_zone: bool = True,
        #p2sh_addr: str = None, 
    ) -> str:
        """
        Creates a commitment transaction for a payment channel where:
        - A portion of the funds (pay_to_receiver_sats) is sent to the receiver
        - The remainder may stay locked in the payment channel based on amount
        - Transaction fees are handled according to the following logic:
          1. If remainder is zero (sending everything) - take fee from receiver amount
          2. If remainder is dust (< 2x tx fee) - send everything to receiver minus fee
          3. If remainder is significant - take fee from the remainder

        Args:
            funding_txid: Transaction ID of the funding transaction
            vout: Output index in the funding transaction
            funding_value: Total value of the funding output in satoshis
            redeem_script: The redeem script for the payment channel
            pay_to_receiver_sats: Amount to pay to the receiver in satoshis (before fee adjustment)
            receiver_addr: Address of the receiver
            tx_fee_sats: Transaction fee in satoshis
            dust_threshold_multiple: Multiple of tx fee below which change is considered dust
            respect_dust_zone: If true the transaction will fail to create when 0 < change < result of dust_threshold_multiple 
            p2sh_addr: Optional payment channel address, calculated from redeem_script if not provided
            
        Returns:
            Hex of partially-signed transaction (Alice's sig only)
        """
        # Validate the transaction fee
        if tx_fee_sats <= 0:
            raise ValueError("Transaction fee must be positive")
        
        # Validate the payment amount
        if not 0 < pay_to_receiver_sats <= funding_value:
            raise ValueError("Payment amount must be positive and not exceed the funding value")
        
        # Calculate the potential remainder (before considering fees)
        remainder = funding_value - pay_to_receiver_sats
        
        # Define dust threshold (e.g., 3x transaction fee) 
        # assumes 1 input 1 outputs is total fee for typical tx
        dust_threshold = (tx_fee_sats * 3) * dust_threshold_multiple 
        
        # Create the input that spends from the funding transaction
        txin = CMutableTxIn(COutPoint(lx(funding_txid), vout))
        
        # Get or calculate the P2SH address from the redeem script
        #p2sh_addr = p2sh_addr or self.generateP2SHAddress(redeem_script)
        
        # Get the scriptPubKey for the P2SH address
        script_pub = P2SHEvrmoreAddress.from_redeemScript(redeem_script).to_scriptPubKey()

        # Create outputs based on the different cases
        txouts = []
        
        # Case 1 & 2 & 3: No remainder or remainder is dust - send everything to receiver minus fee
        if remainder  == 0 or remainder < dust_threshold:
            if remainder > 0 and respect_dust_zone:
                raise ValueError(f"In Dust Zone.")

            # in this case we have 1 input and 1 output
            tx_fee_sats = tx_fee_sats * 2

            # Send everything to receiver minus fee
            actual_receiver_amount = funding_value - tx_fee_sats
            
            if actual_receiver_amount <= 0:
                raise ValueError(f"Fee ({tx_fee_sats} sats) exceeds available funds ({funding_value} sats)")
            
            txouts.append(CMutableTxOut(
                actual_receiver_amount,
                CEvrmoreAddress(receiver_addr).to_scriptPubKey()
            ))
        
        # Case 4: Remainder is significant - take fee from remainder
        else:
            # in this case we have 1 input and 2 output
            tx_fee_sats = tx_fee_sats * 3

            # Receiver gets exactly what was specified
            txouts.append(CMutableTxOut(
                pay_to_receiver_sats,
                CEvrmoreAddress(receiver_addr).to_scriptPubKey()
            ))
            
            # Channel gets remainder minus fee
            change_amount = remainder - tx_fee_sats
            
            if change_amount <= 0:
                raise ValueError(f"Fee ({tx_fee_sats} sats) exceeds remainder ({remainder} sats)")
            
            txouts.append(CMutableTxOut(
                change_amount,
                script_pub  # Using same P2SH address for the remainder
            ))

        # Check that we have at least one output
        if not txouts:
            raise ValueError("Transaction must have at least one output after fee deduction")
        
        # Create the transaction with Alice's signature
        tx = self._createPartialOriginatorSimple([txin], [script_pub], txouts)
        return self._txToHex(tx)

    # 4. Bob finalises & broadcasts  ────────────────────────────────────────────────
    def finaliseCommitmentTx(
        self, 
        partial_tx_hex: str,
        redeem_script: CScript
    ) -> str:
        """
        Adds Bob's signature, returns fully-signed tx hex.
        """
        tx = self._deserialize(bytes.fromhex(partial_tx_hex))
        txin = tx.vin[0]
        script_pub = P2SHEvrmoreAddress.from_redeemScript(redeem_script).to_scriptPubKey()

        # extract Alice's existing sig
        old_sigs = [e for e in txin.scriptSig if isinstance(e, bytes)]

        # add Bob's sig
        self._signInput(tx, 0, txin, script_pub, SIGHASH_ALL,
                        redeem_script=redeem_script,
                        signatures=old_sigs)

        return self._txToHex(tx)
#Usage sketch
#
#python
#Copy
#Edit
#alice = EvrmoreWallet.create(...)
#bob   = EvrmoreWallet.create(...)
#
## open channel (Alice side)
#redeem, chan_addr, fund_hex = alice.openPaymentChannel(
#    bob_pub=bob._privateKeyObj.pub,
#    amount_sats=100_000_000,             # 1 EVR
#    abs_timeout=height_or_time)
#
## after fund_hex is mined …
#commit_hex = alice.createCommitmentTx(
#    funding_txid=<txid>, vout=<n>, funding_value=100_000_000,
#    redeem_script=redeem,
#    pay_sats=3_000_000,                 # 0.03 EVR
#    bob_addr=bob.address)
#
## Bob finishes and broadcasts
#final_hex = bob.finaliseCommitmentTx(commit_hex, redeem)
#electrumx.broadcast(final_hex)    