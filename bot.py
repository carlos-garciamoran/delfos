#!/usr/bin/env python3
import json
import sys
from loguru import logger

from binance import *
from constants import *
from indicators import *
from strategies import *


account     = 1000.0      # available capital + (realized) pnl
allocated   = 0.0         # capital allocated in positions
pnl         = [0.0, 0.0]  # total realized and recompounded profit & loss [percentage, USDT]
positions   = []          # stores the objects of the open positions
wins, loses = 0, 0        # counters of trades with profits and loses

emojis = {
    True:  '💎', False:  '❌',
    'BUY': '🐃', 'SELL': '🐻',
}


def main():
    while True:
        # Fetch prices from Binance USDT pairs and the request's HTTP status code
        pairs, code = get_prices()

        # API error checking
        if code != 200:
            logger.error('[!] Binance API returned non-200 (%d); exiting...' % code)
            return

        # Each array stores an object for each pair made up of [symbol, price, RSI]
        potential = scan(pairs)  # Takes ~16 secs to scan 223 pairs

        logger.debug('🔎 Found %d potential positions' % len(potential))
        logger.info(potential)

        open_positions(potential)


def scan(pairs):
    '''Fetch RSI, close positions which need so, and store pairs matching price signal for post-ordering.'''
    potential = []

    # For each pair, fetch its RSI and check if it should be closed.
    for pair in pairs:
        symbol = pair['symbol']

        # Add slash between symbol and base (USDT) | TODO: refactor without using .find()
        coin = symbol[:symbol.find('USDT')]
        t_symbol = coin + '/' + symbol[-4:]

        logger.debug('💡 ' + coin)

        # Catch odd error related to openssl socket connection
        try:
            pair['RSI'], code = get_RSI(t_symbol)
        except OSError:
            continue

        # API error checking
        if code != 200:
            # These TAAPI errors appear often, so they are not logged
            if code == 400 or code == 500:
                continue

            logger.error('[!] TAAPI error returned an odd non-200 (%d); exiting...' % code)
            sys.exit(1)

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(pair['price'], pair['RSI']))

        # NOTE: alternative: check if position (corresponding to the pair) should be closed based on SL/TP + RSI
        close_if_needed(symbol, pair['price'], pair['RSI'])

        # Only consider pairs meeting the price signal
        if pair['RSI'] >= RSI_MAX or pair['RSI'] <= RSI_MIN:
            pair['strength'] = abs(50 - pair['RSI'])  # determines strength of RSI
            potential.append(pair)

    # Most extreme RSIs have priority (i.e. positions are opened first). Strength is key ;)
    potential = sorted(potential, key=lambda k: k['strength'], reverse=True)

    return potential


def close_if_needed(symbol, price, RSI):
    global allocated, account, pnl, wins, loses

    opened = False

    for position in positions:
        if position['symbol'] == symbol:
            opened = True
            break

    if opened:
        if position['side'] == 'BUY':
            stop_loss_hit   = price <= position['stop_loss']
            take_profit_hit = price >= position['take_profit']
        else:
            stop_loss_hit   = price >= position['stop_loss']
            take_profit_hit = price <= position['take_profit']

        # Strategy is called here. Always returns either true or false.
        price_signal_hit = evaluate_RSI(position, price, RSI)

        needs_to_close = price_signal_hit or stop_loss_hit or take_profit_hit

        if needs_to_close:
            position = close_order(position, price)
            positions.remove(position)

            if position['pnl'][0] >= 0:
                wins += 1
            else:
                loses += 1

            allocated -= position['size']                     # Adjust allocated capital
            account += position['size'] + position['pnl'][1]  # Recompound magic, baby
            pnl[0] += position['pnl'][0]                      # Record net p&l (percentage)
            pnl[1] += position['pnl'][1]                      # Idem           (USDT)

            logger.warning('{} Closed {} {} at {}! P&L is {:0.2f}%, ${:0.2f}'.format(
                emojis[position['pnl'][0] >= 0], position['symbol'], position['side'], position['exit_price'], position['pnl'][0], position['pnl'][1]
            ))
            logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(account+allocated, allocated))

            if stop_loss_hit:
                logger.info('🚫 SL hit' % stop_loss_hit)
            elif take_profit_hit:
                logger.info('🤝 TP hit' % take_profit_hit)

            logger.info('💸 Total realized P&L is {:0.2f}%, ${:0.2f}'.format(pnl[0], pnl[1]))
            logger.info('🤑 Wins: %d\t 🤔 Loses: %d' % (wins, loses))

            with open('%s-closed.positions' % logfile, 'a') as fd:
                fd.write(json.dumps(position, indent=4) + '\n')


def open_positions(potential):
    '''Open positions based on potential if there's available capital. Ensure no more than 1 position per symbol is opened'''
    global allocated, account, pnl, wins, loses

    # NOTE: expensive op: O(N) growth, where N=len(positions)
    open_symbols = list(map(lambda p: p['symbol'], positions))

    # TODO: run multiple strategies at the same time.

    for pair in potential:
        # Do not open a new position if there's an existing position
        if pair['symbol'] in open_symbols:
            continue

        # Halving is for testing purposes
        position_size = (account + allocated) * ACCOUNT_RISK / STOP_LOSS / 2

        # This check is needed in the edge case of `ACCOUNT_RISK > STOP_LOSS`
        if position_size < account:
            # By this point there is a price signal (RSI is either >= RSI_MAX or <= RSI_MIN due to scan() filtering)
            # BUY/SELL is the naming convention used by Binance, as opposed to bullish/bearish
            side = 'SELL' if pair['RSI'] >= RSI_MAX else 'BUY'

            position = new_order(pair['symbol'], side, pair['price'], position_size)
            positions.append(position)

            account -= position_size    # Remove the position size from the available capital
            allocated += position_size  # Add the position size to the allocated counter

            logger.warning('{} Opened {} {} at {} with ${:0.2f}'.format(
                emojis[side], pair['symbol'], side, pair['price'], position_size
            ))
            logger.info('🚫 SL: %0.5f\t\t 🤝 TP: %0.5f' % (position['stop_loss'], position['take_profit']))
            logger.info('💰 Unused capital: ${:0.2f}\t 💵 Allocated capital: ${:0.2f} | {} positions'.format(
                account, allocated, len(positions)
            ))

            with open('%s.positions' % logfile, 'a') as fd:
                fd.write(json.dumps(position, indent=4) + '\n')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('[!] Need to provide a log file as argv, exiting...')
        sys.exit(1)

    logfile = sys.argv[1] + '.log'

    logger.remove()

    # Use debug() for writing to STDOUT but NOT to logfile
    logger.add(logfile, format="{time:MM-DD HH:mm:ss.SSS} | {message}", level="INFO")
    logger.add(sys.stderr, colorize=True, format="<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>")

    logger.debug('Logging at: %s' % logfile)

    # TODO: start logging price when position is opened
    logger.info('ACCOUNT_RISK: %0.2f' % ACCOUNT_RISK)
    logger.info('STOP_LOSS: %0.2f\tTAKE_PROFIT: %0.2f' % (STOP_LOSS, TAKE_PROFIT))
    logger.info('RSI_MAX: %d\tRSI_MIN: %d' % (RSI_MAX, RSI_MIN))

    try:
        main()
    except KeyboardInterrupt:
        logger.info('Heard CTRL-C, quitting...')
    # except Exception as e:
    #     logger.error('Unknown error: quitting...')
    #     logger.error(e)
