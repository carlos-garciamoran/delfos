from datetime import datetime


class Position:
    def __init__(self, pair, side, size, strategy):
        self.symbol = pair.symbol  # symbol name
        self.entry_price = pair.price  # float
        self.side = side  # either 'SELL' or 'BUY'
        self.size = size  # in USDT

        self.opened_at = datetime.now().isoformat()

        # TODO: do not hardcode taker fee rate: create a constant
        self.fee = self.size * 0.00036  # opening fee in USDT

        self.exit_price = None
        self.closed_at = None

        self.pnl = [None, None]  # [percentage, USDT]

        # NOTE: conditional not placed in method to save function call. Position objects are created often.
        # Set SL and TP according to the side and the strategy parameters
        if side == 'BUY':
            self.stop_loss = self.entry_price - (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price + (self.entry_price * strategy.take_profit)
        else:
            self.stop_loss = self.entry_price + (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price - (self.entry_price * strategy.take_profit)

    def __eq__(self, other):
        if not isinstance(other, Position):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        # Only check the necessary attributes
        return self.symbol == other.symbol \
            and self.entry_price == other.entry_price \
            and self.size == other.size \
            and self.opened_at == other.opened_at

    def __str__(self):
        return '''{}
    side = {}
    size = {}
    entry_price = {} 
    opened_at = {}
    exit_price = {}
    closed_at = {}
    fee = {}
    pnl = {}
    stop_loss = {}
    take_profit = {}\n'''.format(
        self.symbol, self.side, self.size, self.entry_price, self.opened_at,
        self.exit_price, self.closed_at, self.fee, self.pnl, self.stop_loss, self.take_profit
        )


    def close(self, exit_price):
        """Mark the position as closed at the given exit_price and calculate P&L and fees."""
        self.exit_price = exit_price
        self.closed_at = datetime.now().isoformat()

        if self.side == 'BUY':
            self.pnl[0] = (exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl[0] = (self.entry_price - exit_price) / exit_price

        self.pnl[0] *= 100
        self.pnl[1] = self.size * self.pnl[0] / 100

        # TODO: do not hardcode maker fee rate: create a constant
        self.fee += (self.size + self.pnl[1]) * 0.00018
