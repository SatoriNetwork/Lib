# P2SH Payment Channels Documentation

## Overview

P2SH (Pay-to-Script-Hash) allows locking funds to a script hash rather than a simple address. The funds can only be spent by providing the original script (redeem script) and satisfying its conditions. This implementation uses P2SH to create payment channels on the Evrmore blockchain.

## Architecture

### Key Components

1. **Redeem Script Creation** (`evrmore/scripts.py`)
   - Contains `P2SHRedeemScripts` class
   - Generates various types of redeem scripts for different channel types

2. **Channel Management** (`evrmore/wallet.py`)
   - Opening/funding channels
   - Creating commitment transactions
   - Finalizing and broadcasting transactions

3. **Transaction Utilities** (`utils/transaction.py`)
   - Fee estimation
   - Amount conversions
   - Address handling

## Payment Channel Flow

### 1. Channel Opening (Funding)

```python
def generatePaymentChannel(self, redeemScript, amount):
    # Creates P2SH address from redeem script
    p2shAddress = self.generateP2SHAddress(redeemScript)
    
    # Creates transaction that locks funds to this P2SH address
    # Returns: (redeem_script, p2sh_address, funding_tx_hex)
```

**Example Usage:**
```python
redeem_script, p2sh_address, funding_tx_hex = wallet.generatePaymentChannel(
    amount=24,
    redeemScript=wallet.scripts.renewable_light_channel(
        sender=wallet.publicKeyBytes,
        receiver=other.pubkey,
        blocks=60*60*24))  # timeout in blocks

tx = wallet.broadcast(funding_tx_hex)
```

This creates a funding transaction that locks EVR into the payment channel at the P2SH address.

### 2. Commitment Transactions

Commitment transactions are how payments are made through the channel:

```python
def generateCommitmentTx(
    self, 
    funding_txid,           # The funding tx that locked the funds
    vout,                   # Output index in funding tx
    funding_value,          # Total locked amount in satoshis
    redeem_script,          # The script that controls spending
    pay_to_receiver_sats,   # Amount to pay
    receiver_addr,          # Where to send payment
    tx_fee_sats=12000,      # Transaction fee (default 0.00012 EVR)
):
```

**Key Features:**
- Spends from the P2SH output (locked funds)
- Sends payment to receiver's address
- Returns change back to P2SH address (if significant)

#### Dust Handling Logic

The implementation includes smart dust handling:

1. **No remainder or dust amount** (< 3x fee)
   - Send everything to receiver minus fee
   - Single output transaction

2. **Significant remainder** (≥ 3x fee)
   - Receiver gets exact payment amount
   - Remainder minus fee returns to channel
   - Two output transaction

3. **Dust zone protection**
   - Prevents creating outputs in the "dust zone"
   - Configurable via `respect_dust_zone` parameter

### 3. Transaction Finalization

Since payment channels typically use 2-of-2 multisig, both parties must sign:

```python
def finaliseCommitmentTx(self, partial_tx_hex, redeem_script):
    # Extract Alice's existing signature
    # Add Bob's signature
    # Return fully-signed transaction
```

**Process:**
1. Alice creates and signs commitment transaction
2. Bob adds his signature to complete it
3. Bob can broadcast when ready to claim payment

## How P2SH Works Under the Hood

### Creating a P2SH Address

```python
# 1. Hash the redeem script
script_hash = Hash160(redeem_script)

# 2. Create address with network-specific prefix
# Evrmore mainnet P2SH prefix: 92 (0x5C)
p2sh_address = base58_encode(0x5C + script_hash + checksum)
```

### Spending from P2SH

When spending from a P2SH output, the transaction must provide:

1. **Signatures** satisfying the redeem script conditions
2. **The redeem script itself** (to prove it hashes to the script hash)

```python
if redeem_script:
    # Sign the redeem script, not the scriptPubKey
    sighash = SignatureHash(redeem_script, tx, i, sighashFlag)
    sig = self.identity._privateKeyObj.sign(sighash)
    
    # ScriptSig format: [signatures..., redeem_script]
    txin.scriptSig = CScript([sig1, sig2, ..., redeem_script])
```

## Redeem Script Types

### Renewable Light Channel

