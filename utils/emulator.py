import datetime


def close_order(position, exit_price):
    position['exit_price'] = exit_price
    position['closed_at']  = datetime.datetime.now().isoformat()

    if position['side'] == 'BUY':
        position['pnl'][0] = (exit_price - position['entry_price']) / position['entry_price']
    else:
        position['pnl'][0] = (position['entry_price'] - exit_price) / exit_price

    position['pnl'][0] *= 100
    position['pnl'][1] = position['size'] * position['pnl'][0] / 100

    return position


def new_order(symbol, side, entry_price, size, strategy):
    if side == 'BUY':
        stop_loss   = entry_price - (entry_price * strategy.stop_loss)
        take_profit = entry_price + (entry_price * strategy.take_profit)
    else:
        stop_loss   = entry_price + (entry_price * strategy.stop_loss)
        take_profit = entry_price - (entry_price * strategy.take_profit)

    position = {
        'symbol': symbol,
        'side': side,
        'size': size,
        'entry_price': entry_price,
        'exit_price': None,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'pnl': [None, None],   # [%, USDT]
        'opened_at': datetime.datetime.now().isoformat(),
        'closed_at': None,
    }

    return position
