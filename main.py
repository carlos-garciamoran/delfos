#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from loguru import logger

from models.Position import Position
from models.Strategy import Strategy

import utils.aggregator as aggregator
from utils.constants import *


accounts, strategies, symbols = [], [], []
macro_RSI = 0.0
real_loaded = False

emojis = {
    True:  '💎', False:  '❌',
    'buy': '🐃', 'sell': '🐻',
}


def main():
    global macro_RSI

    while True:
        setup_accounts_and_strategies()

        logger.debug('📡 Aggregating market data...')

        # Catch openssl socket connection errors
        try:
            pairs, macro_RSI, HTTP_error = aggregator.get_market_data(logger, symbols)
        except (KeyError, OSError) as e:
            logger.error('[!] Crashed on market data request, dumping error...')
            logger.error(e)
            continue

        if HTTP_error:
            logger.error('[!] Binance %s returned %d; exiting...' % (HTTP_error[0], HTTP_error[1]))
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

        trade(pairs)


def setup_accounts_and_strategies():
    """Parse JSON strategies and set up an account and directory for new ones."""
    global real_loaded, symbols

    with open('strategies.json') as fd:
        data = json.loads(fd.read())

    for strategy_data in data['strategies']:
        # HACK: fix this fucked up logic
        # Only try to create a real strategy if it has not been created before.
        if 'REAL' not in list(strategy_data) or not real_loaded:
            try:
                strategy = Strategy(data['defaults'], strategy_data)
                account = strategy.account

                if strategy.real:
                    symbols = list(strategy.markets)
                    real_loaded = True
            except KeyError as e:
                logger.error('[!] Error parsing %s' % strategy_data['name'])
                logger.error('[!] Need to add strategy parameter %s, skipping...' % e)
                continue

        # Skip already existing and real strategies so they are not reset
        if strategy in strategies:
            continue

        name = strategy.name

        Path(name).mkdir(exist_ok=True)  # Each strategy gets its own directory

        # Create JSON files for tracking positions
        with open('%s/closed.json' % name, 'w') as fd1, \
            open('%s/opened.json' % name, 'w') as fd2:
            fd1.write('[]\n')
            fd2.write('[]\n')

        # NOTE: `available` is not set by strategy, it only uses the default
        accounts.append(account)
        strategies.append(strategy)

        logger.info(strategy)
        logger.info('Running %d strategies' % len(strategies))


def trade(pairs):
    """Close positions which need so, store interesting pairs, and open positions if possible."""
    logged_pairs = []

    for strategy in strategies:
        account = strategy.account

        opened_positions = {}
        for position in account.positions:
            opened_positions[position.symbol] = position

        logger.debug('🔍 Closing positions for %s...' % strategy.name)
        # First, close all necessary positions for the given strategy
        for pair in pairs:
            if pair.symbol in opened_positions:
                position = opened_positions[pair.symbol]

                # HACK: could move function to a Position method
                close_if_needed(position, pair, strategy)

                # Log the pair of the open position if it has not been logged.
                if pair.symbol not in logged_pairs:
                    # IDEA: move call after strategies loop is over
                    with open('history.csv', 'a') as fd:
                        fd.write('%s,%f,%f,%s\n' % (pair.symbol, pair.price, pair.RSI, datetime.now()))

                    logged_pairs.append(pair.symbol)

            # Store pairs hitting price signal
            if pair.is_interesting(strategy):
                pair.compute_strength()
                account.potential.append(pair)

        # Then, sort potential positions so most extreme RSIs get priority (i.e. positions are opened first)
        account.potential.sort(key=lambda p: p.strength, reverse=True)

        logger.debug('🔎 Trying to open %d potential positions...' % len(account.potential))

        # Finally, open the interesting positions
        open_new_positions(strategy, opened_positions)

        account.log_positions_to_json()  # Dump open positions to opened.json

        # All potential positions have been opened so reset the array for the next round
        account.potential = []


def close_if_needed(position, pair, strategy):
    """Given a pair, close its position if its SL, TP, or a price signal has been hit."""
    account, price = strategy.account, pair.price

    # NOTE: causes returned for testing purposes
    needs_to_close, causes = strategy.should_close(position, pair, macro_RSI)

    if needs_to_close:
        position.close(price, strategy)

        # HACK: for real accounts, could use balance from fetch_balance()
        account.log_closed_order(position)

        # Optimization happening here, baby ;)
        msg = '\n{:>4} 🔮 Strategy: {}\n' \
            '{:>6} Closed {} {} at {}\n' \
            '{:>4} 💸 P&L: {:0.2f}%, ${:0.2f}\n' \
            '{:>4} 🧨 Fee = ${:0.2f}\n'.format(
                '', strategy.name,
                emojis[position.pnl[0] >= 0], position.symbol, position.side, position.exit_price,
                '', position.pnl[0], position.pnl[1],
                '', position.fee
            )

        if causes[0]:
            msg += '{:>5}🎛  Macro signal\n'.format('')
        elif causes[1]:
            msg += '{:>5}⛔️ SL hit\n'.format('')
        elif causes[2]:
            msg += '{:>5}🤝 TP hit\n'.format('')
        elif causes[3]:
            msg += '{:>5}📞 Price signal hit\n'.format('')

        logger.warning(msg)

        # Percentage increase = (final_value - starting_value) / starting_value * 100
        percentage = \
            (account.available + account.allocated - strategy.account_size) \
            / strategy.account_size * 100

        logger.info(
            '\n{:>4} 💸 Total realized P&L: {:0.2f}%, ${:0.2f}\n'
            '{:>4} 🤑 Wins: {}\t\t 🤔 Loses: {}\n'
            '{:>4} 💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}\n'.format(
                '', percentage, account.pnl,
                '', account.wins, account.loses,
                '', account.available + account.allocated - account.fees, account.allocated
            )
        )

        account.log_positions_to_json(position)


def open_new_positions(strategy, opened_positions):
    """Open positions based on RSI strength. Ensure no more than 1 position per symbol is opened."""
    account = strategy.account
    msg = '🔮 Opened positions for %s:' % strategy.name

    for pair in account.potential:
        # Do not open a new position if there's an existing position with the same symbol
        if pair.symbol in opened_positions:
            continue

        size = strategy.determine_position_size(account.allocated, account.available)

        # This check is needed in the edge case of `strategy.account_risk > strategy.stop_loss`
        if size <= account.available:
            # By this point there is a price signal due to pair.is_interesting()
            side = pair.determine_position_side(macro_RSI)

            # HACK: move code away from open_positions. Simply check macro_RSI before including
            #       pair in `account.potential` at `trade()`
            if macro_RSI <= MACRO_RSI_MIN and side == 'buy':
                logger.debug('⛔ Skipping false-flag (BUY in bearish market)')
                continue
            elif macro_RSI >= MACRO_RSI_MAX and side == 'sell':
                logger.debug('⛔ Skipping false-flag (SELL in bullish market)')
                continue

            position = Position(pair, side, size, strategy)
            account.log_new_order(position)

            msg += '\n{:>6} {} {} at {} with ${:0.2f}\n' \
                '{:>4} 🚫 SL: {:0.5f}\t\t 🤝 TP: {:0.5f}\n'.format(
                emojis[side], pair.symbol, side, position.entry_price, position.size,
                '', position.stop_loss, position.take_profit,
            )

    # Only log when msg has been appended some content
    if len(msg) > 55:
        msg += '\n{:>4} 💰 Total account: ${:0.2f}\t 💵 Allocated capital: ${:0.2f}\n'.format(
            '', account.available + account.allocated - account.fees, account.allocated
        )
        logger.warning(msg)


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
