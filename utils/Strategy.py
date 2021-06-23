from utils.constants import *


class Strategy:
    """NOTE: every method assumes self.type == 'RSI'. This should be checked first for other indicators."""

    def __init__(self, strategy):
        self.name = strategy['name']
        self.type = strategy['type']
        self.profit_close = strategy['profit_close']
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        # Optional parameters
        self.stop_loss = strategy['stop_loss'] \
            if 'stop_loss' in strategy.keys() \
            else STOP_LOSS
        self.take_profit = strategy['take_profit'] \
            if 'take_profit' in strategy.keys() \
            else TAKE_PROFIT

    def __str__(self):
        return '''{}
    type         = {}
    profit_close = {}
    min, max     = {}, {}
    stop_loss    = {}
    take_profit  = {}\n'''.format(self.name, self.type, self.profit_close, self.min, self.max, self.stop_loss, self.take_profit)

    def pair_is_interesting(self, pair):
        """Return True if the RSI is overbought (RSI >= max) or oversold (RSI <= min)."""
        return pair['RSI'] >= self.max or pair['RSI'] <= self.min

    def compute_strength(self, pair):
        """Calculate the strength of the pair's RSI."""
        return abs(50 - pair['RSI'])

    def determine_side(self, pair):
        """Return 'SELL' if the asset to be traded should be shorted; else return 'BUY'."""
        return 'SELL' if pair['RSI'] >= 50 else 'BUY'

    def should_close(self, position, pair):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position['side'] == 'BUY':
            should_close = pair['RSI'] >= self.max

            if self.profit_close:
                should_close = should_close and pair['price'] >= position['entry_price']
        else:
            should_close = pair['RSI'] <= self.min

            if self.profit_close:
                should_close = should_close and pair['price'] <= position['entry_price']

        return should_close
