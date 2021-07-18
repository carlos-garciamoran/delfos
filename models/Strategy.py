import ccxt
from dotenv import dotenv_values, load_dotenv
from loguru import logger

from models.Account import Account
from utils.constants import MACRO_RSI_MAX, MACRO_RSI_MIN


class Strategy:
    def __init__(self, defaults, strategy):
        # Required attributes
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

        self.name = f'{self.min}-{self.max}_SL-{(self.stop_loss*100):g}_TP-{(self.take_profit*100):g}'
        self.name += '_profit' if self.profit_close else ''

        if self.real:
            self.name += '_REAL'
            initial_account_size = self.init_real()
        else:
            self.trader, self.markets = None, None
            initial_account_size = strategy['account_size'] \
                if 'account_size' in strategy.keys() \
                else defaults['account_size']

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

    def init_real(self):
        load_dotenv()

        self.trader = ccxt.binanceusdm({
            'apiKey': dotenv_values()['BINANCE_APIKEY'],
            'secret': dotenv_values()['BINANCE_SECRETKEY'],
            'enableRateLimit': True
        })

        self.markets = self.trader.load_markets()

        # Filter undesired symbols
        for symbol in list(self.markets):
            info = self.markets[symbol]['info']
            if info['quoteAsset'] != 'USDT' or \
                info['contractType'] != 'PERPETUAL' or \
                info['status'] != 'TRADING' or \
                info['underlyingType'] != 'COIN':
                # Skip non-USDT, non-perpetual, non-traded, and quarterlies contracts
                del self.markets[symbol]
                continue

        # Fresh start: close all open positions on Binance before starting to trade
        for position in self.trader.fetchPositions():
            if position['entryPrice']:
                symbol, side = position['symbol'], position['side']
                inverted_side = 'sell' if side == 'long' else 'buy'
                size = abs(float(position['info']['positionAmt']))

                logger.info(f"Closing {symbol} {side} ({size:g})...")

                # Close the existing order
                self.trader.create_order(symbol, 'MARKET', inverted_side, size)

                # Cancel the corresponding SL & TP orders
                self.trader.fapiPrivate_delete_allopenorders({
                    'symbol': symbol.replace('/', '')
                })

        return self.trader.fetch_balance()['USDT']['free']

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

            if self.profit_close:
                price_signal = price_signal and pair.price >= position.entry_price
        else:
            stop_loss_hit = pair.price >= position.stop_loss
            take_profit_hit = pair.price <= position.take_profit

            macro_close = True if macro_RSI >= MACRO_RSI_MAX else False
            price_signal = pair.RSI <= self.min

            if self.profit_close:
                price_signal = price_signal and pair.price <= position.entry_price

        if macro_close:
            with open('macro-close.csv', 'a') as fd:
                fd.write(
                    f'{str(position.__dict__)},{str(pair.__dict__)},{macro_RSI:.2f}\n'
                )

        return (
            stop_loss_hit or take_profit_hit or macro_close or price_signal,
            [stop_loss_hit, take_profit_hit, macro_close, price_signal]
        )
