import logging
from evrmore.wallet import CEvrmoreSecret, CEvrmoreAddress
#from satorilib.wallet.evrmore.walletsh import EvrmoreP2SHWallet
from satorilib.wallet import wallet

# Initialize the wallet instance with the correct number of signatures
#wallet = EvrmoreP2SHWallet(wallet_path="test_wallet.dat", is_testnet=False)

# Restore previously saved private keys
private_keys = [
    CEvrmoreSecret('KxcXS9BzcRsZbqXhCK3sCTmSPW8Txh77iBAvB4fVM9BLJ7hJzEuF'),
    CEvrmoreSecret('L5h5ULcJCniNMZSVF1EcftQXAoVqsZCB88KNGXhncmZ51LvodoGq'),
    CEvrmoreSecret('KyWWcQpcqZqXKEkT7peHaj2f4SXBgRH2wWzEHzU1Z8AZWFh4w69C')
]

# Convert private keys to public keys
public_keys = [key.pub for key in private_keys]
# The P2SH address and UTXO details
recipient_address = 'EZganBbjrEmNZHW3ZYntpWWRNmMVNSbxt4'
txid = '999e627c1c9bfd3a2cd1fdcfbb0209880b32cfba538a7fa5364159740611e817'
vout_index = 0
amount_to_send = 95000000

# Generate a new P2SH address and redeem script based on the private keys
try:
    p2sh_address, redeem_script = wallet.generate_multi_party_p2sh_address(public_keys, required_signatures=2)
    if not p2sh_address:
        raise ValueError("Failed to generate P2SH address and redeem script.")
    print(f"Generated P2SH Address: {p2sh_address}")
    logging.info(f"Redeem Script: {redeem_script}")
except Exception as e:
    logging.error(f"Error generating P2SH address: {e}")
    raise

# Step 1: Create an unsigned transaction
try:
    logging.info("Creating an unsigned transaction...")
    unsigned_tx = wallet.create_unsigned_transaction(txid, vout_index, amount_to_send, recipient_address)
    if not unsigned_tx:
        raise ValueError("Failed to create an unsigned transaction.")
    logging.info("Unsigned transaction created successfully.")
except Exception as e:
    logging.error(f"Error creating unsigned transaction: {e}")
    raise

# Step 2: Sign the transaction using the wallet's sign_transaction method
try:
    logging.info("Signing the transaction...")
    selected_private_keys = private_keys[:2]
    print(selected_private_keys, "privated selcted")
    signed_tx = wallet.sign_transaction(unsigned_tx, selected_private_keys)
    if not signed_tx:
        raise ValueError("Failed to sign the transaction.")
    signed_tx_hex = signed_tx.serialize().hex()
    logging.info(f"Signed transaction hex: {signed_tx_hex}")
    print(f"Signed Transaction Hex:\n{signed_tx_hex}")
except Exception as e:
    logging.error(f"Error signing the transaction: {e}")
    raise

# (Optional) Broadcast the signed transaction to the network
try:
    logging.info("Broadcasting the transaction...")
    broadcast_result = wallet.broadcast_transaction(signed_tx)
    logging.info(f"Transaction broadcast result: {broadcast_result}")
except Exception as e:
    logging.error(f"Error broadcasting the transaction: {e}")
    raise
