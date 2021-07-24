class Pair:
    def __init__(self, symbol, price, RSI):
        self.symbol = symbol
        self.price = price
        self.RSI = RSI

        self.tactic = ''  # 'trend', 'reversal'
        self.strength = 0.0

    def __str__(self):
        return self.symbol + '\n' \
            f'\tprice    = {self.price}\n' \
            f'\tRSI      = {self.RSI:.2f}\n' \
            f'\ttactic   = {self.tactic}\n' \
            f'\tstrength = {self.strength:.2f}\n'

    def is_interesting(self, macro_RSI, strategy):
        """Return if price signal has been hit. If True, store tactic and strength."""
        if macro_RSI >= strategy.MACRO_RSI_MAX and self.RSI < strategy.MACRO_RSI_MAX \
            or macro_RSI <= strategy.MACRO_RSI_MIN and self.RSI > strategy.MACRO_RSI_MIN:
            # NOTE: strength here is always >= 50 since the trend has priority
            self.tactic = 'trend'
            self.strength = abs(macro_RSI - self.RSI) + 50
            return True

        if self.RSI >= strategy.RSI_MAX or self.RSI <= strategy.RSI_MIN:
            self.tactic = 'reversal'
            self.strength = abs(50 - self.RSI)
            return True

        return False

    def determine_position_side(self, macro_RSI, strategy):
        """Return 'sell' if the asset should be shorted or 'buy' if it should be longed."""
        # In both cases, follow the trend if the RSI is extreme, else look for the reverse
        if self.RSI >= 50:
            return 'buy' if macro_RSI >= strategy.MACRO_RSI_MAX else 'sell'

        return 'sell' if macro_RSI <= strategy.MACRO_RSI_MIN else 'buy'
