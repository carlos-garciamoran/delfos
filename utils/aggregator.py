from datetime import datetime

from talib import RSI as rsi

from models.Pair import Pair
from utils.constants import *
import utils.binance as binance


def get_market_data(logger, symbols):
    """Fetch prices from Binance and calculate RSIs. Return pairs and macro-RSI."""
    pairs = []

    # Parse the price for each symbol and request the candlesticks of the latter
    for symbol in symbols:
        logger.debug('💡 ' + symbol[:-5])

        closes, code, error = binance.get_close_candles(symbol.replace('/', ''))

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
