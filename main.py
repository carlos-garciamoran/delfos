#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from os import chdir, listdir
from pathlib import Path
from shutil import copyfile

import ccxt
from loguru import logger

from models.Position import Position
from models.Strategy import Strategy
from models.Trader import Trader

import utils.aggregator as aggregator
from utils.constants import *

accounts, strategies, symbols = [], [], []
trader, exchange = None, None

macro_RSI = 0.0

emojis = {
    True:  '💎', False:  '❌',
    'buy': '🐃', 'sell': '🐻',
}


def main():
    """Setup the session strategies and run the main trading loop."""
    global macro_RSI, symbols
    global trader   # split because it's G

    trader = Trader()
    symbols = trader.symbols

    logger.info(f'Loaded {len(symbols)} symbols')

    setup_accounts_and_strategies()

    while True:
        try:
            logger.debug('📡 Aggregating market data...')

            # Catch openssl socket connection error
            try:
                pairs, macro_RSI, HTTP_error = aggregator.get_market_data(symbols)
            except OSError as e:
                logger.error('Crashed on market data request: ' + e)
                continue

            if HTTP_error:
                logger.critical(f'HTTP error {HTTP_error[0]} at /v1/klines endpoint; dumping and exiting...')
                logger.critical(HTTP_error[1])
                return

            logger.debug(f'🎛  Macro-RSI: {macro_RSI:.2f}')
            trade(pairs)
        except KeyboardInterrupt:
            logger.warning('Heard CTRL-C!')
            logger.warning('Quit now? All open positions will be CLOSED! (y/N) ', end='')
            answer = input()

            if answer == 'y' or answer == 'Y':
                if exchange is not None:
                    # NOTE: this function does not log the closed positions to closed.json
                    trader.close_all_positions()

                logger.info('Exited gracefully.')
                return


def setup_accounts_and_strategies():
    """Parse JSON strategies and set up an account and directory for new ones."""
    global exchange

    with open('strategies.json') as fd:
        data = json.loads(fd.read())

    for strategy_data in data['strategies']:
        try:
            strategy = Strategy(data['defaults'], strategy_data)
            account = strategy.account

            if strategy.real:
                exchange = trader.exchange
                trader.setup_real_account(account)

                strategy.exchange = exchange   # link the trader object to the strategy
        except KeyError as e:
            logger.error(f'Required strategy parameter {e} missing, skipping...')
            continue

        name = strategy.name

        # Create files for position tracking
        with open(name + '__closed.json', 'w') as fd1, \
            open(name + '__opened.json', 'w') as fd2:
            fd1.write('[]\n')
            fd2.write('[]\n')

        accounts.append(account)
        strategies.append(strategy)

        logger.info(strategy)
        logger.info(account)

    logger.info(f'Running {len(strategies)} strategies')


def trade(pairs):
    """Close positions which need so, store interesting pairs, and open positions if possible."""
    logged_pairs = []

    for strategy in strategies:
        account = strategy.account

        opened_positions = {}
        for position in account.positions:
            opened_positions[position.symbol] = position

        logger.debug(f'🔍 Checking {len(opened_positions)} positions for {strategy.name}...')

        # First, close all necessary positions for the given strategy
        for pair in pairs:
            if pair.symbol in opened_positions:
                position = opened_positions[pair.symbol]

                # HACK: move function to a Position method(?)
                close_if_needed(position, pair, strategy)

                # Log the pair of the open position if it has not been logged.
                if pair.symbol not in logged_pairs:
                    # HACK: move call after strategies loop is over
                    with open('price-history.csv', 'a') as fd:
                        fd.write(f'{pair.symbol[:-5]},{pair.price},{pair.RSI},{datetime.now()}\n')

                    logged_pairs.append(pair.symbol)

            # Store pairs hitting price signal
            if pair.is_interesting(strategy):
                # NOTE: strength calculated here to save useless function call
                pair.strength = abs(50 - pair.RSI)
                account.potential.append(pair)

        # Then, sort potential positions so most extreme RSIs get priority (i.e. positions are opened first)
        account.potential.sort(key=lambda p: p.strength, reverse=True)

        logger.debug(f'🔎 Got {len(account.potential)} potential positions...')

        # Finally, open the interesting positions
        open_new_positions(strategy, opened_positions)

        account.log_positions_to_json()  # Dump open positions to opened.json

        # All potential positions have been opened so reset the array for the next round
        account.potential = []


