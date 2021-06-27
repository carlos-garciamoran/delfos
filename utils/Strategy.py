from utils.constants import *


class Strategy:
    """NOTE: every method assumes self.type == 'RSI'. This should be checked first for other indicators."""

    def __init__(self, strategy):
        self.name = strategy['name']
        self.profit_close = strategy['profit_close']
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        # Default values
        self.type = strategy['type'] \
            if 'type' in strategy.keys() \
            else 'RSI'
        self.stop_loss = strategy['stop_loss'] \
            if 'stop_loss' in strategy.keys() \
            else STOP_LOSS
        self.take_profit = strategy['take_profit'] \
            if 'take_profit' in strategy.keys() \
            else TAKE_PROFIT

    def __eq__(self, other):
        if not isinstance(other, Strategy):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        return self.name == other.name and self.profit_close == other.profit_close \
            and self.min == other.min and self.max == other.max \
            and self.stop_loss == other.stop_loss and self.take_profit == other.take_profit \
            and self.type == other.type

    def __str__(self):
        return '''{}
    type         = {}
    profit_close = {}
    min, max     = {}, {}
    stop_loss    = {}
    take_profit  = {}\n'''.format(
        self.name, self.type, self.profit_close, self.min, self.max, self.stop_loss, self.take_profit
        )


    def pair_is_interesting(self, pair):
        """Return True if the RSI is overbought (RSI >= max) or oversold (RSI <= min)."""
        return self.RSI_is_touched(pair) # and self.macro_trend_confirms()

    def macro_trend_confirms(self):
        pass

    def RSI_is_touched(self, pair):
        """Return True if the RSI is overbought (RSI >= max) or oversold (RSI <= min)."""
        return pair['RSI'] >= self.max or pair['RSI'] <= self.min

    def compute_strength(self, pair):
        """Calculate the strength of the pair's indicator."""
        return abs(50 - pair['RSI'])

    def determine_side(self, pair):
        """Return 'SELL' if the asset should be shorted or 'BUY' if it should be longed."""
        return 'SELL' if pair['RSI'] >= 50 else 'BUY'

    def should_close(self, position, pair):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position['side'] == 'BUY':
            stop_loss_hit = pair['price'] <= position['stop_loss']
            take_profit_hit = pair['price'] >= position['take_profit']

            price_signal = pair['RSI'] >= self.max

            if self.profit_close:
                price_signal = price_signal and pair['price'] >= position['entry_price']
        else:
            stop_loss_hit = pair['price'] >= position['stop_loss']
            take_profit_hit = pair['price'] <= position['take_profit']

            price_signal = pair['RSI'] <= self.min

            if self.profit_close:
                price_signal = price_signal and pair['price'] <= position['entry_price']

        return price_signal or stop_loss_hit or take_profit_hit
