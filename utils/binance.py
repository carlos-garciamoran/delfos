import hmac
import time

import numpy as np
from dotenv import dotenv_values, load_dotenv
from requests import Session
from urllib import parse as urllib

from utils.constants import *


load_dotenv()

APIKEY = dotenv_values()["BINANCE_APIKEY"]
SECRETKEY = dotenv_values()["BINANCE_SECRETKEY"].encode()

if EXCHANGE == 'binanceusdm':
    URL = 'https://fapi.binance.com'
    V = URL + '/fapi/v1'
else:
    URL = 'https://api.binance.com'
    V = URL + '/api/v3'
    SAPI = URL + '/sapi/v1'

s = Session()
s.headers.update({ 'X-MBX-APIKEY': APIKEY })


def get_all_coins_info():
    """Get information of coins (available for deposit and withdraw). Weight: 1."""
    endpoint = SAPI + '/capital/config/getall'

    params = sign_timestamp()
    resp = s.get(endpoint, params=params)

    return resp.json(), resp.status_code


def get_USDT_capital():
    """Get the available USDT spot capital. Return -1 if the API didn't return an HTTP 200."""
    assets, code = get_all_coins_info()

    if code != 200:
        return -1

    for asset in assets:
        if asset['coin'] == 'USDT':
            return float(asset['free'])


# NOTE: unused; TODO: parse used JSON objects
def get_account_info():
    """Get current account information. Weight: 10"""
    endpoint = V + '/account'

    params = sign_timestamp()
    resp = s.get(endpoint, params=params)

    return resp.json(), resp.status_code


def get_close_candles(symbol):
    """
    Get the last 499 kline/candlestick close values for a symbol.

    Limit       Weight
    [1,100)     1
    [100, 500)  2
    [500, 1000] 5
    > 1000      10
    """
    closes = np.array([])
    endpoint = V + '/klines'

    # Get the last 499 candles to calculate a precise RSI & stay in weight 2
    resp = s.get(endpoint, params={
        'symbol': symbol, 'interval': INTERVAL, 'limit': 499
    })

    for candle in resp.json():
        closes = np.append(closes, float(candle[4]))

    return closes, resp.status_code


def get_price(symbol):
    """Get the latest prices for the given symbol. Weight: 1."""
    endpoint = V + '/ticker/price'

    resp = s.get(endpoint, params={ 'symbol': symbol })
    price = float(resp.json()['price'])

    return price, resp.status_code


def get_prices():
    """Get the latests prices for all symbols. Weight: 2."""
    endpoint = V + '/ticker/price'

    resp = s.get(endpoint)
    prices = resp.json()

    # Basic error checking
    if resp.status_code != 200:
        return prices, resp.status_code, resp.text

    return prices, resp.status_code, None


# TODO: parse used JSON objects
def open_limit_order(symbol, side, entry_price, size):
    """Send in a new limit order. Weight: 1."""
    endpoint = V + '/order'

    order = {
        'symbol': symbol,
        'side': side,
        'type': 'LIMIT',
        'timeInForce': 'GTC',  # GTC (Good Til Canceled), IOC (Immediate Or Cancel), FOK (Fill or Kill)
        'quantity': size,
        'price': entry_price,
        'recvWindow': 5000,
        'timestamp': int(time.time()),
    }

    signature = hmac.new(SECRETKEY, urllib.urlencode(order), 'SHA256').hexdigest()
    order['signature'] = signature

    resp = s.post(endpoint, data=order)

    return resp.json(), resp.status_code


# TODO: retrieve order and parse used JSON objects
def close_limit_order(order, exit_price):
    """Close an existing limit order. Weight: 1."""
    endpoint = V + '/order'

    signature = hmac.new(SECRETKEY, urllib.urlencode(order), 'SHA256').hexdigest()
    order['signature'] = signature

    resp = s.post(endpoint, data=order)

    return resp.json(), resp.status_code


def sign_timestamp():
    """Sign millisecond timestamp with HMAC256 signature using Binance API's secret key."""
    # Convert UNIX time from seconds to milliseconds
    params = { 'timestamp': int(time.time() * 1000) }
    payload = urllib.urlencode(params).encode()

    signature = hmac.new(SECRETKEY, payload, 'SHA256').hexdigest()
    params['signature'] = signature

    return params
