from datetime import datetime

from models.Account import Account
from utils.constants import MACRO_RSI_MAX, MACRO_RSI_MIN, TIMER_TRIGGER


class Strategy:
    def __init__(self, defaults, strategy):
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        self.profit_close = strategy['profit_close'] \
            if 'profit_close' in strategy.keys() \
            else False
        self.stop_loss = strategy['stop_loss'] \
            if 'stop_loss' in strategy.keys() \
            else defaults['stop_loss']
        self.take_profit = strategy['take_profit'] \
            if 'take_profit' in strategy.keys() \
            else defaults['take_profit']
        self.risk = strategy['risk'] \
            if 'risk' in strategy.keys() \
            else defaults['risk']
        self.real = strategy['REAL'] \
            if 'REAL' in strategy.keys() \
            else False
        initial_account_size = strategy['account_size'] \
            if 'account_size' in strategy.keys() \
            else defaults['account_size']

        self.name = f'{self.min}-{self.max}_SL-{(self.stop_loss*100):g}_TP-{(self.take_profit*100):g}'
        self.name += '_profit' if self.profit_close else ''

        if self.real:
            self.name += '_REAL'
        else:
            self.exchange = None

        # Create dedicated trading account and link it to the strategy
        self.account = Account(self, initial_account_size)

    def __eq__(self, other):
        # NOTE: `self.account` is not compared on purpose
        return self.name == other.name \
            and self.min == other.min \
            and self.max == other.max \
            and self.profit_close == other.profit_close \
            and self.stop_loss == other.stop_loss \
            and self.take_profit == other.take_profit \
            and self.risk == other.risk \
            and self.real == other.real

    def __str__(self):
        return self.name + '\n' \
            f'\treal         = {self.real}\n' \
            f'\tmin, max     = {self.min}, {self.max}\n' \
            f'\tstop_loss    = {self.stop_loss}\n' \
            f'\ttake_profit  = {self.take_profit}\n' \
            f'\tprofit_close = {self.profit_close}\n' \
            f'\trisk         = {self.risk}\n'

    def determine_position_cost(self):
        """Calculate the position size according to account and strategy parameters."""
        return (self.account.allocated + self.account.available) * self.risk / self.stop_loss

    def should_close(self, position, pair, macro_RSI):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position.side == 'buy':
            stop_loss_hit = pair.price <= position.stop_loss
            take_profit_hit = pair.price >= position.take_profit

            macro_close = True if macro_RSI <= MACRO_RSI_MIN else False
            price_signal = pair.RSI >= self.max

            if self.profit_close and price_signal:
                price_signal = pair.price >= position.entry_price
        else:
            stop_loss_hit = pair.price >= position.stop_loss
            take_profit_hit = pair.price <= position.take_profit

            macro_close = True if macro_RSI >= MACRO_RSI_MAX else False
            price_signal = pair.RSI <= self.min

            if self.profit_close and price_signal:
                price_signal = pair.price <= position.entry_price

        # Calculate the position's length in minutes
        position_duration = (datetime.now() - position.opened_at).seconds / 60
        timer_hit = True if position_duration >= TIMER_TRIGGER else False

        return (
            stop_loss_hit or take_profit_hit or macro_close or price_signal or timer_hit,
            [stop_loss_hit, take_profit_hit, macro_close, price_signal, timer_hit]
        )
