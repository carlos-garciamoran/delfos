from dotenv import dotenv_values, load_dotenv

load_dotenv()

BINANCE_APIKEY = dotenv_values()['BINANCE_APIKEY']
BINANCE_SECRETKEY = dotenv_values()['BINANCE_SECRETKEY']

INTERVAL = '1m'  # 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w

TIMER_TRIGGER = 60  # maximum time to keep a position open (minutes)
