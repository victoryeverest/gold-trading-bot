"""
AGGRESSIVE MODE - High Returns with Managed Risk
For traders who want maximum returns and understand the risks
"""

import numpy as np
from datetime import datetime
import pandas as pd

class AggressiveModeTrader:
    """
    High-return trading mode with aggressive position sizing.
    
    Key Features:
    - Higher leverage utilization (1:500)
    - Larger position sizes (10-15% risk per trade)
    - More trades per day (5-8)
    - Partial profit securing
    - Dynamic risk adjustment
    
    WARNING: Higher returns = Higher risk
    """
    
    def __init__(self, initial_capital: float = 50.0, leverage: int = 500):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.leverage = leverage
        
        # Aggressive settings
        self.risk_per_trade = 0.12  # 12% risk per trade
        self.max_risk_per_trade = 0.20  # Max 20% on high confidence
        self.max_daily_trades = 8
        self.max_open_positions = 3
        
        # High win rate approach
        self.tp_pips = 10
        self.sl_pips = 20
        
        # Profit securing
        self.partial_close_at = 0.5  # Close 50% at 50% of TP
        self.breakeven_at = 0.3
        
        # Risk limits
        self.max_daily_loss = 0.25  # Stop at 25% daily loss
        self.max_drawdown = 0.40  # Stop at 40% total drawdown
        
        # Tracking
        self.trades = []
        self.daily_pnl = {}
        self.peak_capital = initial_capital
        
    def calculate_position_size(self, confidence: float = 0.5) -> float:
        """Calculate aggressive position size based on confidence."""
        # Adjust risk based on confidence
        if confidence > 0.8:
            risk = self.max_risk_per_trade
        elif confidence > 0.6:
            risk = self.risk_per_trade
        else:
            risk = self.risk_per_trade * 0.7
        
        risk_amount = self.capital * risk
        
        # Position size in lots
        pip_value = 10.0  # $10 per pip for 1 lot
        position_lots = risk_amount / (self.sl_pips * pip_value)
        
        # Cap by leverage
        max_lots = (self.capital * self.leverage) / 100000
        position_lots = min(position_lots, max_lots)
        
        return max(0.01, round(position_lots, 2))
    
    def run_simulation(self, days: int = 30, win_rate: float = 0.70) -> dict:
        """Run aggressive trading simulation."""
        
        np.random.seed(None)  # Random for realism
        
        capital = self.initial_capital
        trades = []
        daily_pnl = {}
        peak = capital
        max_dd = 0
        
        pip_value = 10.0
        
        for day in range(days):
            date = f"Day {day + 1}"
            daily_pnl[date] = 0.0
            
            # Check if stopped due to drawdown
            current_dd = (peak - capital) / peak if peak > 0 else 0
            if current_dd > self.max_drawdown:
                break
            
            # Number of trades today
            num_trades = np.random.poisson(6)  # Avg 6 trades
            num_trades = max(2, min(num_trades, self.max_daily_trades))
            
            for _ in range(num_trades):
                if capital <= 0:
                    break
                
                # Check daily loss
                if daily_pnl[date] < -self.initial_capital * self.max_daily_loss:
                    break
                
                # Confidence affects risk
                confidence = np.random.uniform(0.5, 0.9)
                position = self.calculate_position_size(confidence)
                
                # Win or lose
                is_win = np.random.random() < win_rate
                
                # Random R:R based on market conditions
                if is_win:
                    # Sometimes hit TP, sometimes partial
                    if np.random.random() < 0.6:
                        pnl = self.tp_pips * pip_value * position
                        exit_type = 'TP'
                    else:
                        # Partial close scenario
                        partial_pnl = (self.tp_pips * 0.5) * pip_value * position * 0.5
                        remaining_pnl = self.tp_pips * pip_value * position * 0.5
                        pnl = partial_pnl + remaining_pnl
                        exit_type = 'PARTIAL_TP'
                else:
                    # Loss - sometimes saved by breakeven
                    if np.random.random() < 0.3:
                        # Partial profit secured, then BE hit
                        pnl = (self.tp_pips * 0.5) * pip_value * position * 0.5
                        exit_type = 'BE_SAVE'
                    else:
                        pnl = -self.sl_pips * pip_value * position
                        exit_type = 'SL'
                
                capital += pnl
                daily_pnl[date] += pnl
                
                if capital > peak:
                    peak = capital
                
                dd = (peak - capital) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                
                trades.append({
                    'day': day + 1,
                    'win': is_win,
                    'pnl': pnl,
                    'capital': capital,
                    'exit': exit_type
                })
        
        # Results
        wins = sum(1 for t in trades if t['win'])
        losses = len(trades) - wins
        
        total_profit = capital - self.initial_capital
        growth = (total_profit / self.initial_capital) * 100
        
        profitable_days = sum(1 for p in daily_pnl.values() if p > 0)
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_profit': total_profit,
            'growth_percent': growth,
            'total_trades': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(trades) * 100 if trades else 0,
            'max_drawdown': max_dd * 100,
            'profitable_days': profitable_days,
            'total_days': len(daily_pnl),
            'daily_win_rate': profitable_days / len(daily_pnl) * 100 if daily_pnl else 0
        }


