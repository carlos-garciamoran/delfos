from models.Account import Account
from utils.constants import *


class Strategy:
    """NOTE: every method assumes self.type == 'RSI'. This should be checked first for other indicators."""
    def __init__(self, defaults, strategy):
        # Required attributes
        self.name = strategy['name']
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        # Create dedicated trading account and link it to the strategy
        self.account = Account(defaults['account_size'], self)

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

        # NOTE: the account should not be compared
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


    def determine_position_size(self, allocated, available):
        """Calculate the position size according to account and strategy parameters."""
        return (allocated + available) * self.account_risk / self.stop_loss

    def should_close(self, position, pair, macro_RSI):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position.side == 'BUY':
            macro_close = True if macro_RSI <= MACRO_RSI_MIN else False

            stop_loss_hit = pair.price <= position.stop_loss
            take_profit_hit = pair.price >= position.take_profit

            price_signal = pair.RSI >= self.max

            if self.profit_close:
                price_signal = price_signal and pair.price >= position.entry_price
        else:
            macro_close = True if macro_RSI >= MACRO_RSI_MAX else False

            stop_loss_hit = pair.price >= position.stop_loss
            take_profit_hit = pair.price <= position.take_profit

            price_signal = pair.RSI <= self.min

            if self.profit_close:
                price_signal = price_signal and pair.price <= position.entry_price

        # NOTE: for testing purposes
        if macro_close:
            with open('macro-close.csv', 'a') as fd:
                fd.write('%s,%s,%f\n' % (str(position.__dict__), str(pair.__dict__), macro_RSI))

        # NOTE: return causes for testing purposes
        return (
            macro_close or stop_loss_hit or take_profit_hit or price_signal,
            [macro_close, stop_loss_hit, take_profit_hit, price_signal]
        )
