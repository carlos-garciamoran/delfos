from datetime import datetime

from loguru import logger
from talib import RSI as rsi

from models.Pair import Pair
import utils.binance as binance


def get_market_data(symbols):
    """Fetch prices from Binance and calculate RSIs. Return pairs and macro-RSI."""
    pairs = []

    # Request the candlesticks of each symbol and calculate its RSI
    for symbol in symbols:
        closes, code, error = binance.get_close_candles(symbol.replace('/', ''))

        if code != 200:
            return [], [], [code, error]

        # Last value of the array is the most recent
        price, RSI = closes[-1], rsi(closes)[-1]

        pairs.append(Pair(symbol, price, RSI))

        logger.debug(f'💡 {symbol[:-5]:<8} - 📟 ${price:<11} 📈 {RSI:.2f}')

    macro_RSI = sum(map(lambda p: p.RSI, pairs)) / len(pairs)

    with open('macro-trend.csv', 'a') as fd:
        fd.write(f'{macro_RSI},{datetime.now()}\n')

    return pairs, macro_RSI, None
