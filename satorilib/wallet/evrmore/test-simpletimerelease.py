#!/usr/bin/env python3
"""
Manual Test Script for Simple Time Release P2SH

This script provides functions to manually test the simpleTimeRelease P2SH implementation.
Run each step sequentially and verify the expected outcomes.

REQUIREMENTS:
- Two wallets (Alice and Bob)
- Some EVR for transaction fees
- Access to Evrmore testnet or mainnet
- ElectrumX connection

TEST SCENARIO:
Alice creates a P2SH address where:
- Alice can retrieve funds immediately
- Bob can retrieve funds only after a timeout
"""

import time
import datetime as dt
from typing import Tuple
from satorilib.wallet.evrmore.wallet import EvrmoreWallet
from satorilib.wallet.evrmore.scripts import P2SHRedeemScripts
from satorilib.electrumx import Electrumx
from evrmore.core import b2x, lx
from evrmore.core.script import CScript
from satorilib import logging

# Configuration
USE_TESTNET = True  # Set to False for mainnet
LOCKTIME_BLOCKS = 10  # Number of blocks for timeout (10 blocks = ~10 minutes for testing)
FUNDING_AMOUNT = 0.1  # Amount of EVR to lock in P2SH

# Global variables to store test state
alice_wallet = None
bob_wallet = None
redeem_script = None
p2sh_address = None
funding_txid = None
funding_vout = None
funding_value = None


def setup_wallets():
    """
    Step 1: Initialize Alice and Bob's wallets
    
    TODO: Update paths and connection details as needed
    """
    global alice_wallet, bob_wallet
    
    print("=" * 60)
    print("STEP 1: Setting up wallets")
    print("=" * 60)
    
    # TODO: Update these paths to your actual wallet files
    # TODO: Ensure ElectrumX connection details are correct
    
    # Alice's wallet (immediate spender)
    alice_wallet = EvrmoreWallet.create(
        walletPath="alice-wallet.yaml",
        password=None,  # TODO: Add password if encrypted
        electrumx=Electrumx.create(
            hostPort="electrumx.evrmore.com:50001",  # TODO: Update with actual server
            persistent=True
        )
    )
    
    # Bob's wallet (delayed spender)
    bob_wallet = EvrmoreWallet.create(
        walletPath="bob-wallet.yaml",
        password=None,  # TODO: Add password if encrypted
        electrumx=Electrumx.create(
            hostPort="electrumx.evrmore.com:50001",  # TODO: Update with actual server
            persistent=True
        )
    )
    
    # Get current balances
    alice_wallet.get()
    bob_wallet.get()
    
    print(f"Alice's address: {alice_wallet.address}")
    print(f"Alice's balance: {alice_wallet.currency.amount} EVR")
    print(f"Bob's address: {bob_wallet.address}")
    print(f"Bob's balance: {bob_wallet.currency.amount} EVR")
    
    # Verify Alice has enough funds
    if alice_wallet.currency.amount < FUNDING_AMOUNT + 0.01:  # Extra for fees
        print(f"⚠️  WARNING: Alice needs at least {FUNDING_AMOUNT + 0.01} EVR to run this test")
        print(f"   Current balance: {alice_wallet.currency.amount} EVR")
        return False
    
    print("✅ Wallets initialized successfully")
    return True


