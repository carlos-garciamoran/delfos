#!/usr/bin/env python3
import sys
from loguru import logger

from binance import *
from constants import *
from indicators import *
from strategies import *

account = {
    'allocated': 0.0,         # capital allocated in positions
    'liquid':    1000.0,      # available capital + (realized) pnl
    'pnl':       [0.0, 0.0],  # total realized and recompounded profit & loss [percentage, USDT]
    'loses':     0,           # counters of trades with profits and loses
    'wins':      0,
}

allocated = 0.0     # capital allocated in positions
account = 1000.0    # available capital + (realized) pnl
pnl = [0.0, 0.0]    # total realized and recompounded profit & loss [percentage, USDT]
wins, loses = 0, 0  # counters of trades with profits and loses

positions = []      # stores the objects of the open positions


def main():
    while True:
        # Fetch prices from Binance USDT pairs and the request's HTTP status code
        pairs, code = get_prices()

        # Error checking
        if code != 200:
            logger.error('[!] Binance API returned non-200 (%d); exiting...' % code)
            return

        # Arrays store an object for each pair made up of: symbol, price, and RSI
        bearish, bullish = fetch_potential(pairs)

        # Sort the pairs by their respective extremes. Pairs with the most extreme RSI's are opened first
        bearish = sorted(bearish, key=lambda k: k['RSI'], reverse=True)  # Highest RSI first
        bullish = sorted(bullish, key=lambda k: k['RSI'])                # Lowest  RSI first

        logger.info('🔎 Found %d bearish & %d bullish' % (len(bearish), len(bullish)))

        logger.info(bearish)
        logger.info(bullish)

        bearish_symbols = list(map(lambda p: p['symbol'], bearish))
        bullish_symbols = list(map(lambda p: p['symbol'], bullish))

        # TODO: first close existing positions, then open interesting positions
        for position in positions:
            if position['symbol'] in bearish_symbols:
                # close_position()
                pass

            if position['symbol'] in bullish_symbols:
                pass

        # TODO: open positions for each pair. Always check available balance!!
        # TODO: start logging price when position is opened


def fetch_potential(pairs):
    '''Store pairs matching price signal for post-ordering. Takes ~16 secs to scan 223 pairs.'''
    bearish, bullish = [], []

    # NOTE: expensive operation
    open_symbols = list(map(lambda p: p['symbol'], positions))

    for pair in pairs:
        symbol = pair['symbol']

        # Add slash between symbol and base (USDT) | TODO: Improve without using .find()
        coin = symbol[:symbol.find('USDT')]
        t_symbol = coin + '/' + symbol[-4:]

        logger.debug('💡 ' + coin)

        # Catch odd error related to openssl socket connection
        try:
            RSI, code = get_RSI(t_symbol)
        except OSError:  # requests.exceptions.ConnectionError
            continue

        if code != 200:
            # These TAAPI errors appear often, so they are not logged
            if code == 400 or code == 500:
                continue

            logger.error('[!] TAAPI error returned an odd non-200 (%d); exiting...' % code)
            sys.exit(1)

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(pair['price'], RSI))

        pair['RSI'] = RSI

        # Only consider pairs meeting the price signal
        if RSI >= RSI_MAX:
            # TODO: look for open position and close it if opposite direction
            bearish.append(pair)
            if symbol in open_symbols:
                # TODO: close position
                pass

        elif RSI <= RSI_MIN:
            bullish.append(pair)

        # think(symbol, price, RSI)
    return bearish, bullish


def close_position(position):
    position = close(position, price)
    positions.remove(position)

    if position['pnl'][0] >= 0:
        wins += 1
    else:
        loses += 1

    allocated -= position['size']                     # Adjust allocated capital
    account += position['size'] + position['pnl'][1]  # Recompound magic, baby
    pnl[0] += position['pnl'][0]                      # Record net p&l (percentage)
    pnl[1] += position['pnl'][1]                      # Idem           (USDT)

    logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(account+allocated, allocated))
    logger.info('🚫 SL hit: %r\t 🤝 TP hit: %r' % (stop_loss_hit, take_profit_hit))
    logger.info('💸 Total realized P&L is ${:0.2f}'.format(pnl))
    logger.info('🤑 Wins: %d\t 🤔 Loses: %d' % (wins, loses))


def think(symbol, price, RSI):
    global account, allocated, liquid, loses, pnl, wins

    opened = False

    # If no price signal, quit
    if RSI > RSI_MIN and RSI < RSI_MAX:
        return

    # Close open positions
    for position in positions:
        if position['symbol'] == symbol:
            opened = True

            if position['side'] == 'BUY':
                stop_loss_hit   = price <= position['stop_loss']
                take_profit_hit = price >= position['take_profit']
            else:
                stop_loss_hit   = price >= position['stop_loss']
                take_profit_hit = price <= position['take_profit']

            # TODO: run multiple strategies at the same time.

            # Strategy is called here. Always returns either true or false.
            needsToClose = evaluateRSI(position, price, RSI) or stop_loss_hit or take_profit_hit

            if needsToClose:
                position = close(position, price)
                positions.remove(position)

                if position['pnl'][0] >= 0:
                    wins += 1
                else:
                    loses += 1

                allocated -= position['size']                     # Adjust allocated capital
                account += position['size'] + position['pnl'][1]  # Recompound magic, baby
                pnl[0] += position['pnl'][0]                      # Record net p&l (percentage)
                pnl[1] += position['pnl'][1]                      # Idem           (USDT)

                logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(account+allocated, allocated))
                logger.info('🚫 SL hit: %r\t 🤝 TP hit: %r' % (stop_loss_hit, take_profit_hit))
                logger.info('💸 Total realized P&L is ${:0.2f}'.format(pnl))
                logger.info('🤑 Wins: %d\t 🤔 Loses: %d' % (wins, loses))

    # halving is for testing purposes
    position_size = (account + allocated) * ACCOUNT_RISK / STOP_LOSS / 2

    # NOTE: position_size < account check may not be needed
    # Open a new position if there is minimum capital and there's no existing position
    if position_size < account and not opened:
        # By this point there is a price signal (RSI is either >= RSI_MAX or <= RSI_MIN)
        side = 'SELL' if RSI >= RSI_MAX else 'BUY'

        positions.append( new_order( symbol, side, price, position_size ) )

        account -= position_size    # Remove the position size from the available capital
        allocated += position_size  # Add the position size to the allocated counter

        logger.info('💰 Unused capital: ${:0.2f}\t 💵 Allocated capital: ${:0.2f} | {} positions'.format(
            account, allocated, len(positions)
        ))


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('[!] Need to provide a log file as argv, exiting...')
        sys.exit(1)

    logfile = sys.argv[1] + '.log'

    logger.remove()

    # NOTE: use debug() for writing to STDOUT but NOT to logfile
    logger.add(logfile, format="{time:MM-DD HH:mm:ss.SSS} | {message}", level="INFO")
    logger.add(sys.stderr, colorize=True, format="<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>")

    logger.debug('Logging at: %s' % logfile)

    logger.info('ACCOUNT_RISK: %0.2f' % ACCOUNT_RISK)
    logger.info('STOP_LOSS: %0.2f\t TAKE_PROFIT: %0.2f' % (STOP_LOSS, TAKE_PROFIT))
    logger.info('RSI_MAX: %d\tRSI_MIN: %d' % (RSI_MAX, RSI_MIN))

    try:
        main()
    except KeyboardInterrupt:
        logger.info('Heard CTRL-C, quitting...')
    # except Exception as e:
    #     logger.error('Unknown error: quitting...')
    #     logger.error(e)
