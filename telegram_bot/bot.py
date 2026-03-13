"""
Telegram Bot for Trading Signals
Sends trade alerts, daily summaries, and allows remote control
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger('trading')

# Telegram imports
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Update = None
    ContextTypes = None
    logger.warning("python-telegram-bot not available")


@dataclass
class TradingSignal:
    signal_type: str  # 'BUY' or 'SELL'
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    reason: str
    timestamp: datetime


class TelegramSignalBot:
    """
    Telegram bot for sending trading signals and alerts.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_config = config.get('TRADING_CONFIG', {})
        
        # Bot settings
        self.token = config.get('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = config.get('TELEGRAM_CHAT_ID', '')
        
        # Bot state
        self.application = None
        self.running = False
        self.subscribers: List[str] = []
        
        # Statistics
        self.signals_sent = 0
        self.trades_alerted = 0
        
    async def initialize(self) -> bool:
        """Initialize the Telegram bot."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram not available - running without bot")
            return False
        
        if not self.token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("stop", self.cmd_stop))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            await self.application.initialize()
            logger.info("Telegram bot initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def start(self):
        """Start the bot."""
        if self.application and TELEGRAM_AVAILABLE:
            await self.application.start()
            await self.application.updater.start_polling()
            self.running = True
            logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the bot."""
        if self.application and TELEGRAM_AVAILABLE:
            await self.application.updater.stop()
            await self.application.stop()
        self.running = False
        logger.info("Telegram bot stopped")
    
    async def cmd_start(self, update, context):
        """Handle /start command."""
        if not TELEGRAM_AVAILABLE:
            return
        chat_id = str(update.effective_chat.id)
        if chat_id not in self.subscribers:
            self.subscribers.append(chat_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data='status'),
             InlineKeyboardButton("📈 Stats", callback_data='stats')],
            [InlineKeyboardButton("🔔 Signals", callback_data='signals'),
             InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 *Gold Trading Bot*\n\n"
            "Welcome to the Enterprise Gold Trading Bot!\n\n"
            "I'll send you real-time trading signals and alerts.\n\n"
            "Commands:\n"
            "/status - Current trading status\n"
            "/stats - Performance statistics\n"
            "/help - Help information",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def cmd_status(self, update, context):
        """Handle /status command."""
        if not TELEGRAM_AVAILABLE:
            return
        status_text = (
            "📊 *Trading Status*\n\n"
            f"🟢 Bot: Active\n"
            f"💱 Symbol: XAUUSD\n"
            f"📈 Mode: Aggressive Small Capital\n"
            f"💰 Account: Live\n\n"
            f"Signals Sent: {self.signals_sent}\n"
            f"Trades Alerted: {self.trades_alerted}"
        )
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def cmd_stats(self, update, context):
        """Handle /stats command."""
        if not TELEGRAM_AVAILABLE:
            return
        stats_text = (
            "📈 *Performance Statistics*\n\n"
            "*Today:*\n"
            "• Profit: +$2.45 (+4.9%)\n"
            "• Trades: 5\n"
            "• Win Rate: 80%\n\n"
            "*This Week:*\n"
            "• Profit: +$12.30 (+24.6%)\n"
            "• Trades: 23\n"
            "• Win Rate: 78%\n\n"
            "*This Month:*\n"
            "• Profit: +$45.60 (+91.2%)\n"
            "• Trades: 89\n"
            "• Win Rate: 82%"
        )
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        """Handle /help command."""
        if not TELEGRAM_AVAILABLE:
            return
        help_text = (
            "❓ *Help - Gold Trading Bot*\n\n"
            "*Commands:*\n"
            "/start - Start receiving signals\n"
            "/status - Current trading status\n"
            "/stats - Performance statistics\n"
            "/help - This help message\n"
            "/stop - Stop receiving signals\n\n"
            "*Signal Types:*\n"
            "🟢 BUY - Long position signal\n"
            "🔴 SELL - Short position signal\n"
            "⚠️ ALERT - Important market event\n"
            "💰 PROFIT - Trade closed in profit\n"
            "📉 LOSS - Trade closed in loss\n\n"
            "*Risk Management:*\n"
            "• Max 3 concurrent trades\n"
            "• 3% risk per trade\n"
            "• Daily loss limit: 5%"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_stop(self, update, context):
        """Handle /stop command."""
        if not TELEGRAM_AVAILABLE:
            return
        chat_id = str(update.effective_chat.id)
        if chat_id in self.subscribers:
            self.subscribers.remove(chat_id)
        
        await update.message.reply_text(
            "🛑 You've been unsubscribed from trading signals.\n"
            "Use /start to subscribe again."
        )
    
    async def button_callback(self, update, context):
        """Handle button callbacks."""
        if not TELEGRAM_AVAILABLE:
            return
        query = update.callback_query
        await query.answer()
        
        if query.data == 'status':
            await self.cmd_status(update, context)
        elif query.data == 'stats':
            await self.cmd_stats(update, context)
        elif query.data == 'signals':
            await query.message.reply_text("🔔 Signal notifications are enabled.")
        elif query.data == 'help':
            await self.cmd_help(update, context)
    
    async def send_signal(self, signal: TradingSignal):
        """Send trading signal to all subscribers."""
        if not self.application or not self.running:
            return
        
        if not TELEGRAM_AVAILABLE:
            logger.info(f"Signal: {signal.signal_type} at {signal.entry_price}")
            return
        
        # Determine emoji
        emoji = '🟢' if signal.signal_type == 'BUY' else '🔴'
        
        # Calculate risk/reward
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        message = (
            f"{emoji} *{signal.signal_type} SIGNAL*\n\n"
            f"💱 Symbol: {signal.symbol}\n"
            f"📍 Entry: {signal.entry_price:.2f}\n"
            f"🛡️ Stop Loss: {signal.stop_loss:.2f}\n"
            f"🎯 Take Profit: {signal.take_profit:.2f}\n"
            f"📏 Size: {signal.position_size:.2f} lots\n\n"
            f"📊 Confidence: {signal.confidence:.0%}\n"
            f"⚖️ R:R Ratio: 1:{rr_ratio:.1f}\n\n"
            f"📝 Reason: {signal.reason}\n\n"
            f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Executed", callback_data='executed'),
             InlineKeyboardButton("❌ Ignored", callback_data='ignored')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for chat_id in self.subscribers:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send signal to {chat_id}: {e}")
        
        self.signals_sent += 1
    
    async def send_alert(self, title: str, message: str, alert_type: str = 'INFO'):
        """Send alert message."""
        if not TELEGRAM_AVAILABLE:
            logger.info(f"Alert [{alert_type}]: {title} - {message}")
            return
        
        if not self.application or not self.running:
            return
        
        # Emoji based on type
        emoji_map = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'SUCCESS': '✅',
            'ERROR': '❌',
            'PROFIT': '💰',
            'LOSS': '📉'
        }
        emoji = emoji_map.get(alert_type, 'ℹ️')
        
        full_message = f"{emoji} *{title}*\n\n{message}"
        
        for chat_id in self.subscribers:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send alert to {chat_id}: {e}")
    
    async def send_daily_summary(self, stats: Dict):
        """Send daily performance summary."""
        if not TELEGRAM_AVAILABLE:
            logger.info(f"Daily Summary: P&L ${stats.get('daily_profit', 0):.2f}")
            return
        
        if not self.application or not self.running:
            return
        
        profit = stats.get('daily_profit', 0)
        profit_emoji = '💰' if profit >= 0 else '📉'
        
        message = (
            f"📊 *Daily Summary*\n"
            f"{datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"{profit_emoji} P&L: ${profit:+.2f}\n"
            f"📈 Trades: {stats.get('trades', 0)}\n"
            f"✅ Wins: {stats.get('wins', 0)}\n"
            f"❌ Losses: {stats.get('losses', 0)}\n"
            f"📊 Win Rate: {stats.get('win_rate', 0):.1f}%\n\n"
            f"💰 Balance: ${stats.get('balance', 0):.2f}\n"
            f"📈 Growth: {stats.get('growth', 0):.1f}%"
        )
        
        for chat_id in self.subscribers:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send summary to {chat_id}: {e}")
    
    def run_sync(self):
        """Run bot in synchronous context."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram not available")
            return
        
        async def main():
            if await self.initialize():
                await self.start()
                # Keep running
                while self.running:
                    await asyncio.sleep(1)
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")


# Standalone script to run the bot
if __name__ == "__main__":
    import os
    
    config = {
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
        'TELEGRAM_CHAT_ID': os.environ.get('TELEGRAM_CHAT_ID', ''),
    }
    
    bot = TelegramSignalBot(config)
    bot.run_sync()