def main():
    print("\n" + "="*80)
    print("🔥 AGGRESSIVE MODE - HIGH RETURN TRADING")
    print("="*80)
    print("""
⚠️  WARNING: This mode uses aggressive settings:
    • 12-20% risk per trade (vs 3% conservative)
    • 1:500 leverage (vs 1:100 standard)
    • 6-8 trades per day (vs 2-3 standard)
    • Higher potential returns AND losses
""")
    
    # Run aggressive simulation
    trader = AggressiveModeTrader(initial_capital=50.0, leverage=500)
    
    print("="*80)
    print("📊 AGGRESSIVE MODE SIMULATION (30 days, 70% win rate)")
    print("-"*80)
    
    result = trader.run_simulation(days=30, win_rate=0.70)
    
    print(f"\n💰 ACCOUNT PERFORMANCE:")
    print(f"   Starting: ${result['initial_capital']:.2f}")
    print(f"   Final: ${result['final_capital']:.2f}")
    print(f"   Profit: ${result['total_profit']:.2f}")
    print(f"   Growth: {result['growth_percent']:.1f}%")
    
    print(f"\n📊 TRADING STATS:")
    print(f"   Trades: {result['total_trades']}")
    print(f"   Wins: {result['wins']}")
    print(f"   Losses: {result['losses']}")
    print(f"   Win Rate: {result['win_rate']:.1f}%")
    
    print(f"\n⚠️ RISK METRICS:")
    print(f"   Max Drawdown: {result['max_drawdown']:.1f}%")
    print(f"   Daily Win Rate: {result['daily_win_rate']:.1f}%")
    
    # Run multiple simulations
    print("\n" + "="*80)
    print("📊 50 SIMULATIONS - PROBABILITY DISTRIBUTION")
    print("-"*80)
    
    results = []
    for _ in range(50):
        trader = AggressiveModeTrader(initial_capital=50.0, leverage=500)
        r = trader.run_simulation(days=30, win_rate=0.68)
        results.append(r)
    
    growths = [r['growth_percent'] for r in results]
    finals = [r['final_capital'] for r in results]
    
    print(f"\n📈 OUTCOMES (50 simulations):")
    print(f"   Average Growth: {np.mean(growths):.1f}%")
    print(f"   Median Growth: {np.median(growths):.1f}%")
    print(f"   Best Case: {max(growths):.1f}%")
    print(f"   Worst Case: {min(growths):.1f}%")
    
    doubled = sum(1 for g in growths if g >= 100)
    tripled = sum(1 for g in growths if g >= 200)
    ten_x = sum(1 for g in growths if g >= 900)
    blown = sum(1 for f in finals if f < 10)
    
    print(f"\n🎯 PROBABILITY BREAKDOWN:")
    print(f"   Doubled (100%+): {doubled}/50 ({doubled*2}%)")
    print(f"   Tripled (200%+): {tripled}/50 ({tripled*2}%)")
    print(f"   10x (900%+): {ten_x}/50 ({ten_x*2}%)")
    print(f"   Blown (<$10): {blown}/50 ({blown*2}%)")
    
    print("\n" + "="*80)
    print("💡 KEY TAKEAWAYS:")
    print("="*80)
    print("""
✅ AGGRESSIVE MODE CAN WORK when:
   • You have high win rate entries (70%+)
   • You use partial profit securing
   • You respect daily loss limits
   • You compound gradually

❌ AGGRESSIVE MODE FAILS when:
   • You over-leverage without stops
   • You chase losses after bad days
   • You ignore risk management
   • You get greedy on wins

📊 REALISTIC TARGETS:
   Conservative:  5-10% weekly   = $50 → $80-130 in month
   Moderate:      10-20% weekly  = $50 → $130-300 in month  
   Aggressive:    20-50% weekly  = $50 → $300-1000 in month
   Extreme:       50%+ weekly    = $50 → $1000+ OR $0

🎯 SWEET SPOT:
   15-25% weekly with good risk management
   = Sustainable high growth
   = $50 → $500+ in 3 months
""")
    print("="*80)


if __name__ == "__main__":
    main()
