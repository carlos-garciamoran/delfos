from utils.constants import *


class Strategy:
    """NOTE: every method assumes self.type == 'RSI'. This should be checked first for other indicators."""
    def __init__(self, defaults, strategy):
        # Required attributes
        self.name = strategy['name']
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        # Optional attributes (defaults)
        self.account_risk = strategy['account_risk'] \
            if 'account_risk' in strategy.keys() \
            else defaults['account_risk']
        self.account_size = strategy['account_size'] \
            if 'account_size' in strategy.keys() \
            else defaults['account_size']

        self.profit_close = strategy['profit_close'] \
            if 'profit_close' in strategy.keys() \
            else False
        self.stop_loss = strategy['stop_loss'] \
            if 'stop_loss' in strategy.keys() \
            else defaults['stop_loss']
        self.take_profit = strategy['take_profit'] \
            if 'take_profit' in strategy.keys() \
            else defaults['take_profit']
        # NOTE: unused attribute
        self.type = strategy['type'] \
            if 'type' in strategy.keys() \
            else 'RSI'

    def __eq__(self, other):
        if not isinstance(other, Strategy):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        return self.name == other.name and self.min == other.min and self.max == other.max \
            and self.profit_close == other.profit_close \
            and self.stop_loss == other.stop_loss and self.take_profit == other.take_profit \
            and self.account_risk == other.account_risk and self.account_size == other.account_size \
            and self.type == other.type

    def __str__(self):
        return '''{}
    min, max     = {}, {}
    stop_loss    = {}
    take_profit  = {}
    profit_close = {}
    account_risk = {}
    account_size = {}
    type         = {}\n'''.format(
        self.name, self.min, self.max, self.stop_loss, self.take_profit, self.profit_close,
        self.account_risk, self.account_size, self.type,
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

    def determine_position_size(self, allocated, available):
        """Calculate the position size according to account and strategy parameters."""
        return (allocated + available) * self.account_risk / self.stop_loss

    def determine_side(self, pair, macro_RSI):
        """Return 'SELL' if the asset should be shorted or 'BUY' if it should be longed."""
        if pair['RSI'] >= 50:
            # Follow the trend if RSI is extreme, else look for the reverse
            side = 'BUY' if macro_RSI >= MACRO_RSI_MAX else 'SELL'
        else:
            # Idem
            side = 'SELL' if macro_RSI <= MACRO_RSI_MIN else 'BUY'

        return side

    def should_close(self, position, pair, macro_RSI):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position['side'] == 'BUY':
            macro_close = True if macro_RSI <= MACRO_RSI_MIN else False

            stop_loss_hit = pair['price'] <= position['stop_loss']
            take_profit_hit = pair['price'] >= position['take_profit']

            price_signal = pair['RSI'] >= self.max

            if self.profit_close:
                price_signal = price_signal and pair['price'] >= position['entry_price']
        else:
            macro_close = True if macro_RSI >= MACRO_RSI_MAX else False

            stop_loss_hit = pair['price'] >= position['stop_loss']
            take_profit_hit = pair['price'] <= position['take_profit']

            price_signal = pair['RSI'] <= self.min

            if self.profit_close:
                price_signal = price_signal and pair['price'] <= position['entry_price']

        # NOTE: for testing purposes
        if macro_close:
            with open('macro-testing.log', 'a') as fd:
                fd.write('%s,%s,%f\n' % (str(position), str(pair), macro_RSI))

        # NOTE: return causes for testing purposes
        return (
            macro_close or stop_loss_hit or take_profit_hit or price_signal,
            [macro_close, stop_loss_hit, take_profit_hit, price_signal]
        )
