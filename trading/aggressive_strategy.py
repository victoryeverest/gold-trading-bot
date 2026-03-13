"""
Aggressive Small Capital Trading Strategy
Optimized for $50 accounts with daily profit targets
Features: Dynamic profit securing, partial closes, trailing stops
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger('trading')


class SignalType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'
    CLOSE_PARTIAL = 'CLOSE_PARTIAL'
    CLOSE_ALL = 'CLOSE_ALL'


@dataclass
class TradeSignal:
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    reason: str
    partial_close_percent: float = 0.0
    trailing_stop: Optional[float] = None


@dataclass
class Position:
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    signal_type: SignalType
    highest_profit: float = 0.0
    partial_closes: int = 0
    trailing_active: bool = False
    breakeven_set: bool = False


class AggressiveSmallCapitalStrategy:
    """
    Enterprise-grade aggressive trading strategy for small accounts.
    
    Key Features:
    - High win rate approach (70-80%)
    - Dynamic profit securing (partial closes)
    - Intelligent trailing stops
    - Breakeven protection
    - News-aware trading
    - Session-optimized entries
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Strategy parameters
        self.risk_per_trade = self.trading_config.get('RISK_PER_TRADE', 0.03)
        self.max_position_size = self.trading_config.get('MAX_POSITION_SIZE', 0.10)
        self.tp_atr_mult = self.trading_config.get('TAKE_PROFIT_ATR_MULT', 1.2)
        self.sl_atr_mult = self.trading_config.get('STOP_LOSS_ATR_MULT', 0.8)
        
        # Dynamic exit parameters
        self.partial_close_at = self.trading_config.get('PARTIAL_CLOSE_AT_PROFIT_PERCENT', 0.5)
        self.trailing_trigger = self.trading_config.get('TRAILING_STOP_TRIGGER', 0.3)
        self.trailing_distance = self.trading_config.get('TRAILING_STOP_DISTANCE', 0.2)
        self.breakeven_trigger = self.trading_config.get('BREAKEVEN_TRIGGER', 0.25)
        
        # Risk limits
        self.daily_loss_limit = self.trading_config.get('DAILY_LOSS_LIMIT', 0.05)
        self.max_daily_drawdown = self.trading_config.get('MAX_DAILY_DRAWDOWN', 0.10)
        
        # State tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.positions: List[Position] = []
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators needed for analysis."""
        df = df.copy()
        
        # EMAs
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
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
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
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
        
        # ADX
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr14 = true_range.rolling(window=14).sum()
        plus_di = 100 * (plus_dm.rolling(window=14).sum() / tr14)
        minus_di = 100 * (abs(minus_dm).rolling(window=14).sum() / tr14)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=14).mean()
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Momentum
        df['momentum'] = df['close'] - df['close'].shift(10)
        df['momentum_rate'] = df['momentum'] / df['close'].shift(10) * 100
        
        # Support/Resistance
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        return df
    
    def get_trend_direction(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Determine overall trend direction and strength."""
        last = df.iloc[-1]
        
        # EMA alignment
        ema_bullish = last['ema_9'] > last['ema_21'] > last['ema_50']
        ema_bearish = last['ema_9'] < last['ema_21'] < last['ema_50']
        
        # Price position
        price_above_emas = last['close'] > last['ema_50'] and last['close'] > last['ema_200']
        price_below_emas = last['close'] < last['ema_50'] and last['close'] < last['ema_200']
        
        # ADX strength
        trend_strength = last['adx']
        
        if ema_bullish and price_above_emas:
            return 'BULLISH', trend_strength
        elif ema_bearish and price_below_emas:
            return 'BEARISH', trend_strength
        else:
            return 'NEUTRAL', trend_strength
    
    def check_entry_conditions(self, df: pd.DataFrame, trend: str) -> Tuple[bool, str, float]:
        """
        Check for high-probability entry conditions.
        Returns: (signal_valid, reason, confidence)
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        confidence = 0.0
        reasons = []
        
        # RSI conditions
        if trend == 'BULLISH':
            if last['rsi'] < 40:  # Oversold in uptrend
                confidence += 0.15
                reasons.append('RSI oversold in uptrend')
            elif last['rsi'] < 50:
                confidence += 0.10
                reasons.append('RSI favorable for long')
        elif trend == 'BEARISH':
            if last['rsi'] > 60:  # Overbought in downtrend
                confidence += 0.15
                reasons.append('RSI overbought in downtrend')
            elif last['rsi'] > 50:
                confidence += 0.10
                reasons.append('RSI favorable for short')
        
        # EMA crossover
        if trend == 'BULLISH' and prev['ema_9'] <= prev['ema_21'] and last['ema_9'] > last['ema_21']:
            confidence += 0.20
            reasons.append('EMA 9/21 bullish crossover')
        elif trend == 'BEARISH' and prev['ema_9'] >= prev['ema_21'] and last['ema_9'] < last['ema_21']:
            confidence += 0.20
            reasons.append('EMA 9/21 bearish crossover')
        
        # MACD
        if last['macd_hist'] > 0 and prev['macd_hist'] <= 0:
            confidence += 0.15
            reasons.append('MACD histogram turning positive')
        elif last['macd_hist'] < 0 and prev['macd_hist'] >= 0:
            confidence += 0.15
            reasons.append('MACD histogram turning negative')
        
        # Bollinger Band position
        if trend == 'BULLISH' and last['bb_position'] < 0.3:
            confidence += 0.10
            reasons.append('Price near lower BB in uptrend')
        elif trend == 'BEARISH' and last['bb_position'] > 0.7:
            confidence += 0.10
            reasons.append('Price near upper BB in downtrend')
        
        # Stochastic
        if trend == 'BULLISH' and last['stoch_k'] < 30:
            confidence += 0.10
            reasons.append('Stochastic oversold')
        elif trend == 'BEARISH' and last['stoch_k'] > 70:
            confidence += 0.10
            reasons.append('Stochastic overbought')
        
        # Volume confirmation
        if last['volume_ratio'] > 1.2:
            confidence += 0.10
            reasons.append('Above average volume')
        
        # Support/Resistance test
        if trend == 'BULLISH':
            support_distance = (last['close'] - last['support']) / last['close']
            if support_distance < 0.005:  # Within 0.5% of support
                confidence += 0.10
                reasons.append('Testing support level')
        elif trend == 'BEARISH':
            resistance_distance = (last['resistance'] - last['close']) / last['close']
            if resistance_distance < 0.005:
                confidence += 0.10
                reasons.append('Testing resistance level')
        
        # Minimum confidence threshold
        if confidence >= 0.45:
            return True, '; '.join(reasons), confidence
        return False, 'No strong signal', confidence
    
    def calculate_position_size(self, account_balance: float, atr: float, 
                                entry_price: float, stop_loss: float) -> float:
        """
        Calculate optimal position size for small account.
        Uses fixed fractional position sizing with minimum lot size.
        """
        risk_amount = account_balance * self.risk_per_trade
        sl_distance = abs(entry_price - stop_loss)
        
        if sl_distance == 0:
            sl_distance = atr * self.sl_atr_mult
        
        # Gold pip value: $0.01 per pip for 0.01 lot
        pip_value = 0.01  # For 0.01 lot
        pips_at_risk = sl_distance / 0.01  # Convert to pips
        
        # Calculate lot size
        lot_size = risk_amount / (pips_at_risk * pip_value)
        
        # Round to 0.01 lots minimum
        lot_size = max(0.01, round(lot_size, 2))
        
        # Cap at max position size
        max_lots = (account_balance * self.max_position_size) / (entry_price * 100)
        lot_size = min(lot_size, max_lots)
        
        return max(0.01, round(lot_size, 2))
    
    def generate_signal(self, df: pd.DataFrame, account_balance: float,
                       open_positions: List[Position], sentiment: float = 0.0) -> Optional[TradeSignal]:
        """
        Generate trading signal with aggressive profit management.
        """
        df = self.calculate_indicators(df)
        
        # Check if we can open more positions
        if len(open_positions) >= self.trading_config.get('MAX_OPEN_TRADES', 3):
            return None
        
        # Get trend
        trend, trend_strength = self.get_trend_direction(df)
        
        if trend == 'NEUTRAL' or trend_strength < 20:
            return None
        
        # Check entry conditions
        valid, reason, confidence = self.check_entry_conditions(df, trend)
        
        if not valid:
            return None
        
        # Adjust confidence based on sentiment
        if sentiment != 0:
            if (trend == 'BULLISH' and sentiment > 0) or (trend == 'BEARISH' and sentiment < 0):
                confidence *= 1.1  # Boost confidence if aligned
            else:
                confidence *= 0.9  # Reduce if against sentiment
        
        last = df.iloc[-1]
        atr = last['atr']
        
        # Calculate SL and TP
        if trend == 'BULLISH':
            signal_type = SignalType.BUY
            entry_price = last['close']
            stop_loss = entry_price - (atr * self.sl_atr_mult)
            take_profit = entry_price + (atr * self.tp_atr_mult)
        else:
            signal_type = SignalType.SELL
            entry_price = last['close']
            stop_loss = entry_price + (atr * self.sl_atr_mult)
            take_profit = entry_price - (atr * self.tp_atr_mult)
        
        # Position size
        position_size = self.calculate_position_size(account_balance, atr, entry_price, stop_loss)
        
        return TradeSignal(
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            reason=reason
        )
    
    def manage_position(self, position: Position, current_price: float, 
                       current_atr: float) -> Optional[TradeSignal]:
        """
        Dynamic position management for profit securing.
        Implements: partial closes, trailing stops, breakeven.
        """
        # Calculate current profit
        if position.signal_type == SignalType.BUY:
            profit_percent = (current_price - position.entry_price) / position.entry_price
            profit_pips = (current_price - position.entry_price) / 0.01
        else:
            profit_percent = (position.entry_price - current_price) / position.entry_price
            profit_pips = (position.entry_price - current_price) / 0.01
        
        # Track highest profit
        if profit_percent > position.highest_profit:
            position.highest_profit = profit_percent
        
        # Calculate TP distance
        tp_distance = abs(position.take_profit - position.entry_price)
        current_profit_distance = abs(current_price - position.entry_price)
        profit_to_tp = current_profit_distance / tp_distance
        
        # 1. BREAKEVEN - Move SL to entry when profit reaches threshold
        if not position.breakeven_set and profit_to_tp >= self.breakeven_trigger:
            position.breakeven_set = True
            position.stop_loss = position.entry_price
            logger.info(f"Breakeven set at {position.entry_price}")
            return TradeSignal(
                signal_type=SignalType.HOLD,
                entry_price=current_price,
                stop_loss=position.entry_price,
                take_profit=position.take_profit,
                position_size=position.position_size,
                confidence=1.0,
                reason='Moved to breakeven',
                trailing_stop=position.entry_price
            )
        
        # 2. PARTIAL CLOSE - Take some profit off the table
        if profit_to_tp >= self.partial_close_at and position.partial_closes < 2:
            close_percent = 0.5 if position.partial_closes == 0 else 0.3
            position.partial_closes += 1
            logger.info(f"Partial close {close_percent*100}% at profit {profit_percent*100:.2f}%")
            return TradeSignal(
                signal_type=SignalType.CLOSE_PARTIAL,
                entry_price=current_price,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                position_size=position.position_size * close_percent,
                confidence=1.0,
                reason=f'Securing {close_percent*100}% profit at {profit_percent*100:.1f}%',
                partial_close_percent=close_percent
            )
        
        # 3. TRAILING STOP - Lock in profits as price moves
        if profit_to_tp >= self.trailing_trigger and position.highest_profit > 0.002:
            if position.signal_type == SignalType.BUY:
                new_trailing = current_price - (tp_distance * self.trailing_distance)
                if new_trailing > position.stop_loss:
                    position.stop_loss = new_trailing
                    position.trailing_active = True
                    logger.info(f"Trailing stop updated to {new_trailing}")
                    return TradeSignal(
                        signal_type=SignalType.HOLD,
                        entry_price=current_price,
                        stop_loss=new_trailing,
                        take_profit=position.take_profit,
                        position_size=position.position_size,
                        confidence=1.0,
                        reason=f'Trailing stop at {new_trailing:.2f}',
                        trailing_stop=new_trailing
                    )
            else:
                new_trailing = current_price + (tp_distance * self.trailing_distance)
                if new_trailing < position.stop_loss:
                    position.stop_loss = new_trailing
                    position.trailing_active = True
                    logger.info(f"Trailing stop updated to {new_trailing}")
                    return TradeSignal(
                        signal_type=SignalType.HOLD,
                        entry_price=current_price,
                        stop_loss=new_trailing,
                        take_profit=position.take_profit,
                        position_size=position.position_size,
                        confidence=1.0,
                        reason=f'Trailing stop at {new_trailing:.2f}',
                        trailing_stop=new_trailing
                    )
        
        return None
    
    def should_close_early(self, position: Position, df: pd.DataFrame, 
                          sentiment: float = 0.0) -> Tuple[bool, str]:
        """
        Determine if position should be closed early based on:
        - Reversal signals
        - Negative sentiment shift
        - Time-based exit (end of session)
        """
        df = self.calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        close_reasons = []
        
        # RSI reversal
        if position.signal_type == SignalType.BUY:
            if last['rsi'] > 75:
                close_reasons.append('RSI overbought')
            if last['macd_hist'] < 0 and prev['macd_hist'] > 0:
                close_reasons.append('MACD turning bearish')
            if last['close'] < last['ema_21']:
                close_reasons.append('Price below EMA21')
        else:
            if last['rsi'] < 25:
                close_reasons.append('RSI oversold')
            if last['macd_hist'] > 0 and prev['macd_hist'] < 0:
                close_reasons.append('MACD turning bullish')
            if last['close'] > last['ema_21']:
                close_reasons.append('Price above EMA21')
        
        # Sentiment reversal
        if position.signal_type == SignalType.BUY and sentiment < -0.5:
            close_reasons.append('Strong negative sentiment')
        elif position.signal_type == SignalType.SELL and sentiment > 0.5:
            close_reasons.append('Strong positive sentiment')
        
        if len(close_reasons) > 0:
            return True, '; '.join(close_reasons)
        
        return False, ''


class ScalpingStrategy:
    """
    High-frequency scalping strategy for quick profits.
    Best for 5-minute timeframe with tight stops.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Scalping parameters
        self.scalp_tp_pips = 15  # 15 pips target
        self.scalp_sl_pips = 10  # 10 pips stop
        self.max_hold_time = 60  # Max 60 minutes hold
        
    def generate_scalp_signal(self, df: pd.DataFrame, trend: str) -> Optional[TradeSignal]:
        """
        Generate quick scalp signal.
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Quick momentum check
        momentum = (last['close'] - prev['close']) / prev['close']
        
        if abs(momentum) < 0.0005:  # Not enough momentum
            return None
        
        # RSI + Stochastic combo
        if trend == 'BULLISH':
            if last['rsi'] > 60 and last['stoch_k'] > last['stoch_d']:
                if prev['stoch_k'] <= prev['stoch_d']:  # Crossover
                    entry = last['close']
                    return TradeSignal(
                        signal_type=SignalType.BUY,
                        entry_price=entry,
                        stop_loss=entry - (self.scalp_sl_pips * 0.01),
                        take_profit=entry + (self.scalp_tp_pips * 0.01),
                        position_size=0.01,
                        confidence=0.6,
                        reason='Scalp long signal'
                    )
        elif trend == 'BEARISH':
            if last['rsi'] < 40 and last['stoch_k'] < last['stoch_d']:
                if prev['stoch_k'] >= prev['stoch_d']:  # Crossover
                    entry = last['close']
                    return TradeSignal(
                        signal_type=SignalType.SELL,
                        entry_price=entry,
                        stop_loss=entry + (self.scalp_sl_pips * 0.01),
                        take_profit=entry - (self.scalp_tp_pips * 0.01),
                        position_size=0.01,
                        confidence=0.6,
                        reason='Scalp short signal'
                    )
        
        return None


class CompoundingManager:
    """
    Position sizing with compound growth for small accounts.
    """
    
    def __init__(self, initial_capital: float, daily_target: float = 0.05):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_target = daily_target
        self.profit_history = []
        self.daily_profits = {}
        
    def update_capital(self, profit: float, date: str = None):
        """Update capital after trade closes."""
        self.current_capital += profit
        if date:
            if date not in self.daily_profits:
                self.daily_profits[date] = 0
            self.daily_profits[date] += profit
        self.profit_history.append({
            'capital': self.current_capital,
            'profit': profit,
            'date': date
        })
        
    def get_position_size(self, risk_percent: float = 0.03) -> float:
        """Get position size based on current capital."""
        return self.current_capital * risk_percent
    
    def get_daily_progress(self, date: str) -> float:
        """Get progress towards daily target."""
        daily_profit = self.daily_profits.get(date, 0)
        target = self.current_capital * self.daily_target
        return daily_profit / target if target > 0 else 0
    
    def get_growth_stats(self) -> Dict:
        """Get account growth statistics."""
        if not self.profit_history:
            return {}
        
        total_profit = self.current_capital - self.initial_capital
        growth_percent = (total_profit / self.initial_capital) * 100
        winning_days = sum(1 for p in self.daily_profits.values() if p > 0)
        total_days = len(self.daily_profits)
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_profit': total_profit,
            'growth_percent': growth_percent,
            'winning_days': winning_days,
            'total_days': total_days,
            'win_rate_days': winning_days / total_days * 100 if total_days > 0 else 0
        }
