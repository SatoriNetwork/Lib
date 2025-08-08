from typing import Union
import datetime as dt
from evrmore.core.script import (
    CScript, OP_CHECKSIG, OP_CHECKSIGVERIFY, OP_DROP, OP_IF, OP_ELSE, OP_ENDIF, 
    OP_CHECKMULTISIG, OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY, OP_TRUE)


class P2SHRedeemScripts():

    @staticmethod
    def basicMultisig(pubkeys: list[Union[bytes, str]], signatures: int) -> CScript:
        """Create a multi-signature redeem script.
        
        Args:
            pubkeys: List of public keys in bytes or hex strings
            signatures: Number of signatures required (M of N)
            
        Returns:
            CScript containing the redeem script
        """
        if not 1 <= signatures <= len(pubkeys):
            raise ValueError("Required signatures must be between 1 and number of public keys")
        
        # Convert hex strings to bytes if needed
        byteKeys = []
        for key in pubkeys:
            if isinstance(key, str):
                byteKeys.append(bytes.fromhex(key))
            elif isinstance(key, bytes):
                byteKeys.append(key)
            else:
                raise TypeError(f"Public key must be bytes or hex string, got {type(key)}")
        
        return CScript([signatures] + byteKeys + [len(byteKeys), OP_CHECKMULTISIG])

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def simpleTimeRelease(
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
            - Provide: 1 <signature_for_delayed_key>
            
        To spend with immediate_key (anytime):
            - Provide: 0 <signature_for_immediate_key>
            
        Example:
            ```python
            # Alice can retrieve funds immediately, Bob can retrieve after 144 blocks
            redeem_script = P2SHRedeemScripts.simpleTimeRelease(
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
                delayed_bytes, OP_CHECKSIGVERIFY,
                locktime_value, OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                OP_TRUE,
            OP_ELSE,
                immediate_bytes, OP_CHECKSIG,
            OP_ENDIF
        ])


    @staticmethod
    def enhancedSimpleTimeRelease(
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
            redeem_script = P2SHRedeemScripts.enhancedSimpleTimeRelease(
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
