"""
EXTREME AGGRESSIVE Trading Simulation
Shows what's mathematically possible vs. likely outcomes
"""

import numpy as np
from datetime import datetime
import pandas as pd

def extreme_aggressive_simulation(
    initial_capital: float = 50.0,
    leverage: int = 500,
    risk_per_trade: float = 0.20,  # 20% risk - VERY AGGRESSIVE
    win_rate: float = 0.65,
    days: int = 30,
    trades_per_day: float = 5.0,
    tp_pips: int = 15,
    sl_pips: int = 15,
    compound: bool = True
):
    """
    Simulate extreme aggressive trading with high leverage.
    
    WARNING: This shows both winning AND losing scenarios.
    """
    
    np.random.seed(None)  # Random each time for realistic simulation
    
    capital = initial_capital
    daily_pnl = {}
    trades_log = []
    max_capital = capital
    max_drawdown = 0
    
    pip_value_per_lot = 10.0  # $10 per pip for 1 lot
    
    for day in range(days):
        date = f"Day {day + 1}"
        daily_pnl[date] = 0.0
        
        if capital <= 0:
            break  # Account blown
        
        num_trades = max(1, int(np.random.poisson(trades_per_day)))
        
        for _ in range(num_trades):
            if capital <= 0:
                break
            
            # Calculate position with leverage
            # With 1:500 leverage, $50 can control $25,000
            max_position_lots = (capital * leverage) / 100000  # 100k per lot
            risk_amount = capital * risk_per_trade
            
            # Position size based on risk
            position_lots = risk_amount / (sl_pips * pip_value_per_lot)
            position_lots = min(position_lots, max_position_lots)
            position_lots = max(0.01, round(position_lots, 2))
            
            # Win or lose
            is_win = np.random.random() < win_rate
            
            if is_win:
                pnl = tp_pips * pip_value_per_lot * position_lots
            else:
                pnl = -sl_pips * pip_value_per_lot * position_lots
            
            # Check for margin call
            if abs(pnl) > capital * 0.8:  # 80% loss in one trade
                pnl = -capital * 0.9  # Near total loss
                capital *= 0.1
                trades_log.append({
                    'day': day + 1,
                    'result': 'MARGIN_CALL',
                    'pnl': pnl,
                    'capital': capital
                })
                break
            
            capital += pnl
            daily_pnl[date] += pnl
            
            trades_log.append({
                'day': day + 1,
                'result': 'WIN' if is_win else 'LOSS',
                'pnl': pnl,
                'capital': capital
            })
            
            # Track max capital and drawdown
            if capital > max_capital:
                max_capital = capital
            current_dd = (max_capital - capital) / max_capital
            if current_dd > max_drawdown:
                max_drawdown = current_dd
            
            # Stop if daily loss > 50%
            if daily_pnl[date] < -initial_capital * 0.5:
                break
    
    # Calculate results
    wins = sum(1 for t in trades_log if t['result'] == 'WIN')
    losses = sum(1 for t in trades_log if t['result'] == 'LOSS')
    margin_calls = sum(1 for t in trades_log if t['result'] == 'MARGIN_CALL')
    
    total_trades = len(trades_log)
    actual_win_rate = wins / max(total_trades, 1) * 100
    
    total_profit = capital - initial_capital
    growth = total_profit / initial_capital * 100
    
    return {
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_profit': total_profit,
        'growth_percent': growth,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'margin_calls': margin_calls,
        'win_rate': actual_win_rate,
        'max_drawdown': max_drawdown * 100,
        'account_blown': capital <= initial_capital * 0.1,
        'trades_log': trades_log,
        'daily_pnl': daily_pnl
    }


def run_multiple_simulations(runs: int = 100):
    """Run multiple simulations to show probability distribution."""
    
    results = []
    blown_accounts = 0
    massive_wins = 0  # 10x or more
    
    for _ in range(runs):
        result = extreme_aggressive_simulation(
            initial_capital=50.0,
            leverage=500,
            risk_per_trade=0.15,
            win_rate=0.60,
            days=30,
            trades_per_day=5.0
        )
        results.append(result)
        
        if result['account_blown']:
            blown_accounts += 1
        if result['growth_percent'] >= 900:  # 10x
            massive_wins += 1
    
    # Statistics
    final_capitals = [r['final_capital'] for r in results]
    growths = [r['growth_percent'] for r in results]
    
    return {
        'runs': runs,
        'avg_final_capital': np.mean(final_capitals),
        'median_final_capital': np.median(final_capitals),
        'avg_growth': np.mean(growths),
        'best_case': max(growths),
        'worst_case': min(growths),
        'blown_accounts': blown_accounts,
        'blown_rate': blown_accounts / runs * 100,
        'massive_wins': massive_wins,
        'massive_win_rate': massive_wins / runs * 100,
        'profitable_runs': sum(1 for g in growths if g > 0),
        'profit_rate': sum(1 for g in growths if g > 0) / runs * 100
    }