def create_timerelease_script():
    """
    Step 2: Create the simple time release redeem script
    
    Alice can spend immediately, Bob can spend after timeout
    """
    global redeem_script, p2sh_address
    
    print("\n" + "=" * 60)
    print("STEP 2: Creating time release script")
    print("=" * 60)
    
    # Get current block height for calculating absolute locktime
    # TODO: You might need to implement a way to get current block height
    # For now, we'll use a hardcoded future block
    current_block = 200000  # TODO: Get actual current block height
    locktime_block = current_block + LOCKTIME_BLOCKS
    
    print(f"Current block (estimated): {current_block}")
    print(f"Locktime block: {locktime_block}")
    print(f"Bob must wait {LOCKTIME_BLOCKS} blocks (~{LOCKTIME_BLOCKS} minutes)")
    
    # Create the redeem script
    #redeem_script = P2SHRedeemScripts.simpleTimeRelease(
    #    immediate_key=alice_wallet.pubkey,  # Alice can unlock anytime
    #    delayed_key=bob_wallet.pubkey,      # Bob can unlock after timeout
    #    locktime=locktime_block,             # Absolute block height
    #    use_blocks=True
    #)
      # Option 3: Using a specific future date
    specific_date = dt.datetime(2024, 12, 31, 12, 0, 0)  # Dec 31, 2024 at noon
    redeem_script = P2SHRedeemScripts.simpleTimeRelease(
        immediate_key=alice_wallet.pubkey,
        delayed_key=bob_wallet.pubkey,
        locktime=specific_date,
        use_blocks=False
    )
    
    # Generate P2SH address from redeem script
    p2sh_address = alice_wallet.generateP2SHAddress(redeem_script)
    
    print(f"P2SH Address: {p2sh_address}")
    print(f"Redeem script hex: {b2x(redeem_script)}")
    print(f"Redeem script size: {len(redeem_script)} bytes")
    
    print("\n📋 Script logic:")
    print("  - Alice can spend: IMMEDIATELY")
    print(f"  - Bob can spend: AFTER block {locktime_block}")
    
    print("✅ Time release script created successfully")
    return True


def fund_p2sh_address():
    """
    Step 3: Alice funds the P2SH address
    
    This locks the funds according to the redeem script rules
    """
    global funding_txid, funding_vout, funding_value
    
    print("\n" + "=" * 60)
    print("STEP 3: Funding the P2SH address")
    print("=" * 60)
    
    print(f"Alice will send {FUNDING_AMOUNT} EVR to P2SH address: {p2sh_address}")
    
    # Alice creates a simple transaction to the P2SH address
    # TODO: This is a simplified version - you might need to adapt based on actual wallet methods
    try:
        # Use the wallet's existing transaction methods
        # This is a regular send, not a P2SH-specific transaction
        funding_txid = alice_wallet.currencyTransaction(
            amount=FUNDING_AMOUNT,
            address=p2sh_address
        )
        
        # For testing, we'll assume vout is 0 (first output)
        # In production, you'd need to examine the transaction to find the correct output
        funding_vout = 0
        funding_value = int(FUNDING_AMOUNT * 100_000_000)  # Convert to satoshis
        
        print(f"✅ Funding transaction broadcast!")
        print(f"   TxID: {funding_txid}")
        print(f"   Output index: {funding_vout}")
        print(f"   Value: {funding_value} satoshis ({FUNDING_AMOUNT} EVR)")
        
        print("\n⏳ Wait for confirmation before proceeding to next step...")
        print("   You can check the transaction on the explorer")
        
        return True
        
    except Exception as e:
        print(f"❌ Error funding P2SH address: {e}")
        return False


def alice_spend_immediate():
    """
    Step 4A: Alice attempts to spend immediately (should succeed)
    
    Alice provides: 0 <signature_for_alice>
    This selects the ELSE branch which allows immediate spending
    """
    print("\n" + "=" * 60)
    print("STEP 4A: Alice spending immediately")
    print("=" * 60)
    
    if not funding_txid:
        print("❌ No funding transaction found. Run step 3 first.")
        return False
    
    print("Alice is attempting to spend the funds immediately...")
    print("This should SUCCEED because Alice has immediate access")
    
    try:
        # Create a transaction that spends from the P2SH
        # The commitment transaction will need Alice's signature with the unlock script: 0 <sig>
        
        # TODO: This is where you'd create the actual spending transaction
        # The key part is providing the correct unlock script:
        # - Stack: 0 <alice_signature> <redeem_script>
        # - The 0 selects the ELSE branch (immediate spend)
        
        print("\n📝 Unlock script structure:")
        print("   0 (select ELSE branch)")
        print("   <alice_signature>")
        print("   <redeem_script>")
        
        # Placeholder for actual transaction creation
        # You might use something like:
        # tx_hex = alice_wallet.createP2SHSpendTransaction(
        #     funding_txid=funding_txid,
        #     vout=funding_vout,
        #     amount=funding_value - 10000,  # Minus fee
        #     to_address=alice_wallet.address,
        #     redeem_script=redeem_script,
        #     branch_selector=0  # ELSE branch
        # )
        
        print("\n⚠️  TODO: Implement actual P2SH spending transaction")
        print("   The transaction should spend to Alice's regular address")
        
        # If implemented, broadcast would look like:
        # txid = alice_wallet.broadcast(tx_hex)
        # print(f"✅ Transaction broadcast! TxID: {txid}")
        
    except Exception as e:
        print(f"❌ Error creating spending transaction: {e}")
        return False
    
    return True


