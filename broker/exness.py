"""
Exness Broker Integration via MetaTrader 5
Handles connection, order execution, and account management
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time

logger = logging.getLogger('trading')

# MT5 imports
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 not available. Using simulation mode.")


class OrderType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_LIMIT = 'BUY_LIMIT'
    SELL_LIMIT = 'SELL_LIMIT'
    BUY_STOP = 'BUY_STOP'
    SELL_STOP = 'SELL_STOP'


class OrderStatus(Enum):
    PENDING = 'PENDING'
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'
    REJECTED = 'REJECTED'


@dataclass
class Order:
    order_id: int
    symbol: str
    order_type: OrderType
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    status: OrderStatus
    timestamp: datetime
    comment: str = ''


@dataclass
class Position:
    position_id: int
    symbol: str
    order_type: OrderType
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    profit: float
    swap: float
    commission: float
    open_time: datetime


class ExnessBroker:
    """
    Exness broker integration via MetaTrader 5.
    Handles live trading operations.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Connection settings
        self.server = self.trading_config.get('MT5_SERVER', 'Exness-Real')
        self.login = self.trading_config.get('MT5_LOGIN', '')
        self.password = self.trading_config.get('MT5_PASSWORD', '')
        
        # State
        self.connected = False
        self.account_info = None
        self.positions: List[Position] = []
        self.orders: List[Order] = []
        
        # Symbol info
        self.symbol = self.trading_config.get('SYMBOL', 'XAUUSD')
        self.point = 0.01  # Gold pip value
        self.digits = 2
        
    def connect(self) -> bool:
        """Connect to MetaTrader 5 terminal."""
        if not MT5_AVAILABLE:
            logger.warning("MT5 not available, running in simulation mode")
            return True
        
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Login to account
            if self.login and self.password:
                if not mt5.login(int(self.login), self.password, self.server):
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False
            
            # Get account info
            self.account_info = mt5.account_info()
            if self.account_info is None:
                logger.error("Failed to get account info")
                return False
            
            # Get symbol info
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error(f"Failed to get symbol info for {self.symbol}")
                return False
            
            self.point = symbol_info.point
            self.digits = symbol_info.digits
            
            self.connected = True
            logger.info(f"Connected to {self.server}, Balance: {self.account_info.balance}")
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5."""
        if MT5_AVAILABLE:
            mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5")
    
    def get_account_info(self) -> Dict:
        """Get current account information."""
        if not MT5_AVAILABLE:
            # Simulation mode
            return {
                'balance': 50.0,
                'equity': 50.0,
                'margin': 0.0,
                'free_margin': 50.0,
                'margin_level': 0.0,
                'profit': 0.0
            }
        
        if not self.connected:
            return {}
        
        info = mt5.account_info()
        if info:
            return {
                'balance': info.balance,
                'equity': info.equity,
                'margin': info.margin,
                'free_margin': info.margin_free,
                'margin_level': info.margin_level,
                'profit': info.profit
            }
        return {}
    
    def get_balance(self) -> float:
        """Get current account balance."""
        info = self.get_account_info()
        return info.get('balance', 0.0)
    
    def get_equity(self) -> float:
        """Get current account equity."""
        info = self.get_account_info()
        return info.get('equity', 0.0)
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        if not MT5_AVAILABLE:
            return self.positions
        
        if not self.connected:
            return []
        
        positions = mt5.positions_get(symbol=self.symbol)
        result = []
        
        if positions:
            for pos in positions:
                position = Position(
                    position_id=pos.ticket,
                    symbol=pos.symbol,
                    order_type=OrderType.BUY if pos.type == 0 else OrderType.SELL,
                    volume=pos.volume,
                    entry_price=pos.price_open,
                    current_price=pos.price_current,
                    stop_loss=pos.sl,
                    take_profit=pos.tp,
                    profit=pos.profit,
                    swap=pos.swap,
                    commission=0.0,
                    open_time=datetime.fromtimestamp(pos.time)
                )
                result.append(position)
        
        self.positions = result
        return result
    
    def get_current_price(self, symbol: str = None) -> Tuple[float, float]:
        """Get current bid/ask prices."""
        symbol = symbol or self.symbol
        
        if not MT5_AVAILABLE:
            # Simulation - return fake prices
            return 2000.0, 2000.1
        
        if not self.connected:
            return 0.0, 0.0
        
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return tick.bid, tick.ask
        return 0.0, 0.0
    
    def calculate_margin(self, volume: float, price: float) -> float:
        """Calculate required margin for position."""
        if not MT5_AVAILABLE:
            # Approximate margin for gold (1:500 leverage typical for Exness)
            return (volume * 100 * price) / 500
        
        if not self.connected:
            return 0.0
        
        margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, self.symbol, volume, price)
        return margin if margin else 0.0
    
    def place_order(self, order_type: OrderType, volume: float,
                   stop_loss: float, take_profit: float,
                   comment: str = '') -> Tuple[bool, Optional[Order]]:
        """
        Place a market order.
        Returns: (success, order)
        """
        if not MT5_AVAILABLE:
            # Simulation mode
            order = Order(
                order_id=int(time.time() * 1000),
                symbol=self.symbol,
                order_type=order_type,
                volume=volume,
                price=2000.0,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status=OrderStatus.FILLED,
                timestamp=datetime.now(),
                comment=comment
            )
            self.orders.append(order)
            logger.info(f"SIMULATION: Order placed - {order_type.value} {volume} lots")
            return True, order
        
        if not self.connected:
            logger.error("Not connected to MT5")
            return False, None
        
        # Get current price
        bid, ask = self.get_current_price()
        
        # Determine order type and price
        if order_type == OrderType.BUY:
            mt5_order_type = mt5.ORDER_TYPE_BUY
            price = ask
        elif order_type == OrderType.SELL:
            mt5_order_type = mt5.ORDER_TYPE_SELL
            price = bid
        else:
            logger.error(f"Unsupported order type: {order_type}")
            return False, None
        
        # Create order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            logger.error(f"Order failed: {mt5.last_error()}")
            return False, None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order rejected: {result.comment}")
            return False, None
        
        # Create order object
        order = Order(
            order_id=result.order,
            symbol=self.symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.FILLED,
            timestamp=datetime.now(),
            comment=comment
        )
        
        self.orders.append(order)
        logger.info(f"Order placed: {order_type.value} {volume} lots at {price}")
        
        return True, order
    
    def close_position(self, position_id: int, volume: float = None) -> bool:
        """
        Close a position (fully or partially).
        """
        if not MT5_AVAILABLE:
            logger.info(f"SIMULATION: Position {position_id} closed")
            return True
        
        if not self.connected:
            return False
        
        # Get position
        position = mt5.positions_get(ticket=position_id)
        if not position:
            logger.error(f"Position {position_id} not found")
            return False
        
        pos = position[0]
        close_volume = volume if volume else pos.volume
        
        # Determine close order type
        if pos.type == 0:  # BUY
            order_type = mt5.ORDER_TYPE_SELL
            price = self.get_current_price()[0]  # bid
        else:  # SELL
            order_type = mt5.ORDER_TYPE_BUY
            price = self.get_current_price()[1]  # ask
        
        # Create close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_volume,
            "type": order_type,
            "position": position_id,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Close failed: {result.comment if result else mt5.last_error()}")
            return False
        
        logger.info(f"Position {position_id} closed")
        return True
    
    def modify_position(self, position_id: int, stop_loss: float = None,
                       take_profit: float = None) -> bool:
        """Modify position SL/TP."""
        if not MT5_AVAILABLE:
            logger.info(f"SIMULATION: Position {position_id} modified")
            return True
        
        if not self.connected:
            return False
        
        # Get position
        position = mt5.positions_get(ticket=position_id)
        if not position:
            return False
        
        pos = position[0]
        
        # Use existing values if not provided
        sl = stop_loss if stop_loss else pos.sl
        tp = take_profit if take_profit else pos.tp
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "position": position_id,
            "sl": sl,
            "tp": tp,
            "type": mt5.ORDER_TYPE_BUY if pos.type == 0 else mt5.ORDER_TYPE_SELL,
            "price": pos.price_open,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Modify failed: {result.comment if result else mt5.last_error()}")
            return False
        
        logger.info(f"Position {position_id} modified: SL={sl}, TP={tp}")
        return True
    
    def get_market_data(self, timeframe: str = 'M15', count: int = 500) -> List[Dict]:
        """
        Get historical market data.
        """
        if not MT5_AVAILABLE:
            # Generate synthetic data
            return self._generate_synthetic_data(count)
        
        if not self.connected:
            return []
        
        # Map timeframe string to MT5 constant
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }
        
        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
        
        # Get rates
        rates = mt5.copy_rates_from_pos(self.symbol, mt5_timeframe, 0, count)
        
        if rates is None:
            logger.error(f"Failed to get market data: {mt5.last_error()}")
            return []
        
        # Convert to list of dicts
        data = []
        for rate in rates:
            data.append({
                'time': datetime.fromtimestamp(rate['time']),
                'open': rate['open'],
                'high': rate['high'],
                'low': rate['low'],
                'close': rate['close'],
                'volume': rate['tick_volume']
            })
        
        return data
    
    def _generate_synthetic_data(self, count: int) -> List[Dict]:
        """Generate synthetic gold price data for testing."""
        import random
        
        data = []
        price = 2000.0  # Starting price
        
        for i in range(count):
            change = random.gauss(0, 2)  # Random price change
            price += change
            
            high = price + random.uniform(0, 3)
            low = price - random.uniform(0, 3)
            open_price = price + random.uniform(-1, 1)
            close_price = price
            volume = random.randint(100, 1000)
            
            data.append({
                'time': datetime.now(),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
        
        return data
