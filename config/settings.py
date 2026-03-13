"""
 Gold Trading Bot Configuration
Optimized for Small Capital ($50) with Aggressive Daily Profits
"""

import os
from datetime import timedelta

# Django Settings
SECRET_KEY = 'gold-trading-bot-enterprise-secret-key-2024'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
    'trading',
    'ml',
    'news',
    'broker',
    'telegram_bot',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/home/z/my-project/gold-trading-bot/data/trading.db',
    }
}

# Trading Configuration - Aggressive Small Capital Settings
TRADING_CONFIG = {
    # Account Settings
    'INITIAL_CAPITAL': 50.0,  # $50 starting capital
    'CURRENCY': 'USD',
    'SYMBOL': 'XAUUSD',  # Gold
    
    # Aggressive Position Sizing (for small accounts)
    'RISK_PER_TRADE': 0.03,  # 3% risk per trade
    'MAX_POSITION_SIZE': 0.10,  # Max 10% of account in single position
    'MIN_LOT_SIZE': 0.01,  # Minimum lot size
    'MAX_OPEN_TRADES': 3,  # Max concurrent trades for small account
    
    # Aggressive Profit Targets
    'DAILY_PROFIT_TARGET_PERCENT': 0.05,  # 5% daily target
    'WEEKLY_PROFIT_TARGET_PERCENT': 0.25,  # 25% weekly target (compounds to 90%+)
    'TAKE_PROFIT_ATR_MULT': 1.2,  # Dynamic take profit
    'STOP_LOSS_ATR_MULT': 0.8,  # Tighter stop loss for aggressive trading
    
    # Dynamic Profit Securing (KEY FEATURE)
    'ENABLE_DYNAMIC_EXIT': True,
    'PARTIAL_CLOSE_AT_PROFIT_PERCENT': 0.5,  # Close 50% at 50% of TP
    'TRAILING_STOP_TRIGGER': 0.3,  # Start trailing at 30% profit
    'TRAILING_STOP_DISTANCE': 0.2,  # Trail at 20% of profit
    'BREAKEVEN_TRIGGER': 0.25,  # Move to breakeven at 25% profit
    
    # Risk Management
    'MAX_DAILY_DRAWDOWN': 0.10,  # Max 10% daily drawdown
    'MAX_WEEKLY_DRAWDOWN': 0.20,  # Max 20% weekly drawdown
    'DAILY_LOSS_LIMIT': 0.05,  # Stop trading after 5% daily loss
    
    # Technical Indicators
    'RSI_OVERSOLD': 30,
    'RSI_OVERBOUGHT': 70,
    'EMA_FAST': 9,
    'EMA_MEDIUM': 21,
    'EMA_SLOW': 50,
    'ATR_PERIOD': 14,
    'BB_PERIOD': 20,
    'BB_STD': 2.0,
    
    # ML Configuration
    'ML_CONFIDENCE_THRESHOLD': 0.65,
    'ML_ENABLED': True,
    'ML_FEATURES': ['rsi', 'macd', 'ema_cross', 'bb_position', 'atr', 'volume', 'sentiment'],
    
    # News Settings
    'NEWS_ENABLED': True,
    'HIGH_IMPACT_NEWS_MULTIPLIER': 2.0,  # Wider stops during high impact news
    'NEWS_BLACKOUT_MINUTES': 15,  # No trading 15 min before/after high impact news
    
    # Session Settings (Gold trading hours)
    'TRADING_SESSIONS': {
        'asian': {'start': '00:00', 'end': '08:00', 'active': False},
        'london': {'start': '08:00', 'end': '16:00', 'active': True},
        'new_york': {'start': '13:00', 'end': '21:00', 'active': True},
        'overlap': {'start': '13:00', 'end': '16:00', 'active': True},  # Best time
    },
    
    # Telegram Settings
    'TELEGRAM_ENABLED': True,
    'SEND_SIGNALS': True,
    'SEND_TRADE_ALERTS': True,
    'SEND_DAILY_SUMMARY': True,
    
    # Broker Settings
    'BROKER': 'exness',
    'MT5_SERVER': 'Exness-Real',
    'MT5_LOGIN': '',
    'MT5_PASSWORD': '',
    
    # Timeframes
    'PRIMARY_TIMEFRAME': 'M15',  # 15-minute for aggressive scalping
    'CONFIRMATION_TIMEFRAME': 'H1',  # 1-hour for trend confirmation
    'SCALPING_TIMEFRAME': 'M5',  # 5-minute for entry timing
}

# API Keys (set via environment variables)
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/home/z/my-project/gold-trading-bot/logs/trading.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'trading': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