def bob_spend_early():
    """
    Step 4B: Bob attempts to spend before timeout (should fail)
    
    Bob provides: 1 <signature_for_bob>
    This selects the IF branch which requires the locktime to pass
    """
    print("\n" + "=" * 60)
    print("STEP 4B: Bob attempting to spend early (before timeout)")
    print("=" * 60)
    
    if not funding_txid:
        print("❌ No funding transaction found. Run step 3 first.")
        return False
    
    print("Bob is attempting to spend the funds BEFORE the timeout...")
    print("This should FAIL because the locktime hasn't passed")
    
    try:
        print("\n📝 Unlock script structure:")
        print("   1 (select IF branch)")
        print("   <bob_signature>")
        print("   <redeem_script>")
        
        # TODO: Create spending transaction with Bob's signature
        # This should fail when broadcast because locktime hasn't passed
        
        print("\n⚠️  TODO: Implement actual P2SH spending transaction")
        print("   Expected result: Transaction rejected due to locktime")
        
        # Example of what might happen:
        # try:
        #     tx_hex = bob_wallet.createP2SHSpendTransaction(...)
        #     txid = bob_wallet.broadcast(tx_hex)
        #     print("❌ Unexpected: Transaction was accepted! This shouldn't happen")
        # except Exception as e:
        #     if "non-final" in str(e) or "locktime" in str(e):
        #         print("✅ Expected failure: Transaction rejected due to locktime")
        #     else:
        #         print(f"❌ Unexpected error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    return True