def close_if_needed(position, pair, strategy):
    """Given a pair, close its position if its SL, TP, or a price signal has been hit."""
    account = strategy.account

    needs_to_close, causes = strategy.should_close(position, pair, macro_RSI)

    if needs_to_close:
        # NOTE: cath -2019 error (margin is insufficient)
        try:
            position.close(pair, strategy, causes, macro_RSI)
        # TODO: determine what to do with this error
        except ccxt.InsufficientFunds as e:
            # TODO: retrieve balance
            logger.error('InsufficientFunds: failed closing ' \
                f'{position.side} {pair.symbol} with ${position.cost:.4f} ({e})'
            )
            logger.info(account)
            logger.info(strategy.exchange.fetch_balance()['USDT'])

            return
        # TODO: determine what to do with this error
        except ccxt.NetworkError as e:
            logger.error('NetworkError: failed closing ' \
                f'{position.side} {pair.symbol} with ${position.cost:.4f} ({e})'
            )
            logger.info(account)

            return

        # HACK: for real accounts, could use balance from fetch_balance()
        account.log_closed_order(position)

        # Optimization happening here, baby ;)
        msg = '\n' \
            f'     🔮 Strategy: {strategy.name}\n' \
            f'     {emojis[position.net_pnl >= 0]} Closed {position.symbol} {position.side} at {position.exit_price}\n' \
            f'     💸 P&L: {position.pnl:.2f}%, ${position.net_pnl:.4f}\n' \
            f'     🧨 Fee: ${position.fee:.4f}\n' \
            '     '

        if causes[0]:
            msg += '⛔️ SL hit\n'
        elif causes[1]:
            msg += '🤝 TP hit\n'
        elif causes[2]:
            msg += '🎛  Macro signal\n'

            # NOTE: is this data still useful?
            with open('macro-close.csv', 'a') as fd:
                fd.write(f'{str(position.__dict__)},{str(pair.__dict__)},{macro_RSI:.2f}\n')
        elif causes[3]:
            msg += '📞 Price signal hit\n'
        elif causes[4]:
            msg += '⏱ Timer hit\n'

        logger.warning(msg)

        # Percentage increase = (final_value - starting_value) / starting_value * 100
        percentage = (
            account.available + account.allocated - account.INITIAL_SIZE
            ) / account.INITIAL_SIZE * 100

        # No need to substract fees since P&L factored is already net
        total = account.available + account.allocated

        logger.info('\n'
            f'     💸 Total realized P&L: {percentage:.2f}%, ${account.pnl:.4f}\n'
            f'     🤑 Wins: {account.wins}\t\t 🤔 Loses: {account.loses}\n'
            f'     💰 Total account: ${total:.4f}\t 💵 Allocated capital: ${account.allocated:.4f}\n'
        )

        account.log_positions_to_json(position)


