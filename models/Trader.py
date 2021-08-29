import ccxt
from loguru import logger

from utils.constants import BINANCE_APIKEY, BINANCE_SECRETKEY, LEVERAGE


class Trader:
    def __init__(self):
        """Initialise CCXT object and load markets."""
        self.exchange = ccxt.binanceusdm({
            'apiKey': BINANCE_APIKEY,
            'secret': BINANCE_SECRETKEY,
            'enableRateLimit': True
        })

        self.exchange.load_markets()
        self.symbols = self.filter_symbols()

    def filter_symbols(self):
        """Delete unwanted symbols from self.markets."""
        markets = self.exchange.markets

        for symbol in list(markets):
            info = markets[symbol]['info']
            if info['quoteAsset'] != 'USDT' or \
                info['contractType'] != 'PERPETUAL' or \
                info['status'] != 'TRADING' or \
                info['underlyingType'] != 'COIN':
                # Skip non-USDT, non-perpetual, non-traded, and quarterlies contracts
                del markets[symbol]
                continue

        # return list(map(lambda x: x.replace('/',''), markets))
        return list(markets)

    def setup_real_account(self, account, reset):
        """Reset margins if wanted, close open positions and set account balance."""
        logger.warning(f'⚠️  Found REAL strategy')

        if reset:
            logger.debug(f'Setting all token\'s leverage to x{LEVERAGE}...')
            self.set_leverage()

            logger.debug('Setting all token\'s margin mode to ISOLATED...')
            self.set_margin_mode()
        elif reset is None:
            logger.info(f'Reset leverage to x{LEVERAGE}? Takes about 1 minute (y/N) ', end='')
            answer = input()
            if answer == 'y' or answer == 'Y':
                logger.debug(f'Setting all token\'s leverage to x{LEVERAGE}...')
                self.set_leverage()

            logger.info('Reset margin mode to ISOLATED? Takes about 1 minute (y/N) ', end='')
            answer = input()
            if answer == 'y' or answer == 'Y':
                logger.debug('Setting all token\'s margin mode to ISOLATED...')
                self.set_margin_mode()

        # NOTE: `close_all_positions` does not ensure no positions are left open
        logger.debug('Fetching and closing open positions before launching...')
        self.close_all_positions()

        # Overwrite default balance with actual capital on exchange
        free_balance = self.exchange.fetch_balance()['USDT']['free']
        account.available, account.INITIAL_SIZE = free_balance, free_balance

    def set_leverage(self):
        """Set all token's leverage to `LEVERAGE` on Binance."""
        for symbol in self.symbols:
            logger.debug(symbol[:-5])
            alt_symbol = symbol.replace('/', '')

            self.exchange.fapiPrivate_post_leverage({'symbol': alt_symbol, 'leverage': LEVERAGE})
    
    def set_margin_mode(self):
        """Set  all token's margin mode to ISOLATED on Binance."""
        for symbol in self.symbols:
            logger.debug(symbol[:-5])
            alt_symbol = symbol.replace('/', '')

            try:
                self.exchange.fapiPrivate_post_margintype({
                    'symbol': alt_symbol, 'marginType': 'ISOLATED'
                })
            except ccxt.ExchangeError as e:
                logger.debug(e)
                continue
            else:
                logger.info('Margin mode adjusted for ' + symbol)

    def close_all_positions(self):
        """Close all open positions on exchange with market order."""
        open_positions = list(filter(
            lambda p: p['contracts'] != 0, self.exchange.fetchPositions()
        ))

        logger.debug(f'Found {len(open_positions)} open positions')

        if len(open_positions) > 0:
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
