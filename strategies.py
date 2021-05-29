from constants import *


def evaluateRSI(position, price, RSI):
    '''Close the position if .'''
    shouldCloseLong  = RSI >= RSI_MAX and position['side'] == 'BUY'  and price >= position['entry_price']
    shouldCloseShort = RSI <= RSI_MIN and position['side'] == 'SELL' and price <= position['entry_price']

    return shouldCloseLong or shouldCloseShort
