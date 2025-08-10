from typing import Union
import datetime as dt
from evrmore.core.script import (
    CScript, OP_CHECKSIG, OP_DROP, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY)


def renewableLightChannel(
    sender: Union[bytes, str], 
    receiver: Union[bytes, str], 
    blocks: Union[int, None] = None, 
    minutes: Union[int, None] = None,
) -> CScript:
    """Create a renewable timed multi-signature redeem script.
    
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
        For 1 hour: 7 units (3600 ÷ 512 = ~7)
        Value: 0x00400007 (4194311 decimal)
        For 1 day: 168 units (86400 ÷ 512 = 168)
        Value: 0x004000A8 (4194472 decimal)
    """
    if blocks is None and minutes is None:
        raise ValueError("Either blocks or minutes must be specified")
    
    if blocks is not None and minutes is not None:
        raise ValueError("Only one of blocks or minutes can be specified")
    
    # Convert hex strings to bytes if needed
    senderBytes = sender if isinstance(sender, bytes) else bytes.fromhex(sender)
    receiverBytes = receiver if isinstance(receiver, bytes) else bytes.fromhex(receiver)
    
    # Calculate the timeout value based on provided parameters
    if blocks is not None:
        # For blocks, we just use the raw value (up to 65535)
        if not 1 <= blocks <= 65535:
            raise ValueError("blocks must be between 1 and 65535")
        timeoutValue = blocks
    else:
        # For minutes, convert to 512-second units and set the time bit
        if not 1 <= minutes <= (65535 * 8.5):
            raise ValueError(f"minutes must be between 1 and {int(65535 * 8.5)} minutes")
        timeUnits = (minutes * 60) // 512
        if timeUnits < 1:
            timeUnits = 1  # Minimum 1 unit (about 8.5 minutes)
        # Set bit 22 (0x00400000) to indicate time units instead of blocks
        timeoutValue = 0x00400000 | (int(timeUnits) & 0xFFFF)
    
    # Create the redeem script
    return CScript([
        OP_IF,
            2, senderBytes, receiverBytes, 2, OP_CHECKMULTISIG,
        OP_ELSE,
            timeoutValue, OP_CHECKSEQUENCEVERIFY, OP_DROP,
            senderBytes, OP_CHECKSIG,
        OP_ENDIF
    ])

def nonrenewableLightChannel(
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
    """
    if blocks is None and timestamp is None:
        raise ValueError("Either blocks or timestamp must be specified")
    
    if blocks is not None and timestamp is not None:
        raise ValueError("Only one of blocks or timestamp can be specified")
    
    # Convert hex strings to bytes if needed
    senderBytes = sender if isinstance(sender, bytes) else bytes.fromhex(sender)
    receiverBytes = receiver if isinstance(receiver, bytes) else bytes.fromhex(receiver)
    
    # Calculate the timeout value based on provided parameters
    if blocks is not None:
        # For CLTV with blocks, we use the raw block height
        if blocks <= 0:
            raise ValueError("blocks must be positive")
        timeoutValue = blocks
    else:
        # For CLTV with time, we use the provided Unix timestamp
        # For time-based locks, the value is interpreted as a Unix timestamp
        # if it's greater than 500,000,000 (roughly year 1985)
        
        # Check if it's a datetime object and convert to timestamp if needed
        import datetime
        if isinstance(timestamp, datetime.datetime):
            timestamp = int(timestamp.timestamp())
        else:
            timestamp = timestamp
        
        if timestamp <= 0:
            raise ValueError("timestamp must be positive")
        
        # Use the provided/converted timestamp
        timeoutValue = timestamp
        
        # Ensure the value is large enough to be interpreted as a timestamp
        if timeoutValue < 500000000:
            raise ValueError("Timestamp value is too small to be a valid timestamp (must be > 500,000,000)")
    
    # unlocking scripts:
    # if path: <sig_sender> <sig_receiver> 0 1 <redeemScript>
    # else path: <sig_sender> 0 <redeemScript>
    
    # Create the redeem script
    return CScript([
        OP_IF,
            2, senderBytes, receiverBytes, 2, OP_CHECKMULTISIG,
        OP_ELSE,
            timeoutValue, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
            senderBytes, OP_CHECKSIG,
        OP_ENDIF
    ])