def main():
    print("\n" + "="*80)
    print("🎰 EXTREME AGGRESSIVE TRADING - THE REALITY CHECK")
    print("="*80)
    
    print("\n📊 SCENARIO 1: Single Run (High Leverage 1:500)")
    print("-"*80)
    
    result = extreme_aggressive_simulation(
        initial_capital=50.0,
        leverage=500,
        risk_per_trade=0.15,
        win_rate=0.60,
        days=30,
        trades_per_day=5.0
    )
    
    print(f"\n💰 Starting Capital: ${result['initial_capital']:.2f}")
    print(f"💎 Final Capital: ${result['final_capital']:.2f}")
    print(f"📈 Growth: {result['growth_percent']:.1f}%")
    print(f"\n📊 Trades: {result['total_trades']}")
    print(f"✅ Wins: {result['wins']}")
    print(f"❌ Losses: {result['losses']}")
    print(f"⚠️ Margin Calls: {result['margin_calls']}")
    print(f"🎯 Win Rate: {result['win_rate']:.1f}%")
    print(f"📉 Max Drawdown: {result['max_drawdown']:.1f}%")
    
    if result['account_blown']:
        print("\n🔴 ACCOUNT BLOWN!")
    elif result['growth_percent'] >= 100:
        print(f"\n🚀 DOUBLED ACCOUNT! ({result['growth_percent']:.0f}%)")
    elif result['growth_percent'] >= 200:
        print(f"\n🔥 TRIPLED ACCOUNT! ({result['growth_percent']:.0f}%)")
    
    print("\n" + "="*80)
    print("📊 SCENARIO 2: 100 Simulations (Probability Distribution)")
    print("-"*80)
    print("Running 100 simulations to show REAL outcomes...")
    
    stats = run_multiple_simulations(100)
    
    print(f"\n📈 STATISTICS (100 runs):")
    print(f"   Average Final Capital: ${stats['avg_final_capital']:.2f}")
    print(f"   Median Final Capital: ${stats['median_final_capital']:.2f}")
    print(f"   Average Growth: {stats['avg_growth']:.1f}%")
    print(f"   Best Case: {stats['best_case']:.1f}%")
    print(f"   Worst Case: {stats['worst_case']:.1f}%")
    
    print(f"\n⚠️ RISK ANALYSIS:")
    print(f"   🔴 Accounts Blown (90%+ loss): {stats['blown_accounts']}/{stats['runs']} ({stats['blown_rate']:.0f}%)")
    print(f"   💚 Profitable Runs: {stats['profitable_runs']}/{stats['runs']} ({stats['profit_rate']:.0f}%)")
    print(f"   🚀 Massive Wins (10x+): {stats['massive_wins']}/{stats['runs']} ({stats['massive_win_rate']:.0f}%)")
    
    print("\n" + "="*80)
    print("💡 THE TRUTH ABOUT 300% DAILY RETURNS")
    print("="*80)
    
    print("""
📚 MATHEMATICAL REALITY:

   To make 300% in ONE day with $50:
   • Need $150 profit from $50
   • With 1:500 leverage = $25,000 position
   • Need 15 pip move at full position
   • SAME 15 pips AGAINST you = Account WIPED OUT

🎯 WHAT ACTUALLY HAPPENS:

   "Guru" bots that show 300% daily:
   1. Cherry-picked best period
   2. Ignoring risk of ruin
   3. Often selling you something
   4. Survivorship bias (you only hear winners)

📊 REALISTIC EXPECTATIONS:

   Conservative (2-5% weekly):     Sustainable, low risk
   Moderate (5-15% weekly):        Achievable with skill
   Aggressive (15-30% weekly):     Possible, higher risk
   Extreme (50%+ weekly):          High chance of blowout
   "300% daily":                   CASINO GAMBLING, not trading

🎰 THE GAMBLER'S FALLACY:

   Many "successful" extreme traders:
   1. Win big initially
   2. Think they're skilled
   3. Eventually hit losing streak
   4. Account blown
   5. Quietly disappear

✅ SUSTAINABLE APPROACH:

   • Start with 5-10% weekly target
   • Compound profits
   • Build skills
   • Increase size gradually
   • Survive to trade another day
""")
    
    print("="*80)
    
    # Show compound growth comparison
    print("\n📊 COMPOUND GROWTH COMPARISON (Starting $50, 12 weeks):")
    print("-"*80)
    
    scenarios = [
        ("Conservative (5%/week)", 0.05),
        ("Moderate (10%/week)", 0.10),
        ("Aggressive (20%/week)", 0.20),
        ("Very Aggressive (50%/week)", 0.50),
    ]
    
    for name, rate in scenarios:
        capital = 50.0
        for week in range(12):
            capital *= (1 + rate)
        growth = (capital - 50) / 50 * 100
        print(f"   {name:30s}: ${capital:,.2f} ({growth:.0f}% total)")
    
    print("\n" + "="*80)
    print("🔥 BOTTOM LINE:")
    print("   • 300% daily = Gambling, not trading")
    print("   • Sustainable = 5-20% weekly with compound growth")
    print("   • $50 → $1000+ in 3 months is achievable with discipline")
    print("   • $50 → $150 in ONE day = Likely to lose everything next day")
    print("="*80)


if __name__ == "__main__":
    main()
