from utils.constants import MACRO_RSI_MAX, MACRO_RSI_MIN


class Pair:
    def __init__(self, symbol, price, RSI):
        self.symbol = symbol
        self.price = price
        self.RSI = RSI
        self.strength = 0.0  # strength of the RSI

    def __str__(self):
        return self.symbol + '\n' \
            f'\tprice    = {self.price}\n' \
            f'\tRSI      = {self.RSI}\n' \
            f'\tstrength = {self.strength}\n'


    def is_interesting(self, strategy):
        """Return True if the RSI is overbought or oversold, according to the strategy."""
        return self.RSI >= strategy.max or self.RSI <= strategy.min

    def determine_position_side(self, macro_RSI):
        """Return 'sell' if the asset should be shorted or 'buy' if it should be longed."""
        # In both cases, follow the trend if the RSI is extreme, else look for the reverse
        if self.RSI >= 50:
            return 'buy' if macro_RSI >= MACRO_RSI_MAX else 'sell'

        return 'sell' if macro_RSI <= MACRO_RSI_MIN else 'buy'
