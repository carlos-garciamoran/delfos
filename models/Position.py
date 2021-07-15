from datetime import datetime


class Position:
    def __init__(self, pair, side, cost, strategy):
        self.symbol = pair.symbol  # symbol name
        self.side = side           # 'buy', 'sell'

        if strategy.real:
            tentative_size = cost / pair.price  # base currency (COIN)
            order = strategy.trader.create_order(
                pair.symbol, 'MARKET', side, tentative_size
            )

            self.opened_at = datetime.now()
            self.entry_price = order['price']  # quote currency (USDT)
            self.cost = order['cost']    # quote currency (USDT)
            self.size = order['filled']  # base currency (COIN)

            self.set_SL_and_TP(strategy)  # NOTE: called here due to dependence on self.entry_price
            inverted_side = 'sell' if side == 'buy' else 'buy'

            # Create orders with the returned base size
            sl_order = strategy.trader.create_order(
                self.symbol, 'STOP_MARKET', inverted_side, self.size, None, {'stopPrice': self.stop_loss}
            )
            self.sl_id = sl_order['id']
            self.stop_loss = sl_order['stopPrice']

            tp_order = strategy.trader.create_order(
                self.symbol, 'TAKE_PROFIT_MARKET', inverted_side, self.size, None, {'stopPrice': self.take_profit}
            )
            self.tp_id = tp_order['id']
            self.take_profit = tp_order['stopPrice']
        else:
            self.opened_at = datetime.now()
            self.entry_price = pair.price
            self.cost = cost
            self.size = cost / pair.price

            self.set_SL_and_TP(strategy)
            self.sl_id, self.tp_id = None, None

        self.fee = self.cost * 0.00036  # opening taker fee in USDT
        self.exit_price = None
        self.closed_at = None

        self.pnl = [None, None]  # [percentage, USDT]

    def __str__(self):
        return '''{} {}
    cost        = {}
    size        = {}
    opened_at   = {}
    entry_price = {} 
    stop_loss   = {}
    take_profit = {}
    exit_price  = {}
    closed_at   = {}
    fee         = {}
    pnl         = {}\n'''.format(self.symbol, self.side,
        self.cost, self.size, self.opened_at, self.entry_price, self.stop_loss, self.take_profit,
        self.exit_price, self.closed_at, self.fee, self.pnl
        )


    def set_SL_and_TP(self, strategy):
        """Calculates and sets stop loss and take profit prices."""
        if self.side == 'buy':
            self.stop_loss = self.entry_price - (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price + (self.entry_price * strategy.take_profit)
        else:
            self.stop_loss = self.entry_price + (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price - (self.entry_price * strategy.take_profit)

    def close(self, exit_price, strategy, causes):
        """Mark the position as closed at the given exit_price and calculate P&L and fees."""
        if strategy.real:
            # Close all symbol orders (i.e. TP & SL) with a single call (weight = 1)
            strategy.trader.fapiPrivate_delete_allopenorders({
                'symbol': self.symbol.replace('/', '')
            })

            # Order may have already been closed by exchange due to TP or SL being hit
            if not (causes[0] or causes[1]):
                # Neither SL or TP have been hit, then create a market order for closing the position
                inverted_side = 'sell' if self.side == 'buy' else 'buy'

                # Close the order manually (weight = 1)
                order = strategy.trader.create_order(
                    self.symbol, 'MARKET', inverted_side, self.size
                )
            else:
                # NOTE: this assumes order['status'] == 'FILLED'
                # Retrieve closing price from SL or TP to log exit price precisely (weight = 1)
                order = strategy.trader.fetch_order(
                    self.sl_id if causes[0] else self.tp_id,
                    self.symbol
                )

            self.exit_price = order['price']
            self.fee += order['cost'] * 0.00036
        else:
            self.exit_price = exit_price

        self.closed_at = datetime.now()

        if self.side == 'buy':
            self.pnl[0] = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl[0] = (self.entry_price - self.exit_price) / self.exit_price

        self.pnl[1] = self.cost * self.pnl[0]  # P&L in USDT
        self.pnl[0] *= 100                     # P&L in percentage

        # HACK: create a function for calculating P&L + call it inside both if and else
        # Ugly & wet but needed; P&L needs to be calculated after the exit price
        if not strategy.real:
            self.fee += (self.cost + self.pnl[1]) * 0.00036
