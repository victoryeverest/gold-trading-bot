"""
ML Predictor Module
Ensemble model with XGBoost, LightGBM, and Random Forest
Features: Technical indicators, sentiment, market regime detection
FIXED: Label encoding for XGBoost compatibility
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import pickle
import os
from datetime import datetime

logger = logging.getLogger('trading')

# ML imports
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn not available, ML features disabled")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available")


@dataclass
class MLPrediction:
    direction: int  # 1 = long, -1 = short, 0 = hold
    confidence: float
    probability_long: float
    probability_short: float
    feature_importance: Dict[str, float]
    model_agreement: float


class FeatureEngineer:
    """Generate ML features from price data."""
    
    def __init__(self):
        self.feature_names = []
        
    def create_features(self, df: pd.DataFrame, sentiment: float = 0.0) -> pd.DataFrame:
        """Create comprehensive feature set for ML model."""
        df = df.copy()
        
        # Price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['volume_change'] = df['volume'].pct_change()
        
        # Volatility features
        df['volatility_10'] = df['returns'].rolling(10).std()
        df['volatility_20'] = df['returns'].rolling(20).std()
        df['volatility_ratio'] = df['volatility_10'] / df['volatility_20'].replace(0, 0.001)
        
        # Momentum features
        df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
        df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
        df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        
        # Trend features
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        df['ema_ratio_9_21'] = df['ema_9'] / df['ema_21'].replace(0, 0.001)
        df['ema_ratio_21_50'] = df['ema_21'] / df['ema_50'].replace(0, 0.001)
        df['price_to_ema9'] = df['close'] / df['ema_9'].replace(0, 0.001)
        df['price_to_ema21'] = df['close'] / df['ema_21'].replace(0, 0.001)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_change'] = df['rsi'].diff()
        
        # MACD
        exp12 = df['close'].ewm(span=12).mean()
        exp26 = df['close'].ewm(span=26).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_hist_change'] = df['macd_hist'].diff()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']).replace(0, 0.001)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'].replace(0, 0.001)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_ratio'] = df['atr'] / df['close'].replace(0, 0.001)
        
        # Stochastic
        low_min = df['low'].rolling(14).min()
        high_max = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min).replace(0, 0.001))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['stoch_diff'] = df['stoch_k'] - df['stoch_d']
        
        # Volume features
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma'].replace(0, 1)
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean().replace(0, 1)
        
        # Candle patterns
        df['body'] = abs(df['close'] - df['open'])
        df['bullish_candle'] = (df['close'] > df['open']).astype(int)
        
        # Sentiment (if provided)
        df['sentiment'] = sentiment
        
        # Target variable (for training) - FIXED: Use 0, 1, 2 instead of -1, 0, 1
        # 0 = short, 1 = hold, 2 = long
        df['target'] = np.where(df['close'].shift(-1) > df['close'], 2,  # long
                               np.where(df['close'].shift(-1) < df['close'], 0, 1))  # short, hold
        
        # Drop NaN
        df = df.dropna()
        
        # Feature names
        exclude_cols = ['target', 'open', 'high', 'low', 'close', 'volume', 
                       'bb_upper', 'bb_lower', 'bb_middle', 'bb_std',
                       'ema_9', 'ema_21', 'ema_50', 'ema_200']
        self.feature_names = [col for col in df.columns if col not in exclude_cols]
        
        return df
    
    def get_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """Get feature matrix for ML model."""
        features = df[self.feature_names].values
        return features, self.feature_names


class EnsemblePredictor:
    """
    Ensemble ML predictor combining multiple models.
    Uses XGBoost, LightGBM, and Random Forest.
    FIXED: Proper label encoding for all models.
    """
    
    # Label mapping: original -> encoded
    LABEL_MAP = {-1: 0, 0: 1, 1: 2}  # short=0, hold=1, long=2
    REVERSE_LABEL_MAP = {0: -1, 1: 0, 2: 1}  # decode back
    
    def __init__(self, config: Dict):
        self.config = config
        self.ml_config = config.get('TRADING_CONFIG', {}).get('ML_FEATURES', [])
        
        self.feature_engineer = FeatureEngineer()
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
        # Models
        self.models = {}
        self.is_trained = False
        self.trained_models = set()  # Track which models are actually trained
        
        # Initialize models
        if SKLEARN_AVAILABLE:
            self.models['rf'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
            
        if XGBOOST_AVAILABLE:
            self.models['xgb'] = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='mlogloss',
                num_class=3  # 3 classes: short, hold, long
            )
            
        if LIGHTGBM_AVAILABLE:
            self.models['lgb'] = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbose=-1,
                num_class=3
            )
        
        self.model_dir = '/home/z/my-project/gold-trading-bot/models/'
        os.makedirs(self.model_dir, exist_ok=True)
        
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare features and labels for training."""
        df = self.feature_engineer.create_features(df)
        
        X, feature_names = self.feature_engineer.get_feature_matrix(df)
        y = df['target'].values  # Already encoded as 0, 1, 2
        
        # Scale features
        if self.scaler:
            X = self.scaler.fit_transform(X)
        
        return X, y, feature_names
    
    def train(self, df: pd.DataFrame) -> Dict:
        """Train ensemble model."""
        if not self.models:
            logger.warning("No ML models available for training")
            return {}
        
        X, y, feature_names = self.prepare_training_data(df)
        
        # Validate labels are in correct format (0, 1, 2)
        unique_labels = np.unique(y)
        logger.info(f"Training labels: {unique_labels}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        results = {}
        self.trained_models = set()
        
        for name, model in self.models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                results[name] = {
                    'accuracy': accuracy_score(y_test, y_pred),
                    'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                    'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0)
                }
                
                self.trained_models.add(name)
                logger.info(f"{name} trained: accuracy={results[name]['accuracy']:.4f}")
                
            except Exception as e:
                logger.error(f"Error training {name}: {e}")
                results[name] = {'error': str(e)}
        
        self.is_trained = len(self.trained_models) > 0
        if self.is_trained:
            self.save_models()
        
        return results
    
    def predict(self, df: pd.DataFrame, sentiment: float = 0.0) -> MLPrediction:
        """Generate ensemble prediction."""
        if not self.is_trained:
            # Auto-train if not trained
            if len(df) > 200:
                self.train(df)
            else:
                return MLPrediction(
                    direction=0,
                    confidence=0.0,
                    probability_long=0.5,
                    probability_short=0.5,
                    feature_importance={},
                    model_agreement=0.0
                )
        
        # Create features
        df = self.feature_engineer.create_features(df, sentiment)
        X, feature_names = self.feature_engineer.get_feature_matrix(df[-1:])
        
        if self.scaler:
            X = self.scaler.transform(X)
        
        predictions = []
        probabilities = []
        feature_importance = {}
        
        for name, model in self.models.items():
            # Skip models that failed to train
            if name not in self.trained_models:
                continue
                
            try:
                pred = model.predict(X)[0]
                proba = model.predict_proba(X)[0]
                
                predictions.append(pred)
                
                # Handle class probabilities
                classes = model.classes_
                prob_dict = {c: p for c, p in zip(classes, proba)}
                probabilities.append(prob_dict)
                
                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    importance = model.feature_importances_
                    for feat, imp in zip(self.feature_engineer.feature_names, importance):
                        if feat not in feature_importance:
                            feature_importance[feat] = []
                        feature_importance[feat].append(imp)
                        
            except Exception as e:
                logger.error(f"Prediction error for {name}: {e}")
        
        if not predictions:
            return MLPrediction(
                direction=0,
                confidence=0.0,
                probability_long=0.5,
                probability_short=0.5,
                feature_importance={},
                model_agreement=0.0
            )
        
        # Aggregate predictions (labels are 0=short, 1=hold, 2=long)
        avg_pred = np.mean(predictions)
        
        # Average probabilities
        prob_short = np.mean([p.get(0, 0.33) for p in probabilities])
        prob_hold = np.mean([p.get(1, 0.33) for p in probabilities])
        prob_long = np.mean([p.get(2, 0.33) for p in probabilities])
        
        # Normalize
        total = prob_long + prob_short + prob_hold
        if total > 0:
            prob_long /= total
            prob_short /= total
        
        # Determine direction
        if prob_long > prob_short and prob_long > 0.4:
            direction = 1
            confidence = prob_long
        elif prob_short > prob_long and prob_short > 0.4:
            direction = -1
            confidence = prob_short
        else:
            direction = 0
            confidence = max(prob_long, prob_short)
        
        # Model agreement
        if predictions:
            agreement = len([p for p in predictions if p == round(avg_pred)]) / len(predictions)
        else:
            agreement = 0.0
        
        # Average feature importance
        avg_importance = {k: np.mean(v) for k, v in feature_importance.items()}
        
        return MLPrediction(
            direction=direction,
            confidence=confidence,
            probability_long=prob_long,
            probability_short=prob_short,
            feature_importance=avg_importance,
            model_agreement=agreement
        )
    
    def save_models(self):
        """Save trained models to disk."""
        for name in self.trained_models:
            if name in self.models:
                path = os.path.join(self.model_dir, f'{name}_model.pkl')
                with open(path, 'wb') as f:
                    pickle.dump(self.models[name], f)
        
        # Save scaler
        if self.scaler:
            path = os.path.join(self.model_dir, 'scaler.pkl')
            with open(path, 'wb') as f:
                pickle.dump(self.scaler, f)
        
        # Save trained model names
        path = os.path.join(self.model_dir, 'trained_models.pkl')
        with open(path, 'wb') as f:
            pickle.dump(self.trained_models, f)
        
        logger.info("Models saved successfully")
    
    def load_models(self):
        """Load trained models from disk."""
        # Load trained model names
        trained_path = os.path.join(self.model_dir, 'trained_models.pkl')
        if os.path.exists(trained_path):
            with open(trained_path, 'rb') as f:
                self.trained_models = pickle.load(f)
        
        for name in self.trained_models:
            path = os.path.join(self.model_dir, f'{name}_model.pkl')
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    self.models[name] = pickle.load(f)
        
        # Load scaler
        scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
        
        self.is_trained = len(self.trained_models) > 0
        logger.info(f"Models loaded successfully: {self.trained_models}")


