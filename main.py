#!/usr/bin/env python3
"""
Main entry point for the Telegram Food Poll Bot.

This script initializes and runs the bot with proper error handling.
"""

import sys
import logging
from bot import FoodPollBot

logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot."""
    try:
        # Create and setup bot
        bot = FoodPollBot()
        bot.setup()
        
        # Run the bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
