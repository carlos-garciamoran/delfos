ACCOUNT_RISK = 0.01  # risk taken per trade (e.g. 0.01 = 1% of account)
ACCOUNT_SIZE = 1000.0  # initial account size in USDT

STOP_LOSS = 0.04     # distance from entry price (e.g. 0.07 = 7% away)
TAKE_PROFIT = 0.07   # idem

RSI_MAX = 75
RSI_MIN = 25

RSI_BUY_OPEN = 20
RSI_BUY_CLOSE = 70
RSI_SELL_OPEN = 80
RSI_SELL_CLOSE = 30

# Strategies to run simultaneously as defined in strategies.py
STRATEGIES = [
    {
        'is_interesting': 'hits_RSI_20_80',
        'compute_strength': 'compute_RSI_strength',
        'should_close': 'evaluate_RSI',
        'get_side': 'determine_RSI_side',
    },
    {
        'is_interesting': 'hits_RSI_30_70',
        'compute_strength': 'compute_RSI_strength',
        'should_close': 'evaluate_RSI',
        'get_side': 'determine_RSI_side',
    },
]

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

    # Dead coins on Binance / Not recognised by TAAPI
    'ATA',
    'BCC',
    'BCHABC',
    'BCHSV',
    'BKRW',
    'ERD',
    'LEND',
    'HC',
    'MCO',
    'NPXS',
    'NU',
    'PXS',
    'STORM',
    'STRAT',
    'VEN',
    'XZC',
]

for i in range(len(NON_TRADED_SYMBOLS)):
    NON_TRADED_SYMBOLS[i] += 'USDT'
