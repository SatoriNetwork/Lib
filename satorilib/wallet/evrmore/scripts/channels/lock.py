import math
from typing import Union
import datetime as dt
from evrmore.core.script import (
    CScript, OP_CHECKSIG, OP_DROP, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY)


CSV_TIME_BIT = 0x00400000  # bit 22
CSV_UNIT_SECS = 512
CSV_MAX_UNITS = 0xFFFF     # 16 bits # 33,553,920 s = 559,232 min ≈ 388.36 days


def thunderChannel(
    sender: Union[bytes, str], 
    receiver: Union[bytes, str], 
    blocks: Union[int, None] = None, 
    minutes: Union[int, None] = None,
) -> CScript:
    """Create a persistent timed multi-signature redeem script.
    
    Args:
        sender: public key in bytes or hex strings
        receiver: public key in bytes or hex strings
        blocks: number of blocks since last funding event that the funds are locked for
        minutes: number of minutes (which will get rounded up to the nearest 8.5 minute increment) since last funding event that the funds are locked for
        
    Returns:
        CScript containing the redeem script

    Notes:
        script will look like this:
            ```
            OP_IF
                2 <SENDER_PUB> <RECEIVER_PUB> 2 OP_CHECKMULTISIG
            OP_ELSE
                <RELATIVE_BLOCKS_OR_TIME> OP_CHECKSEQUENCEVERIFY OP_DROP
                <SENDER_PUB> OP_CHECKSIG
            OP_ENDIF
            ```
        To specify time instead of blocks, you need to set specific bits in your nSequence value:
        Set bit 22 (0x00400000) to indicate you're using time units instead of blocks
        The time is measured in units of 512 seconds (~8.5 minutes)
        The lower 16 bits hold the actual value (max 65535)
        For example:
        For nearly 1 hour: 7 units (3600 ÷ 512 = ~7.03 or 7*512 = 3584)
        Value: 0x00400007 (4194311 decimal)
        For 1 day: 168 units (86400 ÷ 512 = 168.789 or 168*512 = 86016)
        Value: 0x004000A8 (4194472 decimal)
    
    Usecase:
        a permanent (though possibly itermittent) economic relationship between the two parties exists,
        and the receiver periodically claims funds from the sender
        (at a shorter time interval than the lockout period).
        Since the pattern is to load the channel with a large amount of funds upfront,
        then issue incremental funds to the receiver over time, 
        this can be thought as a "reloadable" or "renewable" channel:
        once it is depleted, the channel can be reloaded with a new amount of funds 
        (though, the lockout period cannot be changed).
        Because the channel is persistent it always exists and can be "reloaded" or "renewed".
    """
    if (blocks is None) == (minutes is None):
        raise ValueError("Specify exactly one of blocks or minutes")
    
    # Convert hex strings to bytes if needed
    sender_bytes = sender if isinstance(sender, bytes) else bytes.fromhex(sender)
    receiver_bytes = receiver if isinstance(receiver, bytes) else bytes.fromhex(receiver)
    
    # Calculate the timeout value based on provided parameters
    if blocks is not None:
        # For blocks, we just use the raw value (up to 65535)
        if not (1 <= blocks <= CSV_MAX_UNITS):
            raise ValueError(f"blocks must be in [1, {CSV_MAX_UNITS}]")
        timeout_value = blocks
    else:
        # For minutes, convert to 512-second units and set the time bit
        if minutes <= 0:
            raise ValueError("minutes must be > 0")
        units = max(1, math.ceil(minutes * 60 / CSV_UNIT_SECS))  # <-- round UP
        if units > CSV_MAX_UNITS:
            # max minutes ~= floor(65535*512/60) = 559232
            raise ValueError("minutes too large for CSV (exceeds 65535 units)")
        timeout_value = CSV_TIME_BIT | int(units)
    # Create the redeem script
    return CScript([
        OP_IF,
            2, sender_bytes, receiver_bytes, 2, OP_CHECKMULTISIG,
        OP_ELSE,
            timeout_value, OP_CHECKSEQUENCEVERIFY, OP_DROP,
            sender_bytes, OP_CHECKSIG,
        OP_ENDIF
    ])


CLTV_TS_THRESHOLD = 500_000_000  # <=> block-height mode below this, timestamp mode at/above this


def thunderExpiring(
    sender: Union[bytes, str], 
    receiver: Union[bytes, str], 
    blocks: Union[int, None] = None, 
    timestamp: Union[int, dt.datetime, None] = None,
) -> CScript:
    """Create a non-renewable timed multi-signature redeem script.
    
    Args:
        sender: public key in bytes or hex strings
        receiver: public key in bytes or hex strings
        blocks: absolute block height after which the sender can reclaim funds
        timestamp: absolute Unix timestamp (seconds since epoch) or a datetime object
                            after which the sender can reclaim funds
        
    Returns:
        CScript containing the redeem script

    Notes:
        script will look like this:
            ```
            OP_IF
                2 <SENDER_PUB> <RECEIVER_PUB> 2 OP_CHECKMULTISIG
            OP_ELSE
                <ABSOLUTE_HEIGHT_OR_TIME> OP_CHECKLOCKTIMEVERIFY OP_DROP
                <SENDER_PUB> OP_CHECKSIG
            OP_ENDIF
            ```
    Usecase:
        a temporary economic relationship between the two parties exists,
        and the receiver may intend to wait til just before timeout 
        or til all the funds are sent before claiming.
        The channel is not persistent, it only exists for the duration of the lockout period. 
        After that the guarantee that the sender cannot reclaim the funds is lost,
        so the channel is said to be not "reloadable" or "renewable".
    """
    if (blocks is None) == (timestamp is None):
        raise ValueError("Specify exactly one of `blocks` or `timestamp`")
    
    # Convert hex strings to bytes if needed
    sender_bytes = sender if isinstance(sender, bytes) else bytes.fromhex(sender)
    receiver_bytes = receiver if isinstance(receiver, bytes) else bytes.fromhex(receiver)
    
    # Calculate the timeout value based on provided parameters
    if blocks is not None:
        # For CLTV with blocks, we use the raw block height
        if not (1 <= int(blocks) < CLTV_TS_THRESHOLD):
            raise ValueError(f"blocks must be in [1, {CLTV_TS_THRESHOLD-1}]")
        timeout_value = int(blocks)  # height mode
    else:
        # For CLTV with time, we use the provided Unix timestamp
        # For time-based locks, the value is interpreted as a Unix timestamp
        # if it's greater than 500,000,000 (roughly year 1985)
        
        # Check if it's a datetime object and convert to timestamp if needed
        if isinstance(timestamp, dt.datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
            ts = int(timestamp.timestamp())
        else:
            ts = int(timestamp)
        # Ensure the value is large enough to be interpreted as a timestamp
        if ts < CLTV_TS_THRESHOLD:
            raise ValueError("timestamp must be >= 500_000_000 (Unix seconds)")
        # Use the provided/converted timestamp
        timeout_value = ts
    return CScript([
        OP_IF,
            2, sender_bytes, receiver_bytes, 2, OP_CHECKMULTISIG,
        OP_ELSE,
            timeout_value, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
            sender_bytes, OP_CHECKSIG,
        OP_ENDIF
    ])
