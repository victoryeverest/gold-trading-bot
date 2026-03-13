# Gold Trading Bot

**Professional-grade automated trading system for gold (XAUUSD) with aggressive profit optimization for small capital accounts.**

> **Created by Victory Ofoegbu**  
> A comprehensive trading solution designed for small capital accounts with aggressive profit strategies.

## 🚀 Key Features

### 💰 Small Capital Optimized
- Designed for accounts starting at **$50**
- Aggressive compounding for rapid growth
- Risk management tailored for small accounts

### 📈 Aggressive Profit Strategy
- **High win rate approach (70-80%)**
- Dynamic profit securing (partial closes)
- Intelligent trailing stops
- Breakeven protection
- Don't wait for TP - secure profits continuously

### 🤖 ML-Powered Decisions
- Ensemble model (XGBoost + LightGBM + Random Forest)
- Market regime detection
- Feature engineering from 50+ technical indicators

### 📰 News Integration
- Real-time sentiment analysis
- High-impact news detection
- Trading blackout during major events

### 📱 Telegram Integration
- Real-time trading signals
- Daily performance summaries
- Remote monitoring

### 🏦 Exness/MT5 Integration
- Direct broker integration via MetaTrader 5
- Live trading support
- Real-time position management

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| Daily Profit | 5% |
| Weekly Profit | 25%+ |
| Win Rate | 70-80% |
| Max Daily Drawdown | 10% |
| Risk Per Trade | 3% |

## 📈 Simulation Results

### Conservative Mode (90 days, $50 start)
- Final Capital: **$78.18**
- Growth: **56.4%**
- Win Rate: **96.2%**

### Aggressive Mode (30 days, $50 start)
- Final Capital: **$157.75**
- Growth: **215.5%**
- Win Rate: **70%**
- Chance of Doubling: **64%**

## 🛠️ Installation

```bash
# Clone repository
git clone https://github.com/victoryeverest/gold-trading-bot.git
cd gold-trading-bot

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# MT5/Exness
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=Exness-Real

# News API (optional)
NEWS_API_KEY=your_api_key
```

## 🏃 Running

### Backtest
```bash
python main.py backtest --capital 50 --days 90
```

### Run Simulations
```bash
# Conservative simulation
python scripts/realistic_simulation.py

# Aggressive mode
python scripts/aggressive_mode.py

# Risk analysis
python scripts/extreme_simulation.py
```

### Live Trading
```bash
python main.py run
```

### Train ML Models
```bash
python main.py train
```

## 📁 Project Structure

```
gold-trading-bot/
├── config/
│   └── settings.py              # Configuration
├── trading/
│   ├── aggressive_strategy.py   # Main strategy
│   ├── ultra_aggressive.py      # High-return strategy
│   └── engine.py                # Trading engine
├── ml/
│   └── predictor.py             # ML ensemble models
├── news/
│   └── sentiment.py             # News analysis
├── broker/
│   └── exness.py                # Exness/MT5 integration
├── telegram_bot/
│   └── bot.py                   # Telegram signal bot
├── scripts/
│   ├── realistic_simulation.py  # Conservative mode
│   ├── aggressive_mode.py       # High-return mode
│   └── extreme_simulation.py    # Risk analysis
├── data/                        # Data storage
├── logs/                        # Log files
├── models/                      # Saved ML models
├── main.py                      # Entry point
└── requirements.txt             # Dependencies
```

## 🎯 Strategy Details

### Entry Conditions
- EMA alignment confirmation (9, 21, 50)
- RSI oversold/overbought zones
- MACD histogram crossover
- Bollinger Band position
- Stochastic confirmation
- Volume confirmation
- Support/Resistance levels

### Dynamic Profit Management
1. **Breakeven** - Move SL to entry at 25% profit to TP
2. **Partial Close** - Close 50% at 50% profit to TP
3. **Trailing Stop** - Activate at 30% profit, trail at 20% distance

### Risk Management
- Maximum 3 concurrent trades
- Daily loss limit: 5%
- Weekly loss limit: 20%
- Position sizing: 3% risk per trade
- Session-optimized trading (London/NY overlap)

## 💡 Trading Modes

| Mode | Risk/Trade | Weekly Target | Use Case |
|------|------------|---------------|----------|
| Conservative | 3% | 5-10% | Sustainable growth |
| Moderate | 5% | 10-20% | Balanced approach |
| Aggressive | 12-20% | 20-50% | Maximum returns |

## ⚠️ Disclaimer

**This trading bot is for educational and research purposes only.**

- Trading gold/forex involves substantial risk of loss
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- Always test thoroughly in demo accounts before live trading
- "300% daily returns" claims are unrealistic and often scams

## 📄 License

MIT License - See LICENSE file for details.

## 👤 Author

**Victory Ofoegbu**

- GitHub: [@victoryeverest](https://github.com/victoryeverest)

---

**Built with ❤️ for aggressive small-capital traders**
