#!/usr/bin/env python3
"""
PROFESSIONAL Gold Trading Backtest
With Market Structure Awareness:
- Volatility Regime Detection
- Liquidity Sweep Detection  
- Session-Based Strategy Switching
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging

# Import professional strategy
from trading.professional_strategy import ProfessionalTradingStrategy, ProfessionalSignal
from trading.market_structure import (
    MarketStructureAnalyzer, VolatilityRegime, TradingSession, LiquidityEvent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('trading')


@dataclass
class TradeResult:
    """Trade result with market structure context."""
    direction: str
    entry: float
    exit: float
    pnl: float
    pips: int
    result: str
    session: str
    regime: str
    strategy: str
    confidence: float
    duration_bars: int


class ProfessionalBacktest:
    """
    Professional backtest with market structure awareness.
    """
    
    def __init__(self, initial_capital: float = 50.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        config = {'TRADING_CONFIG': {
            'RISK_PER_TRADE': 0.02,
            'TAKE_PROFIT_PIPS': 12,
            'STOP_LOSS_PIPS': 10,
            'MAX_OPEN_TRADES': 2
        }}
        
        self.strategy = ProfessionalTradingStrategy(config)
        self.structure_analyzer = MarketStructureAnalyzer()
        
        # Results tracking
        self.trades: List[TradeResult] = []
        self.daily_pnl: Dict[str, float] = {}
        self.session_performance: Dict[str, Dict] = {}
        self.regime_performance: Dict[str, Dict] = {}
        
    def generate_realistic_data(self, days: int = 90) -> pd.DataFrame:
        """
        Generate realistic gold price data with various market conditions.
        Includes trending, ranging, and volatile periods.
        """
        np.random.seed(42)
        candles_per_day = 96  # 15-minute candles
        total_candles = days * candles_per_day
        
        dates = pd.date_range(end=datetime.now(), periods=total_candles, freq='15min')
        
        prices = [2000.0]
        
        for i in range(total_candles - 1):
            # Multiple market condition cycles
            # Trend cycles
            trend = np.sin(i / 400) * 0.35  # Longer trend cycles
            
            # Volatility cycles (simulating news events)
            vol_multiplier = 1.0
            if i % 500 < 20:  # News event every ~500 candles
                vol_multiplier = 2.5
            
            # Noise
            noise = np.random.normal(0, 0.7 * vol_multiplier)
            
            # Jumps
            jump = np.random.choice([0, 0, 0, 0, 0, -1.5, 1.5], 1)[0] * vol_multiplier
            
            new_price = prices[-1] + trend + noise + jump
            new_price = max(1940, min(2060, new_price))
            prices.append(new_price)
        
        df = pd.DataFrame({
            'open': prices[:-1],
            'close': [p + np.random.uniform(-0.15, 0.15) for p in prices[:-1]],
            'high': [p + np.random.uniform(0.4, 1.2) for p in prices[:-1]],
            'low': [p - np.random.uniform(0.4, 1.2) for p in prices[:-1]],
            'volume': np.random.randint(600, 2500, total_candles - 1)
        }, index=dates[:-1])
        
        return df
    
    def run_backtest(self, days: int = 90, verbose: bool = True) -> Dict:
        """Run professional backtest with market structure awareness."""
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"  🎯 PROFESSIONAL GOLD TRADING BACKTEST")
            print(f"  With Market Structure Awareness")
            print(f"{'='*70}")
            print(f"\n💰 Initial Capital: ${self.initial_capital:,.2f}")
            print(f"📅 Period: {days} days")
        
        # Generate data
        df = self.generate_realistic_data(days)
        
        # Add volume for structure analyzer (needs volume column)
        if 'volume' not in df.columns:
            df['volume'] = np.random.randint(500, 2000, len(df))
        
        # Trading state
        positions = []
        self.trades = []
        self.daily_pnl = {}
        self.capital = self.initial_capital
        
        # Session/regime tracking
        session_stats = {s.value: {'trades': 0, 'wins': 0, 'pnl': 0} for s in TradingSession}
        regime_stats = {r.value: {'trades': 0, 'wins': 0, 'pnl': 0} for r in VolatilityRegime}
        
        pip = 0.01
        
        # Main trading loop
        for i in range(150, len(df)):
            current_date = df.index[i].strftime('%Y-%m-%d')
            current_price = df['close'].iloc[i]
            
            if current_date not in self.daily_pnl:
                self.daily_pnl[current_date] = 0
            
            # Manage open positions
            for pos in positions[:]:
                pnl = self._check_exit(pos, current_price, pip)
                
                if pnl is not None:
                    # Record trade
                    trade = TradeResult(
                        direction=pos['direction'],
                        entry=pos['entry'],
                        exit=current_price,
                        pnl=pnl['pnl'],
                        pips=pnl['pips'],
                        result='WIN' if pnl['pnl'] > 0 else 'LOSS',
                        session=pos['session'],
                        regime=pos['regime'],
                        strategy=pos['strategy'],
                        confidence=pos['confidence'],
                        duration_bars=i - pos['entry_bar']
                    )
                    self.trades.append(trade)
                    
                    # Update capital and stats
                    self.capital += pnl['pnl']
                    self.daily_pnl[current_date] += pnl['pnl']
                    
                    session_stats[pos['session']]['trades'] += 1
                    session_stats[pos['session']]['pnl'] += pnl['pnl']
                    if pnl['pnl'] > 0:
                        session_stats[pos['session']]['wins'] += 1
                    
                    regime_stats[pos['regime']]['trades'] += 1
                    regime_stats[pos['regime']]['pnl'] += pnl['pnl']
                    if pnl['pnl'] > 0:
                        regime_stats[pos['regime']]['wins'] += 1
                    
                    positions.remove(pos)
            
            # Daily loss limit
            if self.daily_pnl[current_date] < -self.capital * 0.05:
                continue
            
            # Generate new signal
            if len(positions) < 2:
                signal = self.strategy.generate_signal(
                    df.iloc[:i+1], 
                    account_balance=self.capital,
                    open_positions=len(positions)
                )
                
                if signal and signal.confidence >= 0.5:
                    positions.append({
                        'entry': current_price,
                        'sl': signal.stop_loss,
                        'tp': signal.take_profit,
                        'lot': signal.position_size,
                        'direction': signal.direction,
                        'session': signal.session,
                        'regime': signal.volatility_regime,
                        'strategy': signal.strategy_type,
                        'confidence': signal.confidence,
                        'entry_bar': i
                    })
        
        # Close remaining positions
        for pos in positions:
            loss = abs(pos['entry'] - pos['sl']) / pip * 10 * pos['lot']
            self.capital -= loss
        
        # Calculate results
        return self._calculate_results(session_stats, regime_stats, verbose)
    
    def _check_exit(self, pos: Dict, price: float, pip: float) -> Optional[Dict]:
        """Check if position should be closed."""
        pip_value = 10.0 * pos['lot']
        
        if pos['direction'] == 'BUY':
            if price <= pos['sl']:
                pips = int((pos['sl'] - pos['entry']) / pip)
                return {'pnl': -abs(pips) * pip_value, 'pips': pips}
            elif price >= pos['tp']:
                pips = int((pos['tp'] - pos['entry']) / pip)
                return {'pnl': pips * pip_value, 'pips': pips}
        else:
            if price >= pos['sl']:
                pips = int((pos['entry'] - pos['sl']) / pip)
                return {'pnl': -abs(pips) * pip_value, 'pips': pips}
            elif price <= pos['tp']:
                pips = int((pos['entry'] - pos['tp']) / pip)
                return {'pnl': pips * pip_value, 'pips': pips}
        
        return None
    
    def _calculate_results(self, session_stats: Dict, regime_stats: Dict, 
                          verbose: bool) -> Dict:
        """Calculate and display results."""
        
        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in self.trades)
        win_rate = len(wins) / len(self.trades) * 100 if self.trades else 0
        
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        profitable_days = sum(1 for p in self.daily_pnl.values() if p > 0)
        total_days = len(self.daily_pnl)
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': round(self.capital, 2),
            'total_profit': round(total_pnl, 2),
            'growth_percent': round((self.capital - self.initial_capital) / self.initial_capital * 100, 1),
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profitable_days': profitable_days,
            'total_days': total_days,
            'daily_win_rate': round(profitable_days / total_days * 100, 1) if total_days else 0,
            'session_performance': session_stats,
            'regime_performance': regime_stats,
            'avg_confidence': round(np.mean([t.confidence for t in self.trades]), 2) if self.trades else 0
        }
        
        if verbose:
            self._print_results(results, session_stats, regime_stats)
        
        return results
    
    def _print_results(self, results: Dict, session_stats: Dict, regime_stats: Dict):
        """Print detailed results."""
        print(f"\n{'='*70}")
        print(f"  📈 BACKTEST RESULTS")
        print(f"{'='*70}")
        
        print(f"\n💰 Capital Performance:")
        print(f"   Initial:     ${self.initial_capital:,.2f}")
        print(f"   Final:       ${results['final_capital']:,.2f}")
        print(f"   Profit:      ${results['total_profit']:,.2f}")
        print(f"   Growth:      {results['growth_percent']:.1f}%")
        
        print(f"\n📊 Trade Statistics:")
        print(f"   Total:       {results['total_trades']}")
        print(f"   Wins:        {results['winning_trades']}")
        print(f"   Losses:      {results['losing_trades']}")
        print(f"   Win Rate:    {results['win_rate']:.1f}%")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        
        print(f"\n📅 Daily Performance:")
        print(f"   Profitable Days: {results['profitable_days']}/{results['total_days']}")
        print(f"   Daily Win Rate:  {results['daily_win_rate']:.1f}%")
        
        print(f"\n🗓️ Session Performance:")
        for session, stats in session_stats.items():
            if stats['trades'] > 0:
                wr = stats['wins'] / stats['trades'] * 100
                print(f"   {session:10}: {stats['trades']:3} trades | WR: {wr:5.1f}% | PnL: ${stats['pnl']:>8.2f}")
        
        print(f"\n📊 Volatility Regime Performance:")
        for regime, stats in regime_stats.items():
            if stats['trades'] > 0:
                wr = stats['wins'] / stats['trades'] * 100
                print(f"   {regime:10}: {stats['trades']:3} trades | WR: {wr:5.1f}% | PnL: ${stats['pnl']:>8.2f}")
        
        print(f"\n{'='*70}\n")


def test_scalability():
    """Test professional strategy across account sizes."""
    print(f"\n{'='*70}")
    print(f"  🚀 PROFESSIONAL STRATEGY SCALABILITY TEST")
    print(f"{'='*70}\n")
    
    sizes = [50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 2000000]
    
    for capital in sizes:
        bt = ProfessionalBacktest(initial_capital=capital)
        results = bt.run_backtest(days=90, verbose=False)
        
        status = "✅" if results['profit_factor'] >= 1.0 else "⚠️"
        print(f"  {status} ${capital:>10,} → ${results['final_capital']:>12,.2f} | "
              f"WR: {results['win_rate']:>5.1f}% | PF: {results['profit_factor']:>4.2f}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    test_scalability()
    
    # Run detailed backtest
    bt = ProfessionalBacktest(initial_capital=50.0)
    results = bt.run_backtest(days=90)
    
    # Save results
    output_dir = '/home/z/my-project/download'
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert for JSON
    json_results = {k: v for k, v in results.items() 
                   if k not in ['session_performance', 'regime_performance']}
    
    with open(f'{output_dir}/professional_backtest.json', 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"Results saved to {output_dir}/professional_backtest.json")
