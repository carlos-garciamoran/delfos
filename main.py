#!/usr/bin/env python3
import json
from pathlib import Path
import os
import sys
from datetime import datetime
from time import sleep

from loguru import logger

import utils.binance as binance
import utils.emulator as emulator
import utils.taapi as taapi
from utils.constants import *
from utils.strategies import *


accounts = []
emojis = {
    True:  '💎', False:  '❌',
    'BUY': '🐃', 'SELL': '🐻',
}


def main():
    while True:
        logger.debug('📡 Hitting Binance...')

        # Catch odd error related to openssl socket connection
        try:
            # Fetch prices from Binance USDT pairs and the request's HTTP status code
            pairs, code, error = binance.get_prices()
        except OSError as e:
            logger.error('[!] Crashed on Binance request, dumping error...')
            logger.error(e)
            continue

        # API error checking
        if code != 200:
            logger.error('[!] Binance API returned non-200 (%d); exiting...' % code)
            logger.error(error)
            return

        scan(pairs)

        open_positions()


def scan(pairs):
    """Fetch RSIs, close positions which need so, and store pairs matching price signal for potential positions."""
    # For each pair, fetch its RSI and check if its position should be closed.
    global logged_symbols
    logged_symbols = []

    for pair in pairs:
        symbol = pair['symbol']

        # NOTE: should refactor without using .find()
        coin = symbol[:symbol.find('USDT')]
        t_symbol = '{}/{}'.format(coin, symbol[-4:])

        logger.debug('💡 ' + coin)

        # Catch odd error related to openssl socket connection
        try:
            pair['RSI'], code, error = taapi.get_RSI(t_symbol)
        except (KeyError, OSError) as e:
            logger.error('[!] Crashed on TAAPI request, dumping error...')
            logger.error(e)
            continue

        # API error checking
        if code != 200:
            logger.error('[!] TAAPI %d' % code)

            # Bad request. Most likely a dead coin still listed in Binance
            if code == 400:
                logger.error('[!] Found potential dead coin: ' + coin)
                # NON_TRADED_SYMBOLS.append(coin + 'USDT')
                continue
            # These codes are odd but happen, we just ignore them. 500's return an empty body
            elif code == 500 or code == 502 or code == 504 or code == 524 or code == 525:
                continue
            elif code == 429:
                logger.error(error)
                sleep(90)  # The rate-limit-exceeded block lasts 3 minutes for the Pro plan
            else:
                # Exit for unknown errors
                logger.error(error)
                sys.exit(1)

        logger.debug('   📟 Price: ${:<13} 📈 RSI: {:0.2f}'.format(pair['price'], pair['RSI']))

        for i in range(len(STRATEGIES)):
            account, strategy = accounts[i], STRATEGIES[i]

            # NOTE: this iterates for each position symbol
            account = close_if_needed(account, strategy, pair)

            if eval(strategy['is_interesting'])(pair):
                pair['strength'] = eval(strategy['compute_strength'])(pair)
                account['potential'].append(pair)

            accounts[i] = account
        # sleep(0.04)  # Avoid 429's from TAAPI

    # For each account, sort all potential positions in terms of strength
    for i in range(len(accounts)):
        account = accounts[i]
        # Most extreme RSIs have priority (i.e. positions are opened first)
        account['potential'].sort(key=lambda k: k['strength'], reverse=True)
        accounts[i] = account


def close_if_needed(account, strategy, pair):
    """Given a pair, close its position if its SL, TP, or a price signal has been hit."""
    opened = False
    price = pair['price']

    # Search for an existing position for the given symbol.
    for position in account['positions']:
        if position['symbol'] == pair['symbol']:
            opened = True
            break

    if opened:
        # Log the pair, price, and RSI of the open asset.
        if pair['symbol'] not in logged_symbols:
            with open('intel.csv', 'a') as fd:
                fd.write("%s,%f,%f,%s\n" % (pair['symbol'], price, pair['RSI'], datetime.now()))

            logged_symbols.append(pair['symbol'])

        # Stop loss and take profit are the same for all strategies.
        if position['side'] == 'BUY':
            stop_loss_hit   = price <= position['stop_loss']
            take_profit_hit = price >= position['take_profit']
        else:
            stop_loss_hit   = price >= position['stop_loss']
            take_profit_hit = price <= position['take_profit']

        # Always returns either true or false.
        price_signal_hit = eval(strategy['should_close'])(position, pair, strategy['is_interesting'])

        needs_to_close = price_signal_hit or stop_loss_hit or take_profit_hit

        if needs_to_close:
            position = emulator.close_order(position, price)
            account['positions'].remove(position)

            if position['pnl'][0] >= 0:
                account['wins'] += 1
            else:
                account['loses'] += 1

            account['allocated'] -= position['size']  # Adjust allocated capital
            account['available'] += position['size'] + position['pnl'][1]  # Recompound magic, baby

            account['pnl'] += position['pnl'][1]  # Update net p&l in USDT

            # Percentage increase = (final_value - starting_value) / starting_value * 100
            percentage = (account['available'] + account['allocated'] - ACCOUNT_SIZE) / ACCOUNT_SIZE * 100

            logger.warning('🔮 Strat: ' + strategy['name'])
            logger.warning('{} Closed {} {} at {}. P&L: {:0.2f}%, ${:0.2f}'.format(
                emojis[position['pnl'][0] >= 0], position['symbol'], position['side'],
                position['exit_price'], position['pnl'][0], position['pnl'][1]
            ))
            logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(
                account['available'] + account['allocated'], account['allocated']
            ))

            if stop_loss_hit:
                logger.info('🚫 SL hit')
            elif take_profit_hit:
                logger.info('🤝 TP hit')

            logger.info('💸 Total realized P&L: {:0.2f}%, ${:0.2f}'.format(
                percentage, account['pnl']
            ))
            logger.info('🤑 Wins: %d\t\t 🤔 Loses: %d' % (account['wins'], account['loses']))

            log_to_json(account, position)

    return account


