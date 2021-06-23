# NOTE: file should be renamed to constants.py

ACCOUNT_RISK = 0.01    # risk taken per trade (e.g. 0.01 = 1% of account)
ACCOUNT_SIZE = 1000.0  # initial account size in USDT

STOP_LOSS = 0.03     # distance from entry price (e.g. 0.07 = 7% away)
TAKE_PROFIT = 0.04   # idem

STRATEGIES = [
    {
        'name': 'RSI_30_70',
        'type': 'RSI',
        'profit_close': False,
        'constants': (30, 70),
        'stop_loss': 0.08,
        'take_profit': 0.07,
    },
    {
        'name': 'RSI_30_70_profit',
        'type': 'RSI',
        'profit_close': True,
        'constants': (30, 70),
        'take_profit': 0.01
    },
    {
        'name': 'RSI_40_60',
        'type': 'RSI',
        'profit_close': False,
        'constants': (40, 80),
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
