import json


class Account:
    def __init__(self, initial_size, strategy):
        self.strategy = strategy  # Strategy object associated with the account

        self.allocated = 0.0  # capital allocated in positions (USDT)
        self.available = initial_size  # liquid unused capital + pnl - fees

        # Arrays storing Position objects
        self.positions = []  # currently open positions
        self.potential = []  # positions to be opened

        self.fees = 0.0  # total trading fees incurred by the account
        self.pnl = 0.0   # total realized and recompounded profit & loss in USDT
        self.loses = 0   # counter of unprofitable trades
        self.wins = 0    # counter of profitable trades

    def __eq__(self, other):
        if not isinstance(other, Account):
            # Do not attempt to compare against unrelated types
            return NotImplemented

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
        return '''{}
    allocated = {}
    available = {}
    positions = {}
    potential = {}
    fees      = {}
    pnl       = {}
    wins, loses = {}, {}\n'''.format(
        self.strategy.name, self.allocated, self.available, len(self.positions), len(self.potential),
        self.fees, self.pnl, self.wins, self.loses
        )


    def log_new_order(self, position):
        """Add the position to its array and update the appropriate counters."""
        self.positions.append(position)

        self.allocated += position.size
        self.available -= position.size

    def log_closed_order(self, position):
        """Remove the position from its array and update the appropriate counters."""
        self.positions.remove(position)

        # A win is only such if the position's net P&L is positive
        if position.pnl[1] - position.fee >= 0:
            self.wins += 1
        else:
            self.loses += 1

        self.allocated -= position.size  # Adjust allocated capital
        self.available += position.size + position.pnl[1] - position.fee  # Recompound magic, baby

        self.fees += position.fee
        self.pnl += position.pnl[1]

    def log_positions_to_json(self, position=None):
        """Append the last closed position to closed.json or dump open positions to opened.json."""
        if position:
            with open('%s/closed.json' % self.strategy.name, 'r+') as fd:
                data = fd.read()
                closed = json.loads(data) + [position.__dict__]
                fd.seek(0)
                fd.write(json.dumps(closed, indent=4) + '\n')
                fd.truncate()

            return

        raw_positions = []
        for pos in self.positions:
            raw_positions.append(pos.__dict__)

        with open('%s/opened.json' % self.strategy.name, 'w') as fd:
            fd.write(json.dumps(raw_positions, indent=4) + '\n')
