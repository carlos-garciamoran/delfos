from dotenv import dotenv_values, load_dotenv
from requests import Session

from utils.constants import *


load_dotenv()

URL = 'https://api.taapi.io'
TAAPI_APIKEY = dotenv_values()["TAAPI_APIKEY"]

s = Session()
s.params.update({
    'secret': TAAPI_APIKEY,
    'exchange': EXCHANGE,
    'interval': INTERVAL
})


def get_RSI(symbol):
    resp = s.get(URL + '/rsi', params={ 'symbol': symbol })

    # TAAPI sometimes returns 5xx's
    if resp.status_code == 200:
        RSI = resp.json()['value']
        return RSI, resp.status_code, None
    
    return -1, resp.status_code, resp.text
