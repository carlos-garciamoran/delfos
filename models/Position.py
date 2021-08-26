from datetime import datetime

from loguru import logger


class Position:
    def __init__(self, pair, cost, strategy, macro_RSI):
        self.symbol = pair.symbol  # symbol name
        self.side = pair.side      # 'buy', 'sell'

        self.entry_macro_RSI = macro_RSI  # for post-analysis purposes
        self.entry_RSI = pair.RSI         # for post-analysis purposes
        self.entry_trigger = pair.tactic  # 'trend', 'reversal'

        if strategy.REAL:
            self.create_orders(pair, cost, strategy)
        else:
            self.opened_at = datetime.now()
            self.entry_price = pair.price
            self.cost = cost
            self.size = cost / pair.price

            self.set_SL_and_TP(strategy)
            self.sl_id, self.tp_id = None, None

        self.exit_macro_RSI = None
        self.exit_RSI = None
        self.exit_trigger = None

        self.fee = self.cost * 0.00036  # opening taker fee (USDT)
        self.exit_price = None
        self.closed_at = None

        self.pnl = None  # percentage
        self.net_pnl = None  # USDT

    def __str__(self):
        return f'{self.symbol} {self.side}\n' \
            f'\tcost = {self.cost:.4f}\n' \
            f'\tsize = {self.size}\n' \
            f'\topened_at = {self.opened_at}\n' \
            f'\tentry_price     = {self.entry_price}\n' \
            f'\tentry_macro_RSI = {self.entry_macro_RSI:.2f}\n' \
            f'\tentry_RSI       = {self.entry_RSI:.2f}\n' \
            f'\tentry_trigger   = {self.entry_trigger}\n' \
            f'\tstop_loss       = {self.stop_loss:.4f}\n' \
            f'\ttake_profit     = {self.take_profit:.4f}\n' \
            f'\texit_price      = {self.exit_price}\n' \
            f'\texit_macro_RSI  = {self.exit_macro_RSI}\n' \
            f'\texit_RSI        = {self.exit_RSI}\n' \
            f'\texit_trigger    = {self.exit_trigger}\n' \
            f'\tclosed_at = {self.closed_at}\n' \
            f'\tfee       = {self.fee:.4f}\n' \
            f'\tpnl       = {self.pnl}\n' \
            f'\tnet_pnl   = {self.net_pnl}\n'

    def create_orders(self, pair, cost, strategy):
        tentative_size = cost / pair.price  # base currency (COIN)
        order = strategy.exchange.create_order(
            pair.symbol, 'MARKET', pair.side, tentative_size
        )

        logger.info(order)

        self.opened_at = datetime.now()
        self.entry_price = order['price']  # quote currency (USDT)
        self.cost = order['cost']    # quote currency
        self.size = order['filled']  # base currency

        self.set_SL_and_TP(strategy)  # NOTE: called here due to dependence on self.entry_price
        inverted_side = 'sell' if pair.side == 'buy' else 'buy'

        # Create orders with the returned base size
        sl_order = strategy.exchange.create_order(
            self.symbol, 'STOP_MARKET', inverted_side, self.size, None, {'stopPrice': self.stop_loss}
        )
        self.sl_id, self.stop_loss = sl_order['id'], sl_order['stopPrice']

        logger.info(sl_order)

        tp_order = strategy.exchange.create_order(
            self.symbol, 'TAKE_PROFIT_MARKET', inverted_side, self.size, None, {'stopPrice': self.take_profit}
        )
        self.tp_id, self.take_profit = tp_order['id'], tp_order['stopPrice']

        logger.info(tp_order)

    def set_SL_and_TP(self, strategy):
        """Calculates and sets stop loss and take profit prices."""
        if self.side == 'buy':
            self.stop_loss = self.entry_price - (self.entry_price * strategy.STOP_LOSS)
            self.take_profit = self.entry_price + (self.entry_price * strategy.TAKE_PROFIT)
        else:
            self.stop_loss = self.entry_price + (self.entry_price * strategy.STOP_LOSS)
            self.take_profit = self.entry_price - (self.entry_price * strategy.TAKE_PROFIT)

    def close(self, pair, strategy, trigger, macro_RSI):
        """Mark the position as closed at the given exit_price and calculate P&L and fees."""
        if strategy.REAL:
            # Close all symbol orders (i.e. TP & SL) with a single call (weight = 1)
            strategy.exchange.fapiPrivate_delete_allopenorders({
                'symbol': self.symbol.replace('/', '')
            })

            # Order may have already been closed by exchange due to SL/TP hit
            if trigger == 'SL' or trigger == 'TP':
                logger.info(f'{trigger} hit, dumping order...')

                # Retrieve SL/TP order to log exit price precisely (weight = 1)
                order = strategy.exchange.fetch_order(
                    self.sl_id if trigger == 'SL' else self.tp_id,
                    self.symbol
                )

                # Do not assume order['status'] == 'filled'
                if order['amount'] != order['filled']:
                    logger.critical('Order did NOT FILL, trying to close manually...')

                    inverted_side = 'sell' if self.side == 'buy' else 'buy'
                    order = strategy.exchange.create_order(
                        self.symbol, 'MARKET', inverted_side, self.size
                    )
            # SL/TP haven't been hit: create market order for closing position
            else:
                logger.info('Closing position, dumping order...')
                inverted_side = 'sell' if self.side == 'buy' else 'buy'

                # Close the order manually (weight = 1)
                order = strategy.exchange.create_order(
                    self.symbol, 'MARKET', inverted_side, self.size
                )

            logger.info(order)

            self.exit_price = order['price']
            self.fee += order['cost'] * 0.00036  # the cost has the raw P&L included
        else:
            self.exit_price = pair.price

        self.closed_at = datetime.now()
        self.exit_macro_RSI, self.exit_RSI = macro_RSI, pair.RSI

        if self.side == 'buy':
            self.pnl = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - self.exit_price) / self.exit_price

        self.net_pnl = self.cost * self.pnl  # P&L in USDT (not net yet)
        self.pnl *= 100                      # P&L in percentage

        # HACK: create a function for calculating P&L + call it inside both if and else
        # Ugly & wet but needed; P&L needs to be calculated after the exit price
        if not strategy.REAL:
            # P&L has to be included because cost is the entry one so P&L is NOT included
            self.fee += (self.cost + self.net_pnl) * 0.00036

        self.net_pnl -= self.fee  # net P&L in USDT
