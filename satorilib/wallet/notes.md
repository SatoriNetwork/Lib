def generate_multi_party_p2sh_address(self, public_keys: List[bytes], required_signatures: int) -> Tuple[P2SHEvrmoreAddress, CScript]:
        """Generates a multi-party P2SH address."""
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

def setUp(self):
        # Create test keys
        self.private_keys = []
        self.public_keys = []
        for _ in range(3):
            privkey = CECKey()
            privkey.set_secretbytes(os.urandom(32))
            self.private_keys.append(privkey)
            self.public_keys.append(CPubKey(privkey.get_pubkey()))

