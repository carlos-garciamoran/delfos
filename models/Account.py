import json
import math

import ccxt


class Account:
    def __init__(self, initial_size):
        self.INITIAL_SIZE = initial_size  # constant
        self.strategy = None  # Strategy object associated with the account

        self.allocated = 0.0  # capital allocated in positions (USDT)
        self.available = initial_size  # free capital + realized pnl - fees
        self.free_trading_slots = None

        # Arrays storing Position objects
        self.positions = []  # currently open positions
        self.potential = []  # positions to be opened

        self.fees = 0.0  # total trading fees incurred by the account
        self.pnl = 0.0   # total realized and recompounded net profit & loss in USDT
        self.loses = 0   # counter of unprofitable trades
        self.wins = 0    # counter of profitable trades

    def __eq__(self, other):
        return self.strategy == other.strategy \
            and self.allocated == other.allocated \
            and self.available == other.available \
            and self.positions == other.positions \
            and self.potential == other.potential \
            and self.fees == other.fees \
            and self.pnl == other.pnl \
            and self.loses == other.loses \
            and self.wins == other.wins

    def __str__(self):
        return self.strategy.name + '\n' \
            f'\tINITIAL_SIZE = {self.INITIAL_SIZE:4f}\n' \
            f'\tallocated    = {self.allocated:4f}\n' \
            f'\tavailable    = {self.available:4f}\n' \
            f'\tfree_slots   = {self.free_trading_slots}\n' \
            f'\tpositions    = {len(self.positions)}\n' \
            f'\tpotential    = {len(self.potential)}\n' \
            f'\tfees         = {self.fees:4f}\n' \
            f'\tpnl          = {self.pnl:4f}\n' \
            f'\twins, loses  = {self.wins}, {self.loses}\n'

    def fetch_real_balance(self):
        """Fetch account data from exchange."""
        try:
            balance = self.strategy.exchange.fetch_balance()['USDT']
            self.allocated = balance['used']
            self.available = balance['free']
        except ccxt.NetworkError:
            self.fetch_real_balance()   # If failed, try again until success

    def log_new_position(self, position):
        """Add the position to its array and update the appropriate counters."""
        self.positions.append(position)

        if self.strategy.REAL:
            self.fetch_real_balance()
        else:
            self.allocated += position.cost
            self.available -= position.cost - position.fee

        self.free_trading_slots = math.floor(
            self.available * self.strategy.STOP_LOSS * self.strategy.RISK * 100
        )

    def log_closed_position(self, position):
        """Remove the position from its array and update the appropriate counters."""
        self.positions.remove(position)

        # A win is only such if the position's net P&L is positive
        if position.net_pnl >= 0:
            self.wins += 1
        else:
            self.loses += 1

        if self.strategy.REAL:
            self.fetch_real_balance()
        else:
            self.allocated -= position.cost  # Adjust allocated capital
            self.available += position.cost + position.net_pnl  # Recompound magic, baby

        self.fees += position.fee
        self.pnl += position.net_pnl

        self.free_trading_slots = math.floor(
            self.available * self.strategy.STOP_LOSS * self.strategy.RISK * 100
        )

        # Append the last closed position to closed.json.
        with open(self.strategy.name + '__closed.json', 'r+') as fd:
            data = fd.read()
            closed = json.loads(data) + [position.__dict__]
            fd.seek(0)
            fd.write(json.dumps(closed, indent=4, default=str) + '\n')
            fd.truncate()

    def log_open_positions(self):
        """Dump open positions to opened.json."""
        raw_positions = []
        for pos in self.positions:
            raw_positions.append(pos.__dict__)

        with open(self.strategy.name + '__opened.json', 'w') as fd:
            fd.write(json.dumps(raw_positions, indent=4, default=str) + '\n')
