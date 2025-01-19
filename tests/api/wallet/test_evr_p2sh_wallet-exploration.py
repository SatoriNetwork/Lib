class TestEvrmoreP2SHWalletProcessNotes():
    '''https://chatgpt.com/share/678d5947-c75c-800f-b073-22494700216d'''

    def step1(self):
        '''
        1. Instantiating the Wallet
        You typically create a wallet instance by calling:
        '''
        from satorilib.wallet.evrmore.walletsh import EvrmoreP2SHWallet
        self.wallet = EvrmoreP2SHWallet(
            wallet_path='/Satori/Neuron/wallet-testing/wallet-2.yaml',
            is_testnet=False,     # or True, if you're on testnet
            required_signatures=2 # how many signatures are required in the multisig
        )
        '''
        wallet_path is just where it might store or load wallet data.
        is_testnet toggles network parameters.
        required_signatures is how many total sigs you need in your multisig.
        If you already have an Electrumx server you want to connect to, you can pass it as electrumx=someElectrumxInstance, but if not given, it will pick from its defaults.
        '''

    def step2a(self):
        '''
        2. Generating (or Reconstructing) a Multi‐Sig P2SH Address
        Single‐Party "Generate" (test/dev scenario)
        If you just want to test by generating multiple private keys yourself:
        '''
        p2sh_address, redeem_script = self.wallet.generate_single_party_p2sh_address(
            num_keys=3,             # total keys to generate
            required_signatures=2   # 2 of 3 needed to sign
        )
        print("P2SH Address:", p2sh_address)
        print("Redeem Script:", redeem_script.hex())
        '''
        This auto‐generates 3 private keys internally, sets wallet.private_keys and wallet.public_keys, and creates a standard 2-of-3 redeem script. In real multi‐party usage, you’d rarely do it this way—because each participant would want their own private key.
        '''

    def step2b(self, public_keys):
        '''
        2. Generating (or Reconstructing) a Multi‐Sig P2SH Address
        Multi‐Party "Combine"
        If you already have your own private key and you’ve collected other participants’ public keys, you can do:
        # Suppose these are your co-signers' public keys
        public_keys = [
            someUser_pubKey,
            someOtherUser_pubKey,
            ...
        ]
        '''
        p2sh_address, redeem_script = self.wallet.generate_multi_party_p2sh_address(
            public_keys=public_keys,
            required_signatures=2
        )
        print("P2SH Address:", p2sh_address)
        '''
        This method:
        Builds the multisig redeem script from those public keys and required_signatures.
        Stores self.redeem_script and self.p2sh_address.
        Returns (p2sh_address, redeem_script).
        Yes, you do need the public keys of every participant because that’s how the redeem script is constructed for a P2SH multisig.
        '''

    def step3(self):
        '''
        3. Funding the P2SH Address
        Once you have that P2SH address, you simply send funds to it (e.g. from an exchange or normal wallet). The script in walletsh.py doesn’t manage that piece; you just need to wait until you see the UTXO(s) on the address.
        '''

    def step4(self):
        '''
        4. Creating an Unsigned Transaction
        When you want to spend from that P2SH:
        '''
        unsigned_tx = self.wallet.create_unsigned_transaction(
            txid="abcdef1234...",   # The UTXO transaction id
            vout_index=0,           # which output index in that tx
            amount=95000000,        # how many satoshis to send
            recipient_address="EZganBbjrEmNZHW3ZYntpWWRNmMVNSbxt4"
        )
        '''
        This returns a CMultiSigTransaction (subclass of CMutableTransaction) with the input referencing your P2SH’s UTXO and one output for the recipient.
        Important: for a real multi‐party scenario, you’d share this raw unsigned transaction (usually as hex) with all the signers so they can each apply their signature.
        '''

    def step5a(self, unsigned_tx):
        '''
        5. Signing the Transaction (Partial or Complete)
        All Signers at Once (if you have all the keys)
        If you happen to have all the private keys (like in a test environment), you can sign with them all at once:
        '''
        signed_tx = self.wallet.sign_transaction(
            tx=unsigned_tx,
            private_keys=self.wallet.private_keys
        )
        signed_hex = signed_tx.serialize().hex()
        '''
        Internally, this calls tx.sign_with_multiple_keys(...) for each key and updates the transaction’s scriptSig(s).
        Once you’ve got the fully‐signed transaction, you can broadcast it via wallet.broadcast_transaction(signed_tx).
        '''

    def step5b(self, unsigned_tx):
        '''
        5. Signing the Transaction (Partial or Complete)
        Partial Signing (Typical Multi‐Party Flow)
        If you only have one of the private keys, you can pass just that one:
        '''
        partial_tx = self.wallet.sign_transaction(
            tx=unsigned_tx,
            private_keys=[self.wallet._privateKeyObj]
        )

        ## That yields a transaction that now includes one signature in its scriptSig. You’d serialize it:

        partial_hex = partial_tx.serialize().hex()

        ## Then you give that partially signed transaction (the hex) to the next cosigner. The next cosigner would do something like:

        from satorilib.wallet.evrmore.walletsh import CMultiSigTransaction
        # They reconstruct the transaction from hex
        their_tx_obj = CMultiSigTransaction.deserialize(bytes.fromhex(partial_hex))

        # Then sign with their key:
        second_sign_tx = self.wallet.sign_transaction(
            tx=their_tx_obj,
            private_keys=[self.wallet._privateKeyObj]
        )

        # The result now has at least two signatures.
        fully_signed_hex = second_sign_tx.serialize().hex()
        '''
        At that point, if 2 of 3 was required, you have enough signatures, and can broadcast.
        The code is somewhat simplified—sign_transaction basically expects you to pass all the private keys you want to apply at once. But calling it multiple times in succession works too, as long as the transaction object you pass in carries the existing signatures in scriptSig.
        '''

    def step6(self, signed_tx):
        '''
        6. Broadcasting the Transaction
        Finally, once you have a fully‐signed transaction, you broadcast:
        '''
        self.wallet.broadcast_transaction(signed_tx)
        '''
        which uses the Electrumx API to push it onto the network. If successful, it returns the final txid.
        '''
