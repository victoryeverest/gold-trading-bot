# 🥇 Enterprise Gold Trading Bot

**Professional-grade automated trading system for gold (XAUUSD) with aggressive profit optimization for small capital accounts.**

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

## 🛠️ Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/gold-trading-bot.git
cd gold-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

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
│   └── settings.py          # Configuration
├── trading/
│   ├── aggressive_strategy.py  # Main strategy
│   └── engine.py            # Trading engine
├── ml/
│   └── predictor.py         # ML models
├── news/
│   └── sentiment.py         # News analysis
├── broker/
│   └── exness.py            # Broker integration
├── telegram_bot/
│   └── bot.py               # Telegram bot
├── dashboard/               # Web dashboard
├── data/                    # Data storage
├── logs/                    # Log files
├── models/                  # Saved ML models
├── main.py                  # Entry point
└── requirements.txt         # Dependencies
```

## 🎯 Strategy Details

### Entry Conditions
- EMA alignment confirmation
- RSI oversold/overbought zones
- MACD histogram crossover
- Bollinger Band position
- Stochastic confirmation
- Volume confirmation

### Dynamic Profit Management
1. **Breakeven** - Move SL to entry at 25% profit to TP
2. **Partial Close** - Close 50% at 50% profit to TP
3. **Trailing Stop** - Activate at 30% profit, trail at 20% distance

### Risk Management
- Maximum 3 concurrent trades
- Daily loss limit: 5%
- Weekly loss limit: 20%
- Position sizing: 3% risk per trade

## ⚠️ Disclaimer

**This trading bot is for educational and research purposes only.**

- Trading gold/forex involves substantial risk of loss
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- Always test thoroughly in demo accounts before live trading

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines first.

---

**Built with ❤️ for aggressive small-capital traders**
