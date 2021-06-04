from constants import *


def evaluate_RSI(position, pair):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= RSI_MAX and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= RSI_MIN and pair['price'] <= position['entry_price']

    return should_close


def evaluate_flexible_RSI(position, pair):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= RSI_BUY_CLOSE and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= RSI_SELL_CLOSE and pair['price'] <= position['entry_price']

    return should_close
