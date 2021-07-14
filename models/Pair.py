from utils.constants import *


class Pair:
    def __init__(self, symbol, price, RSI):
        self.symbol = symbol
        self.price = price
        self.RSI = RSI

        self.strength = 0.0   # strength of the RSI

    def __str__(self):
        return '''{}
    price    = {}
    RSI      = {}
    strength = {}\n'''.format(self.symbol, self.price, self.RSI, self.strength)


    def is_interesting(self, strategy):
        """Return True if the RSI is overbought or oversold, according to the strategy."""
        return self.RSI >= strategy.max or self.RSI <= strategy.min

    def compute_strength(self):
        """Calculate the strength of the pair's indicator."""
        self.strength = abs(50 - self.RSI)

    def determine_position_side(self, macro_RSI):
        """Return 'sell' if the asset should be shorted or 'buy' if it should be longed."""
        # In both cases, follow the trend if the RSI is extreme, else look for the reverse
        if self.RSI >= 50:
            return 'buy' if macro_RSI >= MACRO_RSI_MAX else 'sell'

        return 'sell' if macro_RSI <= MACRO_RSI_MIN else 'buy'
