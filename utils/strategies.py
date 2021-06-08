from utils.constants import *


def hits_RSI_20_80(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 80 or pair['RSI'] <= 20

def hits_RSI_30_70(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 70 or pair['RSI'] <= 30

def compute_RSI_strength(pair):
    """Calculate the strength of the pair's RSI."""
    return abs(50 - pair['RSI'])

def evaluate_RSI(position, pair, strategy):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    _max, _min = (80, 20) if strategy == 'hits_RSI_20_80' else (70, 30)

    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= _max and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= _min and pair['price'] <= position['entry_price']

    return should_close

def determine_RSI_side(pair):
    """Return 'SELL' if the RSI is overbought else return 'BUY'."""
    return 'SELL' if pair['RSI'] >= 50 else 'BUY'


# NOTE: unused strat
def evaluate_flexible_RSI(position, pair):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= RSI_BUY_CLOSE and pair['price'] >= position['entry_price']
    else:
        should_close = pair['RSI'] <= RSI_SELL_CLOSE and pair['price'] <= position['entry_price']

    return should_close