class MarketRegimeDetector:
    """
    Detect current market regime (trending, ranging, volatile).
    Helps adapt strategy to market conditions.
    """
    
    def __init__(self):
        self.regime = 'UNKNOWN'
        self.confidence = 0.0
        
    def detect_regime(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Detect market regime from price data.
        Returns: (regime, confidence)
        """
        if len(df) < 100:
            return 'UNKNOWN', 0.0
        
        # Calculate indicators
        close = df['close']
        
        # ADX for trend strength
        high = df['high']
        low = df['low']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = pd.concat([high - low, 
                       abs(high - close.shift()), 
                       abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        tr14 = tr.rolling(14).sum()
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr14.replace(0, 0.001))
        minus_di = 100 * (abs(minus_dm).rolling(14).sum() / tr14.replace(0, 0.001))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 0.001)
        adx = dx.rolling(14).mean().iloc[-1]
        
        # Volatility
        returns = close.pct_change()
        volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        
        # Range detection
        high_roll = high.rolling(20).max()
        low_roll = low.rolling(20).min()
        range_size = (high_roll.iloc[-1] - low_roll.iloc[-1]) / close.iloc[-1]
        
        # Regime determination
        if adx > 25:
            if volatility > 0.25:
                self.regime = 'TRENDING_VOLATILE'
                self.confidence = min(adx / 50, 1.0)
            else:
                self.regime = 'TRENDING'
                self.confidence = min(adx / 50, 1.0)
        else:
            if range_size < 0.03:
                self.regime = 'RANGING_TIGHT'
                self.confidence = 1 - (range_size / 0.03)
            else:
                self.regime = 'RANGING'
                self.confidence = 0.6
        
        return self.regime, self.confidence
    
    def get_strategy_modifier(self) -> Dict:
        """
        Get strategy parameter modifiers based on regime.
        """
        modifiers = {
            'tp_multiplier': 1.0,
            'sl_multiplier': 1.0,
            'position_size_modifier': 1.0,
            'entry_threshold': 0.45
        }
        
        if self.regime == 'TRENDING':
            modifiers['tp_multiplier'] = 1.5  # Let profits run
            modifiers['sl_multiplier'] = 1.2  # Wider stops
            modifiers['entry_threshold'] = 0.40  # Easier entry
            
        elif self.regime == 'TRENDING_VOLATILE':
            modifiers['tp_multiplier'] = 1.3
            modifiers['sl_multiplier'] = 1.5  # Much wider stops
            modifiers['position_size_modifier'] = 0.7  # Smaller size
            modifiers['entry_threshold'] = 0.50  # More selective
            
        elif self.regime == 'RANGING':
            modifiers['tp_multiplier'] = 0.8  # Quick profits
            modifiers['sl_multiplier'] = 0.9  # Tighter stops
            modifiers['entry_threshold'] = 0.50
            
        elif self.regime == 'RANGING_TIGHT':
            modifiers['tp_multiplier'] = 0.6  # Very quick profits
            modifiers['sl_multiplier'] = 0.8
            modifiers['position_size_modifier'] = 0.8
            modifiers['entry_threshold'] = 0.55
        
        return modifiers