Expected structure (based on usage):
```
IF
    # Normal case: both parties cooperate
    2 <Alice's pubkey> <Bob's pubkey> 2 CHECKMULTISIG
ELSE
    # Timeout case: sender can reclaim after delay
    <timeout_blocks> CHECKLOCKTIMEVERIFY DROP
    <Alice's pubkey> CHECKSIG
ENDIF
```

This allows:
- **Cooperative close**: Both parties sign together anytime
- **Unilateral close**: Sender reclaims funds after timeout

### Multi-Signature Scripts

Standard m-of-n multisig for shared control:
```python
# 2-of-3 multisig example
redeem_script = wallet.scripts.multiSig([pubkey1, pubkey2, pubkey3], 2)
```

## Payment Channel Concept

This implements a **unidirectional payment channel**:

### Lifecycle Example

1. **Alice funds channel** with 1 EVR
2. **Progressive payments**:
   - Payment 1: 0.1 EVR to Bob, 0.9 EVR remains in channel
   - Payment 2: 0.2 EVR to Bob, 0.8 EVR remains in channel
   - Payment 3: 0.3 EVR to Bob, 0.7 EVR remains in channel
3. **Channel closing**: Bob broadcasts last commitment transaction

### Advantages
- Multiple payments with only 2 on-chain transactions
- Reduced transaction fees
- Instant payments (no confirmation wait)
- Privacy (intermediate payments not on-chain)

## Network Configuration

### Evrmore Network Bytes
- **P2PKH prefix**: 33 (0x21) - Regular addresses start with 'E'
- **P2SH prefix**: 92 (0x5C) - Script addresses start with 'e'
- **Secret key prefix**: 128 (0x80)

## Implementation Status

### Completed ✅
- Basic P2SH transaction creation
- Commitment transaction generation
- Multi-signature support
- Dust handling logic
- Transaction signing for P2SH inputs
- P2SH address generation

### Incomplete/TODO ❓
- Complete redeem script templates in `scripts.py`
- Channel state management (tracking latest commitment)
- Revocation mechanism (preventing old state broadcasts)
- Channel closure handling
- Dispute resolution logic
- Persistent storage of channel states
- Channel monitoring service

## Security Considerations

1. **Private Key Security**
   - Never share private keys
   - Sign transactions offline when possible

2. **Commitment Transaction Management**
   - Only broadcast latest commitment
   - Implement revocation for old states

3. **Timeout Values**
   - Choose appropriate timeout blocks
   - Consider blockchain congestion

4. **Fee Estimation**
   - Monitor network fee rates
   - Include sufficient fees for timely confirmation

## Example: Complete Channel Flow

```python
# 1. Create wallets
alice = EvrmoreWallet.create(walletPath="alice.yaml")
bob = EvrmoreWallet.create(walletPath="bob.yaml")

# 2. Alice opens channel to Bob
redeem_script, p2sh_addr, funding_hex = alice.generatePaymentChannel(
    redeemScript=alice.scripts.renewable_light_channel(
        sender=alice.publicKeyBytes,
        receiver=bob.publicKeyBytes,
        blocks=144),  # ~24 hours timeout
    amount=1.0)  # 1 EVR

# 3. Broadcast funding transaction
funding_txid = alice.broadcast(funding_hex)

# 4. Create commitment transaction (Alice pays Bob 0.1 EVR)
commitment_hex = alice.generateCommitmentTx(
    funding_txid=funding_txid,
    vout=0,
    funding_value=100_000_000,  # 1 EVR in satoshis
    redeem_script=redeem_script,
    pay_to_receiver_sats=10_000_000,  # 0.1 EVR
    receiver_addr=bob.address)

# 5. Bob finalizes and can broadcast when ready
final_hex = bob.finaliseCommitmentTx(commitment_hex, redeem_script)
txid = bob.broadcast(final_hex)
```

## Testing Recommendations

1. **Unit Tests**
   - Test redeem script generation
   - Verify P2SH address creation
   - Test signature validation

2. **Integration Tests**
   - Test full channel lifecycle on testnet
   - Verify timeout conditions
   - Test dispute scenarios

3. **Edge Cases**
   - Dust amount handling
   - Fee exhaustion scenarios
   - Concurrent channel updates

## References

- [BIP 16 - Pay to Script Hash](https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki)
- [Lightning Network Paper](https://lightning.network/lightning-network-paper.pdf)
- [Evrmore Asset Layer](https://evrmore.com/assets)