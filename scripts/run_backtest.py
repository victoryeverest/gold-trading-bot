"""
High-Performance Backtest for Small Capital Accounts
Optimized for $50 starting capital with aggressive daily profit targets
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger('trading')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    result: str  # 'WIN', 'LOSS', 'BREAKEVEN'
    exit_reason: str


class UltraAggressiveBacktest:
    """
    Backtest engine optimized for small capital aggressive trading.
    Features: High win rate, partial closes, dynamic profit securing.
    """
    
    def __init__(self, initial_capital: float = 50.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # Strategy parameters
        self.risk_per_trade = 0.05  # 5% risk
        self.max_trades_per_day = 5
        
        # TP/SL for HIGH WIN RATE
        self.tp_atr_mult = 0.6  # Close TP = wins often
        self.sl_atr_mult = 1.5  # Far SL = rarely hit
        
        # Partial close
        self.partial_close_at = 0.4  # Close 50% at 40% of TP
        self.breakeven_at = 0.2  # Move to BE at 20% of TP
        
        # Risk limits
        self.daily_loss_limit = 0.08  # 8% daily max loss
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = df.copy()
        
        # EMAs
        for period in [9, 21, 50]:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Stochastic
        low_min = df['low'].rolling(window=14).min()
        high_max = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def get_trend(self, df: pd.DataFrame, idx: int) -> str:
        """Get current trend direction."""
        row = df.iloc[idx]
        
        if row['ema_9'] > row['ema_21'] and row['close'] > row['ema_21']:
            return 'BULLISH'
        elif row['ema_9'] < row['ema_21'] and row['close'] < row['ema_21']:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def check_entry(self, df: pd.DataFrame, idx: int, trend: str) -> Tuple[bool, float]:
        """Check entry conditions with scoring."""
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        score = 0.0
        
        if trend == 'BULLISH':
            # RSI oversold
            if row['rsi'] < 35:
                score += 0.25
            elif row['rsi'] < 45:
                score += 0.15
            
            # Stochastic turning up
            if row['stoch_k'] < 30 and row['stoch_k'] > prev['stoch_k']:
                score += 0.20
            
            # MACD bullish
            if row['macd_hist'] > 0 and prev['macd_hist'] <= 0:
                score += 0.20
            elif row['macd'] > row['macd_signal']:
                score += 0.10
            
            # Near lower BB
            if row['bb_position'] < 0.25:
                score += 0.15
            
            # EMA bounce
            if row['low'] <= row['ema_21'] * 1.001 and row['close'] > row['ema_21']:
                score += 0.15
            
        elif trend == 'BEARISH':
            # RSI overbought
            if row['rsi'] > 65:
                score += 0.25
            elif row['rsi'] > 55:
                score += 0.15
            
            # Stochastic turning down
            if row['stoch_k'] > 70 and row['stoch_k'] < prev['stoch_k']:
                score += 0.20
            
            # MACD bearish
            if row['macd_hist'] < 0 and prev['macd_hist'] >= 0:
                score += 0.20
            elif row['macd'] < row['macd_signal']:
                score += 0.10
            
            # Near upper BB
            if row['bb_position'] > 0.75:
                score += 0.15
            
            # EMA rejection
            if row['high'] >= row['ema_21'] * 0.999 and row['close'] < row['ema_21']:
                score += 0.15
        
        # Volume
        if row['volume_ratio'] > 1.2:
            score += 0.10
        
        return score >= 0.50, min(score, 1.0)
    
    def run_backtest(self, days: int = 90) -> Dict:
        """Run comprehensive backtest."""
        logger.info(f"Running {days}-day backtest with ${self.initial_capital}...")
        
        # Generate realistic gold price data
        candles_per_day = 96  # 15-minute candles
        total_candles = days * candles_per_day
        
        np.random.seed(42)
        
        # Generate price series with realistic properties
        prices = []
        price = 2000.0
        
        for i in range(total_candles):
            # Multiple components for realistic movement
            trend = np.sin(i / 150) * 0.3  # Slow trend cycle
            momentum = np.sin(i / 50) * 0.2  # Medium momentum
            noise = np.random.normal(0, 1.5)  # Random noise
            
            # Occasional jumps (news events)
            if np.random.random() < 0.02:
                jump = np.random.choice([-8, -5, 5, 8])
            else:
                jump = 0
            
            price += trend + momentum + noise + jump
            price = max(1800, min(2200, price))
            prices.append(price)
        
        # Create OHLC data
        dates = pd.date_range(end=datetime.now(), periods=total_candles, freq='15min')
        
        df_data = {
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }
        
        for i, price in enumerate(prices):
            spread = np.random.uniform(0.5, 2.5)
            df_data['open'].append(price + np.random.uniform(-0.5, 0.5))
            df_data['close'].append(price)
            df_data['high'].append(price + spread)
            df_data['low'].append(price - spread)
            df_data['volume'].append(np.random.randint(100, 2000))
        
        df = pd.DataFrame(df_data, index=dates)
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Trading simulation
        trades: List[Trade] = []
        open_positions = []
        daily_pnl = {}
        daily_trades = {}
        capital_history = [self.capital]
        
        for i in range(50, len(df)):
            current_date = df.index[i].strftime('%Y-%m-%d')
            current_price = df['close'].iloc[i]
            atr = df['atr'].iloc[i]
            
            # Initialize daily tracking
            if current_date not in daily_pnl:
                daily_pnl[current_date] = 0
                daily_trades[current_date] = 0
            
            # Check daily loss limit
            if daily_pnl[current_date] < -self.capital * self.daily_loss_limit:
                continue  # Skip trading for today
            
            # Manage open positions
            for pos in open_positions[:]:
                # Calculate current P&L
                if pos['direction'] == 'BUY':
                    current_pnl_pips = (current_price - pos['entry']) / 0.01
                    profit_distance = current_price - pos['entry']
                else:
                    current_pnl_pips = (pos['entry'] - current_price) / 0.01
                    profit_distance = pos['entry'] - current_price
                
                tp_distance = abs(pos['tp'] - pos['entry'])
                profit_to_tp = abs(profit_distance) / tp_distance
                
                # Check stop loss
                if pos['direction'] == 'BUY' and current_price <= pos['sl']:
                    pnl = (pos['sl'] - pos['entry']) / 0.01 * 0.1 * pos['size']
                    self.capital += pnl
                    daily_pnl[current_date] += pnl
                    trades.append(Trade(
                        entry_time=pos['time'],
                        exit_time=df.index[i],
                        direction=pos['direction'],
                        entry_price=pos['entry'],
                        exit_price=pos['sl'],
                        position_size=pos['original_size'],
                        pnl=pnl,
                        result='LOSS',
                        exit_reason='Stop Loss'
                    ))
                    open_positions.remove(pos)
                    continue
                    
                elif pos['direction'] == 'SELL' and current_price >= pos['sl']:
                    pnl = (pos['entry'] - pos['sl']) / 0.01 * 0.1 * pos['size']
                    self.capital += pnl
                    daily_pnl[current_date] += pnl
                    trades.append(Trade(
                        entry_time=pos['time'],
                        exit_time=df.index[i],
                        direction=pos['direction'],
                        entry_price=pos['entry'],
                        exit_price=pos['sl'],
                        position_size=pos['original_size'],
                        pnl=pnl,
                        result='LOSS',
                        exit_reason='Stop Loss'
                    ))
                    open_positions.remove(pos)
                    continue
                
                # Check take profit
                if pos['direction'] == 'BUY' and current_price >= pos['tp']:
                    pnl = (pos['tp'] - pos['entry']) / 0.01 * 0.1 * pos['size']
                    self.capital += pnl
                    daily_pnl[current_date] += pnl
                    trades.append(Trade(
                        entry_time=pos['time'],
                        exit_time=df.index[i],
                        direction=pos['direction'],
                        entry_price=pos['entry'],
                        exit_price=pos['tp'],
                        position_size=pos['original_size'],
                        pnl=pnl,
                        result='WIN',
                        exit_reason='Take Profit'
                    ))
                    open_positions.remove(pos)
                    continue
                    
                elif pos['direction'] == 'SELL' and current_price <= pos['tp']:
                    pnl = (pos['entry'] - pos['tp']) / 0.01 * 0.1 * pos['size']
                    self.capital += pnl
                    daily_pnl[current_date] += pnl
                    trades.append(Trade(
                        entry_time=pos['time'],
                        exit_time=df.index[i],
                        direction=pos['direction'],
                        entry_price=pos['entry'],
                        exit_price=pos['tp'],
                        position_size=pos['original_size'],
                        pnl=pnl,
                        result='WIN',
                        exit_reason='Take Profit'
                    ))
                    open_positions.remove(pos)
                    continue
                
                # Partial close at 40% of TP
                if profit_to_tp >= self.partial_close_at and not pos.get('partial_closed'):
                    partial_size = pos['size'] * 0.5
                    if pos['direction'] == 'BUY':
                        partial_pnl = (current_price - pos['entry']) / 0.01 * 0.1 * partial_size
                    else:
                        partial_pnl = (pos['entry'] - current_price) / 0.01 * 0.1 * partial_size
                    
                    self.capital += partial_pnl
                    daily_pnl[current_date] += partial_pnl
                    pos['size'] -= partial_size
                    pos['partial_closed'] = True
                    
                    # Move to breakeven
                    pos['sl'] = pos['entry']
                
                # Trailing stop after partial
                if pos.get('partial_closed') and profit_to_tp >= 0.6:
                    trail = tp_distance * 0.2
                    if pos['direction'] == 'BUY':
                        new_sl = current_price - trail
                        if new_sl > pos['sl']:
                            pos['sl'] = new_sl
                    else:
                        new_sl = current_price + trail
                        if new_sl < pos['sl']:
                            pos['sl'] = new_sl
            
            # Look for new trades
            if len(open_positions) < 2 and daily_trades[current_date] < self.max_trades_per_day:
                trend = self.get_trend(df, i)
                
                if trend != 'NEUTRAL':
                    valid, score = self.check_entry(df, i, trend)
                    
                    if valid:
                        row = df.iloc[i]
                        
                        # Calculate position size
                        risk_amount = self.capital * self.risk_per_trade
                        atr = row['atr']
                        
                        if trend == 'BULLISH':
                            entry = current_price
                            sl = entry - (atr * self.sl_atr_mult)
                            tp = entry + (atr * self.tp_atr_mult)
                            direction = 'BUY'
                        else:
                            entry = current_price
                            sl = entry + (atr * self.sl_atr_mult)
                            tp = entry - (atr * self.tp_atr_mult)
                            direction = 'SELL'
                        
                        sl_distance = abs(entry - sl)
                        pips_at_risk = sl_distance / 0.01
                        position_size = risk_amount / (pips_at_risk * 0.1)
                        position_size = max(0.01, round(position_size, 2))
                        
                        open_positions.append({
                            'time': df.index[i],
                            'entry': entry,
                            'sl': sl,
                            'tp': tp,
                            'size': position_size,
                            'original_size': position_size,
                            'direction': direction,
                            'partial_closed': False
                        })
                        
                        daily_trades[current_date] += 1
            
            capital_history.append(self.capital)
        
        # Calculate statistics
        wins = [t for t in trades if t.result == 'WIN']
        losses = [t for t in trades if t.result == 'LOSS']
        
        total_profit = self.capital - self.initial_capital
        growth_percent = (total_profit / self.initial_capital) * 100
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        
        total_won = sum(t.pnl for t in wins)
        total_lost = abs(sum(t.pnl for t in losses))
        profit_factor = total_won / total_lost if total_lost > 0 else float('inf')
        
        # Daily statistics
        profitable_days = sum(1 for p in daily_pnl.values() if p > 0)
        losing_days = sum(1 for p in daily_pnl.values() if p < 0)
        breakeven_days = sum(1 for p in daily_pnl.values() if p == 0)
        total_days = len(daily_pnl)
        
        # Weekly analysis
        dates_sorted = sorted(daily_pnl.keys())
        weekly_returns = []
        for i in range(0, len(dates_sorted), 7):
            week_pnl = sum(daily_pnl.get(d, 0) for d in dates_sorted[i:i+7])
            weekly_returns.append(week_pnl)
        
        avg_weekly_return = np.mean(weekly_returns) if weekly_returns else 0
        weekly_growth_rate = avg_weekly_return / self.initial_capital * 100
        
        # Monthly projection
        monthly_projection = weekly_growth_rate * 4
        
        # Calculate maximum drawdown
        peak = self.initial_capital
        max_drawdown = 0
        for cap in capital_history:
            if cap > peak:
                peak = cap
            drawdown = (peak - cap) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_profit': total_profit,
            'growth_percent': growth_percent,
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_days': total_days,
            'profitable_days': profitable_days,
            'losing_days': losing_days,
            'daily_win_rate': profitable_days / total_days * 100 if total_days else 0,
            'avg_weekly_return': avg_weekly_return,
            'weekly_growth_rate': weekly_growth_rate,
            'monthly_projection': monthly_projection,
            'max_drawdown': max_drawdown * 100,
            'daily_pnl': daily_pnl,
            'trades': trades,
            'capital_history': capital_history
        }
        
        return results


def main():
    """Run backtest and display results."""
    backtest = UltraAggressiveBacktest(initial_capital=50.0)
    results = backtest.run_backtest(days=90)
    
    print("\n" + "="*70)
    print("🥇 GOLD TRADING BOT - AGGRESSIVE SMALL CAPITAL BACKTEST")
    print("="*70)
    print(f"\n💰 Starting Capital: ${results['initial_capital']:.2f}")
    print(f"💎 Final Capital: ${results['final_capital']:.2f}")
    print(f"📈 Total Profit: ${results['total_profit']:.2f}")
    print(f"🚀 Growth: {results['growth_percent']:.1f}%")
    
    print(f"\n📊 TRADING STATISTICS:")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   ✅ Wins: {results['winning_trades']}")
    print(f"   ❌ Losses: {results['losing_trades']}")
    print(f"   🎯 Win Rate: {results['win_rate']:.1f}%")
    print(f"   ⚖️ Profit Factor: {results['profit_factor']:.2f}")
    print(f"   📉 Max Drawdown: {results['max_drawdown']:.1f}%")
    
    print(f"\n📅 DAILY PERFORMANCE:")
    print(f"   Total Days: {results['total_days']}")
    print(f"   💚 Profitable: {results['profitable_days']}")
    print(f"   ❤️ Losing: {results['losing_days']}")
    print(f"   ⚪ Breakeven: {results['total_days'] - results['profitable_days'] - results['losing_days']}")
    print(f"   📈 Daily Win Rate: {results['daily_win_rate']:.1f}%")
    
    print(f"\n💵 WEEKLY/MONTHLY PROJECTIONS:")
    print(f"   Avg Weekly Return: ${results['avg_weekly_return']:.2f}")
    print(f"   Weekly Growth Rate: {results['weekly_growth_rate']:.1f}%")
    print(f"   Monthly Projection: {results['monthly_projection']:.1f}%")
    
    print("="*70)
    
    # Additional insights
    if results['weekly_growth_rate'] >= 20:
        print("\n🔥 EXCELLENT: Weekly growth above 20% target!")
    elif results['weekly_growth_rate'] >= 15:
        print("\n✅ GOOD: Weekly growth is solid")
    else:
        print("\n⚠️ NOTE: Adjust strategy parameters for better performance")
    
    print(f"\n💡 To achieve 90% weekly growth, consider:")
    print("   - Higher risk per trade (currently 5%)")
    print("   - More aggressive position sizing")
    print("   - Multiple sessions trading")


if __name__ == "__main__":
    main()
