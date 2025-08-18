"""
Main bot class for the Telegram Food Poll Bot.
"""

import logging
import asyncio
from telegram.ext import Application
from .config import BOT_TOKEN, setup_logging
from .handlers import setup_handlers

logger = logging.getLogger(__name__)

class FoodPollBot:
    """
    Main bot class that handles the Telegram Food Poll Bot functionality.
    """
    
    def __init__(self):
        """Initialize the bot."""
        self.application = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        setup_logging()
        logger.info("Logging setup completed")
    
    def setup(self) -> None:
        """Setup the bot application and handlers."""
        try:
            # Create application without job queue to avoid weak reference issues
            self.application = (
                Application.builder()
                .token(BOT_TOKEN)
                .job_queue(None)  # Disable job queue to avoid weak reference issues
                .build()
            )
            
            # Setup handlers
            setup_handlers(self.application)
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup bot: {e}")
            raise
    
    def run(self) -> None:
        """Run the bot using the same approach as simple_bot.py."""
        if not self.application:
            raise RuntimeError("Bot not setup. Call setup() first.")
        
        try:
            # Start polling with minimal configuration (same as simple_bot.py)
            logger.info("Starting bot...")
            self.application.run_polling(drop_pending_updates=True)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise 