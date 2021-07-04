from datetime import datetime
from time import sleep

from models.Pair import Pair

import utils.binance as binance
import utils.taapi as taapi
from utils.constants import *


def get_market_data(logger):
    """Fetch prices from Binance and RSIs from TAAPI. Return prices, RSIs, and macro-RSI."""
    pairs = []
    prices, code, error = binance.get_prices()

    if code != 200:
        return [], [], ['Binance', code, error]

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

        # NOTE: should refactor without using .find()
        coin = symbol[:symbol.find('USDT')]
        taapi_symbol = '{}/{}'.format(coin, symbol[-4:])

        logger.debug('💡 ' + coin)

        price = float(price['price'])
        RSI, code, error = taapi.get_RSI(taapi_symbol)

        if code != 200:
            # Bad request: either dead coin listed in Binance or recent addition not recognised by TAAPI
            if code == 400:
                logger.error('[!] Found potential dead/unlisted coin: ' + coin)
                logger.error(error)
                # NON_TRADED_SYMBOLS.append(coin + 'USDT')
                continue
            # These codes are odd but happen, we just ignore them. 500's return an empty body
            elif code >= 500:  # known errors: 500, 502, 504, 524, 525
                sleep(2)
                continue
            elif code == 429:
                logger.error(error)
                sleep(60)  # The rate-limit-exceeded block lasts 3 minutes for the Pro plan
            else:
                # Exit for unknown errors
                return [], [], ['TAAPI', code, error]

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(price, RSI))

        pairs.append(Pair(symbol, price, RSI))

        sleep(0.03)

    macro_RSI = sum(map(lambda p: p.RSI, pairs)) / len(pairs)

    with open('macro-trend.csv', 'a') as fd:
        fd.write('%f,%s\n' % (macro_RSI, datetime.now()))

    return pairs, macro_RSI, None