def bob_spend_after_timeout():
    """
    Step 4C: Bob attempts to spend after timeout (should succeed)
    
    Bob provides: 1 <signature_for_bob>
    This selects the IF branch, and locktime should now be satisfied
    """
    print("\n" + "=" * 60)
    print("STEP 4C: Bob spending after timeout")
    print("=" * 60)
    
    if not funding_txid:
        print("❌ No funding transaction found. Run step 3 first.")
        return False
    
    print(f"Bob is attempting to spend the funds AFTER {LOCKTIME_BLOCKS} blocks...")
    print("This should SUCCEED because the locktime has passed")
    
    try:
        print("\n📝 Unlock script structure:")
        print("   1 (select IF branch)")
        print("   <bob_signature>")
        print("   <redeem_script>")
        
        # TODO: Create spending transaction with Bob's signature
        # This should succeed if enough blocks have passed
        
        print("\n⚠️  TODO: Implement actual P2SH spending transaction")
        print("   Expected result: Transaction accepted and broadcast")
        
        # Example:
        # tx_hex = bob_wallet.createP2SHSpendTransaction(
        #     funding_txid=funding_txid,
        #     vout=funding_vout,
        #     amount=funding_value - 10000,  # Minus fee
        #     to_address=bob_wallet.address,
        #     redeem_script=redeem_script,
        #     branch_selector=1  # IF branch
        # )
        # txid = bob_wallet.broadcast(tx_hex)
        # print(f"✅ Transaction broadcast! TxID: {txid}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def run_test_sequence():
    """
    Main test sequence - run this to execute all tests
    """
    print("\n" + "🚀 " * 20)
    print("SIMPLE TIME RELEASE P2SH - MANUAL TEST SEQUENCE")
    print("🚀 " * 20)
    
    print("\nThis test will demonstrate:")
    print("1. Creating a time-locked P2SH address")
    print("2. Funding the address")
    print("3. Attempting to spend with different keys at different times")
    
    print("\n⚠️  IMPORTANT: This uses real EVR on the network!")
    print("Make sure you're using testnet or small amounts")
    
    input("\nPress Enter to begin setup...")
    
    # Step 1: Setup wallets
    if not setup_wallets():
        print("❌ Failed to setup wallets")
        return
    
    input("\nPress Enter to create time release script...")
    
    # Step 2: Create time release script
    if not create_timerelease_script():
        print("❌ Failed to create script")
        return
    
    input("\nPress Enter to fund the P2SH address...")
    
    # Step 3: Fund the P2SH address
    if not fund_p2sh_address():
        print("❌ Failed to fund address")
        return
    
    print("\n" + "-" * 60)
    print("FUNDING COMPLETE - Now testing spending conditions")
    print("-" * 60)
    
    input("\nPress Enter to test Alice's immediate spend...")
    
    # Step 4A: Alice tries to spend immediately (should work)
    alice_spend_immediate()
    
    input("\nPress Enter to test Bob's early spend attempt...")
    
    # Step 4B: Bob tries to spend early (should fail)
    bob_spend_early()
    
    print("\n" + "⏰ " * 20)
    print(f"WAIT FOR {LOCKTIME_BLOCKS} BLOCKS TO PASS")
    print(f"(approximately {LOCKTIME_BLOCKS} minutes)")
    print("⏰ " * 20)
    
    input(f"\nOnce {LOCKTIME_BLOCKS} blocks have passed, press Enter to test Bob's delayed spend...")
    
    # Step 4C: Bob tries to spend after timeout (should work)
    bob_spend_after_timeout()
    
    print("\n" + "🎉 " * 20)
    print("TEST SEQUENCE COMPLETE")
    print("🎉 " * 20)
    
    print("\nSummary of expected results:")
    print("✅ Alice can spend immediately")
    print("❌ Bob cannot spend before timeout")
    print("✅ Bob can spend after timeout")


def test_script_only():
    """
    Minimal test - just create and examine the script without wallets
    """
    print("\n🔬 Testing script creation only (no wallets needed)")
    
    # Create dummy public keys for testing
    alice_pubkey = "02" + "11" * 32  # Dummy compressed pubkey
    bob_pubkey = "02" + "22" * 32    # Dummy compressed pubkey
    
    # Create script with block-based locktime
    script_blocks = P2SHRedeemScripts.simpleTimeRelease(
        immediate_key=alice_pubkey,
        delayed_key=bob_pubkey,
        locktime=750000,  # Some future block
        use_blocks=True
    )
    
    print(f"\nBlock-based script hex: {b2x(script_blocks)}")
    print(f"Script size: {len(script_blocks)} bytes")
    
    # Create script with timestamp-based locktime
    future_time = dt.datetime.now() + dt.timedelta(days=1)
    script_time = P2SHRedeemScripts.simpleTimeRelease(
        immediate_key=alice_pubkey,
        delayed_key=bob_pubkey,
        locktime=future_time,
        use_blocks=False
    )
    
    print(f"\nTime-based script hex: {b2x(script_time)}")
    print(f"Script size: {len(script_time)} bytes")
    print(f"Locktime: {future_time.isoformat()}")
    
    print("\n✅ Scripts created successfully")


if __name__ == "__main__":
    print("Simple Time Release P2SH - Manual Test Script")
    print("=" * 60)
    print("\nOptions:")
    print("1. Run full test sequence (requires wallets and EVR)")
    print("2. Test script creation only (no wallets needed)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        run_test_sequence()
    elif choice == "2":
        test_script_only()
    else:
        print("Exiting...")