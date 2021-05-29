import json
from dotenv import dotenv_values, load_dotenv
from loguru import logger
from requests import Session

load_dotenv()

URL = 'https://api.taapi.io'
TAAPI_APIKEY = dotenv_values()["TAAPI_APIKEY"]

s = Session()
s.params.update({
    'secret': TAAPI_APIKEY,
    'exchange': 'binance',
    'interval': '1m'  # 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w
})


def get_RSI(symbol):
    RSI = -1
    endpoint = URL + '/rsi'
    resp = s.get(endpoint, params={ 'symbol': symbol })

    # Endpoint sometimes returns a 500
    if resp.status_code == 200:
        RSI = resp.json()['value']
        # RSI = json.loads(resp.text)['value']

    return RSI, resp.status_code
