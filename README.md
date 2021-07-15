# delfos 🔮 | Cryptocurrency Trading Bot

## Features
- Leverages Binance USD-M Futures API 🔌
- Scans last 499 candles of 4 pairs in 1 second ⏱
- Trades multiple strategies with dedicated accounts 💰
- Opens most interesting positions based on RSI strength 💡
- Manages risk
    - Calculates position size based on risk and SL
    - Sets and manages SL & TP
- Closes positions based on 📊
    - RSI reverse
    - macro-RSI (average RSI of the market)
    - stop-loss
    - take-profit
- Tracks account balance, P&L, fees, and other factors 📐
- Logs 💾
    - currently open and closed positions in JSON
    - price-data (symbol, price, and strength) in CSV
    - macro-RSI in CSV

## Strategies

**Required default parameters**
- `account_size` | initial account size in USDT (e.g. 1000)
- `risk` | risk taken per trade (e.g. 0.01 = 1% of account)
- `stop_loss` | distance from entry price (e.g. 0.05 = 5% away)
- `take_profit` | idem
- `profit_close` | close position when `current_price >= entry_price` and the RSI has reversed

**Attributes**
- `name` | should be unique
- `constants` | RSI min and max triggers (e.g. `[30, 70]`, `[20, 80]`)

**TODO**
- Higher timeframes
- Volume
- RSI divergences
- Heikin-Ashi candles
- Momentum

## Setup
- rename `constants-model.py` to `constants.py`
- rename `strategies-model.json` to `strategies.json`
