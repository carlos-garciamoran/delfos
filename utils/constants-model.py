MACRO_RSI_MAX = 70
MACRO_RSI_MIN = 30

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
