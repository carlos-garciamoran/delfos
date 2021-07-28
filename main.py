#!/usr/bin/env python3
import json
import math
import sys
from datetime import datetime
from os import chdir, listdir
from pathlib import Path
from shutil import copyfile

import ccxt
from loguru import logger

from models.Account import Account
from models.Position import Position
from models.Strategy import Strategy
from models.Trader import Trader
import utils.aggregator as aggregator
from utils.constants import INTERVAL

accounts, strategies, symbols = [], [], []
trader, exchange = None, None

emojis = {
    True:  '💎', False:  '❌',
    'buy': '🐃', 'sell': '🐻',
}


def main():
    """Setup the session strategies and run the main trading loop."""
    global macro_RSI, symbols
    global trader   # split because it's G

    logger.debug('🔌 Booting up ccxt...')
    trader = Trader()

    symbols = trader.symbols
    logger.info(f'🪙  Loaded {len(symbols)} symbols')

    setup_accounts_and_strategies()
    logger.info(f'💡 Loaded {len(strategies)} strategies')

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
                    trader.close_all_positions()

                # TODO: iterate through accounts, close positions and call account.log_closed_position()

                logger.info('Exited gracefully.')
                return


def setup_accounts_and_strategies():
    """Parse JSON strategies and set up an account and directory for new ones."""
    global exchange

    with open('strategies.json') as fd:
        data = json.loads(fd.read())

    for raw_strategy in data['strategies']:
        try:
            initial_account_size = raw_strategy['account_size'] \
                if 'account_size' in raw_strategy.keys() \
                else data['defaults']['account_size']

            account = Account(initial_account_size)
            strategy = Strategy(account, data['defaults'], raw_strategy)

            account.strategy = strategy
            account.free_trading_slots = math.floor(
                account.available * strategy.STOP_LOSS * strategy.RISK * 100
            )

            if strategy.REAL:
                exchange = trader.exchange
                trader.setup_real_account(account)

                strategy.exchange = exchange   # link the trader object to the strategy
        except KeyError as e:
            logger.critical(f'Required strategy parameter {e} missing, exiting...')
            sys.exit(1)

        # Create files for position tracking
        with open(strategy.name + '__closed.json', 'w') as fd1, \
            open(strategy.name + '__opened.json', 'w') as fd2:
            fd1.write('[]\n')
            fd2.write('[]\n')

        accounts.append(account)
        strategies.append(strategy)

        logger.info(strategy)
        logger.info(account)


def trade(pairs):
    """Close positions which need so, store interesting pairs, and open positions if possible."""
    logged_pairs = []

    for strategy in strategies:
        account = strategy.account

        opened_positions = {}
        for position in account.positions:
            opened_positions[position.symbol] = position

        logger.info(f'🔍 Checking {len(opened_positions)} positions for {strategy.name}...')

        # First, close all necessary positions for the given strategy
        for pair in pairs:
            if pair.symbol in opened_positions:
                position = opened_positions[pair.symbol]

                # HACK: move function to a Position method(?)
                needs_to_close, trigger = strategy.should_close(position, pair, macro_RSI)

                if needs_to_close:
                    close_position(position, pair, strategy, trigger)

                if pair.symbol not in logged_pairs:
                    with open('price-history.csv', 'a') as fd:
                        fd.write(f'{pair.symbol[:-5]},{pair.price},{pair.RSI},{datetime.now()}\n')

                    logged_pairs.append(pair.symbol)

            # Store pairs hitting price signal and calculate its tactic and strength
            if pair.is_interesting(macro_RSI, strategy):
                account.potential.append(pair)

        # Then, sort potential pairs so most extreme RSIs get priority (i.e. positions are opened first)
        account.potential.sort(key=lambda p: p.strength, reverse=True)

        logger.debug(f'🔎 Got {len(account.potential)} potential positions...')

        # Finally, open the interesting positions
        open_new_positions(strategy, opened_positions)

        # Dump open positions to opened.json
        account.log_open_positions()

        # All potential positions have been opened so reset the array for the next round
        account.potential = []


