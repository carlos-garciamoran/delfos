# delfos 🔮 | Cryptocurrency Trading Bot

## Features
- Leverages Binance and TAAPI APIs 🔌
- Trades multiple strategies with dedicated accounts 💰
- Manages risk
    - Calculates position size
    - Sets & manages SL and TP
- Scans ~10 pairs per second ⏱
- Tracks trades, realized P&L, and other factors 📐
- Logs currently open and closed positions via JSON 💾
- Calculates and logs average RSI of the market (macro-RSI) 📊

## Strategies

**Required default parameters**
- `account_risk` | risk taken per trade (e.g. 0.01 = 1% of account)
- `account_size` | initial account size in USDT (e.g. 1000)
- `stop_loss` | distance from entry price (e.g. 0.05 = 5% away)
- `take_profit` | idem
- `profit_close` | close position when `current_price >= entry_price` and the RSI has reversed

**Attributes**
- `name` | should be unique
- `constants` | RSI min and max triggers (e.g. `[30, 70]`, `[20, 80]`)
- ~`type`~ | type of indicator

**TODO**
- RSI divergences
- Heikin-Ashi candles
- Momentum

## Setup
- rename `constants-model.py` to `constants.py`
- rename `strategies-model.json` to `strategies.json`