import time
from satoriwallet import TxUtils

class Balance():

    @staticmethod
    def empty(symbol) -> 'Balance':
        return Balance(symbol=symbol, confirmed=0, unconfirmed=0)

    @staticmethod
    def fromBalances(symbol: str, balances: dict) -> 'Balance':
        if symbol.lower() == 'evr':
            balance = balances.get('evr', balances.get('rvn'))
        else:
            balance = balances.get(symbol)
        if balance is None:
            return Balance.empty(symbol)
        return Balance.fromBalance(symbol, balance)

    @staticmethod
    def fromBalance(symbol: str, balance: dict) -> 'Balance':
        return Balance(
            symbol=symbol,
            confirmed=balance.get('confirmed', 0),
            unconfirmed=balance.get('unconfirmed', 0))

    def __init__(self, symbol: str, confirmed: int, unconfirmed: int, divisibility: int = 8):
        self.symbol = symbol
        self.confirmed = confirmed
        self.unconfirmed = unconfirmed
        self.divisibility = divisibility
        self.total = confirmed + unconfirmed
        self.amount = TxUtils.asAmount(self.total or 0, self.divisibility)
        self.ts = time.time()

    def __repr__(self):
        return f'{self.symbol} Balance: {self.confirmed}'

    def __str__(self):
        return f'{self.symbol} Balance: {self.confirmed}'

    def __call__(self):
        return self.total

    def __lt__(self, other):
        if isinstance(other, Balance):
            return self.total < other.total
        elif isinstance(other, (int, float)):  # Handle comparison with numbers
            return self.total < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Balance):
            return self.total <= other.total
        elif isinstance(other, (int, float)):
            return self.total <= other
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Balance):
            return self.total > other.total
        elif isinstance(other, (int, float)):
            return self.total > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Balance):
            return self.total >= other.total
        elif isinstance(other, (int, float)):
            return self.total >= other
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Balance):
            return self.total == other.total
        elif isinstance(other, (int, float)):
            return self.total == other
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Balance):
            return self.total != other.total
        elif isinstance(other, (int, float)):
            return self.total != other
        return NotImplemented

class TransactionResult():
    def __init__(self, result: str = '', success: bool = False, tx: bytes = None, msg: str = '', reportedFeeSats: int = None):
        self.result = result
        self.success = success
        self.tx = tx
        self.msg = msg
        self.reportedFeeSats = reportedFeeSats


class TransactionFailure(Exception):
    '''
    unable to create a transaction for some reason
    '''

    def __init__(self, message='Transaction Failure', extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data

    def __str__(self):
        return f"{self.__class__.__name__}: {self.args[0]} {self.extra_data or ''}"