def close_position(position, pair, strategy, trigger):
    """Wrapper for closing positions."""
    account = strategy.account

    try:
        position.close(pair, strategy, trigger, macro_RSI)
    # NOTE: catch -2019 error (margin is insufficient)
    except ccxt.InsufficientFunds as e:
        # TODO: retrieve balance
        logger.critical('InsufficientFunds: failed closing ' \
            f'{position.side} {pair.symbol} with ${position.cost:.4f} ({e})'
        )
        balance = strategy.exchange.fetch_balance()['USDT']

        logger.warning(account)
        account.allocated, account.available = balance['used'], balance['free']
        logger.warning(account)

        return
    except ccxt.NetworkError as e:
        logger.error('NetworkError: failed closing ' \
            f'{position.side} {pair.symbol} with ${position.cost:.4f} ({e})'
        )

        # Try closing the position it again
        close_position(position, pair, strategy, trigger)

    account.log_closed_position(position)

    # Optimization happening here, baby ;)
    msg = ('\n'
        f'     🔮 Strategy: {strategy.name}\n'
        f'     🧭 Tactic: {position.entry_trigger}\n'
        f'     {emojis[position.net_pnl >= 0]} Closed {position.symbol} {position.side} at {position.exit_price}\n'
        f'     💸 P&L: {position.pnl:.2f}%, ${position.net_pnl:.4f}\n'
        f'     🧨 Fee: ${position.fee:.4f}\n'
        '     '
    )

    if trigger == 'trend-tactic':
        position.exit_trigger = 'trend-tactic'
        msg += '🎛 Trend signal hit\n'

        with open('macro-close.csv', 'a') as fd:
            fd.write(f'{str(position.__dict__)},{str(pair.__dict__)},{macro_RSI:.2f}\n')
    elif trigger == 'reversal-tactic':
        position.exit_trigger = 'reversal-tactic'
        msg += '📞 Reversal signal hit\n'
    elif trigger == 'macro-opposed':
        msg += '❌ Macro early-close\n'

        with open('macro-close.csv', 'a') as fd:
            fd.write(f'{str(position.__dict__)},{str(pair.__dict__)},{macro_RSI:.2f}\n')
    elif trigger == 'SL':
        position.exit_trigger = 'SL'
        msg += '⛔️ SL hit\n'
    elif trigger == 'TP':
        position.exit_trigger = 'TP'
        msg += '🤝 TP hit\n'
    elif trigger == 'timer':
        position.exit_trigger = 'timer'
        msg += '⏱ Timer hit\n'

    logger.warning(msg)

    # Percentage increase = (final_value - starting_value) / starting_value * 100
    percentage = (
        account.available + account.allocated - account.INITIAL_SIZE
        ) / account.INITIAL_SIZE * 100

    # No need to substract fees since P&L factored is already net
    total = account.available + account.allocated

    balance = strategy.exchange.fetch_balance()['USDT']

    logger.info('\n'
        f'     💸 Account P&L: {percentage:.2f}%, ${account.pnl:.4f}\n'
        f'     🤑 Wins: {account.wins}\t\t\t 🤔 Loses: {account.loses}\n'
        f'     💰 Available capital: ${account.available:.4f} ({balance["free"]})\n'
        f'     💵 Allocated capital: ${account.allocated:.4f} ({balance["used"]})\n'
        f'     💳 Total capital: ${total:.4f} ({balance["used"] + balance["free"]})\n'
    )


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

        # This check is needed in the edge case of `strategy.RISK > strategy.STOP_LOSS`
        if cost <= account.available and account.free_trading_slots >= 1:
            side = pair.determine_position_side(macro_RSI, strategy)

            # HACK: move code away from this function. Simply check macro_RSI before including
            #       pair in `account.potential` at `trade()`. NOTE: need to know `side` in advance
            if macro_RSI <= strategy.MACRO_RSI_MIN and side == 'buy':
                logger.info('⛔ Skipping false-flag (BUY in bearish market)')
                continue
            elif macro_RSI >= strategy.MACRO_RSI_MAX and side == 'sell':
                logger.info('⛔ Skipping false-flag (SELL in bullish market)')
                continue

            try:
                position = Position(pair, side, cost, strategy, macro_RSI)
            # NOTE: cath -2019 error (margin is insufficient)
            except ccxt.InsufficientFunds as e:
                logger.error(
                    f'InsufficientFunds: failed opening {side} {pair.symbol} with ${cost:.4f}'
                )

                logger.warning(account)
                logger.warning(strategy.exchange.fetch_balance()['USDT'])

                # TODO: create function for opening position and call it again here: recursion!
                # For insufficient margin, try opening the position with smaller cost (-10%).
                # position = Position(pair, side, cost - (cost*.1), strategy)
                continue
            # NOTE: catch -4003 error (quantity less than zero)
            # HACK: check `tentative_size <= exchange.markets['limits']['amount']['min']` before creating order
            except ccxt.ExchangeError as e:
                logger.error(
                    f'Failed opening {side} {pair.symbol} with ${cost:.4f} ({(cost / pair.price):.4f}): {e}'
                )

                continue
            except ccxt.NetworkError as e:
                logger.error(
                    f'NetworkError: failed opening {side} {pair.symbol} with ${cost:.4f} ({e})'
                )
                logger.error(account)

                continue

            account.log_new_position(position)

            # HACK: improve spacing: use :>x syntax
            msg += (f'\n{emojis[side]:>6} {pair.symbol} {side} at {position.entry_price} with ${position.cost:.4f}\n'
                f'     🚫 SL: {position.stop_loss:.4f}\t\t 🤝 TP: {position.take_profit:.4f}\n'
                f'     📈 RSI: {position.entry_RSI:.2f}\t\t 🎛  Macro-RSI: {position.entry_macro_RSI:.2f}\n'
                f'     🧭 Tactic: {position.entry_trigger}\n'
            )

    total = account.available + account.allocated
    balance = strategy.exchange.fetch_balance()['USDT']

    # Only log when msg has been appended some content
    if msg.endswith('\n'):
        logger.warning(msg + '\n'
            f'     💰 Available capital: ${account.available:.4f} ({balance["free"]})\n'
            f'     💵 Allocated capital: ${account.allocated:.4f} ({balance["used"]})\n'
            f'     💳 Total capital: ${total:.4f} ({balance["used"] + balance["free"]})\n'
        )


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

    with open('price-history.csv', 'w') as fd1, open('macro-history.csv', 'w') as fd2:
        fd1.write('symbol,price,RSI,timestamp\n')
        fd2.write('macro_RSI,timestamp\n')

    # Use `debug()` for writing to STDOUT but NOT to logfile.
    logger.remove()
    logger.add(f'{prefix}_tracking.log', level='INFO',
        format='{time:MM-DD HH:mm:ss.SSS} | {level} | {message}'
    )
    logger.add(sys.stdout, colorize=True, format=
        '<green>{time:MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>'
    )

    logger.info('Logging at: ' + full_path)
    logger.info(f'INTERVAL: {INTERVAL}')

    main()