def open_positions():
    """Open positions based on RSI strength. Ensure no more than 1 position per symbol is opened."""
    for i in range(len(STRATEGIES)):
        account, strategy = accounts[i], STRATEGIES[i]

        # NOTE: expensive op: O(N) growth, where N=len(positions)
        open_symbols = list(map(lambda p: p['symbol'], account['positions']))

        for pair in account['potential']:
            # Do not open a new position if there's an existing position (based on the symbol)
            if pair['symbol'] in open_symbols:
                continue

            # Halving is for testing purposes
            position_size = (account['available'] + account['allocated']) * ACCOUNT_RISK / STOP_LOSS / 2

            # This check is needed in the edge case of `ACCOUNT_RISK > STOP_LOSS`
            if position_size <= account['available']:
                # By this point there is a price signal due to scan() filtering via strategy['is_interesting']
                side = eval(strategy['get_side'])(pair)

                position = emulator.new_order(pair['symbol'], side, pair['price'], position_size)
                account['positions'].append(position)

                account['available'] -= position_size    # Remove the position size from the available capital
                account['allocated'] += position_size  # Add the position size to the allocated counter

                logger.warning('🔮 Strat: ' + strategy['name'])
                logger.warning('{} Opened {} {} at {} with ${:0.2f}'.format(
                    emojis[side], pair['symbol'], side, pair['price'], position_size
                ))
                logger.info('🚫 SL: %0.5f\t\t 🤝 TP: %0.5f' % (position['stop_loss'], position['take_profit']))
                logger.info('💰 Unused capital: ${:0.2f}\t 💵 Allocated capital: ${:0.2f} | {} positions'.format(
                    account['available'], account['allocated'], len(account['positions'])
                ))

                log_to_json(account)

        # All potential positions have been opened so reset the array for the next round
        account['potential'] = []

        accounts[i] = account


def log_to_json(account, position=None):
    if position:
        # Parse opened positions file and add the last opened position
        with open('%s/closed.json' % account['strategy'], 'r+') as fd:
            data = fd.read()
            closed = json.loads(data) + [position]
            fd.seek(0)
            fd.write(json.dumps(closed, indent=4) + '\n')
            fd.truncate()

        return

    # If no argument passed, dump all open positions
    with open('%s/opened.json' % account['strategy'], 'w') as fd:
        fd.write(json.dumps(account['positions'], indent=4) + '\n')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('[!] Need to provide a session name as argv, exiting...')
        sys.exit(1)

    session = sys.argv[1]

    Path('sessions/' + session).mkdir(parents=True, exist_ok=True)
    os.chdir('sessions/' + session)

    with open('intel.csv', 'w') as fd:
        fd.write("pair,price,RSI,timestamp\n")

    logger.remove()

    # Use debug() for writing to STDOUT but NOT to logfile
    logger.add('tracking.log', format="{time:MM-DD HH:mm:ss.SSS} | {message}", level="INFO")
    logger.add(sys.stdout, colorize=True, format="<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>")

    logger.info('Logging at: sessions/%s/' % session)

    logger.info('ACCOUNT_RISK: %0.2f' % ACCOUNT_RISK)
    logger.info('ACCOUNT_SIZE: %0.2f' % ACCOUNT_SIZE)
    logger.info('STOP_LOSS: %0.2f\tTAKE_PROFIT: %0.2f' % (STOP_LOSS, TAKE_PROFIT))

    # Create 1 dedicated account and directory for each trading strategy
    for strategy in STRATEGIES:
        strategy = strategy['name']

        Path(strategy).mkdir(parents=True, exist_ok=True)

        # Initialise JSON positions files
        with open('%s/closed.json' % strategy, 'w') as fd1, \
             open('%s/opened.json' % strategy, 'w') as fd2:
            fd1.write('[]\n')
            fd2.write('[]\n')

        accounts.append({
            'strategy': strategy,        # strategy name
            'allocated' : 0.0,           # capital allocated in positions
            'available' : ACCOUNT_SIZE,  # liquid unused capital + (realized) pnl
            'positions' : [],  # objects of the open positions
            'potential' : [],  # objects of potential positions to be opened: [symbol, price, RSI, strength]
            'pnl' : 0.0,  # total realized and recompounded profit & loss in USDT
            'loses' : 0,  # counter of profitable trades
            'wins': 0,    # counter of unprofitable trades
        })

    logger.info('ℹ️  Loaded %d strategies' % len(STRATEGIES))
    logger.info(STRATEGIES)

    try:
        main()
    except KeyboardInterrupt:
        logger.info('Heard CTRL-C, quitting...')
