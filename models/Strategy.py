import ccxt
from dotenv import dotenv_values, load_dotenv

from models.Account import Account
from utils.constants import *


class Strategy:
    def __init__(self, defaults, strategy):
        # Required attributes
        self.name = strategy['name']
        self.min, self.max = strategy['constants'][0], strategy['constants'][1]

        # Optional attributes (defaults)
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

        if self.real:
            load_dotenv()

            self.trader = ccxt.binanceusdm({
                'apiKey': dotenv_values()["BINANCE_APIKEY"],
                'secret': dotenv_values()["BINANCE_SECRETKEY"],
                'enableRateLimit': True
            })

            initial_size = self.trader.fetch_balance()['USDT']['free']
            self.markets = self.trader.load_markets()

            for symbol in list(self.markets):
                if symbol[-4:] != 'USDT' \
                    or '/' not in symbol \
                    or self.markets[symbol]['info']['underlyingType'] != 'COIN':
                    # Skip non-USDT, quarterlies, and indexes
                    del self.markets[symbol]
                    continue
        else:
            self.trader, self.markets = None, None
            initial_size = strategy['account_size'] \
                if 'account_size' in strategy.keys() \
                else defaults['account_size']

        # Create dedicated trading account and link it to the strategy
        self.account = Account(self, initial_size)

    def __eq__(self, other):
        if not isinstance(other, Strategy):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        # NOTE: the account should not be compared
        return self.name == other.name \
            and self.min == other.min \
            and self.max == other.max \
            and self.profit_close == other.profit_close \
            and self.stop_loss == other.stop_loss \
            and self.take_profit == other.take_profit \
            and self.risk == other.risk \
            and self.real == other.real

    def __str__(self):
        return '''{}
    real         = {}
    min, max     = {}, {}
    stop_loss    = {}
    take_profit  = {}
    profit_close = {}
    risk         = {}\n'''.format(self.name,
        self.real, self.min, self.max, self.stop_loss, self.take_profit,
        self.profit_close, self.risk
        )


    def determine_position_size(self, allocated, available):
        """Calculate the position size according to account and strategy parameters."""
        return (allocated + available) * self.risk / self.stop_loss

    def should_close(self, position, pair, macro_RSI):
        """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
        if position.side == 'buy':
            stop_loss_hit = pair.price <= position.stop_loss
            take_profit_hit = pair.price >= position.take_profit

            macro_close = True if macro_RSI <= MACRO_RSI_MIN else False
            price_signal = pair.RSI >= self.max

            if self.profit_close:
                price_signal = price_signal and pair.price >= position.entry_price
        else:
            stop_loss_hit = pair.price >= position.stop_loss
            take_profit_hit = pair.price <= position.take_profit

            macro_close = True if macro_RSI >= MACRO_RSI_MAX else False
            price_signal = pair.RSI <= self.min

            if self.profit_close:
                price_signal = price_signal and pair.price <= position.entry_price

        # NOTE: for testing purposes
        if macro_close:
            with open('macro-close.csv', 'a') as fd:
                fd.write('%s,%s,%0.2f\n' % (str(position.__dict__), str(pair.__dict__), macro_RSI))

        # NOTE: return causes for testing purposes
        return (
            stop_loss_hit or take_profit_hit or macro_close or price_signal,
            [stop_loss_hit, take_profit_hit, macro_close, price_signal]
        )
