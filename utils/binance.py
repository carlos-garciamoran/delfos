import hmac
import time

import numpy as np
from requests import Session
from urllib import parse as urllib

from utils.constants import BINANCE_APIKEY, BINANCE_SECRETKEY, INTERVAL


BASEURL = 'https://fapi.binance.com/fapi'

s = Session()
s.headers.update({ 'X-MBX-APIKEY': BINANCE_APIKEY })


# NOTE: unused; TODO: parse used JSON objects
def get_account_info():
    """Get current account information, including positions. Weight: 5"""
    endpoint = BASEURL + '/v2/account'

    resp = s.get(endpoint, params=sign_timestamp())

    return resp.json(), resp.status_code


def get_close_candles(symbol, limit=499):
    """
    Get the last 499 kline/candlestick close values for a symbol.

    Limit       Weight
    [1,100)     1
    [100, 500)  2
    [500, 1000] 5
    > 1000      10
    """
    closes = np.array([])
    endpoint = BASEURL + '/v1/klines'

    # Get the last 499 candles to calculate a precise RSI & stay in weight 2
    resp = s.get(endpoint, params={
        'symbol': symbol, 'interval': INTERVAL, 'limit': limit
    })

    # Basic error checking
    if resp.status_code != 200:
        return [], resp.status_code, resp.text

    for candle in resp.json():
        closes = np.append(closes, float(candle[4]))

    return closes, resp.status_code, None


def sign_timestamp():
    """Sign millisecond timestamp with HMAC256 signature using Binance API's secret key."""
    # Convert UNIX time from seconds to milliseconds
    params = { 'timestamp': int(time.time() * 1000) }
    payload = urllib.urlencode(params).encode()

    signature = hmac.new(BINANCE_SECRETKEY, payload, 'SHA256').hexdigest()
    params['signature'] = signature

    return params
