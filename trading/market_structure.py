"""
Market Structure Analysis Module
Professional quant trading features:
1. Volatility Regime Detection
2. Liquidity Sweep Detection  
3. Session-Based Strategy Switching
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time
import logging

logger = logging.getLogger('trading')


class VolatilityRegime(Enum):
    LOW = 'LOW'           # Tight ranges, mean reversion works
    NORMAL = 'NORMAL'     # Normal trading conditions
    HIGH = 'HIGH'         # Breakout strategies, wider stops
    EXTREME = 'EXTREME'   # News events, reduce position size


class TradingSession(Enum):
    ASIAN = 'ASIAN'       # 00:00-08:00 UTC - Low volatility, range trading
    LONDON = 'LONDON'     # 08:00-16:00 UTC - Trend following
    NEW_YORK = 'NEW_YORK' # 13:00-21:00 UTC - High volatility, momentum
    OVERLAP = 'OVERLAP'   # 13:00-16:00 UTC - Best liquidity, aggressive


class LiquidityEvent(Enum):
    NONE = 'NONE'
    SWEEP_HIGH = 'SWEEP_HIGH'    # Price swept above resistance
    SWEEP_LOW = 'SWEEP_LOW'      # Price swept below support
    DOUBLE_SWEEP = 'DOUBLE_SWEEP' # Both sides swept


@dataclass
class MarketStructure:
    """Current market structure state."""
    volatility_regime: VolatilityRegime
    session: TradingSession
    liquidity_event: LiquidityEvent
    trend_direction: str
    support_levels: List[float]
    resistance_levels: List[float]
    sweep_probability: float
    recommended_strategy: str
    position_size_modifier: float
    stop_loss_modifier: float
    take_profit_modifier: float


class VolatilityRegimeDetector:
    """
    Detect current volatility regime using ATR and price action.
    
    Regimes:
    - LOW: ATR below 20th percentile, tight ranges
    - NORMAL: ATR between 20-80th percentile
    - HIGH: ATR above 80th percentile, trending
    - EXTREME: ATR above 95th percentile, news events
    """
    
    def __init__(self, lookback: int = 100):
        self.lookback = lookback
        self.atr_percentile = 50.0
        self.current_regime = VolatilityRegime.NORMAL
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def detect_regime(self, df: pd.DataFrame) -> Tuple[VolatilityRegime, float]:
        """
        Detect volatility regime based on ATR percentile.
        Returns (regime, percentile)
        """
        if len(df) < self.lookback:
            return VolatilityRegime.NORMAL, 50.0
        
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]
        
        # Calculate percentile rank over lookback period
        atr_history = atr.iloc[-self.lookback:]
        self.atr_percentile = (atr_history < current_atr).sum() / len(atr_history) * 100
        
        # Determine regime
        if self.atr_percentile < 20:
            self.current_regime = VolatilityRegime.LOW
        elif self.atr_percentile < 80:
            self.current_regime = VolatilityRegime.NORMAL
        elif self.atr_percentile < 95:
            self.current_regime = VolatilityRegime.HIGH
        else:
            self.current_regime = VolatilityRegime.EXTREME
        
        return self.current_regime, self.atr_percentile
    
    def get_strategy_modifiers(self) -> Dict[str, float]:
        """Get trading parameters based on volatility regime."""
        modifiers = {
            'position_size': 1.0,
            'stop_loss': 1.0,
            'take_profit': 1.0,
            'entry_threshold': 0.45
        }
        
        if self.current_regime == VolatilityRegime.LOW:
            # Tight ranges - mean reversion
            modifiers['position_size'] = 0.8
            modifiers['stop_loss'] = 0.7
            modifiers['take_profit'] = 0.6
            modifiers['entry_threshold'] = 0.55
            modifiers['strategy'] = 'MEAN_REVERSION'
            
        elif self.current_regime == VolatilityRegime.NORMAL:
            # Normal conditions
            modifiers['strategy'] = 'TREND_FOLLOW'
            
        elif self.current_regime == VolatilityRegime.HIGH:
            # Trending - let profits run
            modifiers['position_size'] = 0.9
            modifiers['stop_loss'] = 1.3
            modifiers['take_profit'] = 1.5
            modifiers['entry_threshold'] = 0.40
            modifiers['strategy'] = 'MOMENTUM'
            
        elif self.current_regime == VolatilityRegime.EXTREME:
            # News event - be cautious
            modifiers['position_size'] = 0.5
            modifiers['stop_loss'] = 1.5
            modifiers['take_profit'] = 1.2
            modifiers['entry_threshold'] = 0.60
            modifiers['strategy'] = 'DEFENSIVE'
        
        return modifiers


class LiquiditySweepDetector:
    """
    Detect liquidity sweeps (stop hunts) at key levels.
    
    A liquidity sweep occurs when:
    1. Price breaks above resistance or below support
    2. Then quickly reverses
    3. This indicates stop-loss hunting by large players
    
    These are high-probability reversal signals.
    """
    
    def __init__(self, lookback: int = 50, sweep_threshold: float = 0.002):
        self.lookback = lookback
        self.sweep_threshold = sweep_threshold  # 0.2% penetration
        self.recent_sweeps = []
        
    def find_key_levels(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """
        Find key support and resistance levels using swing points.
        """
        if len(df) < self.lookback:
            return [], []
        
        data = df.iloc[-self.lookback:]
        
        # Find swing highs (resistance)
        resistance_levels = []
        for i in range(2, len(data) - 2):
            if (data['high'].iloc[i] > data['high'].iloc[i-1] and
                data['high'].iloc[i] > data['high'].iloc[i-2] and
                data['high'].iloc[i] > data['high'].iloc[i+1] and
                data['high'].iloc[i] > data['high'].iloc[i+2]):
                resistance_levels.append(data['high'].iloc[i])
        
        # Find swing lows (support)
        support_levels = []
        for i in range(2, len(data) - 2):
            if (data['low'].iloc[i] < data['low'].iloc[i-1] and
                data['low'].iloc[i] < data['low'].iloc[i-2] and
                data['low'].iloc[i] < data['low'].iloc[i+1] and
                data['low'].iloc[i] < data['low'].iloc[i+2]):
                support_levels.append(data['low'].iloc[i])
        
        # Cluster nearby levels
        resistance = self._cluster_levels(resistance_levels)
        support = self._cluster_levels(support_levels)
        
        return support, resistance
    
    def _cluster_levels(self, levels: List[float], tolerance: float = 0.003) -> List[float]:
        """Cluster nearby levels into single levels."""
        if not levels:
            return []
        
        levels = sorted(levels)
        clustered = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - clustered[-1]) / clustered[-1] > tolerance:
                clustered.append(level)
        
        return clustered[-5:]  # Return top 5 levels
    
    def detect_sweep(self, df: pd.DataFrame) -> Tuple[LiquidityEvent, float]:
        """
        Detect if a liquidity sweep just occurred.
        Returns (event_type, sweep_probability)
        """
        if len(df) < 10:
            return LiquidityEvent.NONE, 0.0
        
        support, resistance = self.find_key_levels(df)
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        sweep_high = False
        sweep_low = False
        sweep_probability = 0.0
        
        # Check for sweep above resistance
        for level in resistance:
            if prev['high'] > level:  # Broke above
                penetration = (prev['high'] - level) / level
                
                # Check for quick reversal
                if penetration < self.sweep_threshold:
                    if current['close'] < level:  # Closed back below
                        sweep_high = True
                        sweep_probability = max(sweep_probability, 
                            0.7 + penetration * 100)
        
        # Check for sweep below support
        for level in support:
            if prev['low'] < level:  # Broke below
                penetration = (level - prev['low']) / level
                
                if penetration < self.sweep_threshold:
                    if current['close'] > level:  # Closed back above
                        sweep_low = True
                        sweep_probability = max(sweep_probability,
                            0.7 + penetration * 100)
        
        # Determine event type
        if sweep_high and sweep_low:
            event = LiquidityEvent.DOUBLE_SWEEP
            sweep_probability = min(sweep_probability + 0.2, 0.95)
        elif sweep_high:
            event = LiquidityEvent.SWEEP_HIGH
        elif sweep_low:
            event = LiquidityEvent.SWEEP_LOW
        else:
            event = LiquidityEvent.NONE
        
        return event, sweep_probability
    
    def get_sweep_signal(self, df: pd.DataFrame) -> Dict:
        """
        Get trading signal based on liquidity sweep.
        Sweeps are reversal signals.
        """
        event, probability = self.detect_sweep(df)
        
        signal = {
            'direction': 0,  # 1=long, -1=short, 0=none
            'confidence': 0.0,
            'event': event,
            'probability': probability,
            'entry_type': 'NONE'
        }
        
        if event == LiquidityEvent.SWEEP_HIGH and probability > 0.6:
            # Price swept above resistance and rejected - SHORT
            signal['direction'] = -1
            signal['confidence'] = probability
            signal['entry_type'] = 'SWEEP_REVERSAL'
            
        elif event == LiquidityEvent.SWEEP_LOW and probability > 0.6:
            # Price swept below support and rejected - LONG
            signal['direction'] = 1
            signal['confidence'] = probability
            signal['entry_type'] = 'SWEEP_REVERSAL'
            
        elif event == LiquidityEvent.DOUBLE_SWEEP and probability > 0.7:
            # Both sides swept - expect consolidation then breakout
            signal['entry_type'] = 'WAIT_BREAKOUT'
        
        return signal


class SessionManager:
    """
    Manage trading session detection and strategy switching.
    
    Sessions (UTC):
    - ASIAN: 00:00-08:00 - Low volatility, range-bound
    - LONDON: 08:00-16:00 - Trend development
    - NEW_YORK: 13:00-21:00 - Momentum moves
    - OVERLAP: 13:00-16:00 - Best liquidity (London+NY)
    """
    
    def __init__(self):
        self.current_session = TradingSession.ASIAN
        self.session_start = None
        self.session_characteristics = {
            TradingSession.ASIAN: {
                'volatility': 'LOW',
                'strategy': 'RANGE_TRADE',
                'typical_range_pips': 15,
                'best_directions': ['BOTH'],  # Both long and short work
                'entry_threshold': 0.55,
                'position_modifier': 0.8,
                'tp_modifier': 0.7,
                'sl_modifier': 0.8
            },
            TradingSession.LONDON: {
                'volatility': 'MEDIUM',
                'strategy': 'TREND_FOLLOW',
                'typical_range_pips': 30,
                'best_directions': ['BULL', 'BEAR'],
                'entry_threshold': 0.45,
                'position_modifier': 1.0,
                'tp_modifier': 1.0,
                'sl_modifier': 1.0
            },
            TradingSession.NEW_YORK: {
                'volatility': 'HIGH',
                'strategy': 'MOMENTUM',
                'typical_range_pips': 40,
                'best_directions': ['BULL', 'BEAR'],
                'entry_threshold': 0.40,
                'position_modifier': 1.1,
                'tp_modifier': 1.2,
                'sl_modifier': 1.1
            },
            TradingSession.OVERLAP: {
                'volatility': 'HIGHEST',
                'strategy': 'AGGRESSIVE_TREND',
                'typical_range_pips': 50,
                'best_directions': ['BULL', 'BEAR'],
                'entry_threshold': 0.35,
                'position_modifier': 1.2,
                'tp_modifier': 1.3,
                'sl_modifier': 1.0
            }
        }
        
    def detect_session(self, timestamp: datetime) -> TradingSession:
        """Detect current trading session."""
        hour = timestamp.hour
        
        if 0 <= hour < 8:
            self.current_session = TradingSession.ASIAN
        elif 8 <= hour < 13:
            self.current_session = TradingSession.LONDON
        elif 13 <= hour < 16:
            self.current_session = TradingSession.OVERLAP  # Best time
        elif 16 <= hour < 21:
            self.current_session = TradingSession.NEW_YORK
        else:
            self.current_session = TradingSession.ASIAN  # Default to Asian
            
        return self.current_session
    
    def get_session_config(self, session: TradingSession = None) -> Dict:
        """Get configuration for current session."""
        if session is None:
            session = self.current_session
        return self.session_characteristics.get(session, 
            self.session_characteristics[TradingSession.LONDON])
    
    def is_optimal_trading_time(self, timestamp: datetime) -> Tuple[bool, str]:
        """
        Check if current time is optimal for trading.
        Returns (is_optimal, reason)
        """
        session = self.detect_session(timestamp)
        
        if session == TradingSession.OVERLAP:
            return True, "London-NY overlap - highest liquidity"
        elif session == TradingSession.LONDON:
            return True, "London session - good trend development"
        elif session == TradingSession.NEW_YORK:
            return True, "NY session - momentum opportunities"
        elif session == TradingSession.ASIAN:
            return False, "Asian session - low volatility, wait for ranges"
        
        return True, "Active trading session"
    
    def get_strategy_for_session(self, session: TradingSession) -> str:
        """Get recommended strategy for session."""
        config = self.get_session_config(session)
        return config.get('strategy', 'TREND_FOLLOW')


class MarketStructureAnalyzer:
    """
    Main class combining all market structure analysis.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        self.volatility_detector = VolatilityRegimeDetector()
        self.liquidity_detector = LiquiditySweepDetector()
        self.session_manager = SessionManager()
        
    def analyze(self, df: pd.DataFrame) -> MarketStructure:
        """
        Perform complete market structure analysis.
        """
        # Detect volatility regime
        vol_regime, vol_percentile = self.volatility_detector.detect_regime(df)
        
        # Detect liquidity events
        liq_event, sweep_prob = self.liquidity_detector.detect_sweep(df)
        
        # Detect session
        timestamp = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else datetime.now()
        session = self.session_manager.detect_session(timestamp)
        
        # Find key levels
        support, resistance = self.liquidity_detector.find_key_levels(df)
        
        # Determine trend
        trend = self._determine_trend(df)
        
        # Get modifiers
        vol_mods = self.volatility_detector.get_strategy_modifiers()
        sess_config = self.session_manager.get_session_config()
        
        # Calculate combined modifiers
        position_mod = vol_mods['position_size'] * sess_config['position_modifier']
        sl_mod = vol_mods['stop_loss'] * sess_config['sl_modifier']
        tp_mod = vol_mods['take_profit'] * sess_config['tp_modifier']
        
        # Determine recommended strategy
        if sweep_prob > 0.6:
            strategy = 'SWEEP_REVERSAL'
        else:
            strategy = sess_config['strategy']
        
        return MarketStructure(
            volatility_regime=vol_regime,
            session=session,
            liquidity_event=liq_event,
            trend_direction=trend,
            support_levels=support,
            resistance_levels=resistance,
            sweep_probability=sweep_prob,
            recommended_strategy=strategy,
            position_size_modifier=position_mod,
            stop_loss_modifier=sl_mod,
            take_profit_modifier=tp_mod
        )
    
    def _determine_trend(self, df: pd.DataFrame) -> str:
        """Determine trend direction using EMAs."""
        if len(df) < 50:
            return 'NEUTRAL'
        
        last = df.iloc[-1]
        
        # EMA alignment
        ema9 = df['close'].ewm(span=9).mean().iloc[-1]
        ema21 = df['close'].ewm(span=21).mean().iloc[-1]
        ema50 = df['close'].ewm(span=50).mean().iloc[-1]
        
        if ema9 > ema21 > ema50:
            return 'BULLISH'
        elif ema9 < ema21 < ema50:
            return 'BEARISH'
        
        return 'NEUTRAL'
    
    def should_trade(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Determine if we should trade based on market structure.
        Returns (should_trade, reason)
        """
        structure = self.analyze(df)
        
        # Check session
        is_optimal, reason = self.session_manager.is_optimal_trading_time(
            df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else datetime.now()
        )
        
        # Check volatility
        if structure.volatility_regime == VolatilityRegime.EXTREME:
            return False, "Extreme volatility - wait for conditions to normalize"
        
        # Check for sweep opportunity
        if structure.liquidity_event != LiquidityEvent.NONE and structure.sweep_probability > 0.6:
            return True, f"Liquidity sweep detected: {structure.liquidity_event.value}"
        
        # Standard session check
        if not is_optimal:
            return False, reason
        
        return True, f"Good conditions - {structure.session.value} session, {structure.volatility_regime.value} volatility"
    
    def get_entry_parameters(self, df: pd.DataFrame) -> Dict:
        """
        Get adjusted entry parameters based on market structure.
        """
        structure = self.analyze(df)
        
        return {
            'strategy': structure.recommended_strategy,
            'position_size_modifier': structure.position_size_modifier,
            'stop_loss_modifier': structure.stop_loss_modifier,
            'take_profit_modifier': structure.take_profit_modifier,
            'trend_direction': structure.trend_direction,
            'session': structure.session.value,
            'volatility_regime': structure.volatility_regime.value,
            'sweep_probability': structure.sweep_probability,
            'support_levels': structure.support_levels,
            'resistance_levels': structure.resistance_levels
        }


# Test function
def test_market_structure():
    """Test market structure analysis."""
    import numpy as np
    
    print("\n" + "="*60)
    print("  🧪 MARKET STRUCTURE ANALYSIS TEST")
    print("="*60)
    
    # Generate test data
    np.random.seed(42)
    n = 500
    dates = pd.date_range(end=datetime.now(), periods=n, freq='15min')
    
    prices = [2000.0]
    for i in range(n-1):
        # Add trend and noise
        trend = np.sin(i / 100) * 0.3
        noise = np.random.normal(0, 1.5)
        prices.append(prices[-1] + trend + noise)
    
    df = pd.DataFrame({
        'open': prices,
        'close': [p + np.random.uniform(-0.5, 0.5) for p in prices],
        'high': [p + np.random.uniform(0.5, 2) for p in prices],
        'low': [p - np.random.uniform(0.5, 2) for p in prices],
        'volume': np.random.randint(500, 2000, n)
    }, index=dates)
    
    # Analyze
    analyzer = MarketStructureAnalyzer()
    structure = analyzer.analyze(df)
    
    print(f"\n📊 Market Structure Analysis:")
    print(f"   Volatility Regime: {structure.volatility_regime.value}")
    print(f"   Session: {structure.session.value}")
    print(f"   Liquidity Event: {structure.liquidity_event.value}")
    print(f"   Trend: {structure.trend_direction}")
    print(f"   Sweep Probability: {structure.sweep_probability:.1%}")
    print(f"   Recommended Strategy: {structure.recommended_strategy}")
    
    print(f"\n📏 Trading Modifiers:")
    print(f"   Position Size: {structure.position_size_modifier:.2f}x")
    print(f"   Stop Loss: {structure.stop_loss_modifier:.2f}x")
    print(f"   Take Profit: {structure.take_profit_modifier:.2f}x")
    
    # Should trade?
    should, reason = analyzer.should_trade(df)
    print(f"\n🎯 Trade Decision: {'YES' if should else 'NO'}")
    print(f"   Reason: {reason}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_market_structure()
