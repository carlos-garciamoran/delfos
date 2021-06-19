from utils.constants import *


def hits_RSI_10_90(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 90 or pair['RSI'] <= 10

def hits_RSI_15_85(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 85 or pair['RSI'] <= 15

def hits_RSI_20_80(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 80 or pair['RSI'] <= 20

def hits_RSI_30_70(pair):
    """Return True if the RSI is overbought or oversold."""
    return pair['RSI'] >= 70 or pair['RSI'] <= 30

def compute_RSI_strength(pair):
    """Calculate the strength of the pair's RSI."""
    return abs(50 - pair['RSI'])

def RSI_hit_opposite(position, pair, strategy):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    _min, _max = int(strategy[9:11]), int(strategy[12:14])

    if position['side'] == 'BUY':
        should_close = pair['RSI'] >= _max
    else:
        should_close = pair['RSI'] <= _min

    return should_close

def RSI_hit_opposite_with_profit(position, pair, strategy):
    """Return True if the RSI is overbought in a BUY position or oversold in a SELL position."""
    _min, _max = int(strategy[9:11]), int(strategy[12:14])

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
