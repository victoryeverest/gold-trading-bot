"""
Ultra Aggressive Small Capital Strategy
Optimized for maximum daily profits with $50 accounts
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


class UltraAggressiveStrategy:
    """
    Ultra-aggressive strategy optimized for small accounts.
    Focus on high win rate with quick profit taking.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Aggressive parameters for small accounts
        self.risk_per_trade = 0.05  # 5% risk (more aggressive)
        
        # Tight stops, close targets for HIGH WIN RATE
        self.tp_atr_mult = 0.6  # Close TP = wins often
        self.sl_atr_mult = 1.5  # Far SL = rarely hit
        
        # Dynamic exit parameters
        self.partial_close_at = 0.4  # Close 50% at 40% of TP
        self.trailing_trigger = 0.25  # Start trailing at 25% profit
        self.breakeven_trigger = 0.2  # Move to breakeven at 20% profit
        
        # State tracking
        self.positions: List[Position] = []
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        df = df.copy()
        
        # EMAs
        for period in [5, 9, 13, 21, 50, 100, 200]:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI with multiple periods
        for period in [7, 14, 21]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_7'] = true_range.rolling(window=7).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
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
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Momentum
        df['momentum'] = df['close'] - df['close'].shift(10)
        df['roc'] = df['momentum'] / df['close'].shift(10) * 100
        
        # Price patterns
        df['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
        df['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
        
        # Support/Resistance
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        # Trend strength
        df['trend_strength'] = (df['ema_9'] - df['ema_21']) / df['ema_21'] * 100
        
        return df
    
    def get_trend_direction(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Determine trend direction with confidence."""
        last = df.iloc[-1]
        
        # Strong bullish
        if (last['ema_9'] > last['ema_21'] > last['ema_50'] and 
            last['close'] > last['ema_9']):
            return 'BULLISH', 0.8
        
        # Moderate bullish
        if last['ema_9'] > last['ema_21'] and last['close'] > last['ema_21']:
            return 'BULLISH', 0.6
        
        # Strong bearish
        if (last['ema_9'] < last['ema_21'] < last['ema_50'] and 
            last['close'] < last['ema_9']):
            return 'BEARISH', 0.8
        
        # Moderate bearish
        if last['ema_9'] < last['ema_21'] and last['close'] < last['ema_21']:
            return 'BEARISH', 0.6
        
        return 'NEUTRAL', 0.3
    
    def check_entry_conditions(self, df: pd.DataFrame, trend: str) -> Tuple[bool, str, float]:
        """Check for high-probability entry with multiple confirmations."""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0.0
        reasons = []
        
        if trend == 'BULLISH':
            # RSI conditions
            if last['rsi_14'] < 35:
                score += 0.25
                reasons.append('RSI oversold')
            elif last['rsi_14'] < 45:
                score += 0.15
                reasons.append('RSI favorable')
            
            # Stochastic oversold
            if last['stoch_k'] < 25 and last['stoch_k'] > prev['stoch_k']:
                score += 0.20
                reasons.append('Stoch turning up from oversold')
            
            # MACD bullish
            if last['macd_hist'] > 0 and prev['macd_hist'] <= 0:
                score += 0.20
                reasons.append('MACD histogram positive')
            elif last['macd'] > last['macd_signal']:
                score += 0.10
                reasons.append('MACD bullish')
            
            # Near support
            support_dist = (last['close'] - last['support']) / last['close']
            if support_dist < 0.003:
                score += 0.15
                reasons.append('Near support')
            
            # BB lower band
            if last['bb_position'] < 0.2:
                score += 0.15
                reasons.append('Near lower BB')
            
            # EMA bounce
            if last['low'] <= last['ema_21'] and last['close'] > last['ema_21']:
                score += 0.15
                reasons.append('EMA21 bounce')
            
        elif trend == 'BEARISH':
            # RSI conditions
            if last['rsi_14'] > 65:
                score += 0.25
                reasons.append('RSI overbought')
            elif last['rsi_14'] > 55:
                score += 0.15
                reasons.append('RSI favorable')
            
            # Stochastic overbought
            if last['stoch_k'] > 75 and last['stoch_k'] < prev['stoch_k']:
                score += 0.20
                reasons.append('Stoch turning down from overbought')
            
            # MACD bearish
            if last['macd_hist'] < 0 and prev['macd_hist'] >= 0:
                score += 0.20
                reasons.append('MACD histogram negative')
            elif last['macd'] < last['macd_signal']:
                score += 0.10
                reasons.append('MACD bearish')
            
            # Near resistance
            resist_dist = (last['resistance'] - last['close']) / last['close']
            if resist_dist < 0.003:
                score += 0.15
                reasons.append('Near resistance')
            
            # BB upper band
            if last['bb_position'] > 0.8:
                score += 0.15
                reasons.append('Near upper BB')
            
            # EMA rejection
            if last['high'] >= last['ema_21'] and last['close'] < last['ema_21']:
                score += 0.15
                reasons.append('EMA21 rejection')
        
        # Volume confirmation
        if last['volume_ratio'] > 1.2:
            score += 0.10
            reasons.append('Above average volume')
        
        # Minimum threshold for trade
        if score >= 0.50:
            return True, '; '.join(reasons[:3]), min(score, 1.0)
        
        return False, 'No strong signal', score
    
    def generate_signal(self, df: pd.DataFrame, account_balance: float,
                       open_positions: List[Position], sentiment: float = 0.0) -> Optional[TradeSignal]:
        """Generate trading signal optimized for high win rate."""
        df = self.calculate_indicators(df)
        
        # Limit positions
        if len(open_positions) >= 2:
            return None
        
        # Get trend
        trend, trend_confidence = self.get_trend_direction(df)
        
        if trend == 'NEUTRAL':
            return None
        
        # Check entry
        valid, reason, confidence = self.check_entry_conditions(df, trend)
        
        if not valid:
            return None
        
        last = df.iloc[-1]
        atr = last['atr']
        
        # Calculate SL and TP for HIGH WIN RATE
        # TP close = wins often, SL far = rarely hit
        if trend == 'BULLISH':
            signal_type = SignalType.BUY
            entry_price = last['close']
            stop_loss = entry_price - (atr * self.sl_atr_mult)  # Far stop
            take_profit = entry_price + (atr * self.tp_atr_mult)  # Close target
        else:
            signal_type = SignalType.SELL
            entry_price = last['close']
            stop_loss = entry_price + (atr * self.sl_atr_mult)
            take_profit = entry_price - (atr * self.tp_atr_mult)
        
        # Position sizing
        risk_amount = account_balance * self.risk_per_trade
        sl_distance = abs(entry_price - stop_loss)
        pips_at_risk = sl_distance / 0.01
        pip_value = 0.01  # For 0.01 lot
        position_size = risk_amount / (pips_at_risk * pip_value)
        position_size = max(0.01, round(position_size, 2))
        
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
        """Dynamic position management for profit securing."""
        # Calculate profit
        if position.signal_type == SignalType.BUY:
            profit_percent = (current_price - position.entry_price) / position.entry_price
        else:
            profit_percent = (position.entry_price - current_price) / position.entry_price
        
        # Track highest profit
        if profit_percent > position.highest_profit:
            position.highest_profit = profit_percent
        
        # TP distance
        tp_distance = abs(position.take_profit - position.entry_price)
        current_profit_distance = abs(current_price - position.entry_price)
        profit_to_tp = current_profit_distance / tp_distance
        
        # 1. BREAKEVEN - very early (20% of TP)
        if not position.breakeven_set and profit_to_tp >= self.breakeven_trigger:
            position.breakeven_set = True
            position.stop_loss = position.entry_price
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
        
        # 2. PARTIAL CLOSE - take profits early (40% of TP)
        if profit_to_tp >= self.partial_close_at and position.partial_closes == 0:
            position.partial_closes = 1
            return TradeSignal(
                signal_type=SignalType.CLOSE_PARTIAL,
                entry_price=current_price,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                position_size=position.position_size * 0.5,
                confidence=1.0,
                reason=f'Securing 50% profit',
                partial_close_percent=0.5
            )
        
        # 3. TRAILING STOP
        if profit_to_tp >= self.trailing_trigger:
            trail_distance = tp_distance * 0.15  # Tight trail
            
            if position.signal_type == SignalType.BUY:
                new_trailing = current_price - trail_distance
                if new_trailing > position.stop_loss:
                    position.stop_loss = new_trailing
                    return TradeSignal(
                        signal_type=SignalType.HOLD,
                        entry_price=current_price,
                        stop_loss=new_trailing,
                        take_profit=position.take_profit,
                        position_size=position.position_size,
                        confidence=1.0,
                        reason='Trailing stop',
                        trailing_stop=new_trailing
                    )
            else:
                new_trailing = current_price + trail_distance
                if new_trailing < position.stop_loss:
                    position.stop_loss = new_trailing
                    return TradeSignal(
                        signal_type=SignalType.HOLD,
                        entry_price=current_price,
                        stop_loss=new_trailing,
                        take_profit=position.take_profit,
                        position_size=position.position_size,
                        confidence=1.0,
                        reason='Trailing stop',
                        trailing_stop=new_trailing
                    )
        
        return None


class CompoundingManager:
    """Position sizing with aggressive compounding."""
    
    def __init__(self, initial_capital: float, daily_target: float = 0.10):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_target = daily_target
        self.profit_history = []
        self.daily_profits = {}
        
    def update_capital(self, profit: float, date: str = None):
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
