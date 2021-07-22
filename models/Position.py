from datetime import datetime

from loguru import logger


class Position:
    def __init__(self, pair, side, cost, strategy, macro_RSI):
        self.symbol = pair.symbol  # symbol name
        self.side = side           # 'buy', 'sell'
        self.entry_RSI = pair.RSI     # for post-analysis purposes
        self.entry_macro = macro_RSI  # for post-analysis purposes

        if strategy.real:
            tentative_size = cost / pair.price  # base currency (COIN)
            order = strategy.exchange.create_order(
                pair.symbol, 'MARKET', side, tentative_size
            )
            logger.info('Dumping created order...')
            logger.info(order)

            self.opened_at = datetime.now()
            self.entry_price = order['price']  # quote currency (USDT)
            self.cost = order['cost']    # quote currency
            self.size = order['filled']  # base currency

            self.set_SL_and_TP(strategy)  # NOTE: called here due to dependence on self.entry_price
            inverted_side = 'sell' if side == 'buy' else 'buy'

            # Create orders with the returned base size
            sl_order = strategy.exchange.create_order(
                self.symbol, 'STOP_MARKET', inverted_side, self.size, None, {'stopPrice': self.stop_loss}
            )
            logger.info('Dumping created SL...')
            logger.info(sl_order)

            self.sl_id = sl_order['id']
            self.stop_loss = sl_order['stopPrice']

            tp_order = strategy.exchange.create_order(
                self.symbol, 'TAKE_PROFIT_MARKET', inverted_side, self.size, None, {'stopPrice': self.take_profit}
            )
            logger.info('Dumping created TP...')
            logger.info(tp_order)
            self.tp_id = tp_order['id']
            self.take_profit = tp_order['stopPrice']
        else:
            self.opened_at = datetime.now()
            self.entry_price = pair.price
            self.cost = cost
            self.size = cost / pair.price

            self.set_SL_and_TP(strategy)
            self.sl_id, self.tp_id = None, None

        self.exit_cause = None
        self.exit_macro = None
        self.exit_RSI = None

        self.fee = self.cost * 0.00036  # opening taker fee (USDT)
        self.exit_price = None
        self.closed_at = None

        self.pnl = 0.0  # percentage
        self.net_pnl = 0.0  # USDT

    def __str__(self):
        return f'{self.symbol} {self.side}\n' \
                f'\tcost        = {self.cost:.4f}\n' \
                f'\tsize        = {self.size}\n' \
                f'\topened_at   = {self.opened_at}\n' \
                f'\tentry_price = {self.entry_price}\n' \
                f'\tstop_loss   = {self.stop_loss:.4f}\n' \
                f'\ttake_profit = {self.take_profit:.4f}\n' \
                f'\texit_price  = {self.exit_price}\n' \
                f'\tclosed_at   = {self.closed_at}\n' \
                f'\tfee         = {self.fee:.4f}\n' \
                f'\tpnl         = {self.pnl}\n' \
                f'\tnet_pnl     = {self.net_pnl:.4f}\n'


    def set_SL_and_TP(self, strategy):
        """Calculates and sets stop loss and take profit prices."""
        if self.side == 'buy':
            self.stop_loss = self.entry_price - (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price + (self.entry_price * strategy.take_profit)
        else:
            self.stop_loss = self.entry_price + (self.entry_price * strategy.stop_loss)
            self.take_profit = self.entry_price - (self.entry_price * strategy.take_profit)

    def close(self, pair, strategy, causes, macro_RSI):
        """Mark the position as closed at the given exit_price and calculate P&L and fees."""
        if causes[0]:
            self.exit_cause = 'SL'
        elif causes[1]:
            self.exit_cause = 'TP'
        elif causes[2]:
            self.exit_cause = 'Macro-RSI'
        elif causes[3]:
            self.exit_cause = 'RSI'
        elif causes[4]:
            self.exit_cause = 'Timer'

        self.exit_macro = macro_RSI
        self.exit_RSI = pair.RSI

        if strategy.real:
            # Close all symbol orders (i.e. TP & SL) with a single call (weight = 1)
            strategy.exchange.fapiPrivate_delete_allopenorders({
                'symbol': self.symbol.replace('/', '')
            })

            # Order may have already been closed by exchange due to TP or SL being hit
            if not (causes[0] or causes[1]):
                # Neither SL or TP have been hit, then create a market order for closing the position
                inverted_side = 'sell' if self.side == 'buy' else 'buy'

                # Close the order manually (weight = 1)
                order = strategy.exchange.create_order(
                    self.symbol, 'MARKET', inverted_side, self.size
                )
                logger.info('Closed position, dumping order...')
            else:
                # NOTE: this assumes order['status'] == 'FILLED'
                # Retrieve closing price from SL or TP to log exit price precisely (weight = 1)
                order = strategy.exchange.fetch_order(
                    self.sl_id if causes[0] else self.tp_id,
                    self.symbol
                )
                logger.info('SL/TP hit, dumping order...')

            logger.info(order)

            self.exit_price = order['price']
            self.fee += order['cost'] * 0.00036  # the cost has the raw P&L included
        else:
            self.exit_price = pair.price

        logger.info(self)
        self.closed_at = datetime.now()

        if self.side == 'buy':
            self.pnl = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - self.exit_price) / self.exit_price

        self.net_pnl = self.cost * self.pnl  # P&L in USDT (not net yet)
        self.pnl *= 100                      # P&L in percentage

        # HACK: create a function for calculating P&L + call it inside both if and else
        # Ugly & wet but needed; P&L needs to be calculated after the exit price
        if not strategy.real:
            # P&L has to be included because cost is the entry one so P&L is NOT included
            self.fee += (self.cost + self.net_pnl) * 0.00036

        self.net_pnl -= self.fee  # net P&L in USDT
