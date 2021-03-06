from datetime import datetime


class Strategy:
    def __init__(self, account, defaults, strategy):
        parameters = strategy.keys()

        self.MODE = strategy['mode'] \
            if 'mode' in parameters \
            else defaults['mode']

        self.OPEN_RSI_MIN, self.OPEN_RSI_MAX = strategy['open_RSIs'] \
            if 'open_RSIs' in parameters \
            else defaults['open_RSIs']
        self.CLOSE_RSI_MAX, self.CLOSE_RSI_MIN = strategy['close_RSIs'] \
            if 'close_RSIs' in parameters \
            else defaults['close_RSIs']

        self.MACRO_RSI = strategy['macro_RSI'] \
            if 'macro_RSI' in parameters \
            else defaults['macro_RSI']
        self.MACRO_RSI_MIN, self.MACRO_RSI_MAX = strategy['macro_RSIs'] \
            if 'macro_RSIs' in parameters \
            else defaults['macro_RSIs']

        self.PROFIT_CLOSE = strategy['profit_close'] \
            if 'profit_close' in parameters \
            else defaults['profit_close']
        self.REAL = strategy['REAL'] \
            if 'REAL' in parameters \
            else False
        self.RISK = strategy['risk'] \
            if 'risk' in parameters \
            else defaults['risk']
        self.STOP_LOSS = strategy['stop_loss'] \
            if 'stop_loss' in parameters \
            else defaults['stop_loss']
        self.TAKE_PROFIT = strategy['take_profit'] \
            if 'take_profit' in parameters \
            else defaults['take_profit']
        self.TIMER_TRIGGER = strategy['timer_trigger'] \
            if 'timer_trigger' in parameters \
            else defaults['timer_trigger']

        # TODO: think of a better alternative than a name (e.g. dump strategy attributes)
        self.name = f'{self.MODE}_{self.OPEN_RSI_MIN}-{self.OPEN_RSI_MAX}_' \
            f'{self.CLOSE_RSI_MIN}-{self.CLOSE_RSI_MAX}_' \
            f'SL-{(self.STOP_LOSS*100):g}_TP-{(self.TAKE_PROFIT*100):g}' \
            f'_{self.TIMER_TRIGGER}'
        self.name += '_profit' if self.PROFIT_CLOSE else ''

        if self.REAL:
            self.name += '_REAL'
        else:
            self.exchange = None

        self.account = account

    def __eq__(self, other):
        # NOTE: `self.account` is not compared on purpose
        return self.MODE == other.MODE \
            and self.OPEN_RSI_MIN == other.OPEN_RSI_MIN \
            and self.OPEN_RSI_MAX == other.OPEN_RSI_MAX \
            and self.CLOSE_RSI_MIN == other.CLOSE_RSI_MIN \
            and self.CLOSE_RSI_MAX == other.CLOSE_RSI_MAX \
            and self.MACRO_RSI == other.MACRO_RSI \
            and self.MACRO_RSI_MIN == other.MACRO_RSI_MIN \
            and self.MACRO_RSI_MAX == other.MACRO_RSI_MAX \
            and self.PROFIT_CLOSE == other.PROFIT_CLOSE \
            and self.REAL == other.REAL \
            and self.RISK == other.RISK \
            and self.STOP_LOSS == other.STOP_LOSS \
            and self.TAKE_PROFIT == other.TAKE_PROFIT \
            and self.TIMER_TRIGGER == other.TIMER_TRIGGER

    def __str__(self):
        return self.name + '\n' \
            f'\tMODE          = {self.MODE}\n' \
            f'\tOPEN_RSI_MIN  = {self.OPEN_RSI_MIN}\n' \
            f'\tOPEN_RSI_MAX  = {self.OPEN_RSI_MAX}\n' \
            f'\tCLOSE_RSI_MIN = {self.CLOSE_RSI_MIN}\n' \
            f'\tCLOSE_RSI_MAX = {self.CLOSE_RSI_MAX}\n' \
            f'\tMACRO_RSI     = {self.MACRO_RSI}\n' \
            f'\tMACRO_RSI_MIN = {self.MACRO_RSI_MIN}\n' \
            f'\tMACRO_RSI_MAX = {self.MACRO_RSI_MAX}\n' \
            f'\tPROFIT_CLOSE  = {self.PROFIT_CLOSE}\n' \
            f'\tREAL          = {self.REAL}\n' \
            f'\tRISK          = {self.RISK*100:g}%\n' \
            f'\tSTOP_LOSS     = {self.STOP_LOSS*100:g}%\n' \
            f'\tTAKE_PROFIT   = {self.TAKE_PROFIT*100:g}%\n' \
            f'\tTIMER_TRIGGER = {self.TIMER_TRIGGER}\n'

    def determine_position_cost(self):
        """Calculate the position size according to account and strategy parameters."""
        # HACK: for real accounts, calculate using free balance from Binance
        return (self.account.allocated + self.account.available) * self.RISK / self.STOP_LOSS

    def should_close(self, position, pair, macro_RSI):
        """Return if the position should be closed according to tactic, SL, TP, and position timer."""
        if position.side == 'buy':
            # NOTE: may want to exit with more margin (e.g. self.MACRO_RSI_MAX - 10)
            if position.entry_trigger == 'trend' and macro_RSI < self.MACRO_RSI_MAX:
                return True, 'trend-tactic'
            else:
                # Reversal has failed (BUY in bearish market)
                if macro_RSI <= self.MACRO_RSI_MIN:
                    return True, 'macro-opposed'

                # Reversal has completed
                if pair.RSI >= self.CLOSE_RSI_MAX:
                    # NOTE: consider using PROFIT_CLOSE in both 'trend' and 'reversal'
                    if not self.PROFIT_CLOSE or (self.PROFIT_CLOSE and pair.price >= position.entry_price):
                        return True, 'reversal-tactic'

            if pair.price <= position.stop_loss:
                return True, 'SL'

            if pair.price >= position.take_profit:
                return True, 'TP'
        else:
            if position.entry_trigger == 'trend' and macro_RSI > self.MACRO_RSI_MIN:
                return True, 'trend-tactic'
            else:
                # Reversal has failed (SELL in bullish market)
                if macro_RSI >= self.MACRO_RSI_MAX:
                    return True, 'macro-opposed'

                # Reversal has completed
                if pair.RSI <= self.CLOSE_RSI_MIN:
                    if not self.PROFIT_CLOSE or (self.PROFIT_CLOSE and pair.price <= position.entry_price):
                        return True, 'reversal-tactic'

            if pair.price >= position.stop_loss:
                return True, 'SL'

            if pair.price <= position.take_profit:
                return True, 'TP'

        # Calculate the position's duration in minutes
        position_duration = (datetime.now() - position.opened_at).seconds / 60
        if position_duration >= self.TIMER_TRIGGER:
            return True, 'timer'

        return False, None
