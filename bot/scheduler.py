"""
Scheduler functionality for the Telegram Food Poll Bot.
"""

import datetime
import logging
import zoneinfo
from typing import Set
from telegram.ext import Application, ContextTypes
from .config import TIMEZONE, SCHEDULED_MESSAGE_TIME, DAILY_MESSAGE
from .utils import remove_job_if_exists

logger = logging.getLogger(__name__)

# Global storage for chat IDs (in production, this should be persistent)
chat_ids_for_scheduled_messages: Set[int] = set()

async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send scheduled message to all stored chat IDs.
    
    Args:
        context: Bot context
    """
    logger.info(f"Attempting to send scheduled message at {datetime.datetime.now()}")
    
    for chat_id in list(chat_ids_for_scheduled_messages):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=DAILY_MESSAGE
            )
            logger.info(f"Message sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")

def add_chat_for_scheduled_messages(chat_id: int) -> None:
    """
    Add a chat ID to receive scheduled messages.
    
    Args:
        chat_id: Telegram chat ID
    """
    chat_ids_for_scheduled_messages.add(chat_id)
    logger.info(f"Added chat {chat_id} for scheduled messages")

def remove_chat_from_scheduled_messages(chat_id: int) -> None:
    """
    Remove a chat ID from scheduled messages.
    
    Args:
        chat_id: Telegram chat ID
    """
    chat_ids_for_scheduled_messages.discard(chat_id)
    logger.info(f"Removed chat {chat_id} from scheduled messages")

async def setup_scheduler(application: Application) -> None:
    """
    Set up the scheduled message job.
    
    Args:
        application: Telegram bot application
    """
    # Remove existing job if it exists
    remove_job_if_exists("daily_message", application)
    
    # Parse scheduled time
    try:
        hour, minute = map(int, SCHEDULED_MESSAGE_TIME.split(':'))
        phnom_penh_timezone = zoneinfo.ZoneInfo(TIMEZONE)
        scheduled_time = datetime.time(hour=hour, minute=minute, tzinfo=phnom_penh_timezone)
        
        # Schedule daily message
        application.job_queue.run_daily(
            send_scheduled_message,
            time=scheduled_time,
            days=tuple(range(7)),  # All days of the week
            name="daily_message"
        )
        
        logger.info(f"Scheduled daily message for {scheduled_time} ({TIMEZONE} time)")
        
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")

def get_scheduled_chats() -> Set[int]:
    """
    Get all chat IDs that receive scheduled messages.
    
    Returns:
        Set of chat IDs
    """
    return chat_ids_for_scheduled_messages.copy() 