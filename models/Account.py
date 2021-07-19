import json
import math


class Account:
    def __init__(self, strategy, initial_size):
        self.INITIAL_SIZE = initial_size  # constant variable
        self.strategy = strategy  # Strategy object associated with the account

        self.allocated = 0.0  # capital allocated in positions (USDT)
        self.available = initial_size  # free capital + realized pnl - fees
        self.free_trading_slots = math.floor(
            self.available * strategy.stop_loss * strategy.risk * 100
        )

        # Arrays storing Position objects
        self.positions = []  # currently open positions
        self.potential = []  # positions to be opened

        self.fees = 0.0  # total trading fees incurred by the account
        self.pnl = 0.0   # total realized and recompounded profit & loss in USDT
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
                f'\tallocated    = {self.allocated:4f}\n' \
                f'\tavailable    = {self.available:4f}\n' \
                f'\tfree_slots   = {self.free_trading_slots}\n' \
                f'\tinitial_size = {self.INITIAL_SIZE:4f}\n' \
                f'\tpositions    = {len(self.positions)}\n' \
                f'\tpotential    = {len(self.potential)}\n' \
                f'\tfees         = {self.fees:4f}\n' \
                f'\tpnl          = {self.pnl:4f}\n' \
                f'\twins, loses  = {self.wins}, {self.loses}\n'

    def log_new_order(self, position):
        """Add the position to its array and update the appropriate counters."""
        self.positions.append(position)

        self.allocated += position.cost
        self.available -= position.cost

        self.free_trading_slots = math.floor(
            self.available * self.strategy.stop_loss * self.strategy.risk * 100
        )

    def log_closed_order(self, position):
        """Remove the position from its array and update the appropriate counters."""
        self.positions.remove(position)

        # A win is only such if the position's net P&L is positive
        if position.net_pnl >= 0:
            self.wins += 1
        else:
            self.loses += 1

        self.allocated -= position.cost  # Adjust allocated capital
        self.available += position.cost + position.net_pnl - position.fee  # Recompound magic, baby

        self.fees += position.fee
        self.pnl += position.net_pnl

        self.free_trading_slots = math.floor(
            self.available * self.strategy.stop_loss * self.strategy.risk * 100
        )

    def log_positions_to_json(self, position=None):
        """Append the last closed position to closed.json or dump open positions to opened.json."""
        if position:
            with open(self.strategy.name + '__closed.json', 'r+') as fd:
                data = fd.read()
                closed = json.loads(data) + [position.__dict__]
                fd.seek(0)
                fd.write(json.dumps(closed, indent=4, default=str) + '\n')
                fd.truncate()

            return

        raw_positions = []
        for pos in self.positions:
            raw_positions.append(pos.__dict__)

        with open(self.strategy.name + '__opened.json', 'w') as fd:
            fd.write(json.dumps(raw_positions, indent=4, default=str) + '\n')
