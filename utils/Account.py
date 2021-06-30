class Account:
    def __init__(self, initial_size, strategy):
        self.strategy = strategy  # Strategy object associated with the account

        self.allocated = 0.0  # capital allocated in positions in USDT
        self.available = initial_size  # liquid unused capital + (realized) pnl

        self.positions = []  # currently open positions
        self.potential = []  # positions to be opened: [symbol, price, RSI, strength]

        self.pnl = 0.0  # total realized and recompounded profit & loss in USDT
        self.loses = 0  # counter of unprofitable trades
        self.wins = 0   # counter of profitable trades

    def __eq__(self, other):
        if not isinstance(other, Account):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        return self.strategy == other.strategy \
            and self.allocated == other.allocated \
            and self.available == other.available \
            and self.positions == other.positions \
            and self.potential == other.potential \
            and self.pnl == other.pnl \
            and self.loses == other.loses \
            and self.wins == other.wins

    def __str__(self):
        return '''{}
    allocated = {} 
    available = {}
    positions = {}
    potential = {}
    pnl       = {}
    loses     = {}
    wins      = {}\n'''.format(
        self.strategy.name, self.allocated, self.available, self.positions, len(self.potential),
        self.pnl, self.loses, self.wins
        )


    def log_new_order(self, position):
        """Add the position to its array and setup the appropriate counters."""
        self.positions.append(position)

        self.allocated += position['size']
        self.available -= position['size']

    def log_closed_order(self, position):
        """Remove the position from its array and setup the appropriate counters."""
        self.positions.remove(position)

        if position['pnl'][0] >= 0:
            self.wins += 1
        else:
            self.loses += 1
        
        self.allocated -= position['size']  # Adjust allocated capital
        self.available += position['size'] + position['pnl'][1]  # Recompound magic, baby

        self.pnl += position['pnl'][1]  # Update net P&L in USDT
