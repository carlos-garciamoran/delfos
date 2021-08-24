import hmac
import time

import numpy as np
from requests import Session
from urllib import parse as urllib

from utils.constants import BINANCE_APIKEY, BINANCE_SECRETKEY, INTERVAL


BASEURL = 'https://fapi.binance.com/fapi'

s = Session()
s.headers.update({ 'X-MBX-APIKEY': BINANCE_APIKEY })


# NOTE: unused
def get_account_info():
    """Get current account information, including positions. Weight: 5"""
    endpoint = BASEURL + '/v2/account'

    resp = s.get(endpoint, params=sign_timestamp())

    return resp.json(), resp.status_code


def get_close_candles(symbol, limit=200):
    """
    Get the last {limit} kline/candlestick close values for a symbol's interval.

    Limit       Weight
    [1,100)     1
    [100, 500)  2
    [500, 1000] 5
    > 1000      10
    """
    closes = np.array([])
    endpoint = BASEURL + '/v1/klines'

    resp = s.get(endpoint, params={
        'interval': INTERVAL, 'symbol': symbol, 'limit': limit
    })

    # Basic error checking
    if resp.status_code != 200:
        return [], resp.status_code, resp.text

    for candle in resp.json():
        closes = np.append(closes, float(candle[4]))

    return closes, resp.status_code, None


def sign_timestamp():
    """Sign millisecond timestamp with HMAC256 signature using Binance API's secret key."""
    params = { 'timestamp': int(time.time() * 1000) }  # Convert UNIX time seconds to milliseconds
    payload = urllib.urlencode(params).encode()

    params['signature'] = hmac.new(BINANCE_SECRETKEY.encode(), payload, 'SHA256').hexdigest()

    return params
