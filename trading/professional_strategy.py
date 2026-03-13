"""
Professional Trading Strategy with Market Structure Awareness
Integrates: Volatility Regimes, Liquidity Sweeps, Session Optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from .market_structure import (
    MarketStructureAnalyzer, MarketStructure, VolatilityRegime,
    TradingSession, LiquidityEvent
)

logger = logging.getLogger('trading')


@dataclass
class ProfessionalSignal:
    """Professional trading signal with market structure context."""
    direction: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    reason: str
    
    # Market structure context
    volatility_regime: str
    session: str
    strategy_type: str  # TREND_FOLLOW, MEAN_REVERSION, SWEEP_REVERSAL
    sweep_probability: float
    risk_reward_ratio: float


class ProfessionalTradingStrategy:
    """
    Professional-grade trading strategy with market structure awareness.
    
    Key Features:
    1. Adapts to volatility regimes (low, normal, high, extreme)
    2. Detects and trades liquidity sweeps
    3. Optimizes for trading sessions
    4. Dynamic risk management
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Base parameters
        self.base_risk = self.trading_config.get('RISK_PER_TRADE', 0.02)
        self.base_tp_pips = self.trading_config.get('TAKE_PROFIT_PIPS', 12)
        self.base_sl_pips = self.trading_config.get('STOP_LOSS_PIPS', 10)
        self.pip_value = 10.0  # $10 per pip per lot for gold
        
        # Market structure analyzer
        self.structure_analyzer = MarketStructureAnalyzer()
        
        # Session preferences
        self.session_weights = {
            TradingSession.ASIAN: 0.6,      # Lower weight - choppy
            TradingSession.LONDON: 1.0,     # Full weight - trending
            TradingSession.NEW_YORK: 0.9,   # Good but volatile
            TradingSession.OVERLAP: 1.2     # Best - high liquidity
        }
        
        # Strategy performance tracking
        self.session_stats = {s.value: {'trades': 0, 'wins': 0} for s in TradingSession}
        self.regime_stats = {r.value: {'trades': 0, 'wins': 0} for r in VolatilityRegime}
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        df = df.copy()
        
        # EMAs
        for period in [9, 21, 50, 100, 200]:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Stochastic
        low_min = df['low'].rolling(14).min()
        high_max = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min).replace(0, 0.001))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']).replace(0, 0.001)
        
        # Volume
        df['vol_sma'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_sma'].replace(0, 1)
        
        return df
    
    def generate_signal(self, df: pd.DataFrame, account_balance: float,
                       open_positions: int = 0) -> Optional[ProfessionalSignal]:
        """
        Generate professional trading signal with market structure awareness.
        """
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        if len(df) < 100:
            return None
        
        # Analyze market structure
        structure = self.structure_analyzer.analyze(df)
        
        # Check if we should trade
        should_trade, reason = self.structure_analyzer.should_trade(df)
        if not should_trade:
            logger.debug(f"No trade: {reason}")
            return None
        
        # Check max positions
        if open_positions >= self.trading_config.get('MAX_OPEN_TRADES', 2):
            return None
        
        # Get entry parameters based on market structure
        params = self.structure_analyzer.get_entry_parameters(df)
        
        # Generate signal based on strategy type
        signal = self._generate_strategy_signal(df, structure, params, account_balance)
        
        return signal
    
    def _generate_strategy_signal(self, df: pd.DataFrame, structure: MarketStructure,
                                  params: Dict, balance: float) -> Optional[ProfessionalSignal]:
        """Generate signal based on current strategy recommendation."""
        
        strategy = params['strategy']
        trend = params['trend_direction']
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0.0
        reasons = []
        
        if strategy == 'SWEEP_REVERSAL':
            # Liquidity sweep detected - trade the reversal
            signal, confidence, reasons = self._sweep_reversal_signal(df, structure)
            
        elif strategy == 'MEAN_REVERSION':
            # Low volatility - range trading
            signal, confidence, reasons = self._mean_reversion_signal(df, structure)
            
        elif strategy == 'TREND_FOLLOW':
            # Normal/high volatility - trend following
            signal, confidence, reasons = self._trend_follow_signal(df, structure)
        
        elif strategy == 'SCALPING':
            # Overlap session - quick scalps
            signal, confidence, reasons = self._scalping_signal(df, structure)
        
        if signal is None or confidence < 0.45:
            return None
        
        # Adjust parameters based on market structure
        entry_price = last['close']
        atr = last['atr']
        
        # Calculate stop loss and take profit
        sl_distance = atr * params['stop_loss_modifier'] * 0.8  # ATR-based
        tp_distance = atr * params['take_profit_modifier'] * 1.2
        
        if signal == 'BUY':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Calculate position size
        position_size = self._calculate_position_size(
            balance, entry_price, stop_loss, params['position_size_modifier']
        )
        
        # Risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Session weight adjustment
        session_weight = self.session_weights.get(structure.session, 1.0)
        confidence *= session_weight
        
        return ProfessionalSignal(
            direction=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            reason='; '.join(reasons),
            volatility_regime=structure.volatility_regime.value,
            session=structure.session.value,
            strategy_type=strategy,
            sweep_probability=structure.sweep_probability,
            risk_reward_ratio=round(rr_ratio, 2)
        )
    
    def _sweep_reversal_signal(self, df: pd.DataFrame, 
                               structure: MarketStructure) -> Tuple[Optional[str], float, List[str]]:
        """
        Liquidity sweep reversal strategy.
        When price sweeps above resistance or below support, look for reversal.
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0.0
        reasons = []
        
        if structure.liquidity_event == LiquidityEvent.SWEEP_HIGH:
            # Price swept above resistance - look for bearish reversal
            if last['close'] < last['open']:  # Bearish candle after sweep
                confidence = 0.7
                signal = 'SELL'
                reasons.append('Bearish rejection after liquidity sweep')
                
            if last['rsi'] > 70:
                confidence += 0.15
                reasons.append('RSI overbought')
                
            if last['stoch_k'] > 80 and last['stoch_k'] < prev['stoch_k']:
                confidence += 0.1
                reasons.append('Stochastic turning down from overbought')
                
        elif structure.liquidity_event == LiquidityEvent.SWEEP_LOW:
            # Price swept below support - look for bullish reversal
            if last['close'] > last['open']:  # Bullish candle after sweep
                confidence = 0.7
                signal = 'BUY'
                reasons.append('Bullish rejection after liquidity sweep')
                
            if last['rsi'] < 30:
                confidence += 0.15
                reasons.append('RSI oversold')
                
            if last['stoch_k'] < 20 and last['stoch_k'] > prev['stoch_k']:
                confidence += 0.1
                reasons.append('Stochastic turning up from oversold')
        
        return signal, confidence, reasons
    
    def _mean_reversion_signal(self, df: pd.DataFrame,
                               structure: MarketStructure) -> Tuple[Optional[str], float, List[str]]:
        """
        Mean reversion strategy for low volatility ranging markets.
        Buy at lower BB, sell at upper BB.
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0.0
        reasons = []
        
        # Price near lower Bollinger Band
        if last['bb_pos'] < 0.2:
            signal = 'BUY'
            confidence = 0.5
            reasons.append('Price near lower Bollinger Band')
            
            if last['rsi'] < 35:
                confidence += 0.15
                reasons.append('RSI oversold')
            
            if last['stoch_k'] < 25:
                confidence += 0.1
                reasons.append('Stochastic oversold')
                
            if last['close'] > last['open']:
                confidence += 0.1
                reasons.append('Bullish candle')
        
        # Price near upper Bollinger Band
        elif last['bb_pos'] > 0.8:
            signal = 'SELL'
            confidence = 0.5
            reasons.append('Price near upper Bollinger Band')
            
            if last['rsi'] > 65:
                confidence += 0.15
                reasons.append('RSI overbought')
            
            if last['stoch_k'] > 75:
                confidence += 0.1
                reasons.append('Stochastic overbought')
                
            if last['close'] < last['open']:
                confidence += 0.1
                reasons.append('Bearish candle')
        
        return signal, confidence, reasons
    
    def _trend_follow_signal(self, df: pd.DataFrame,
                            structure: MarketStructure) -> Tuple[Optional[str], float, List[str]]:
        """
        Trend following strategy for normal/high volatility.
        Trade in direction of trend on pullbacks.
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0.0
        reasons = []
        
        trend = structure.trend_direction
        
        if trend == 'BULLISH':
            # Look for pullback entries
            if last['ema_9'] > last['ema_21'] > last['ema_50']:
                confidence = 0.4
                reasons.append('EMA bullish alignment')
                
                # Pullback to EMA21
                ema21_dist = abs(last['close'] - last['ema_21']) / last['close']
                if ema21_dist < 0.002:
                    confidence += 0.2
                    reasons.append('Pullback to EMA21')
                
                if last['rsi'] < 50:
                    confidence += 0.15
                    reasons.append('RSI favorable for long')
                
                if last['stoch_k'] < 40:
                    confidence += 0.1
                    reasons.append('Stochastic low in uptrend')
                
                if last['macd_hist'] > prev['macd_hist']:
                    confidence += 0.1
                    reasons.append('MACD histogram rising')
                
                if confidence >= 0.6:
                    signal = 'BUY'
                    
        elif trend == 'BEARISH':
            if last['ema_9'] < last['ema_21'] < last['ema_50']:
                confidence = 0.4
                reasons.append('EMA bearish alignment')
                
                ema21_dist = abs(last['close'] - last['ema_21']) / last['close']
                if ema21_dist < 0.002:
                    confidence += 0.2
                    reasons.append('Pullback to EMA21')
                
                if last['rsi'] > 50:
                    confidence += 0.15
                    reasons.append('RSI favorable for short')
                
                if last['stoch_k'] > 60:
                    confidence += 0.1
                    reasons.append('Stochastic high in downtrend')
                
                if last['macd_hist'] < prev['macd_hist']:
                    confidence += 0.1
                    reasons.append('MACD histogram falling')
                
                if confidence >= 0.6:
                    signal = 'SELL'
        
        return signal, confidence, reasons
    
    def _scalping_signal(self, df: pd.DataFrame,
                        structure: MarketStructure) -> Tuple[Optional[str], float, List[str]]:
        """
        Quick scalping strategy for high liquidity overlap session.
        Faster entries with tighter stops.
        """
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0.0
        reasons = []
        
        # Quick momentum check
        momentum = (last['close'] - prev['close']) / prev['close']
        
        if abs(momentum) < 0.0003:
            return None, 0, []
        
        # EMA cross check
        ema_cross_up = prev['ema_9'] <= prev['ema_21'] and last['ema_9'] > last['ema_21']
        ema_cross_down = prev['ema_9'] >= prev['ema_21'] and last['ema_9'] < last['ema_21']
        
        if ema_cross_up and last['rsi'] < 60:
            signal = 'BUY'
            confidence = 0.6
            reasons.append('EMA 9/21 bullish cross')
            
        elif ema_cross_down and last['rsi'] > 40:
            signal = 'SELL'
            confidence = 0.6
            reasons.append('EMA 9/21 bearish cross')
        
        # Volume confirmation
        if last['vol_ratio'] > 1.3:
            confidence += 0.1
            reasons.append('Volume spike')
        
        return signal, confidence, reasons
    
    def _calculate_position_size(self, balance: float, entry: float, 
                                 stop_loss: float, modifier: float) -> float:
        """Calculate position size based on risk and market structure."""
        risk_amount = balance * self.base_risk * modifier
        sl_distance = abs(entry - stop_loss)
        
        if sl_distance == 0:
            return 0.01
        
        # For gold: pip value = $10 per lot per pip
        pips_at_risk = sl_distance / 0.01
        lot_size = risk_amount / (pips_at_risk * self.pip_value * 0.01)
        
        # Round to valid lot size
        lot_size = max(0.01, min(round(lot_size, 2), self._get_max_lot(balance)))
        
        return lot_size
    
    def _get_max_lot(self, balance: float) -> float:
        """Get maximum lot size based on account balance."""
        if balance < 100:
            return 0.05
        elif balance < 500:
            return 0.1
        elif balance < 1000:
            return 0.5
        elif balance < 5000:
            return 1.0
        elif balance < 10000:
            return 2.0
        elif balance < 50000:
            return 5.0
        elif balance < 100000:
            return 10.0
        elif balance < 500000:
            return 20.0
        elif balance < 1000000:
            return 50.0
        else:
            return 100.0
    
    def update_stats(self, session: str, regime: str, won: bool):
        """Update strategy performance statistics."""
        self.session_stats[session]['trades'] += 1
        if won:
            self.session_stats[session]['wins'] += 1
        
        self.regime_stats[regime]['trades'] += 1
        if won:
            self.regime_stats[regime]['wins'] += 1
    
    def get_performance_report(self) -> Dict:
        """Get strategy performance by session and regime."""
        report = {
            'by_session': {},
            'by_regime': {}
        }
        
        for session, stats in self.session_stats.items():
            if stats['trades'] > 0:
                report['by_session'][session] = {
                    'trades': stats['trades'],
                    'wins': stats['wins'],
                    'win_rate': stats['wins'] / stats['trades'] * 100
                }
        
        for regime, stats in self.regime_stats.items():
            if stats['trades'] > 0:
                report['by_regime'][regime] = {
                    'trades': stats['trades'],
                    'wins': stats['wins'],
                    'win_rate': stats['wins'] / stats['trades'] * 100
                }
        
        return report


# Test function
def test_professional_strategy():
    """Test professional trading strategy."""
    print("\n" + "="*60)
    print("  🧪 PROFESSIONAL STRATEGY TEST")
    print("="*60)
    
    # Generate test data
    np.random.seed(42)
    n = 500
    dates = pd.date_range(end=datetime.now(), periods=n, freq='15min')
    
    prices = [2000.0]
    for i in range(n-1):
        trend = np.sin(i / 150) * 0.4
        noise = np.random.normal(0, 1.2)
        prices.append(prices[-1] + trend + noise)
    
    df = pd.DataFrame({
        'open': prices,
        'close': [p + np.random.uniform(-0.3, 0.3) for p in prices],
        'high': [p + np.random.uniform(0.5, 2) for p in prices],
        'low': [p - np.random.uniform(0.5, 2) for p in prices],
        'volume': np.random.randint(500, 2000, n)
    }, index=dates)
    
    config = {'TRADING_CONFIG': {
        'RISK_PER_TRADE': 0.02,
        'TAKE_PROFIT_PIPS': 12,
        'STOP_LOSS_PIPS': 10
    }}
    
    strategy = ProfessionalTradingStrategy(config)
    
    # Generate signals
    signals = []
    for i in range(100, len(df)):
        signal = strategy.generate_signal(df.iloc[:i+1], account_balance=1000)
        if signal:
            signals.append({
                'time': df.index[i],
                'direction': signal.direction,
                'confidence': signal.confidence,
                'strategy': signal.strategy_type,
                'session': signal.session,
                'regime': signal.volatility_regime,
                'reason': signal.reason[:50]
            })
    
    print(f"\n📊 Generated {len(signals)} signals")
    
    if signals:
        print("\n🎯 Sample Signals (last 5):")
        for s in signals[-5:]:
            print(f"   {s['time'].strftime('%Y-%m-%d %H:%M')} | {s['direction']} | "
                  f"{s['strategy']} | {s['session']} | Conf: {s['confidence']:.2f}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_professional_strategy()
