from datetime import datetime
from time import sleep

import utils.binance as binance
import utils.taapi as taapi

from utils.constants import *


def get_market_data(logger):
    """Fetch prices from Binance and RSIs from TAAPI. Return prices, RSIs, and macro-RSI."""
    data, RSIs = [], []
    prices, code, error = binance.get_prices()

    if code != 200:
        return [], [], ['Binance', code, error]

    # Parse the price for each interesting symbol and request the RSI of the latter
    for pair in prices:
        symbol = pair['symbol']

        if symbol[-4:] != 'USDT' or \
            symbol in NON_TRADED_SYMBOLS or \
            'BULL' in symbol or \
            'BEAR' in symbol or \
            'UP' in symbol or \
            'DOWN' in symbol:
            # Skip uninsteresting symbols
            continue

        # NOTE: should refactor without using .find()
        coin = symbol[:symbol.find('USDT')]
        t_symbol = '{}/{}'.format(coin, symbol[-4:])
        logger.debug('💡 ' + coin)

        pair['price'] = float(pair['price'])
        pair['RSI'], code, error = taapi.get_RSI(t_symbol)

        if code != 200:
            # Bad request: either dead coin listed in Binance or recent addition not recognised by TAAPI
            if code == 400:
                logger.error('[!] Found potential dead/unlisted coin: ' + coin)
                # NON_TRADED_SYMBOLS.append(coin + 'USDT')
                continue
            # These codes are odd but happen, we just ignore them. 500's return an empty body
            elif code >= 500:  # known errors: 500, 502, 504, 524, 525
                sleep(2)
                continue
            elif code == 429:
                logger.error(error)
                sleep(90)  # The rate-limit-exceeded block lasts 3 minutes for the Pro plan
            else:
                # Exit for unknown errors
                return [], [], ['TAAPI', code, error]

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(pair['price'], pair['RSI']))
        data.append(pair)
        RSIs.append(pair['RSI'])

    macro_RSI = sum(RSIs) / len(RSIs)

    with open('macro-trend.csv', 'a') as fd:
        fd.write('%f,%s\n' % (macro_RSI, datetime.now()))

    return data, macro_RSI, None
