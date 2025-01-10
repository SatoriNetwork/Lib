from typing import Union
import math
import hashlib
import base58


class TxUtils():
    ''' utility methods for transactions '''

    @staticmethod
    def estimatedFee(inputCount: int = 0, outputCount: int = 0, feeRate: int = 150000) -> int:
        '''
        0.00150000 rvn per item as simple over-estimate
        this fee is on a per input/output basis and it should cover a asset
        output which is larger than a currency output. therefore it should
        always be sufficient for our purposes. usually we're sending 1 asset
        vin and 1 asset vout, and 1 currency vin and 1 currency vout.
        '''
        return (inputCount + outputCount) * feeRate

    @staticmethod
    def estimatedFeeRecursive(txHex: str, feeRate: int = 1100):
        '''
        this assumes you've already created a transaction with the and can
        inspect the size of it to estimate the fee, therere it implies a
        recursive opperation to create the transaction, because the fee must
        be chosen before the transaction is created. so you would build the
        transaction at least twice, but the fee can be much more optimized.
        1.1 standard * 1000 * 192 bytes = 211,200 sats == 0.00211200 rvn
        see example transaction: https://rvn.cryptoscope.io/tx/?txid=
        3a880d09258075635e1565c06dce3f0091a67da987a63140a60f1d8f80a6625a
        we could even base this off of some reasonable upper bound and the
        minimum relay fee specified by the electurmx server using
        blockchain.relayfee(). however, since I'm not willing to write the
        recursive process we're not going to use this function yet.
        feeRate = 1100 # 0.00001100 rvn per byte
        '''
        txSizeInBytes = len(txHex) / 2
        return txSizeInBytes * feeRate

    @staticmethod
    def satsToWei(sats: int) -> int:
        """
        Converts Evrmore satoshis to Ethereum wei.
        Parameters:
            sats (int): The amount in Evrmore satoshis (1 BTC = 10^8 satoshis).
        Returns:
            int: The equivalent amount in Ethereum wei (1 ETH = 10^18 wei).
        # Example Usage
        sats = 100_000  # 0.001 BTC in satoshis
        wei = sats_to_eth_wei(sats)
        print(f"{sats} satoshis = {wei} wei")
        """
        # Scale by 10^(18 - 8) = 10^10 to match Ethereum's 18-decimal precision
        return int(sats * (10 ** 10))

    @staticmethod
    def weiToSats(wei: int) -> int:
        """
        Converts Ethereum wei to Evrmore satoshis.
        Parameters:
            wei (int): The amount in Ethereum wei (1 ETH = 10^18 wei).
        Returns:
            int: The equivalent amount in Evrmore satoshis (1 BTC = 10^8 satoshis).
        # Example Usage
        wei = 1_000_000_000_000_000  # 0.001 ETH in wei
        sats = wei_to_sats(wei)
        print(f"{wei} wei = {sats} satoshis")
        """
        # Scale down by 10^(18 - 8) = 10^10 to match Evrmore's 8-decimal precision
        return int(wei // (10 ** 10))

    @staticmethod
    def asSats(amount: float) -> int:
        from evrmore.core import COIN
        return int(amount * COIN)

    @staticmethod
    def asAmount(sats: int, divisibility: int = 8) -> float:
        from evrmore.core import COIN
        result = sats / COIN
        if result == 0:
            return 0
        if divisibility == 0:
            return int(result)
        return TxUtils.floor(result, divisibility)

    @staticmethod
    def floor(amount: float, divisibility: int) -> float:
        multiplier = 10 ** divisibility
        return math.floor(amount * multiplier) / multiplier

    @staticmethod
    def isAmountDivisibilityValid(amount: float, divisibility: int = 8) -> bool:
        # Multiply the amount by 10^divisibility to shift all the decimals
        # then check if the result is essentially an integer by comparing it with its floor value
        shifted = amount * (10 ** divisibility)
        return shifted == int(shifted)

    @staticmethod
    def isSatsDivisibilityValid(sats: int, divisibility: int = 8) -> bool:
        return str(sats).endswith('0' * (8 - divisibility))

    @staticmethod
    def roundSatsDownToDivisibility(sats: int, divisibility: int = 8) -> bool:
        if TxUtils.isSatsDivisibilityValid(sats, divisibility):
            return sats
        ending = '0' * (8 - divisibility)
        return int(str(sats)[0:-len(ending)] + ending)

    @staticmethod
    def roundDownToDivisibility(amount: float, divisibility: int = 8) -> Union[int, float]:
        '''
        This function truncates the given amount to the allowed number of
        decimal places as defined by the asset's divisibility.
        It returns the truncated amount.
        '''
        if divisibility == 0:
            return int(amount)
        # # Use string formatting to truncate to the allowed number of decimal
        # # places and then convert back to float
        # formatString = f"{{:.{divisibility}f}}"
        # truncatedAmountStr = formatString.format(amount)
        # return float(truncatedAmountStr)
        # I prefer a direct approach:
        return TxUtils.floor(amount, divisibility)

    @staticmethod
    def intToLittleEndianHex(number: int) -> str:
        '''

        100000000 -> "00e1f505" # does not include padding on end: "00000000"
        # Example
        number = 100000000
        little_endian_hex = intToLittleEndianHex(number)
        print(little_endian_hex)
        '''
        # Convert to hexadecimal and remove the '0x' prefix
        hexNumber = hex(number)[2:]
        # Ensure the hex number is of even length
        if len(hexNumber) % 2 != 0:
            hexNumber = '0' + hexNumber
        # Reverse the byte order
        littleEndianHex = ''.join(
            reversed([hexNumber[i:i+2] for i in range(0, len(hexNumber), 2)]))
        return littleEndianHex

    @staticmethod
    def padHexStringTo8Bytes(hexString: str) -> str:
        '''
        # Example usage
        hex_string = "00e1f505"
        padded_hex_string = pad_hex_string_to_8_bytes(hex_string)
        print(padded_hex_string)
        '''
        # Each byte is represented by 2 hexadecimal characters
        targetLength = 16  # 8 bytes * 2 characters per byte
        return hexString.ljust(targetLength, '0')

    @staticmethod
    def addressToH160Bytes(address) -> bytes:
        '''
        address = "RXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV"
        h160 = address_to_h160(address)
        print(h160)
        print(h160.hex()) 'f05325e90d5211def86b856c9569e54808201290'
        '''
        import base58
        decoded = base58.b58decode(address)
        h160 = decoded[1:-4]
        return h160

    @staticmethod
    def hash160ToAddress(pubKeyHash: Union[str, bytes], networkByte: bytes = b'\x00'):
        # Step 1: Add network byte (0x00 for Bitcoin mainnet P2PKH)
        if isinstance(pubKeyHash, str):
            pubKeyHash = bytes.fromhex(pubKeyHash)
        step1 = networkByte + pubKeyHash
        # Step 2 & 3: Perform SHA-256 twice and take the first 4 bytes as checksum
        sha256_1 = hashlib.sha256(step1).digest()
        sha256_2 = hashlib.sha256(sha256_1).digest()
        checksum = sha256_2[:4]
        # Step 4: Append checksum
        step4 = step1 + checksum
        # Step 5: Base58Check encode
        address = base58.b58encode(step4)
        return address.decode()
