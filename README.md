# delfos 🔮 | Cryptocurrency Trading Bot

## Features
- Leverages Binance USDⓈ-M Futures API 🔌
- Scans last 499 candles of 4 pairs in 1 second ⏱
- Trades multiple strategies with dedicated accounts 💰
- Opens positions based on most interesting macro-RSI and pair's RSI 💡
- Manages risk ⛔️
    - Calculates position size based on strategy risk and SL
    - Sets and manages SL & TP
- Closes positions based on 📊
    - RSI reverse
    - macro-RSI (average RSI of the market)
    - stop-loss
    - take-profit
- Tracks account balance, P&L, fees, wins/loses, etc. 📐
- Logs 💾
    - currently open and closed positions in JSON
    - price-data (symbol, price, and strength) in CSV
    - macro-RSI in CSV

## Strategy
**Required default parameters**
- `account_size` | *float*: initial account size in USDT
- `profit_close` | *boolean*: close position when `price >= entry_price` **and** RSI has reversed
- `real` | *boolean*: if the account should use real Binance USDⓈ-M balance
- `risk` | *boolean*: risk taken per trade (e.g. 0.01 = 1% of account)
- `stop_loss` | *float*: distance from entry price (e.g. 0.025 = 2.5% away)
- `take_profit` | *float*: idem

**Required attributes per-strategy**
- `RSI` | *array[int]*: RSI min and max triggers (e.g. `[30, 70]`, `[20, 80]`)

**TODO**
- Higher timeframes
- Volume
- RSI divergences
- Heikin-Ashi candles
- Momentum

## Setup
- rename `.env.example` to `.env`
- rename `constants-model.py` to `constants.py`
- rename `strategies-model.json` to `strategies.json`
