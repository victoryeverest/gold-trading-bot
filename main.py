"""
Enterprise Gold Trading Bot
Main Entry Point
"""

import argparse
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TRADING_CONFIG
from trading.engine import TradingEngine, Backtester


def main():
    parser = argparse.ArgumentParser(description='Enterprise Gold Trading Bot')
    parser.add_argument('command', choices=['run', 'backtest', 'train', 'test'],
                       help='Command to execute')
    parser.add_argument('--capital', type=float, default=50.0,
                       help='Initial capital (default: $50)')
    parser.add_argument('--days', type=int, default=90,
                       help='Backtest duration in days')
    parser.add_argument('--symbol', type=str, default='XAUUSD',
                       help='Trading symbol')
    
    args = parser.parse_args()
    
    config = {'TRADING_CONFIG': TRADING_CONFIG}
    
    if args.command == 'run':
        print("Starting live trading...")
        engine = TradingEngine(config)
        engine.run()
        
    elif args.command == 'backtest':
        print(f"\nRunning {args.days}-day backtest with ${args.capital}...")
        backtester = Backtester(config)
        results = backtester.run_backtest(
            initial_capital=args.capital,
            days=args.days
        )
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS - Aggressive Small Capital Strategy")
        print("="*60)
        print(f"💰 Initial Capital: ${results['initial_capital']:.2f}")
        print(f"💎 Final Capital: ${results['final_capital']:.2f}")
        print(f"📈 Total Profit: ${results['total_profit']:.2f}")
        print(f"🚀 Growth: {results['growth_percent']:.1f}%")
        print()
        print(f"📊 Total Trades: {results['total_trades']}")
        print(f"✅ Winning: {results['winning_trades']}")
        print(f"❌ Losing: {results['losing_trades']}")
        print(f"🎯 Win Rate: {results['win_rate']:.1f}%")
        print(f"⚖️ Profit Factor: {results['profit_factor']:.2f}")
        print()
        print(f"📅 Total Days: {results['total_days']}")
        print(f"💚 Profitable Days: {results['profitable_days']}")
        print(f"📈 Daily Win Rate: {results['daily_win_rate']:.1f}%")
        print(f"💵 Avg Weekly Return: ${results['avg_weekly_return']:.2f}")
        print("="*60)
        
        # Calculate potential growth
        weekly_growth = results['avg_weekly_return'] / args.capital * 100
        print(f"\n💡 Weekly Growth Rate: {weekly_growth:.1f}%")
        print(f"💡 Projected Monthly: {weekly_growth * 4:.1f}%")
        
    elif args.command == 'train':
        print("Training ML models...")
        # This would train the ML models on historical data
        
    elif args.command == 'test':
        print("Running system tests...")
        # Run component tests


if __name__ == "__main__":
    main()
