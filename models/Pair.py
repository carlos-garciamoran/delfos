class Pair:
    def __init__(self, symbol, price, RSI):
        self.symbol = symbol
        self.price = price
        self.RSI = RSI

        self.side = ''  # 'buy', 'sell'
        self.tactic = ''  # 'trend', 'reversal'
        self.strength = 0.0

    def __str__(self):
        return self.symbol + '\n' \
            f'\tprice    = {self.price}\n' \
            f'\tRSI      = {self.RSI:.2f}\n' \
            f'\ttactic   = {self.tactic}\n' \
            f'\tstrength = {self.strength:.2f}\n'

    def is_interesting(self, macro_RSI, strategy):
        """Return if price signal has been hit. If True, set side, tactic, and strength."""
        # Bet for the asset's trend
        if strategy.MACRO_RSI:
            if macro_RSI >= strategy.MACRO_RSI_MAX and self.RSI < strategy.MACRO_RSI_MAX and \
                strategy.MODE != 'bearish':
                # Bet for the bullish trend in a non-overbought asset
                self.side = 'buy'
                self.tactic = 'trend'
                self.strength = abs(macro_RSI - self.RSI) + 50  # NOTE: set to >= 50 to give the trend priority

                return True

            if macro_RSI <= strategy.MACRO_RSI_MIN and self.RSI > strategy.MACRO_RSI_MIN and \
                strategy.MODE != 'bullish':
                # Bet for the bearish trend in a non-oversold asset
                self.side = 'sell'
                self.tactic = 'trend'
                self.strength = abs(macro_RSI - self.RSI) + 50

                return True

        # Bet for the asset's bearish reversal when overbought
        if self.RSI >= strategy.OPEN_RSI_MAX and strategy.MODE != 'bullish':
            self.side = 'sell'
            self.tactic = 'reversal'
            self.strength = abs(50 - self.RSI)

            return True

        # Bet for the asset's bullish reversal when oversold
        if self.RSI <= strategy.OPEN_RSI_MIN and strategy.MODE != 'bearish':
            self.side = 'buy'
            self.tactic = 'reversal'
            self.strength = abs(50 - self.RSI)

            return True

        return False
