ACCOUNT_RISK = 0.01  # risk taken per trade (e.g. 0.01 = 1% of account)

STOP_LOSS = 0.04     # distance from entry price (e.g. 0.07 = 7% away)
TAKE_PROFIT = 0.05   # idem

# POSITION_SIZE = 0.2      # UNUSED: position size (e.g. 0.2 = 20% of total account per position)
# MIN_POSITION_SIZE = 70   # UNUSED: only open positions greater than this size (USDT)

RSI_MAX = 70
RSI_MIN = 30

# TODO: implement into strategy
RSI_BUY_OPEN = 30
RSI_BUY_CLOSE = 80
RSI_SELL_OPEN = 70
RSI_SELL_CLOSE = 20

# Blacklist of symbols ignored
NON_TRADED_SYMBOLS = [
    # Fiat/Stable pairs
    'AUD',
    'DAI',
    'EUR',
    'GBP',
    'USDC',
    'USDS',
    'USDSB',

    # Dead coins on Binance
    'BCC',
    'BCHABC',
    'BCHSV',
    'BKRW',
    'ERD',
    'LEND',
    'HC',
    'MCO',
    'NPXS',
    'PXS',
    'STORM',
    'STRAT',
    'VEN',
    'XZC',
]

for i in range(len(NON_TRADED_SYMBOLS)):
    NON_TRADED_SYMBOLS[i] += 'USDT'
