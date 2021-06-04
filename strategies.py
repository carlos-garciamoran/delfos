from constants import *


def evaluate_RSI(position, price, RSI):
    """Close the position if the RSI is overbought in a BUY position or oversold in a SELL position."""

    if position['side'] == 'BUY':
        should_close = RSI >= RSI_MAX and price >= position['entry_price']
    else:
        should_close = RSI <= RSI_MIN and price <= position['entry_price']

    return should_close


def evaluate_flexible_RSI(position, price, RSI):
    """Close the position if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = RSI >= RSI_BUY_CLOSE and price >= position['entry_price']
    else:
        should_close = RSI <= RSI_SELL_CLOSE and price <= position['entry_price']

    return should_close
