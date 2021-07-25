from datetime import datetime


class Strategy:
    def __init__(self, account, defaults, strategy):
        self.RSI_MIN = strategy['RSI'][0]
        self.RSI_MAX = strategy['RSI'][1]

        self.MACRO_RSI_MIN = strategy['macro_RSI'][0] \
            if 'macro_RSI' in strategy.keys() \
            else defaults['macro_RSI'][0]
        self.MACRO_RSI_MAX = strategy['macro_RSI'][1] \
            if 'macro_RSI' in strategy.keys() \
            else defaults['macro_RSI'][1]
        self.profit_close = strategy['profit_close'] \
            if 'profit_close' in strategy.keys() \
            else defaults['profit_close']
        self.real = strategy['REAL'] \
            if 'REAL' in strategy.keys() \
            else False
        self.risk = strategy['risk'] \
            if 'risk' in strategy.keys() \
            else defaults['risk']
        self.stop_loss = strategy['stop_loss'] \
            if 'stop_loss' in strategy.keys() \
            else defaults['stop_loss']
        self.take_profit = strategy['take_profit'] \
            if 'take_profit' in strategy.keys() \
            else defaults['take_profit']
        self.TIMER_TRIGGER = strategy['timer_trigger'] \
            if 'timer_trigger' in strategy.keys() \
            else defaults['timer_trigger']

        # TODO: think of a better alternative than a name (e.g. dump strategy attributes)
        self.name = f'{self.RSI_MIN}-{self.RSI_MAX}_SL-{(self.stop_loss*100):g}_TP-{(self.take_profit*100):g}' \
            f'_{self.TIMER_TRIGGER}'
        self.name += '_profit' if self.profit_close else ''

        if self.real:
            self.name += '_REAL'
        else:
            self.exchange = None

        self.account = account

    def __eq__(self, other):
        # NOTE: `self.account` is not compared on purpose
        return self.name == other.name \
            and self.RSI_MIN == other.RSI_MIN \
            and self.RSI_MAX == other.RSI_MAX \
            and self.MACRO_RSI_MIN == other.MACRO_RSI_MIN \
            and self.MACRO_RSI_MAX == other.MACRO_RSI_MAX \
            and self.profit_close == other.profit_close \
            and self.real == other.real \
            and self.risk == other.risk \
            and self.stop_loss == other.stop_loss \
            and self.take_profit == other.take_profit \
            and self.TIMER_TRIGGER == other.TIMER_TRIGGER \

    def __str__(self):
        return self.name + '\n' \
            f'\tRSI_MIN = {self.RSI_MIN}\n' \
            f'\tRSI_MAX = {self.RSI_MAX}\n' \
            f'\tMACRO_RSI_MIN = {self.MACRO_RSI_MIN}\n' \
            f'\tMACRO_RSI_MAX = {self.MACRO_RSI_MAX}\n' \
            f'\tprofit_close = {self.profit_close}\n' \
            f'\treal = {self.real}\n' \
            f'\trisk = {self.risk}\n' \
            f'\tstop_loss   = {self.stop_loss}\n' \
            f'\ttake_profit = {self.take_profit}\n' \
            f'\tTIMER_TRIGGER = {self.TIMER_TRIGGER}\n'

    def determine_position_cost(self):
        """Calculate the position size according to account and strategy parameters."""
        return (self.account.allocated + self.account.available) * self.risk / self.stop_loss

    def should_close(self, position, pair, macro_RSI):
        """Return if the position should be closed according to tactic, SL, TP, and position timer."""
        if position.side == 'buy':
            if position.entry_trigger == 'trend':
                price_signal_hit = True if macro_RSI < self.MACRO_RSI_MAX else False
            else:
                price_signal_hit = pair.RSI >= self.RSI_MAX

                # NOTE: consider using profit_close in both 'trend' and 'reversal'
                if self.profit_close and price_signal_hit:
                    price_signal_hit = pair.price >= position.entry_price

            stop_loss_hit = pair.price <= position.stop_loss
            take_profit_hit = pair.price >= position.take_profit
        else:
            if position.entry_trigger == 'trend':
                price_signal_hit = True if macro_RSI > self.MACRO_RSI_MIN else False
            else:
                price_signal_hit = pair.RSI <= self.RSI_MIN

                if self.profit_close and price_signal_hit:
                    price_signal_hit = pair.price <= position.entry_price

            stop_loss_hit = pair.price >= position.stop_loss
            take_profit_hit = pair.price <= position.take_profit

        # Calculate the position's duration in minutes
        position_duration = (datetime.now() - position.opened_at).seconds / 60
        timer_hit = True if position_duration >= self.TIMER_TRIGGER else False

        return (
            price_signal_hit or stop_loss_hit or take_profit_hit or timer_hit,
            [price_signal_hit, stop_loss_hit, take_profit_hit, timer_hit]
        )
