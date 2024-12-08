class Validate():
    ''' heuristics '''

    @staticmethod
    def address(address: str, currency: str) -> bool:
        return (
            (currency.lower() == 'rvn' and address.startswith('R') and len(address) == 34) or
            (currency.lower() == 'evr' and address.startswith('E') and len(address) == 34))

    @staticmethod
    def ethAddress(address: str) -> bool:
        return address.startswith("0x") and len(address) == 42
