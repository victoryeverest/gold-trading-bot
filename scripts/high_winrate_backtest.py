"""
HIGH WIN RATE Strategy for Small Capital
Optimized for 80%+ win rate with aggressive profit securing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger('trading')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class HighWinRateBacktest:
    """
    Strategy optimized for HIGH WIN RATE with small capital.
    
    Key principle: 
    - Take Profit CLOSE to entry (wins often)
    - Stop Loss FAR from entry (rarely hit)
    - This mathematically guarantees high win rate
    """
    
    def __init__(self, initial_capital: float = 50.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # HIGH WIN RATE SETTINGS
        # TP is close (0.5 ATR) = wins frequently
        # SL is far (2.0 ATR) = rarely hit
        self.tp_pips = 8  # 8 pips take profit
        self.sl_pips = 20  # 20 pips stop loss
        
        # This gives us R:R of 1:0.4 but HIGH win rate
        # If win rate is 75%, expected value per trade = 0.75*8 - 0.25*20 = 1 pip profit
        
        self.risk_per_trade = 0.04  # 4% risk per trade
        self.max_daily_trades = 8
        self.max_open_positions = 3
        
    def run_backtest(self, days: int = 90) -> Dict:
        """Run backtest with HIGH WIN RATE strategy."""
        logger.info(f"Running HIGH WIN RATE backtest with ${self.initial_capital}...")
        
        # Generate gold price data
        candles_per_day = 96
        total_candles = days * candles_per_day
        
        np.random.seed(42)
        
        # Generate realistic price movement
        prices = []
        price = 2000.0
        
        for i in range(total_candles):
            # Trend component
            trend = np.sin(i / 200) * 0.3
            
            # Random movement (gold typical 1-2 pips per 15min)
            noise = np.random.normal(0, 1.2)
            
            # Jump component
            if np.random.random() < 0.01:
                jump = np.random.choice([-10, -6, 6, 10])
            else:
                jump = 0
            
            price += trend + noise + jump
            price = max(1900, min(2100, price))
            prices.append(price)
        
        # Create DataFrame
        dates = pd.date_range(end=datetime.now(), periods=total_candles, freq='15min')
        
        ohlc = []
        for i, price in enumerate(prices):
            spread = np.random.uniform(0.3, 1.5)
            ohlc.append({
                'open': price + np.random.uniform(-0.3, 0.3),
                'high': price + spread,
                'low': price - spread,
                'close': price,
                'volume': np.random.randint(100, 2000)
            })
        
        df = pd.DataFrame(ohlc, index=dates)
        
        # Calculate EMAs for trend
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        
        # Trading simulation
        trades = []
        open_positions = []
        daily_pnl = {}
        daily_trades = {}
        
        pip = 0.01  # Gold pip
        
        for i in range(50, len(df)):
            current_date = df.index[i].strftime('%Y-%m-%d')
            current_price = df['close'].iloc[i]
            
            if current_date not in daily_pnl:
                daily_pnl[current_date] = 0
                daily_trades[current_date] = 0
            
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Manage open positions
            for pos in open_positions[:]:
                if pos['direction'] == 'BUY':
                    # Check TP (8 pips profit)
                    if current_price >= pos['tp']:
                        pnl = self.tp_pips * 0.1 * pos['size']  # $0.10 per pip for 0.01 lot
                        self.capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'result': 'WIN',
                            'pnl': pnl,
                            'direction': 'BUY',
                            'exit_reason': 'TP'
                        })
                        open_positions.remove(pos)
                        continue
                    
                    # Check SL (20 pips loss)
                    if current_price <= pos['sl']:
                        pnl = -self.sl_pips * 0.1 * pos['size']
                        self.capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'result': 'LOSS',
                            'pnl': pnl,
                            'direction': 'BUY',
                            'exit_reason': 'SL'
                        })
                        open_positions.remove(pos)
                        continue
                    
                    # Partial close at 50% profit (4 pips)
                    if current_price >= pos['entry'] + self.tp_pips * 0.5 * pip and not pos.get('partial'):
                        partial_pnl = (self.tp_pips * 0.5) * 0.1 * pos['size'] * 0.5
                        self.capital += partial_pnl
                        daily_pnl[current_date] += partial_pnl
                        pos['size'] *= 0.5
                        pos['partial'] = True
                        pos['sl'] = pos['entry']  # Move to breakeven
                        
                else:  # SELL
                    # Check TP
                    if current_price <= pos['tp']:
                        pnl = self.tp_pips * 0.1 * pos['size']
                        self.capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'result': 'WIN',
                            'pnl': pnl,
                            'direction': 'SELL',
                            'exit_reason': 'TP'
                        })
                        open_positions.remove(pos)
                        continue
                    
                    # Check SL
                    if current_price >= pos['sl']:
                        pnl = -self.sl_pips * 0.1 * pos['size']
                        self.capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'result': 'LOSS',
                            'pnl': pnl,
                            'direction': 'SELL',
                            'exit_reason': 'SL'
                        })
                        open_positions.remove(pos)
                        continue
                    
                    # Partial close
                    if current_price <= pos['entry'] - self.tp_pips * 0.5 * pip and not pos.get('partial'):
                        partial_pnl = (self.tp_pips * 0.5) * 0.1 * pos['size'] * 0.5
                        self.capital += partial_pnl
                        daily_pnl[current_date] += partial_pnl
                        pos['size'] *= 0.5
                        pos['partial'] = True
                        pos['sl'] = pos['entry']
            
            # Look for new trades
            if (len(open_positions) < self.max_open_positions and 
                daily_trades[current_date] < self.max_daily_trades):
                
                # Determine trend
                trend = None
                if row['ema_9'] > row['ema_21'] and row['close'] > row['ema_21']:
                    # Additional filter: RSI
                    if row['rsi'] < 45:  # Not overbought
                        trend = 'BUY'
                elif row['ema_9'] < row['ema_21'] and row['close'] < row['ema_21']:
                    if row['rsi'] > 55:  # Not oversold
                        trend = 'SELL'
                
                if trend:
                    # Calculate position size
                    risk_amount = self.capital * self.risk_per_trade
                    position_size = risk_amount / (self.sl_pips * 0.1)  # 0.1 = pip value for 0.01 lot
                    position_size = max(0.01, min(0.10, round(position_size, 2)))
                    
                    entry = current_price
                    
                    if trend == 'BUY':
                        sl = entry - self.sl_pips * pip
                        tp = entry + self.tp_pips * pip
                    else:
                        sl = entry + self.sl_pips * pip
                        tp = entry - self.tp_pips * pip
                    
                    open_positions.append({
                        'entry': entry,
                        'sl': sl,
                        'tp': tp,
                        'size': position_size,
                        'direction': trend,
                        'partial': False,
                        'time': df.index[i]
                    })
                    
                    daily_trades[current_date] += 1
        
        # Calculate results
        wins = [t for t in trades if t['result'] == 'WIN']
        losses = [t for t in trades if t['result'] == 'LOSS']
        
        total_profit = self.capital - self.initial_capital
        growth = total_profit / self.initial_capital * 100
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        
        total_won = sum(t['pnl'] for t in wins)
        total_lost = abs(sum(t['pnl'] for t in losses))
        profit_factor = total_won / total_lost if total_lost > 0 else float('inf')
        
        profitable_days = sum(1 for p in daily_pnl.values() if p > 0)
        total_days = len(daily_pnl)
        daily_win_rate = profitable_days / total_days * 100
        
        # Weekly analysis
        sorted_dates = sorted(daily_pnl.keys())
        weekly_returns = []
        for i in range(0, len(sorted_dates), 7):
            week_pnl = sum(daily_pnl[d] for d in sorted_dates[i:i+7])
            weekly_returns.append(week_pnl)
        
        avg_weekly = np.mean(weekly_returns) if weekly_returns else 0
        weekly_growth = avg_weekly / self.initial_capital * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_profit': total_profit,
            'growth_percent': growth,
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'profitable_days': profitable_days,
            'total_days': total_days,
            'daily_win_rate': daily_win_rate,
            'avg_weekly_return': avg_weekly,
            'weekly_growth': weekly_growth,
            'monthly_projection': weekly_growth * 4,
            'daily_pnl': daily_pnl
        }


def main():
    print("\n" + "="*70)
    print("🔥 HIGH WIN RATE STRATEGY - OPTIMIZED FOR SMALL CAPITAL")
    print("="*70)
    print("\nStrategy Settings:")
    print("  • Take Profit: 8 pips (close to entry = wins often)")
    print("  • Stop Loss: 20 pips (far from entry = rarely hit)")
    print("  • Risk per Trade: 4%")
    print("  • This setup targets 75-80% win rate")
    print("="*70)
    
    backtest = HighWinRateBacktest(initial_capital=50.0)
    results = backtest.run_backtest(days=90)
    
    print(f"\n💰 ACCOUNT PERFORMANCE:")
    print(f"   Starting Capital: ${results['initial_capital']:.2f}")
    print(f"   Final Capital: ${results['final_capital']:.2f}")
    print(f"   Total Profit: ${results['total_profit']:.2f}")
    print(f"   Growth: {results['growth_percent']:.1f}%")
    
    print(f"\n📊 TRADING STATISTICS:")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   ✅ Wins: {results['wins']}")
    print(f"   ❌ Losses: {results['losses']}")
    print(f"   🎯 Win Rate: {results['win_rate']:.1f}%")
    print(f"   ⚖️ Profit Factor: {results['profit_factor']:.2f}")
    
    print(f"\n📅 DAILY PERFORMANCE:")
    print(f"   Profitable Days: {results['profitable_days']}/{results['total_days']}")
    print(f"   Daily Win Rate: {results['daily_win_rate']:.1f}%")
    
    print(f"\n💵 GROWTH PROJECTIONS:")
    print(f"   Avg Weekly Return: ${results['avg_weekly_return']:.2f} ({results['weekly_growth']:.1f}%)")
    print(f"   Monthly Projection: {results['monthly_projection']:.1f}%")
    
    print("="*70)
    
    # Analysis
    if results['win_rate'] >= 75:
        print(f"\n✅ SUCCESS: Win rate of {results['win_rate']:.1f}% achieved!")
    else:
        print(f"\n📈 Win rate is {results['win_rate']:.1f}% - Adjusting...")
    
    # Calculate potential with compounding
    print("\n🚀 COMPOUNDING SIMULATION (90 days):")
    capital = 50.0
    daily_return = results['total_profit'] / results['total_days'] / results['initial_capital']
    
    for week in [1, 2, 4, 8, 12]:
        compounded = capital * ((1 + daily_return) ** (week * 7))
        print(f"   Week {week:2d}: ${compounded:.2f} ({(compounded/capital-1)*100:+.1f}%)")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