def open_new_positions(strategy, opened_positions):
    """Open positions based on RSI strength. Ensure no more than 1 position per symbol is opened."""
    account = strategy.account
    msg = '🔮 Opened positions for ' + strategy.name

    for pair in account.potential:
        # Do not open a new position if there's an existing position with the same symbol
        if pair.symbol in opened_positions:
            continue

        # HACK: for real accounts, calculate using free balance from Binance
        cost = strategy.determine_position_cost() / 10  # divide by 10 for testing purposes

        # This check is needed in the edge case of `strategy.risk > strategy.stop_loss`
        if cost <= account.available and account.free_trading_slots >= 1:
            # By this point there is a price signal due to pair.is_interesting()
            side = pair.determine_position_side(macro_RSI)

            # HACK: move code away from open_positions. Simply check macro_RSI before including
            #       pair in `account.potential` at `trade()`. Need to know `side` in advance
            if macro_RSI <= MACRO_RSI_MIN and side == 'buy':
                logger.debug('⛔ Skipping false-flag (BUY in bearish market)')
                continue
            elif macro_RSI >= MACRO_RSI_MAX and side == 'sell':
                logger.debug('⛔ Skipping false-flag (SELL in bullish market)')
                continue

            # TODO: improve this error handling logic
            try:
                position = Position(pair, side, cost, strategy, macro_RSI)
            # NOTE: cath -2019 error (margin is insufficient)
            except ccxt.InsufficientFunds as e:
                logger.error(
                    f'InsufficientFunds: failed opening {side} {pair.symbol} with ${cost:.4f}'
                )
                logger.info(account)

                # HACK: could retrieve free USDT from Binance to open position accordingly
                # For insufficient margin, try opening the position with smaller cost (-10%).
                # position = Position(pair, side, cost - (cost*.1), strategy)
                continue
            # NOTE: catch -4003 error (quantity less than zero)
            # HACK: instead of catching the error, before opening the order, check
            #       `tentative_size <= strategy.markets['limits']['amount']['min']` is True
            except ccxt.ExchangeError as e:
                logger.error(f'Caught {e}')
                logger.error(
                    f'Failed opening {side} {pair.symbol} with ${cost:.4f} ({cost / pair.price})'
                )

                continue
            # TODO: determine what to do with this error
            except ccxt.NetworkError as e:
                logger.error(
                    f'NetworkError: failed opening {side} {pair.symbol} with ${cost:.4f} ({e})'
                )
                logger.info(account)

                continue

            logger.info(position)
            account.log_new_order(position)

            msg += '\n' \
                f'{emojis[side]:>6} {pair.symbol} {side} at {position.entry_price} with ${position.cost:.4f}\n' \
                f'{"":>4} 🚫 SL: {position.stop_loss:.4f}\t\t 🤝 TP: {position.take_profit:.4f}\n'

    # Only log when msg has been appended some content
    if len(msg) > 55:
        msg += '\n' + \
            f'     💰 Available capital: ${account.available:.4f}\n' \
            f'     💵 Allocated capital: ${account.allocated:.4f}\n'
        logger.warning(msg)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('[!] Need to provide a session name as argv, exiting...')
        sys.exit(1)

    last_index = -1
    _id = sys.argv[1]
    prefix = f'{_id}_{datetime.now():%Y-%m-%d}'

    for session in listdir('sessions/'):
        if session.startswith(prefix):
            # Existing day-session found: get the last index and increment
            last_dash = session.find('_', len(_id) + 1)
            index = int(session[last_dash+1:])
            if index > last_index:
                last_index = index

    session = f'{prefix}_{last_index+1}'
    full_path = 'sessions/' + session

    # Create session directory and initialise files.
    Path(full_path).mkdir(parents=True, exist_ok=True)
    copyfile('strategies.json', full_path + '/strategies.json')
    chdir(full_path)

    with open('price-history.csv', 'w') as fd1, open('macro-trend.csv', 'w') as fd2:
        fd1.write('symbol,price,RSI,timestamp\n')
        fd2.write('RSI,timestamp\n')

    # Use `debug()` for writing to STDOUT but NOT to logfile.
    logger.remove()
    logger.add('tracking.log', level='INFO',
        format='{time:MM-DD HH:mm:ss.SSS} | {level} | {message}'
    )
    logger.add(sys.stdout, colorize=True, format=
        '<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>'
    )

    logger.info('Logging at: ' + full_path)
    logger.info(f'INTERVAL: {INTERVAL}')
    logger.info(f'MACRO_RSI_MAX: {MACRO_RSI_MAX}')
    logger.info(f'MACRO_RSI_MIN: {MACRO_RSI_MIN}')
    logger.info(f'TIMER_TRIGGER: {TIMER_TRIGGER}')

    main()
