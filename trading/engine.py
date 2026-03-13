"""
Enterprise Trading Engine
Orchestrates all trading components for small capital aggressive trading
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import json
import traceback

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TRADING_CONFIG, DATABASES
from trading.aggressive_strategy import (
    AggressiveSmallCapitalStrategy, ScalpingStrategy, 
    CompoundingManager, SignalType, TradeSignal, Position
)
from ml.predictor import EnsemblePredictor, MarketRegimeDetector, MLPrediction
from news.sentiment import SentimentAnalyzer, EconomicCalendar
from broker.exness import ExnessBroker, OrderType, OrderStatus
from telegram_bot.bot import TelegramSignalBot, TradingSignal

logger = logging.getLogger('trading')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/z/my-project/gold-trading-bot/logs/trading.log'),
        logging.StreamHandler()
    ]
)


@dataclass
class TradeResult:
    trade_id: str
    entry_price: float
    exit_price: float
    position_size: float
    direction: str
    pnl: float
    pnl_percent: float
    duration_minutes: int
    exit_reason: str
    timestamp: datetime


class TradingEngine:
    """
    Main trading engine that coordinates all components.
    Optimized for small capital aggressive trading.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {'TRADING_CONFIG': TRADING_CONFIG}
        self.trading_config = self.config.get('TRADING_CONFIG', TRADING_CONFIG)
        
        # Initialize components
        self.strategy = AggressiveSmallCapitalStrategy(self.config)
        self.scalping_strategy = ScalpingStrategy(self.config)
        self.ml_predictor = EnsemblePredictor(self.config)
        self.regime_detector = MarketRegimeDetector()
        self.sentiment_analyzer = SentimentAnalyzer(self.config)
        self.economic_calendar = EconomicCalendar()
        self.broker = ExnessBroker(self.config)
        self.telegram_bot = TelegramSignalBot(self.config)
        
        # Compounding manager
        initial_capital = self.trading_config.get('INITIAL_CAPITAL', 50.0)
        self.compounding = CompoundingManager(
            initial_capital=initial_capital,
            daily_target=self.trading_config.get('DAILY_PROFIT_TARGET_PERCENT', 0.05)
        )
        
        # State
        self.running = False
        self.positions: List[Position] = []
        self.trade_history: List[TradeResult] = []
        self.daily_stats = {
            'trades': 0, 'wins': 0, 'losses': 0,
            'profit': 0.0, 'started': datetime.now()
        }
        
        # Risk tracking
        self.daily_pnl = 0.0
        self.daily_start_balance = initial_capital
        
        # Data storage
        self.market_data = []
        self.data_dir = '/home/z/my-project/gold-trading-bot/data/'
        self.log_dir = '/home/z/my-project/gold-trading-bot/logs/'
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("Initializing trading engine...")
        
        # Connect to broker
        if not self.broker.connect():
            logger.warning("Running in simulation mode")
        
        # Initialize Telegram
        if self.trading_config.get('TELEGRAM_ENABLED', False):
            await self.telegram_bot.initialize()
        
        logger.info("Trading engine initialized")
        return True
    
    async def shutdown(self):
        """Shutdown all components."""
        logger.info("Shutting down trading engine...")
        self.running = False
        self.broker.disconnect()
        await self.telegram_bot.stop()
        logger.info("Trading engine shutdown complete")
    
    def load_market_data(self) -> pd.DataFrame:
        """Load or fetch market data."""
        # Try to load from broker
        raw_data = self.broker.get_market_data(timeframe='M15', count=500)
        
        if not raw_data:
            # Generate synthetic data for backtest
            raw_data = self._generate_synthetic_data(500)
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
        
        return df
    
    def _generate_synthetic_data(self, count: int) -> List[Dict]:
        """Generate synthetic gold price data with realistic patterns."""
        np.random.seed(42)  # For reproducibility
        
        data = []
        price = 2000.0
        trend = 0.0
        
        for i in range(count):
            # Add trend component
            if i % 100 == 0:
                trend = np.random.uniform(-0.5, 0.5)
            
            # Add noise
            noise = np.random.normal(0, 2)
            
            # Add volatility clustering
            if i > 0 and abs(data[-1]['close'] - data[-1]['open']) > 3:
                noise *= 1.5  # Higher volatility after big moves
            
            # Update price
            price += trend + noise
            price = max(1900, min(2100, price))  # Keep in range
            
            # Generate OHLC
            spread = np.random.uniform(0.5, 3)
            high = price + spread
            low = price - spread
            open_price = price + np.random.uniform(-1, 1)
            close_price = price
            volume = np.random.randint(100, 2000)
            
            data.append({
                'time': datetime.now() - timedelta(minutes=15 * (count - i)),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
        
        return data
    
    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Update technical indicators."""
        df = self.strategy.calculate_indicators(df)
        return df
    
    def check_risk_limits(self) -> Tuple[bool, str]:
        """Check if we're within risk limits."""
        # Daily loss limit
        daily_loss_limit = self.trading_config.get('DAILY_LOSS_LIMIT', 0.05)
        max_loss = self.daily_start_balance * daily_loss_limit
        
        if self.daily_pnl < -max_loss:
            return False, f"Daily loss limit reached: ${abs(self.daily_pnl):.2f}"
        
        # Max drawdown
        current_balance = self.daily_start_balance + self.daily_pnl
        drawdown = (self.daily_start_balance - current_balance) / self.daily_start_balance
        
        if drawdown > self.trading_config.get('MAX_DAILY_DRAWDOWN', 0.10):
            return False, f"Max drawdown reached: {drawdown:.1%}"
        
        return True, "Within risk limits"
    
    def should_trade(self) -> Tuple[bool, str]:
        """Check if trading conditions are favorable."""
        # Check risk limits
        risk_ok, risk_msg = self.check_risk_limits()
        if not risk_ok:
            return False, risk_msg
        
        # Check trading hours
        current_hour = datetime.now().hour
        sessions = self.trading_config.get('TRADING_SESSIONS', {})
        
        active_session = False
        for session_name, session in sessions.items():
            if session.get('active', False):
                start = int(session['start'].split(':')[0])
                end = int(session['end'].split(':')[0])
                if start <= current_hour < end:
                    active_session = True
                    break
        
        if not active_session:
            return False, "Outside trading hours"
        
        # Check news blackout
        if self.trading_config.get('NEWS_ENABLED', False):
            blackout, reason = self.sentiment_analyzer.check_news_blackout()
            if blackout:
                return False, reason
        
        return True, "Ready to trade"
    
    async def execute_signal(self, signal: TradeSignal) -> bool:
        """Execute a trading signal."""
        if signal.signal_type == SignalType.BUY:
            order_type = OrderType.BUY
        elif signal.signal_type == SignalType.SELL:
            order_type = OrderType.SELL
        else:
            return False
        
        # Place order
        success, order = self.broker.place_order(
            order_type=order_type,
            volume=signal.position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            comment=signal.reason[:50]
        )
        
        if success and order:
            # Create position
            position = Position(
                entry_price=order.price,
                position_size=order.volume,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                signal_type=signal.signal_type
            )
            self.positions.append(position)
            
            # Send Telegram signal
            if self.trading_config.get('SEND_SIGNALS', False):
                trading_signal = TradingSignal(
                    signal_type=signal.signal_type.value,
                    symbol=self.trading_config.get('SYMBOL', 'XAUUSD'),
                    entry_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    position_size=order.volume,
                    confidence=signal.confidence,
                    reason=signal.reason,
                    timestamp=datetime.now()
                )
                await self.telegram_bot.send_signal(trading_signal)
            
            logger.info(f"Executed {signal.signal_type.value} at {order.price}")
            return True
        
        return False
    
    async def manage_positions(self, df: pd.DataFrame, current_price: float, atr: float):
        """Manage open positions with dynamic profit securing."""
        for position in self.positions[:]:
            # Check for exit signals
            should_close, reason = self.strategy.should_close_early(
                position, df, self.sentiment_analyzer.last_sentiment
            )
            
            if should_close:
                # Close position
                pnl = self._calculate_pnl(position, current_price)
                await self._close_position(position, current_price, reason, pnl)
                continue
            
            # Manage dynamic exits
            mgmt_signal = self.strategy.manage_position(position, current_price, atr)
            
            if mgmt_signal:
                if mgmt_signal.signal_type == SignalType.CLOSE_PARTIAL:
                    # Partial close
                    partial_size = position.position_size * mgmt_signal.partial_close_percent
                    pnl = self._calculate_pnl(position, current_price) * mgmt_signal.partial_close_percent
                    
                    # Update position
                    position.position_size -= partial_size
                    
                    logger.info(f"Partial close {mgmt_signal.partial_close_percent*100}% at profit")
                    await self.telegram_bot.send_alert(
                        "Partial Profit Secured",
                        f"Closed {mgmt_signal.partial_close_percent*100}% at +${pnl:.2f}",
                        "PROFIT"
                    )
                
                elif mgmt_signal.signal_type == SignalType.HOLD and mgmt_signal.trailing_stop:
                    # Update trailing stop
                    self.broker.modify_position(
                        position_id=id(position),
                        stop_loss=mgmt_signal.trailing_stop
                    )
    
    def _calculate_pnl(self, position: Position, current_price: float) -> float:
        """Calculate P&L for a position."""
        if position.signal_type == SignalType.BUY:
            pnl_pips = (current_price - position.entry_price) / 0.01
        else:
            pnl_pips = (position.entry_price - current_price) / 0.01
        
        # Approximate P&L (pip value ~$0.10 for 0.01 lot)
        pnl = pnl_pips * 0.10 * (position.position_size / 0.01)
        return pnl
    
    async def _close_position(self, position: Position, price: float, 
                             reason: str, pnl: float):
        """Close a position and record the result."""
        # Remove from active positions
        if position in self.positions:
            self.positions.remove(position)
        
        # Update stats
        self.daily_pnl += pnl
        self.daily_stats['trades'] += 1
        
        if pnl > 0:
            self.daily_stats['wins'] += 1
            self.daily_stats['profit'] += pnl
            alert_type = 'PROFIT'
        else:
            self.daily_stats['losses'] += 1
            self.daily_stats['profit'] += pnl
            alert_type = 'LOSS'
        
        # Update compounding
        self.compounding.update_capital(pnl, datetime.now().strftime('%Y-%m-%d'))
        
        # Send alert
        await self.telegram_bot.send_alert(
            f"Trade Closed: {reason}",
            f"P&L: ${pnl:+.2f}\nNew Balance: ${self.compounding.current_capital:.2f}",
            alert_type
        )
        
        logger.info(f"Position closed: {reason}, P&L: ${pnl:+.2f}")
    
    async def trading_loop(self):
        """Main trading loop."""
        logger.info("Starting trading loop...")
        self.running = True
        
        while self.running:
            try:
                # Load market data
                df = self.load_market_data()
                df = self.update_indicators(df)
                
                # Get current price and ATR
                last = df.iloc[-1]
                current_price = last['close']
                atr = last['atr']
                
                # Get ML prediction
                ml_pred = self.ml_predictor.predict(df, self.sentiment_analyzer.last_sentiment)
                
                # Detect market regime
                regime, regime_confidence = self.regime_detector.detect_regime(df)
                regime_modifiers = self.regime_detector.get_strategy_modifier()
                
                # Get sentiment
                # (In production, fetch real news here)
                
                # Check if we should trade
                can_trade, trade_reason = self.should_trade()
                
                # Manage existing positions
                await self.manage_positions(df, current_price, atr)
                
                # Check daily profit target
                daily_target = self.daily_start_balance * self.trading_config.get('DAILY_PROFIT_TARGET_PERCENT', 0.05)
                if self.daily_pnl >= daily_target:
                    logger.info(f"Daily profit target reached: ${self.daily_pnl:.2f}")
                    await self.telegram_bot.send_alert(
                        "Daily Target Hit! 🎯",
                        f"Profit: ${self.daily_pnl:.2f}\nStopping trading for today.",
                        "SUCCESS"
                    )
                    break
                
                # Look for new signals
                if can_trade and len(self.positions) < self.trading_config.get('MAX_OPEN_TRADES', 3):
                    # Apply regime modifiers
                    adjusted_confidence = ml_pred.confidence * regime_modifiers.get('entry_threshold', 1.0)
                    
                    # Generate signal
                    signal = self.strategy.generate_signal(
                        df=df,
                        account_balance=self.compounding.current_capital,
                        open_positions=self.positions,
                        sentiment=self.sentiment_analyzer.last_sentiment
                    )
                    
                    if signal and signal.confidence >= 0.45:
                        # Check ML agreement
                        if ml_pred.direction != 0:
                            signal_dir = 1 if signal.signal_type == SignalType.BUY else -1
                            if ml_pred.direction == signal_dir:
                                signal.confidence *= 1.1  # Boost confidence
                        
                        # Execute signal
                        await self.execute_signal(signal)
                
                # Sleep between iterations
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)
        
        logger.info("Trading loop ended")
    
    def run(self):
        """Run the trading engine synchronously."""
        async def main():
            await self.initialize()
            
            # Start Telegram bot
            if self.trading_config.get('TELEGRAM_ENABLED', False):
                await self.telegram_bot.start()
            
            # Run trading loop
            await self.trading_loop()
            
            # Send daily summary
            stats = {
                'daily_profit': self.daily_pnl,
                'trades': self.daily_stats['trades'],
                'wins': self.daily_stats['wins'],
                'losses': self.daily_stats['losses'],
                'win_rate': (self.daily_stats['wins'] / max(self.daily_stats['trades'], 1)) * 100,
                'balance': self.compounding.current_capital,
                'growth': ((self.compounding.current_capital - self.compounding.initial_capital) / 
                          self.compounding.initial_capital * 100)
            }
            await self.telegram_bot.send_daily_summary(stats)
            
            await self.shutdown()
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Stopped by user")


class Backtester:
    """
    Backtest engine for strategy validation.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {'TRADING_CONFIG': TRADING_CONFIG}
        self.trading_config = self.config.get('TRADING_CONFIG', TRADING_CONFIG)
        self.strategy = AggressiveSmallCapitalStrategy(self.config)
        
    def run_backtest(self, initial_capital: float = 50.0, 
                    days: int = 90) -> Dict:
        """
        Run backtest simulation.
        """
        logger.info(f"Running {days}-day backtest with ${initial_capital}...")
        
        # Generate synthetic data
        candles_per_day = 96  # 15-minute candles
        total_candles = days * candles_per_day
        
        # Generate realistic gold data
        np.random.seed(42)
        prices = []
        price = 2000.0
        
        for i in range(total_candles):
            # Trend component
            trend = np.sin(i / 200) * 0.5
            # Volatility
            vol = np.random.normal(0, 2)
            # Jump component (news events)
            jump = np.random.choice([0, 0, 0, 0, 0, -5, 5], 1)[0]
            
            price += trend + vol + jump
            price = max(1800, min(2200, price))
            prices.append(price)
        
        # Create DataFrame
        dates = pd.date_range(end=datetime.now(), periods=total_candles, freq='15min')
        df = pd.DataFrame({
            'open': prices,
            'close': prices,
            'high': [p + np.random.uniform(0.5, 3) for p in prices],
            'low': [p - np.random.uniform(0.5, 3) for p in prices],
            'volume': np.random.randint(100, 2000, total_candles)
        }, index=dates)
        
        # Calculate indicators
        df = self.strategy.calculate_indicators(df)
        
        # Simulate trading
        capital = initial_capital
        trades = []
        open_positions = []
        daily_pnl = {}
        
        atr_col = df['atr'].fillna(df['close'].diff().abs().rolling(14).mean())
        
        for i in range(50, len(df)):
            current_date = df.index[i].strftime('%Y-%m-%d')
            current_price = df['close'].iloc[i]
            atr = atr_col.iloc[i]
            
            if current_date not in daily_pnl:
                daily_pnl[current_date] = 0
            
            # Manage open positions
            for pos in open_positions[:]:
                # Check exit
                if pos['direction'] == 'BUY':
                    if current_price <= pos['sl']:
                        pnl = (pos['sl'] - pos['entry']) / 0.01 * 0.1 * pos['size']
                        capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({**pos, 'exit': pos['sl'], 'pnl': pnl, 'result': 'LOSS'})
                        open_positions.remove(pos)
                    elif current_price >= pos['tp']:
                        pnl = (pos['tp'] - pos['entry']) / 0.01 * 0.1 * pos['size']
                        capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({**pos, 'exit': pos['tp'], 'pnl': pnl, 'result': 'WIN'})
                        open_positions.remove(pos)
                    # Partial close at 50% profit
                    elif current_price >= pos['entry'] + (pos['tp'] - pos['entry']) * 0.5 and not pos.get('partial'):
                        partial_pnl = (current_price - pos['entry']) / 0.01 * 0.1 * pos['size'] * 0.5
                        capital += partial_pnl
                        daily_pnl[current_date] += partial_pnl
                        pos['partial'] = True
                        pos['size'] *= 0.5
                else:  # SELL
                    if current_price >= pos['sl']:
                        pnl = (pos['entry'] - pos['sl']) / 0.01 * 0.1 * pos['size']
                        capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({**pos, 'exit': pos['sl'], 'pnl': pnl, 'result': 'LOSS'})
                        open_positions.remove(pos)
                    elif current_price <= pos['tp']:
                        pnl = (pos['entry'] - pos['tp']) / 0.01 * 0.1 * pos['size']
                        capital += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({**pos, 'exit': pos['tp'], 'pnl': pnl, 'result': 'WIN'})
                        open_positions.remove(pos)
                    elif current_price <= pos['entry'] - (pos['entry'] - pos['tp']) * 0.5 and not pos.get('partial'):
                        partial_pnl = (pos['entry'] - current_price) / 0.01 * 0.1 * pos['size'] * 0.5
                        capital += partial_pnl
                        daily_pnl[current_date] += partial_pnl
                        pos['partial'] = True
                        pos['size'] *= 0.5
            
            # Check daily loss limit
            if daily_pnl[current_date] < -capital * 0.05:
                continue  # Skip trading
            
            # Generate signal
            if len(open_positions) < 3:
                signal = self.strategy.generate_signal(
                    df.iloc[:i+1], capital, open_positions
                )
                
                if signal and signal.confidence >= 0.45:
                    position = {
                        'entry': signal.entry_price,
                        'sl': signal.stop_loss,
                        'tp': signal.take_profit,
                        'size': signal.position_size,
                        'direction': signal.signal_type.value,
                        'time': df.index[i]
                    }
                    open_positions.append(position)
        
        # Calculate statistics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        total_profit = sum(t['pnl'] for t in trades)
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        # Daily statistics
        profitable_days = sum(1 for p in daily_pnl.values() if p > 0)
        total_days = len(daily_pnl)
        
        # Weekly compounding
        weekly_returns = []
        dates_sorted = sorted(daily_pnl.keys())
        for i in range(0, len(dates_sorted), 7):
            week_pnl = sum(daily_pnl.get(d, 0) for d in dates_sorted[i:i+7])
            weekly_returns.append(week_pnl)
        
        avg_weekly_return = np.mean(weekly_returns) if weekly_returns else 0
        
        results = {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_profit': total_profit,
            'growth_percent': (capital - initial_capital) / initial_capital * 100,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': (sum(t['pnl'] for t in winning_trades) / 
                            abs(sum(t['pnl'] for t in losing_trades))) if losing_trades else float('inf'),
            'total_days': total_days,
            'profitable_days': profitable_days,
            'daily_win_rate': profitable_days / total_days * 100 if total_days else 0,
            'avg_weekly_return': avg_weekly_return,
            'daily_pnl': daily_pnl,
            'trades': trades
        }
        
        return results


if __name__ == "__main__":
    # Run backtest
    backtester = Backtester()
    results = backtester.run_backtest(initial_capital=50.0, days=90)
    
    print("\n" + "="*60)
    print("BACKTEST RESULTS - Small Capital Aggressive Strategy")
    print("="*60)
    print(f"Initial Capital: ${results['initial_capital']:.2f}")
    print(f"Final Capital: ${results['final_capital']:.2f}")
    print(f"Total Profit: ${results['total_profit']:.2f}")
    print(f"Growth: {results['growth_percent']:.1f}%")
    print(f"\nTotal Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.1f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"\nDaily Win Rate: {results['daily_win_rate']:.1f}%")
    print(f"Avg Weekly Return: ${results['avg_weekly_return']:.2f}")
    print("="*60)
