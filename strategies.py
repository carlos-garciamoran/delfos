from constants import *


def hits_RSI_max_min(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= RSI_MAX or pair['RSI'] <= RSI_MIN

def compute_RSI_strength(pair):
    """Calculate the strength of the pair's RSI."""
    return abs(50 - pair['RSI'])

def evaluate_RSI(position, pair):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= RSI_MAX and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= RSI_MIN and pair['price'] <= position['entry_price']

    return should_close

def determine_RSI_side(pair):
    """Return 'SELL' if the RSI is overbought else return 'BUY'."""
    return 'SELL' if pair['RSI'] >= RSI_MAX else 'BUY'


def evaluate_flexible_RSI(position, pair):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= RSI_BUY_CLOSE and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= RSI_SELL_CLOSE and pair['price'] <= position['entry_price']

    return should_close
