#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from loguru import logger

from utils.Account import Account
from utils.Strategy import Strategy
from utils.constants import *
import utils.aggregator as aggregator
import utils.emulator as emulator


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
        setup_accounts_and_strategies()

        logger.debug('📡 Aggregating market data...')

        # Catch TAAPI and openssl socket connection errors
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
            logger.debug('🐻🐻 SUPER BEARISH macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 30 and macro_RSI <= 42:
            logger.debug('🐻 BEARISH macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 42 and macro_RSI <= 58:
            logger.debug('⚖️  NEUTRAL macro-trend (%0.2f)' % macro_RSI)
        elif macro_RSI > 58 and macro_RSI <= 70:
            logger.debug('🐃 BULLISH macro-trend (%0.2f)' % macro_RSI)
        else:
            logger.debug('🐃🐃 SUPER BULLISH macro-trend (%0.2f)' % macro_RSI)

        logger.debug('🔎 Closing positions which need so...')
        close_and_open(pairs, macro_RSI)


def setup_accounts_and_strategies():
    """Parse JSON strategies and set up an account and directory for new ones."""
    with open('strategies.json') as fd:
        data = json.loads(fd.read())

    defaults, strategies_data = data['defaults'], data['strategies']

    for strategy_data in strategies_data:
        try:
            strategy = Strategy(defaults, strategy_data)
        except KeyError as e:
            logger.error('[!] Error parsing %s' % strategy_data['name'])
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

        # NOTE: `available` is not set by strategy, it only uses the default
        # Create dedicated trading account
        accounts.append( Account(defaults['account_size'], strategy) )

        logger.info('Defaults: ' + str(defaults))
        logger.info(strategy)
        logger.info('Running %d strategies' % len(strategies))


def close_and_open(pairs, macro_RSI):
    """Close positions which need so and store pairs matching price signal for potential positions."""
    logged_symbols = []  # Tracks symbols logged in history.csv

    for i in range(len(strategies)):
        account, strategy = accounts[i], strategies[i]
        # open_symbols = list(map(lambda s: s['symbol'], account.positions))

        # First close all necessary positions for the given strategy
        for pair in pairs:
            # NOTE: this iterates for each position symbol, expensive op!!
            # TODO: get open positions before `pairs` loop, reduce iteractions => improve perf
            #       same data is also used for `open_positions`, keep code DRY
            close_if_needed(account, strategy, pair, macro_RSI, logged_symbols)

            if strategy.pair_is_interesting(pair):
                pair['strength'] = strategy.compute_strength(pair)
                account.potential.append(pair)

        # Sort all potential positions of each account in terms of strength
        # Most extreme RSIs have priority (i.e. positions are opened first)
        account.potential.sort(key=lambda k: k['strength'], reverse=True)

        logger.debug('Opening potential positions %s...' % strategy.name)

        # Then open the interesting positions
        open_positions(account, strategy, macro_RSI)
        logger.debug(account)


def close_if_needed(account, strategy, pair, macro_RSI, logged_symbols):
    """Given a pair, close its position if its SL, TP, or a price signal has been hit."""
    opened = False
    price = pair['price']

    # Search for an existing position for the given symbol.
    for position in account.positions:
        if position['symbol'] == pair['symbol']:
            opened = True
            break

    if opened:
        # Log the pair, price, and RSI of the open asset.
        if pair['symbol'] not in logged_symbols:
            with open('history.csv', 'a') as fd:
                fd.write('%s,%f,%f,%s\n' % (pair['symbol'], price, pair['RSI'], datetime.now()))

            logged_symbols.append(pair['symbol'])

        # Causes returned for testing purposes
        needs_to_close, causes = strategy.should_close(position, pair, macro_RSI)

        if needs_to_close:
            position = emulator.close_order(position, price)
            logger.debug(account)
            account.log_closed_order(position)
            logger.debug(account)

            # Percentage increase = (final_value - starting_value) / starting_value * 100
            percentage = \
                (account.available + account.allocated - strategy.account_size) \
                / strategy.account_size * 100

            logger.warning('🔮 Strategy: ' + strategy.name)
            logger.warning('{} Closed {} {} at {}. P&L: {:0.2f}%, ${:0.2f}'.format(
                emojis[position['pnl'][0] >= 0], position['symbol'], position['side'],
                position['exit_price'], position['pnl'][0], position['pnl'][1]
            ))
            logger.warning('🧨 Fee = $%0.2f' % position['fee'])
            logger.info('💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}'.format(
                account.available + account.allocated, account.allocated
            ))

            if causes[0]:
                logger.info('🎛  Macro signal')
            elif causes[1]:
                logger.info('⛔️ SL hit')
            elif causes[2]:
                logger.info('🤝 TP hit')
            elif causes[3]:
                logger.info('📞 Price signal hit')

            logger.info('💸 Total realized P&L: {:0.2f}%, ${:0.2f}'.format(
                percentage, account.pnl
            ))
            logger.info('🤑 Wins: %d\t\t 🤔 Loses: %d' % (account.wins, account.loses))

            log_to_json(account, position)


def open_positions(account, strategy, macro_RSI):
    """Open positions based on RSI strength. Ensure no more than 1 position per symbol is opened."""
    # NOTE: expensive op: O(N) growth, where N=len(positions)
    open_symbols = list(map(lambda p: p['symbol'], account.positions))

    for pair in account.potential:
        # Do not open a new position if there's an existing position (based on the symbol)
        if pair['symbol'] in open_symbols:
            continue

        position_size = strategy.determine_position_size(account.allocated, account.available)

        # This check is needed in the edge case of `strategy.account_risk > strategy.stop_loss`
        if position_size <= account.available:
            # By this point there is a price signal due to scan() filtering via strategy['is_interesting']
            side = strategy.determine_side(pair, macro_RSI)

            # TODO: move code away from open_positions. Simply check macro_RSI before including
            #       pair in `account[potential]` at `close_and_open()`
            if macro_RSI <= MACRO_RSI_MIN and side == 'BUY':
                logger.debug('⛔ Skipping false-flag (BUY in bearish market)')
                continue
            elif macro_RSI >= MACRO_RSI_MAX and side == 'SELL':
                logger.debug('⛔ Skipping false-flag (SELL in bullish market)')
                continue

            position = emulator.new_order(pair['symbol'], side, pair['price'], position_size, strategy)
            account.log_new_order(position)

            logger.warning('🔮 Strategy: ' + strategy.name)
            logger.warning('{} Opened {} {} at {} with ${:0.2f}'.format(
                emojis[side], pair['symbol'], side, pair['price'], position_size
            ))
            logger.info('🚫 SL: %0.5f\t\t 🤝 TP: %0.5f' % (position['stop_loss'], position['take_profit']))
            logger.info('💰 Unused capital: ${:0.2f}\t 💵 Allocated capital: ${:0.2f} | {} positions'.format(
                account.available, account.allocated, len(account.positions)
            ))

            log_to_json(account)

    # All potential positions have been opened so reset the array for the next round
    account.potential = []


def log_to_json(account, position=None):
    if position:
        # Parse opened positions file and add the last opened position
        with open('%s/closed.json' % account.strategy.name, 'r+') as fd:
            data = fd.read()
            closed = json.loads(data) + [position]
            fd.seek(0)
            fd.write(json.dumps(closed, indent=4) + '\n')
            fd.truncate()

        return

    # If no argument passed, dump all open positions
    with open('%s/opened.json' % account.strategy.name, 'w') as fd:
        fd.write(json.dumps(account.positions, indent=4) + '\n')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('[!] Need to provide a session name as argv, exiting...')
        sys.exit(1)

    session = sys.argv[1]

    # Create session directory and initialise files.
    Path('sessions/' + session).mkdir(parents=True, exist_ok=True)
    copyfile('strategies.json', 'sessions/{}/strategies.json'.format(session))
    os.chdir('sessions/' + session)

    with open('history.csv', 'w') as fd1, open('macro-trend.csv', 'w') as fd2:
        fd1.write('pair,price,RSI,timestamp\n')
        fd2.write('RSI,timestamp\n')

    # Setup logging. Use `debug()` for writing to STDOUT but NOT to logfile.
    logger.remove()
    logger.add('tracking.log', level="INFO",
        format="{time:MM-DD HH:mm:ss.SSS} | {message}"
    )
    logger.add(sys.stdout, colorize=True,
        format="<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>"
    )

    logger.info('Logging at: sessions/%s/' % session)

    logger.info('EXCHANGE: %s' % EXCHANGE)
    logger.info('INTERVAL: %s' % INTERVAL)
    
    logger.info('MACRO_RSI_MAX: %d' % MACRO_RSI_MAX)
    logger.info('MACRO_RSI_MIN: %d' % MACRO_RSI_MIN)

    try:
        main()
    except KeyboardInterrupt:
        logger.warning('Heard CTRL-C, quitting...')
