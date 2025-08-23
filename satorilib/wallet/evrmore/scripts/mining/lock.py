from typing import Union
import datetime as dt
from evrmore.core.script import (
    CScript, OP_CHECKSIG, OP_CHECKSIGVERIFY, OP_DROP, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_TRUE)


def simpleTime(
    immediate_key: Union[bytes, str],
    delayed_key: Union[bytes, str],
    locktime: Union[int, dt.datetime],
    use_blocks: bool = False
) -> CScript:
    """Create a simple time release redeem script.
    
    One key can unlock immediately, another can unlock only after a certain time/block.
    This is useful for escrow-like situations where one party (e.g., Alice) can 
    retrieve funds immediately, while another party (e.g., Bob) can only retrieve 
    funds after a timeout period.
    
    Args:
        immediate_key: Public key that can unlock funds immediately (Alice)
        delayed_key: Public key that can unlock funds after timeout (Bob)
        locktime: Either block height (if use_blocks=True) or Unix timestamp/datetime
        use_blocks: If True, locktime is interpreted as block height; 
                    if False, as Unix timestamp
        
    Returns:
        CScript containing the redeem script
        
    Script structure:
        ```
        OP_IF
            <delayed_key> OP_CHECKSIGVERIFY
            <locktime> OP_CHECKLOCKTIMEVERIFY
        OP_ELSE
            <immediate_key> OP_CHECKSIG
        OP_ENDIF
        ```
        
    To spend with delayed_key (after locktime):
        - Provide: <signature_for_delayed_key> 1
        
    To spend with immediate_key (anytime):
        - Provide: <signature_for_immediate_key> 0
        
    Example:
        ```python
        # Alice can retrieve funds immediately, Bob can retrieve after 144 blocks
        redeem_script = simpleTime(
            immediate_key=alice_pubkey,  # Alice can unlock anytime
            delayed_key=bob_pubkey,       # Bob can unlock after timeout
            locktime=144,                 # 144 blocks (~24 hours)
            use_blocks=True
        )
        ```
    """
    # Convert hex strings to bytes if needed
    immediate_bytes = immediate_key if isinstance(immediate_key, bytes) else bytes.fromhex(immediate_key)
    delayed_bytes = delayed_key if isinstance(delayed_key, bytes) else bytes.fromhex(delayed_key)
    
    # Process locktime value
    if use_blocks:
        # Using block height
        if not isinstance(locktime, int) or locktime <= 0:
            raise ValueError("When use_blocks=True, locktime must be a positive integer")
        locktime_value = locktime
    else:
        # Using Unix timestamp
        if isinstance(locktime, dt.datetime):
            locktime_value = int(locktime.timestamp())
        elif isinstance(locktime, int):
            locktime_value = locktime
        else:
            raise ValueError("locktime must be an integer timestamp or datetime object")
        
        # For CLTV, values < 500,000,000 are interpreted as block heights,
        # values >= 500,000,000 are interpreted as Unix timestamps
        if locktime_value < 500_000_000:
            raise ValueError(
                "Timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
    
    # Create the redeem script
    # Note: The order matches your specification where delayed_key is in the IF branch
    return CScript([
        OP_IF,
            locktime_value, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
            delayed_bytes, OP_CHECKSIG,
        OP_ELSE,
            immediate_bytes, OP_CHECKSIG,
        OP_ENDIF
    ])


def multiTime(
    immediate_key: Union[bytes, str],
    delayed_key_1: Union[bytes, str],
    delayed_key_2: Union[bytes, str],
    delayed_key_3: Union[bytes, str],
    locktime_1: Union[int, dt.datetime],
    locktime_2: Union[int, dt.datetime],
    locktime_3: Union[int, dt.datetime],
    use_blocks: bool = False
) -> CScript:
    """Create an enhanced time release redeem script with multiple time-locked keys.
    
    One key can unlock immediately, and three other keys can unlock after their respective
    timeout periods. This is useful for multi-party escrow situations where different 
    parties have different time-based access rights.
    
    Args:
        immediate_key: Public key that can unlock funds immediately (Alice)
        delayed_key_1: Public key that can unlock funds after locktime_1 (Bob)
        delayed_key_2: Public key that can unlock funds after locktime_2 (Charlie)
        delayed_key_3: Public key that can unlock funds after locktime_3 (Delta)
        locktime_1: First timeout - block height or Unix timestamp/datetime
        locktime_2: Second timeout - must be > locktime_1
        locktime_3: Third timeout - must be > locktime_2
        use_blocks: If True, locktimes are block heights; if False, Unix timestamps
        
    Returns:
        CScript containing the redeem script
        
    Script structure:
        ```
        OP_IF
            OP_IF
                <delayed_key_3> OP_CHECKSIGVERIFY
                <locktime_3> OP_CHECKLOCKTIMEVERIFY OP_DROP
                OP_TRUE
            OP_ELSE
                <delayed_key_2> OP_CHECKSIGVERIFY 
                <locktime_2> OP_CHECKLOCKTIMEVERIFY OP_DROP
                OP_TRUE
            OP_ENDIF
        OP_ELSE
            OP_IF
                <delayed_key_1> OP_CHECKSIGVERIFY
                <locktime_1> OP_CHECKLOCKTIMEVERIFY OP_DROP
                OP_TRUE
            OP_ELSE
                <immediate_key> OP_CHECKSIG
            OP_ENDIF
        OP_ENDIF
        ```
        
    To spend with delayed_key_3 (after locktime_3):
        - Provide: 1 1 <signature_for_delayed_key_3>

    To spend with delayed_key_2 (after locktime_2):
        - Provide: 1 0 <signature_for_delayed_key_2>

    To spend with delayed_key_1 (after locktime_1):
        - Provide: 0 1 <signature_for_delayed_key_1>
        
    To spend with immediate_key (anytime):
        - Provide: 0 0 <signature_for_immediate_key>
        
    Note: locktime_3 must be > locktime_2 > locktime_1 for logical consistency
        
    Example:
        ```python
        # Alice can retrieve funds immediately, 
        # Bob after 1 day, Charlie after 2 days, Delta after 3 days
        redeem_script = multiTime(
            immediate_key=alice_pubkey,     # Alice can unlock anytime
            delayed_key_1=bob_pubkey,       # Bob can unlock after 1 day
            locktime_1=144,                 # 144 blocks (~24 hours)
            delayed_key_2=charlie_pubkey,   # Charlie can unlock after 2 days
            locktime_2=288,                 # 288 blocks (~48 hours)
            delayed_key_3=delta_pubkey,     # Delta can unlock after 3 days
            locktime_3=432,                 # 432 blocks (~72 hours)
            use_blocks=True
        )
        ```
    """
    # Convert hex strings to bytes if needed
    immediate_bytes = immediate_key if isinstance(immediate_key, bytes) else bytes.fromhex(immediate_key)
    delayed_bytes_1 = delayed_key_1 if isinstance(delayed_key_1, bytes) else bytes.fromhex(delayed_key_1)
    delayed_bytes_2 = delayed_key_2 if isinstance(delayed_key_2, bytes) else bytes.fromhex(delayed_key_2)
    delayed_bytes_3 = delayed_key_3 if isinstance(delayed_key_3, bytes) else bytes.fromhex(delayed_key_3)
    
    # Process locktime values
    if use_blocks:
        # Using block height
        if not isinstance(locktime_1, int) or locktime_1 <= 0:
            raise ValueError("When use_blocks=True, locktime_1 must be a positive integer")
        if not isinstance(locktime_2, int) or locktime_2 <= 0:
            raise ValueError("When use_blocks=True, locktime_2 must be a positive integer")
        if not isinstance(locktime_3, int) or locktime_3 <= 0:
            raise ValueError("When use_blocks=True, locktime_3 must be a positive integer")
        
        locktime_value_1 = locktime_1
        locktime_value_2 = locktime_2
        locktime_value_3 = locktime_3
    else:
        # Process locktime_1
        if isinstance(locktime_1, dt.datetime):
            locktime_value_1 = int(locktime_1.timestamp())
        elif isinstance(locktime_1, int):
            locktime_value_1 = locktime_1
        else:
            raise ValueError("locktime_1 must be an integer timestamp or datetime object")
        
        # Process locktime_2
        if isinstance(locktime_2, dt.datetime):
            locktime_value_2 = int(locktime_2.timestamp())
        elif isinstance(locktime_2, int):
            locktime_value_2 = locktime_2
        else:
            raise ValueError("locktime_2 must be an integer timestamp or datetime object")
        
        # Process locktime_3
        if isinstance(locktime_3, dt.datetime):
            locktime_value_3 = int(locktime_3.timestamp())
        elif isinstance(locktime_3, int):
            locktime_value_3 = locktime_3
        else:
            raise ValueError("locktime_3 must be an integer timestamp or datetime object")
        
        # For CLTV, values < 500,000,000 are interpreted as block heights,
        # values >= 500,000,000 are interpreted as Unix timestamps
        if locktime_value_1 < 500_000_000:
            raise ValueError(
                "locktime_1 timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
        if locktime_value_2 < 500_000_000:
            raise ValueError(
                "locktime_2 timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
        if locktime_value_3 < 500_000_000:
            raise ValueError(
                "locktime_3 timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
    
    # Validate locktime ordering
    if not (locktime_value_1 < locktime_value_2 < locktime_value_3):
        raise ValueError(
            f"Locktimes must be in ascending order: locktime_1 ({locktime_value_1}) < "
            f"locktime_2 ({locktime_value_2}) < locktime_3 ({locktime_value_3})"
        )
    
    # Create the redeem script with proper OP_DROP and OP_TRUE operations
    return CScript([
        OP_IF,
            OP_IF,
                locktime_value_3, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                delayed_bytes_3, OP_CHECKSIG,
            OP_ELSE,
                locktime_value_2, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                delayed_bytes_2, OP_CHECKSIG,
            OP_ENDIF,
        OP_ELSE,
            OP_IF,
                locktime_value_1, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                delayed_bytes_1, OP_CHECKSIG,
            OP_ELSE,
                immediate_bytes, OP_CHECKSIG,
            OP_ENDIF,
        OP_ENDIF
    ])


def multiTimeMultisig(
    immediate_key: Union[bytes, str],
    multi_key_1: Union[bytes, str],
    multi_key_2: Union[bytes, str],
    multi_key_3: Union[bytes, str],
    multi_key_4: Union[bytes, str],
    multi_key_5: Union[bytes, str],
    delayed_key_1: Union[bytes, str],
    delayed_key_2: Union[bytes, str],
    locktime_1: Union[int, dt.datetime],
    locktime_2: Union[int, dt.datetime],
    use_blocks: bool = False
) -> CScript:
    """Create an enhanced time release redeem script with multiple time-locked keys.
    
    One key can unlock immediately, and three other keys can unlock after their respective
    timeout periods. This is useful for multi-party escrow situations where different 
    parties have different time-based access rights.
    
    Args:
        immediate_key: Public key that can unlock funds immediately
        multi_key_1: Public key that can unlock funds after locktime_1
        multi_key_2: Public key that can unlock funds after locktime_2
        multi_key_3: Public key that can unlock funds after locktime_3
        multi_key_4: Public key that can unlock funds after locktime_4
        multi_key_5: Public key that can unlock funds after locktime_5
        delayed_key_1: Public key that can unlock funds after locktime_1
        delayed_key_2: Public key that can unlock funds after locktime_2
        locktime_1: First timeout - must be > locktime_1
        locktime_2: Second timeout - must be > locktime_2
        use_blocks: If True, locktimes are block heights; if False, Unix timestamps
        
    Returns:
        CScript containing the redeem script
        
    Script structure:
        ```
        OP_IF
            OP_IF
                <locktime_2> OP_CHECKLOCKTIMEVERIFY OP_DROP
                <delayed_key_2> OP_CHECKSIG
            OP_ELSE
                <locktime_1> OP_CHECKLOCKTIMEVERIFY OP_DROP
                <delayed_key_1> OP_CHECKSIG
            OP_ENDIF
        OP_ELSE
            OP_IF
                OP_5 <multi_key_1> <multi_key_2> <multi_key_3> <multi_key_4> <multi_key_5> OP_5 OP_CHECKMULTISIG 
            OP_ELSE
                <immediate_key> OP_CHECKSIG
            OP_ENDIF
        OP_ENDIF
        ```
        
    To spend with delayed_key_2 (after locktime_2):
        - Provide: <signature_for_delayed_key_2> OP_TRUE OP_TRUE <redeemScript>

    To spend with delayed_key_1 (after locktime_1):
        - Provide: <signature_for_delayed_key_1> OP_FALSE OP_TRUE <redeemScript>

    To spend with multi keys (anytime):
        - Provide: <signature_for_multi_key_1> <signature_for_multi_key_2> <signature_for_multi_key_3> <signature_for_multi_key_4> <signature_for_multi_key_5> OP_0 OP_TRUE OP_FALSE <redeemScript>
        
    To spend with immediate_key (anytime):
        - Provide: <signature_for_immediate_key> OP_FALSE OP_FALSE <redeemScript>
        
    Note: locktime_2 > locktime_1 for logical consistency
    """
    # Convert hex strings to bytes if needed
    immediate_bytes = immediate_key if isinstance(immediate_key, bytes) else bytes.fromhex(immediate_key)
    multi_bytes_1 = multi_key_1 if isinstance(multi_key_1, bytes) else bytes.fromhex(multi_key_1)
    multi_bytes_2 = multi_key_2 if isinstance(multi_key_2, bytes) else bytes.fromhex(multi_key_2)
    multi_bytes_3 = multi_key_3 if isinstance(multi_key_3, bytes) else bytes.fromhex(multi_key_3)
    multi_bytes_4 = multi_key_4 if isinstance(multi_key_4, bytes) else bytes.fromhex(multi_key_4)
    multi_bytes_5 = multi_key_5 if isinstance(multi_key_5, bytes) else bytes.fromhex(multi_key_5)
    delayed_bytes_1 = delayed_key_1 if isinstance(delayed_key_1, bytes) else bytes.fromhex(delayed_key_1)
    delayed_bytes_2 = delayed_key_2 if isinstance(delayed_key_2, bytes) else bytes.fromhex(delayed_key_2)
    
    
    # Process locktime values
    if use_blocks:
        # Using block height
        if not isinstance(locktime_1, int) or locktime_1 <= 0:
            raise ValueError("When use_blocks=True, locktime_1 must be a positive integer")
        if not isinstance(locktime_2, int) or locktime_2 <= 0:
            raise ValueError("When use_blocks=True, locktime_2 must be a positive integer")
        
        locktime_value_1 = locktime_1
        locktime_value_2 = locktime_2
    else:
        # Process locktime_1
        if isinstance(locktime_1, dt.datetime):
            locktime_value_1 = int(locktime_1.timestamp())
        elif isinstance(locktime_1, int):
            locktime_value_1 = locktime_1
        else:
            raise ValueError("locktime_1 must be an integer timestamp or datetime object")
        
        # Process locktime_2
        if isinstance(locktime_2, dt.datetime):
            locktime_value_2 = int(locktime_2.timestamp())
        elif isinstance(locktime_2, int):
            locktime_value_2 = locktime_2
        else:
            raise ValueError("locktime_2 must be an integer timestamp or datetime object")
        
        # For CLTV, values < 500,000,000 are interpreted as block heights,
        # values >= 500,000,000 are interpreted as Unix timestamps
        if locktime_value_1 < 500_000_000:
            raise ValueError(
                "locktime_1 timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
        if locktime_value_2 < 500_000_000:
            raise ValueError(
                "locktime_2 timestamp value is too small (< 500,000,000). "
                "Use use_blocks=True for block heights, or provide a valid Unix timestamp"
            )
    
    # Validate locktime ordering
    if not (locktime_value_1 < locktime_value_2):
        raise ValueError(
            f"Locktimes must be in ascending order: locktime_1 ({locktime_value_1}) < "
            f"locktime_2 ({locktime_value_2})"
        )
    
    # Create the redeem script with proper OP_DROP 
    return CScript([
        OP_IF,
            OP_IF,
                locktime_value_2, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                delayed_bytes_2, OP_CHECKSIG,
            OP_ELSE,
                locktime_value_1, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                delayed_bytes_1, OP_CHECKSIG,
            OP_ENDIF,
        OP_ELSE,
            OP_IF,
                5, multi_bytes_1, multi_bytes_2, multi_bytes_3, multi_bytes_4, multi_bytes_5, 5, OP_CHECKMULTISIG,
            OP_ELSE,
                immediate_bytes, OP_CHECKSIG,
            OP_ENDIF,
        OP_ENDIF
    ])
