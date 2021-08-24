# delfos 🔮 | Cryptocurrency Trading Bot

## Features

- Leverages Binance USDⓈ-M Futures API 🔌
- Scans last 200 candles of 4 pairs in 1 second ⏱
- Trades multiple strategies with dedicated accounts 💰
- Manages risk ⛔️
  - Calculates position size based on free capital, risk, and SL
  - Sets and manages SL & TP
- Opens positions based on 💡
  - macro-RSI triggers (trend)
  - most extreme pair's RSI (reversal)
- Closes positions based on 📊
  - RSI reverse
  - macro-RSI (average RSI of the market)
  - stop-loss
  - take-profit
  - timer
- Tracks account balance, P&L, fees, wins/loses, etc. 📐
- Logs 💾
  - currently open and closed positions in JSON
  - price data (symbol, price, and RSI) in CSV
  - macro-RSI in CSV

## Strategy

### Required parameters

- `account_size (float)` | initial account size in USDT for non-real accounts
- `macro_RSIs (list[int])` | macro RSI min and max triggers (e.g. `[30, 70]`)
- `open_RSIs (list[int])` | open RSI min and max triggers (e.g. `[40, 60]`)
- `close_RSIs (list[int])` | close RSI max and min triggers (e.g. `[50, 50]`)
- `mode (string)` | open positions **long**, **short**, or **both ways**; `[bullish, bearish, neutral]`
- `profit_close (bool)` | close position when `price >= entry_price` **and** RSI has reversed
- `real (bool)` | if the account should use real Binance USDⓈ-M balance
- `risk (bool)` | risk taken per trade (e.g. `0.01` = 1% of account)
- `stop_loss (float)` | distance from entry price (e.g. `0.025` = 2.5% away)
- `take_profit (float)` | idem
- `timer_trigger (int)` | maximum time to keep a position open (minutes)

### TODO

- Momentum
- Volume
- RSI divergences
- Heikin-Ashi candles

## Setup

```bash
mv .env.example .env
mv strategies-model.json strategies.json
mv utils/constants-model.py utils/constants.py
```
