import logging
import unittest
from unittest.mock import MagicMock, patch
from evrmore.wallet import CEvrmoreSecret, P2SHEvrmoreAddress
from satorilib.wallet.evrmore.walletsh import EvrmoreP2SHWallet
from evrmore.core.transaction import CMultiSigTransaction

class TestEvrmoreP2SHWallet(unittest.TestCase):

    def setUp(self):
        """Setup wallet and mock environment."""
        self.wallet = EvrmoreP2SHWallet(wallet_path="test_wallet.dat", is_testnet=False)

        self.private_keys = [
            CEvrmoreSecret('KxcXS9BzcRsZbqXhCK3sCTmSPW8Txh77iBAvB4fVM9BLJ7hJzEuF'),
            CEvrmoreSecret('L5h5ULcJCniNMZSVF1EcftQXAoVqsZCB88KNGXhncmZ51LvodoGq'),
            CEvrmoreSecret('KyWWcQpcqZqXKEkT7peHaj2f4SXBgRH2wWzEHzU1Z8AZWFh4w69C')
        ]

        self.public_keys = [key.pub for key in self.private_keys]
        self.recipient_address = 'EZganBbjrEmNZHW3ZYntpWWRNmMVNSbxt4'
        self.txid = '999e627c1c9bfd3a2cd1fdcfbb0209880b32cfba538a7fa5364159740611e817'
        self.vout_index = 0
        self.amount_to_send = 1

    @patch('satorilib.wallet.evrmore.walletsh.EvrmoreP2SHWallet.create_electrumx_connection')
    def test_generate_multi_party_p2sh_address(self, mock_electrumx):
        """Test generating a multi-party P2SH address."""
        mock_electrumx.return_value.api.getUnspentAssets = MagicMock(return_value=[])
        
        p2sh_address, redeem_script = self.wallet.generate_multi_party_p2sh_address(
            self.public_keys, required_signatures=2
        )
        self.assertIsNotNone(p2sh_address, "P2SH address generation failed.")
        self.assertIsNotNone(redeem_script, "Redeem script generation failed.")
        
        fetched_utxos = self.wallet.fetch_utxos("EVRMORE")
        logging.info(f"fetched utxos: {fetched_utxos}")
        
        self.assertEqual(len(self.public_keys), 3)
        print(f"Generated P2SH Address: {p2sh_address}")
        
    def test_fetch_utxos_known_address(self):
        """Test UTXO fetching with a known funded address."""
        self.wallet.p2sh_address = P2SHEvrmoreAddress("eEY5brnAULc9wnr2Evfr31rdUHpoZbn1Uq")  
        fetched_stori_utxos = self.wallet.fetch_utxos("SATORI")
        fetched_evr_utxos = self.wallet.fetch_utxos()
        
        self.assertIsInstance(fetched_stori_utxos, list)
        self.assertIsInstance(fetched_evr_utxos, list)
        print("Fetched SATORI UTXOs: ", fetched_stori_utxos)
        print("Fetched EVR UTXOs: ", fetched_evr_utxos)

    def test_create_unsigned_transaction(self):
        """Test creating an unsigned transaction using a specific P2SH address."""
        # Set a known P2SH address with pre-existing UTXOs
        self.wallet.p2sh_address = P2SHEvrmoreAddress("eEY5brnAULc9wnr2Evfr31rdUHpoZbn1Uq")
                
        # Test with SATORI asset
        unsigned_tx_satori = self.wallet.create_unsigned_transaction(
            amount=self.amount_to_send,
            recipient_address=self.recipient_address,
            asset="SATORI"
        )
        self.assertIsNotNone(unsigned_tx_satori, "Failed to create unsigned transaction for SATORI asset.")
        print(f"unsigned_tx_satori: {unsigned_tx_satori}")
        # Test with EVR asset (asset=None)
        unsigned_tx_evr = self.wallet.create_unsigned_transaction(
            amount=self.amount_to_send,
            recipient_address=self.recipient_address,
            asset=None
        )
        self.assertIsNotNone(unsigned_tx_evr, "Failed to create unsigned transaction for EVR asset.")
        print(f"unsigned_tx_evr: {unsigned_tx_evr}")
    
    def test_sign_transaction(self):
        """Test signing a transaction."""
        # Set a known P2SH address with pre-existing UTXOs
        self.wallet.p2sh_address = P2SHEvrmoreAddress("eEY5brnAULc9wnr2Evfr31rdUHpoZbn1Uq")

        self.wallet.generate_multi_party_p2sh_address(self.public_keys, required_signatures=2)
        unsigned_tx = self.wallet.create_unsigned_transaction(
            amount=self.amount_to_send,
            recipient_address=self.recipient_address,
            asset="SATORI"
        )
        
        sighash = self.wallet.generate_sighash(unsigned_tx)
        
        # Independent signing with each key
        signatures = [
            self.wallet.sign_independently(unsigned_tx, self.private_keys[0], sighash),
            self.wallet.sign_independently(unsigned_tx, self.private_keys[1], sighash)
        ]

        # Apply the collected signatures
        signed_tx = self.wallet.apply_signatures(unsigned_tx, signatures)
        print(f"signed_tx: {signed_tx}")
        self.assertIsNotNone(signed_tx)
        print("Transaction Signed Successfully.")

    def test_broadcast_transaction(self):
        """Test broadcasting a transaction."""
        # Set a known P2SH address with pre-existing UTXOs
        self.wallet.p2sh_address = P2SHEvrmoreAddress("eEY5brnAULc9wnr2Evfr31rdUHpoZbn1Uq")

        self.wallet.generate_multi_party_p2sh_address(self.public_keys, required_signatures=2)
        unsigned_tx = self.wallet.create_unsigned_transaction(
            amount=self.amount_to_send,
            recipient_address=self.recipient_address,
            asset="SATORI"
        )
        
        sighash = self.wallet.generate_sighash(unsigned_tx)
        
        # Independent signing with each key
        signatures = [
            self.wallet.sign_independently(unsigned_tx, self.private_keys[0], sighash),
            self.wallet.sign_independently(unsigned_tx, self.private_keys[1], sighash)
        ]

        # Apply signatures and broadcast
        signed_tx = self.wallet.apply_signatures(unsigned_tx, signatures)
        txid = self.wallet.broadcast_transaction(signed_tx)
        
        self.assertIsNotNone(txid, "Failed to broadcast transaction.")
        print(f"Transaction Broadcasted Successfully with txid: {txid}")

if __name__ == '__main__':
    unittest.main()
