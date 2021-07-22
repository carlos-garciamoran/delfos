import ccxt
from loguru import logger

from utils.constants import BINANCE_APIKEY, BINANCE_SECRETKEY


class Trader:
    def __init__(self):
        """Initialise CCXT object and load markets."""
        self.exchange = ccxt.binanceusdm({
            'apiKey': BINANCE_APIKEY,
            'secret': BINANCE_SECRETKEY,
            'enableRateLimit': True
        })

        # Pointer to self.trader.markets
        self.markets = self.exchange.load_markets()
        self.symbols = self.filter_symbols()

    def filter_symbols(self):
        """Delete unwanted symbols from self.markets."""
        for symbol in list(self.markets):
            info = self.markets[symbol]['info']
            if info['quoteAsset'] != 'USDT' or \
                info['contractType'] != 'PERPETUAL' or \
                info['status'] != 'TRADING' or \
                info['underlyingType'] != 'COIN':
                # Skip non-USDT, non-perpetual, non-traded, and quarterlies contracts
                del self.markets[symbol]
                continue

        return list(self.markets)

    def setup_real_account(self, account):
        logger.warning('Found real strategy; reset margin and leverage? Takes about 2 minutes... (y/N) ', end='')
        answer = input()
        if answer == 'y' or answer == 'Y':
            logger.debug('Adjusting margins and leverage...')
            self.exchange.set_margins_and_leverage()

        # NOTE: `close_all_positions` does not ensure no positions are left open
        logger.debug('Fetching and closing open positions before launching...')
        self.close_all_positions()

        # Overwrite default balance with actual capital on exchange
        free_balance = self.exchange.fetch_balance()['USDT']['free']
        account.available, account.INITIAL_SIZE = free_balance, free_balance

    def set_margins_and_leverage(self):
        """Set margins to ISOLATED and leverage to x1 on Binance."""
        for symbol in self.symbols:
            logger.debug(symbol[:-5])
            alt_symbol = symbol.replace('/', '')

            self.exchange.fapiPrivate_post_leverage({'symbol': alt_symbol, 'leverage': 1})

            try:
                self.exchange.fapiPrivate_post_margintype({
                    'symbol': alt_symbol, 'marginType': 'ISOLATED'
                })
            except ccxt.ExchangeError as e:
                logger.debug(e)
                continue
            else:
                logger.info('Margin adjusted for ' + symbol)

    def close_all_positions(self):
        """Close all open positions on exchange with market order."""
        open_positions = list(filter(
            lambda p: p['contracts'] != 0, self.exchange.fetchPositions()
        ))

        if len(open_positions) > 0:
            logger.debug(f'Found {len(open_positions)} open positions. Closing now...')

            for position in open_positions:
                symbol, side = position['symbol'], position['side']
                inverted_side = 'sell' if side == 'long' else 'buy'
                size = abs(float(position['info']['positionAmt']))

                logger.debug(f'Closing {symbol} {side} ({size:g})...')
                logger.info(position)

                # Close the existing order
                logger.info(
                    self.exchange.create_order(symbol, 'MARKET', inverted_side, size)
                )

                # Cancel the corresponding SL & TP orders
                self.exchange.fapiPrivate_delete_allopenorders(
                    {'symbol': symbol.replace('/', '')}
                )
