"""
Enterprise Gold Trading Bot
Main Entry Point - Works with or without MT5 connection
"""

import argparse
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trading')


def main():
    parser = argparse.ArgumentParser(description='Gold Trading Bot')
    parser.add_argument('command', choices=['run', 'backtest', 'train', 'test', 'scalable'],
                       help='Command to execute')
    parser.add_argument('--capital', type=float, default=50.0,
                       help='Initial capital (default: $50)')
    parser.add_argument('--days', type=int, default=90,
                       help='Backtest duration in days')
    parser.add_argument('--symbol', type=str, default='XAUUSD',
                       help='Trading symbol')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        print("="*60)
        print("  🚀 Gold Trading Bot - Live Mode")
        print("="*60)
        print(f"  💰 Capital: ${args.capital}")
        print(f"  📊 Symbol: {args.symbol}")
        print("="*60)
        print()
        print("⚠️  NOTE: Running in SIMULATION mode (MT5 not connected)")
        print("   To connect to MT5, install MetaTrader5 and configure .env")
        print()
        
        try:
            from config.settings import TRADING_CONFIG
            from trading.engine import TradingEngine
            
            config = {'TRADING_CONFIG': TRADING_CONFIG}
            engine = TradingEngine(config)
            engine.run()
        except Exception as e:
            logger.error(f"Error running trading engine: {e}")
            print(f"\n❌ Error: {e}")
            print("\nTo fix MT5 connection issues:")
            print("1. Install MetaTrader 5 terminal")
            print("2. Open MT5 and login to your Exness account")
            print("3. Copy .env.example to .env and add your credentials")
        
    elif args.command == 'backtest':
        print("="*60)
        print(f"  📊 Running {args.days}-day backtest with ${args.capital}")
        print("="*60)
        
        try:
            from config.settings import TRADING_CONFIG
            from trading.engine import Backtester
            
            config = {'TRADING_CONFIG': TRADING_CONFIG}
            backtester = Backtester(config)
            results = backtester.run_backtest(
                initial_capital=args.capital,
                days=args.days
            )
            
            print("\n" + "="*60)
            print("  📈 BACKTEST RESULTS")
            print("="*60)
            print(f"  💰 Initial Capital: ${results['initial_capital']:.2f}")
            print(f"  💎 Final Capital: ${results['final_capital']:.2f}")
            print(f"  📈 Total Profit: ${results['total_profit']:.2f}")
            print(f"  🚀 Growth: {results['growth_percent']:.1f}%")
            print()
            print(f"  📊 Total Trades: {results['total_trades']}")
            print(f"  ✅ Winning: {results['winning_trades']}")
            print(f"  ❌ Losing: {results['losing_trades']}")
            print(f"  🎯 Win Rate: {results['win_rate']:.1f}%")
            print(f"  ⚖️ Profit Factor: {results['profit_factor']:.2f}")
            print()
            print(f"  📅 Total Days: {results['total_days']}")
            print(f"  💚 Profitable Days: {results['profitable_days']}")
            print(f"  📈 Daily Win Rate: {results['daily_win_rate']:.1f}%")
            print(f"  💵 Avg Weekly Return: ${results['avg_weekly_return']:.2f}")
            print("="*60)
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            print(f"\n❌ Error: {e}")
    
    elif args.command == 'scalable':
        # Run the optimized scalable backtest
        print("="*60)
        print("  🚀 Scalable Backtest - $50 to $2M+")
        print("="*60)
        
        try:
            from scripts.profitable_scalable_backtest import test_scalability, ProfitableBacktest
            
            test_scalability()
            
            # Run detailed backtest
            bt = ProfitableBacktest(args.capital)
            results = bt.run(days=args.days)
            
        except ImportError:
            print("Running direct scalable test...")
            exec(open('scripts/profitable_scalable_backtest.py').read())
        except Exception as e:
            logger.error(f"Scalable backtest error: {e}")
            print(f"\n❌ Error: {e}")
        
    elif args.command == 'train':
        print("🎯 Training ML models...")
        try:
            from ml.predictor import EnsemblePredictor
            from config.settings import TRADING_CONFIG
            import pandas as pd
            import numpy as np
            
            # Generate training data
            print("Generating training data...")
            np.random.seed(42)
            n = 5000
            prices = [2000.0]
            for i in range(n):
                prices.append(prices[-1] + np.random.normal(0, 1))
            
            df = pd.DataFrame({
                'open': prices[:-1],
                'close': prices[1:],
                'high': [p + np.random.uniform(0.5, 2) for p in prices[:-1]],
                'low': [p - np.random.uniform(0.5, 2) for p in prices[:-1]],
                'volume': np.random.randint(500, 2000, n)
            })
            
            config = {'TRADING_CONFIG': TRADING_CONFIG}
            predictor = EnsemblePredictor(config)
            results = predictor.train(df)
            
            print("\n✅ Training complete!")
            for model, metrics in results.items():
                if 'error' not in metrics:
                    print(f"  {model}: accuracy={metrics['accuracy']:.4f}")
                else:
                    print(f"  {model}: ERROR - {metrics['error']}")
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            print(f"\n❌ Error: {e}")
        
    elif args.command == 'test':
        print("🧪 Running system tests...\n")
        
        all_passed = True
        
        # Test 1: Config
        try:
            from config.settings import TRADING_CONFIG
            print("✅ Config loaded successfully")
        except Exception as e:
            print(f"❌ Config error: {e}")
            all_passed = False
        
        # Test 2: ML Predictor
        try:
            from ml.predictor import EnsemblePredictor
            print("✅ ML Predictor imports successfully")
        except Exception as e:
            print(f"❌ ML Predictor error: {e}")
            all_passed = False
        
        # Test 3: News Sentiment
        try:
            from news.sentiment import SentimentAnalyzer
            print("✅ News Sentiment imports successfully")
        except Exception as e:
            print(f"❌ News Sentiment error: {e}")
            all_passed = False
        
        # Test 4: Trading Strategy
        try:
            from trading.aggressive_strategy import AggressiveSmallCapitalStrategy
            print("✅ Trading Strategy imports successfully")
        except Exception as e:
            print(f"❌ Trading Strategy error: {e}")
            all_passed = False
        
        # Test 5: Telegram Bot
        try:
            from telegram_bot.bot import TelegramSignalBot
            print("✅ Telegram Bot imports successfully")
        except Exception as e:
            print(f"❌ Telegram Bot error: {e}")
            all_passed = False
        
        print()
        if all_passed:
            print("🎉 All tests passed!")
        else:
            print("⚠️ Some tests failed - check dependencies")


if __name__ == "__main__":
    main()
