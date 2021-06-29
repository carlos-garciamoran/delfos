#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from time import sleep

from loguru import logger

import utils.aggregator as aggregator
import utils.emulator as emulator
from utils.constants import *
from utils.Strategy import Strategy


accounts, strategies = [], []

emojis = {
    True:  '💎', False:  '❌',
    'BUY': '🐃', 'SELL': '🐻',
}


def main():
    while True:
        # TODO: need to find out which strategies have been removed from the file and remove the
        #       account from them. Also record unrealized P&L before closing account.
        #       DO NOT DELETE strategy directory.
        setup_strategies()

        logger.debug('ℹ️ Loaded %d strategies' % len(strategies))
        for strategy in strategies:
            logger.debug(strategy)

        logger.debug('📡 Aggregating market data...')

        # Catch odd openssl socket connection error
        try:
            pairs, macro_RSI, HTTP_error = aggregator.get_market_data(logger)
        except (KeyError, OSError, ZeroDivisionError) as e:
            logger.error('[!] Crashed on market data request, dumping error...')
            logger.error(e)
            continue

        if HTTP_error:
            logger.error('[!] %s API returned %d; exiting...' % (HTTP_error[0], HTTP_error[1]))
            logger.error(HTTP_error[2])
            return

        if macro_RSI <= 30:
            logger.debug('📐🐻🐻 SUPER BEARISH macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 30 and macro_RSI <= 42:
            logger.debug('📐🐻 BEARISH macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 42 and macro_RSI <= 58:
            logger.debug('📐⚖️  NEUTRAL macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 58 and macro_RSI <= 70:
            logger.debug('📐🐃 BULLISH macro-trend (%0.2f)' % macro_RSI)
        else:
            logger.debug('📐🐃🐃 SUPER BULLISH macro-trend (%0.2f)' % macro_RSI)

        logger.debug('Closing positions which need so...')
        close_and_open(pairs, macro_RSI)

        # open_positions(macro_RSI)


def setup_strategies():
    """Parse JSON strategies and set up an account and directory for new ones."""
    with open('strategies.json') as fd:
        raw_strategies = json.loads(fd.read())

    for raw_strategy in raw_strategies:
        try:
            strategy = Strategy(raw_strategy)
        except KeyError as e:
            logger.error('[!] Error parsing %s' % raw_strategy['name'])
            logger.error('[!] Need to add strategy parameter %s, skipping...' % e)
            continue

        # TODO: check name as well?
        # Skip already existing strategies so they are not reset
        name = strategy.name
        if strategy in strategies:
            continue

        strategies.append(strategy)      # Add new strategy
        Path(name).mkdir(exist_ok=True)  # Each strategy gets its own directory

        # Create JSON files for tracking positions
        with open('%s/closed.json' % name, 'w') as fd1, \
            open('%s/opened.json' % name, 'w') as fd2:
            fd1.write('[]\n')
            fd2.write('[]\n')

        # Create dedicated trading account
        accounts.append({
            'strategy': name,
            'allocated': 0.0,  # capital allocated in positions in USDT
            'available': ACCOUNT_SIZE,  # liquid unused capital + (realized) pnl
            'positions': [],  # open positions
            'potential': [],  # positions to be opened: [symbol, price, RSI, strength]
            'pnl': 0.0,  # total realized and recompounded profit & loss in USDT
            'loses': 0,  # counter of unprofitable trades
            'wins': 0,   # counter of profitable trades
        })


def close_and_open(pairs, macro_RSI):
    """Close positions which need so and store pairs matching price signal for potential positions."""
    global accounts

    logged_symbols = []  # Tracks symbols logged in history.csv

    for i in range(len(strategies)):
        account, strategy = accounts[i], strategies[i]
        # open_symbols = list(map(lambda s: s['symbol'], account['positions']))

        # First close all necessary positions for the given strategy
        for pair in pairs:
            # NOTE: this iterates for each position symbol, expensive op!!
            # TODO: get open positions before `pairs` loop, reduce iteractions => improve perf
            #       same data is also used for `open_positions`, keep code DRY
            account = close_if_needed(account, strategy, pair, macro_RSI, logged_symbols)

            if strategy.pair_is_interesting(pair):
                pair['strength'] = strategy.compute_strength(pair)
                account['potential'].append(pair)

        # Sort all potential positions of each account in terms of strength
        # Most extreme RSIs have priority (i.e. positions are opened first)
        account['potential'].sort(key=lambda k: k['strength'], reverse=True)

        # logger.debug('Opening potential positions %s...' % strategy.name)

        # Then open the interesting positions
        account = open_positions(account, strategy, macro_RSI)

        accounts[i] = account


def close_if_needed(account, strategy, pair, macro_RSI, logged_symbols):
    """Given a pair, close its position if its SL, TP, or a price signal has been hit."""
    opened = False
    price = pair['price']

    # Search for an existing position for the given symbol.
    for position in account['positions']:
        if position['symbol'] == pair['symbol']:
            opened = True
            break

    # Search for an existing position for the given symbol.
    if opened:
        # Log the pair, price, and RSI of the open asset.
        if pair['symbol'] not in logged_symbols:
            with open('history.csv', 'a') as fd:
                fd.write('%s,%f,%f,%s\n' % (pair['symbol'], price, pair['RSI'], datetime.now()))

            logged_symbols.append(pair['symbol'])

        needs_to_close = strategy.should_close(position, pair, macro_RSI)

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

            logger.warning('🔮 Strat: ' + strategy.name)
            logger.warning('{} Closed {} {} at {}. P&L: {:0.2f}%, ${:0.2f}'.format(
                emojis[position['pnl'][0] >= 0], position['symbol'], position['side'],
                position['exit_price'], position['pnl'][0], position['pnl'][1]
            ))
            logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(
                account['available'] + account['allocated'], account['allocated']
            ))

            # SL/TP check repeated here for post-analysis purposes
            if position['side'] == 'BUY':
                stop_loss_hit = pair['price'] <= position['stop_loss']
                take_profit_hit = pair['price'] >= position['take_profit']
            else:
                stop_loss_hit = pair['price'] >= position['stop_loss']
                take_profit_hit = pair['price'] <= position['take_profit']

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


def open_positions(account, strategy, macro_RSI):
    """Open positions based on RSI strength. Ensure no more than 1 position per symbol is opened."""
    # NOTE: expensive op: O(N) growth, where N=len(positions)
    open_symbols = list(map(lambda p: p['symbol'], account['positions']))

    for pair in account['potential']:
        # Do not open a new position if there's an existing position (based on the symbol)
        if pair['symbol'] in open_symbols:
            continue

        # Halving is for testing purposes
        position_size = (account['available'] + account['allocated']) * ACCOUNT_RISK / STOP_LOSS

        # This check is needed in the edge case of `ACCOUNT_RISK > STOP_LOSS`
        if position_size <= account['available']:
            # By this point there is a price signal due to scan() filtering via strategy['is_interesting']
            side = strategy.determine_side(pair)

            # TODO: move code away from open_positions. Simply check avg RSI before including
            #        in `potential` from `scan()`
            if macro_RSI <= 30 and side == 'BUY':
                logger.warning('⛔ Skipping false-flag (BUY in bearish market)')
                continue
            elif macro_RSI >= 70 and side == 'SELL':
                logger.warning('⛔ Skipping false-flag (SELL in bullish market)')
                continue

            position = emulator.new_order(pair['symbol'], side, pair['price'], position_size, strategy)
            account['positions'].append(position)

            account['available'] -= position_size  # Remove the position size from the available capital
            account['allocated'] += position_size  # Add the position size to the allocated counter

            logger.warning('🔮 Strat: ' + strategy.name)
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

    return account


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
    copyfile('strategies.json', 'sessions/{}/strategies.json'.format(session))
    os.chdir('sessions/' + session)

    with open('history.csv', 'w') as fd1, open('macro-trend.csv', 'w') as fd2:
        fd1.write('pair,price,RSI,timestamp\n')
        fd2.write('RSI,timestamp\n')

    logger.remove()

    # Use debug() for writing to STDOUT but NOT to logfile
    logger.add('tracking.log', format="{time:MM-DD HH:mm:ss.SSS} | {message}", level="INFO")
    logger.add(sys.stdout, colorize=True, format="<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>")

    logger.info('Logging at: sessions/%s/' % session)
    logger.info('ACCOUNT_RISK: %0.2f' % ACCOUNT_RISK)
    logger.info('ACCOUNT_SIZE: %0.2f' % ACCOUNT_SIZE)

    logger.info('STOP_LOSS: %0.2f' % STOP_LOSS)
    logger.info('TAKE_PROFIT: %0.2f' % TAKE_PROFIT)

    try:
        main()
    except KeyboardInterrupt:
        logger.warning('Heard CTRL-C, quitting...')
