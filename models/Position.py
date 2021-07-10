from datetime import datetime


class Position:
    def __init__(self, pair, side, size, strategy):
        self.symbol = pair.symbol  # symbol name
        self.side = side           # 'buy', 'sell'

        if strategy.real:
            base_size = size / pair.price  # float in base currency

            order = strategy.trader.create_order(pair.symbol, 'MARKET', side, base_size)
            self.opened_at = datetime.now().isoformat()
            self.entry_price = order['price']  # float in quote currency (USDT)
            self.size = order['cost']  # float in quote currency (USDT)

            self.set_SL_and_TP(strategy)  # NOTE: called here due to dependence on self.entry_price
            inverted_side = 'sell' if side == 'buy' else 'buy'

            # TODO: create SL & TP orders together with market order overriding unified API params
            self.sl_id = strategy.trader.create_order(
                self.symbol, 'STOP_MARKET', inverted_side, base_size, None, {'stopPrice': self.stop_loss}
            )['id']
            self.tp_id = strategy.trader.create_order(
                self.symbol, 'TAKE_PROFIT_MARKET', inverted_side, base_size, None, {'stopPrice': self.take_profit}
            )['id']
        else:
            self.size = size  # float in quote currency (USDT)
            self.opened_at = datetime.now().isoformat()
            self.entry_price = pair.price   # float price in quote currency

            self.set_SL_and_TP(strategy)

        self.fee = self.size * 0.00036  # opening taker fee in USDT
        self.exit_price = None
        self.closed_at = None

        self.pnl = [None, None]  # [percentage, USDT]

    def __eq__(self, other):
        if not isinstance(other, Position):
            # Do not attempt to compare against unrelated types
            return NotImplemented

        # Only check the necessary attributes
        return self.symbol == other.symbol \
            and self.entry_price == other.entry_price \
            and self.size == other.size \
            and self.opened_at == other.opened_at

    def __str__(self):
        return '''{}
    side = {}
    size = {}
    entry_price = {} 
    opened_at = {}
    exit_price = {}
    closed_at = {}
    fee = {}
    pnl = {}
    stop_loss = {}
    take_profit = {}\n'''.format(
        self.symbol, self.side, self.size, self.entry_price, self.opened_at,
        self.exit_price, self.closed_at, self.fee, self.pnl, self.stop_loss, self.take_profit
        )


    def set_SL_and_TP(self, strategy):
        """Calculates and sets stop loss and take profit prices."""
        if self.side == 'buy':
            self.stop_loss = self.entry_price - (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price + (self.entry_price * strategy.take_profit)
        else:
            self.stop_loss = self.entry_price + (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price - (self.entry_price * strategy.take_profit)

    def close(self, exit_price, strategy):
        """Mark the position as closed at the given exit_price and calculate P&L and fees."""
        if strategy.real:
            inverted_side = 'sell' if self.side == 'buy' else 'buy'
            size = self.size / self.entry_price

            order = strategy.trader.create_order(self.symbol, 'MARKET', inverted_side, size)
            self.exit_price = order['price']
            self.fee += (order['cost'] * 0.00036)
            print(order)

            # NOTE: SL & TP orders are separate from the main one so they need to be manually cancelled
            strategy.trader.cancel_order(self.sl_id, self.symbol)
            strategy.trader.cancel_order(self.tp_id, self.symbol)
        else:
            self.exit_price = exit_price

        self.closed_at = datetime.now().isoformat()

        if self.side == 'buy':
            self.pnl[0] = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl[0] = (self.entry_price - self.exit_price) / self.exit_price

        # HACK: could probably optimise by doing
        #       self.pnl[1] = self.size * self.pnl[0]
        #       self.pnl[0] *= 100
        self.pnl[0] *= 100
        self.pnl[1] = self.size * self.pnl[0] / 100

        # Ugly & wet but needed; P&L needs to be calculated after the exit price
        if not strategy.real:
            self.fee += (self.size + self.pnl[1]) * 0.00036
