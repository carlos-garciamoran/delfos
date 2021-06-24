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

**Attributes**
- RSI constants (e.g. 30/70, 20/80)
- Stop-loss
- Take-profit
- Close only on profit

**TODO**
- RSI divergences
- momentum