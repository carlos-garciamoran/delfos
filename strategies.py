from constants import *


def evaluate_RSI(position, price, RSI):
    '''Close the position if the RSI is overbought in a BUY position or oversold in a SELL position.'''
    should_close_buy  = RSI >= RSI_MAX and position['side'] == 'BUY'  and price >= position['entry_price']
    should_close_sell = RSI <= RSI_MIN and position['side'] == 'SELL' and price <= position['entry_price']

    return should_close_buy or should_close_sell
