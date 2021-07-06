from datetime import datetime

from models.Pair import Pair

import utils.binance as binance
from talib import RSI as rsi
from utils.constants import *


def get_market_data(logger):
    """Fetch prices from Binance and RSIs from TAAPI. Return prices, RSIs, and macro-RSI."""
    pairs = []

    # NOTE: this call is not really needed, it is only done to retrieve the active symbols.
    prices, code, error = binance.get_prices()

    if code != 200:
        return [], [], ['/ticker', code, error]

    # Parse the price for each interesting symbol and request the RSI of the latter
    for price in prices:
        symbol = price['symbol']

        if symbol[-4:] != 'USDT' or \
            symbol in NON_TRADED_SYMBOLS or \
            'BULL' in symbol or \
            'BEAR' in symbol or \
            'UP' in symbol or \
            'DOWN' in symbol or \
            '_' in symbol:
            # Skip uninsteresting symbols (dead/unlisted, sided, quarterlies)
            continue

        logger.debug('💡 ' + symbol[:-4])

        closes, code = binance.get_close_candles(symbol)

        if code != 200:
            return [], [], ['/kline', code, error]

        # Last value of the array is the most recent
        price, RSI = closes[-1], rsi(closes)[-1]

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(price, RSI))

        pairs.append(Pair(symbol, price, RSI))

    macro_RSI = sum(map(lambda p: p.RSI, pairs)) / len(pairs)

    with open('macro-trend.csv', 'a') as fd:
        fd.write('%f,%s\n' % (macro_RSI, datetime.now()))

    return pairs, macro_RSI, None
