ACCOUNT_RISK = 0.01  # risk taken per trade (e.g. 0.01 = 1% of account)
ACCOUNT_SIZE = 1000.0  # initial account size in USDT

STOP_LOSS = 0.03     # distance from entry price (e.g. 0.07 = 7% away)
TAKE_PROFIT = 0.05   # idem

RSI_BUY_OPEN = 20
RSI_BUY_CLOSE = 70
RSI_SELL_OPEN = 80
RSI_SELL_CLOSE = 30

STRATEGIES = [
    {
        'name': 'RSI_30_70_raw',
        'type': 'RSI',
        'profit_close': False,
        'constants': (30, 70),
    },
    {
        'name': 'RSI_30_70_profit',
        'type': 'RSI',
        'profit_close': True,
        'constants': (30, 70),
    },
    {
        'name': 'RSI_20_80_raw',
        'type': 'RSI',
        'profit_close': False,
        'constants': (20, 80),
    },
    {
        'name': 'RSI_20_80_profit',
        'type': 'RSI',
        'profit_close': True,
        'constants': (20, 80),
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
