import hmac
import time
import datetime
from requests import Session
from urllib import parse as urllib

from dotenv import dotenv_values, load_dotenv
from loguru import logger

from utils.constants import *


load_dotenv()

APIKEY = dotenv_values()["BINANCE_APIKEY"]
SECRETKEY = dotenv_values()["BINANCE_SECRETKEY"].encode()

URL = 'https://api.binance.com'
SAPI = URL + '/sapi/v1'
V3   = URL + '/api/v3'

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
    endpoint = V3 + '/account'

    params = sign_timestamp()
    resp = s.get(endpoint, params=params)

    return resp.json(), resp.status_code


# NOTE: unused; TODO: parse used JSON objects
def get_book(symbol):
    endpoint = V3 + '/ticker/bookTicker'
    resp = s.get(endpoint, params={'symbol': symbol})

    return resp.json(), resp.status_code


# NOTE: unused; TODO: parse used JSON objects
def get_candle(symbol):
    endpoint = V3 + '/klines'
    resp = s.get(endpoint, params={
        'symbol': symbol, 'interval': '1h', 'limit': 1
    })

    return resp.json(), resp.status_code


# NOTE: unused; TODO: parse used JSON objects
def get_exchange_info():
    endpoint = V3 + '/exchangeInfo'
    resp = s.get(endpoint)

    return resp.json(), resp.status_code


def get_price(symbol):
    endpoint = V3 + '/ticker/price'
    resp = s.get(endpoint, params={ 'symbol': symbol })

    price = float(resp.json()['price'])

    return price, resp.status_code


def get_prices():
    """Get all symbol prices and filter them. Weight: 2."""
    prices = []
    endpoint = V3 + '/ticker/price'

    resp = s.get(endpoint)
    dump = resp.json()

    # Basic error checking
    if resp.status_code != 200:
        return prices, resp.status_code, resp.text

    # Parse the price for each interesting symbol
    for pair in dump:
        if pair['symbol'][-4:] != 'USDT' or pair['symbol'] in NON_TRADED_SYMBOLS or \
        'BULL' in pair['symbol'] or 'BEAR' in pair['symbol'] or \
        'UP' in pair['symbol'] or 'DOWN' in pair['symbol']:
            # Skip uninsteresting symbols
            continue

        pair['price'] = float(pair['price'])
        prices.append(pair)

    return prices, resp.status_code, None


# TODO: parse used JSON objects
def open_limit_order(symbol, side, entry_price, size):
    """Send in a new limit order. Weight: 1."""
    endpoint = V3 + '/order'

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


# TODO: parse used JSON objects
def close_limit_order(order, exit_price):
    """Close an existing limit order. Weight: 1."""
    endpoint = V3 + '/order'

    # TODO: retrieve order

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
