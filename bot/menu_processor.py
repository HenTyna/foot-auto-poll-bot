"""
Menu processing functionality for the Telegram Food Poll Bot.
"""

import logging
from typing import Dict, Any
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .config import POLL_QUESTION, ORDER_BUTTON_TEXT, ORDER_INSTRUCTION_TEXT, ERROR_POLL_CREATION
from .utils import with_retry, extract_menu_options

logger = logging.getLogger(__name__)

# Global storage for poll data
poll_data: Dict[str, Dict[str, Any]] = {}
global_orders: Dict[str, Dict[str, int]] = {}
user_selections: Dict[str, Dict[int, Dict[str, Any]]] = {}  # Changed to store user data

# Track if order button is already used for each poll
order_button_used: Dict[str, bool] = {}

async def process_food_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """
    Process text that contains a food menu and create a poll.
    
    Args:
        update: Telegram update object
        context: Bot context
        text: Text containing menu items
    """
    options = extract_menu_options(text)
    
    if len(options) < 2:
        logger.warning(f"Not enough menu options found in text: {len(options)} options")
        return
    
    try:
        # Create poll
        message = await with_retry(
            context.bot.send_poll,
            chat_id=update.effective_chat.id,
            question=POLL_QUESTION,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=True,
            type=Poll.REGULAR
        )
        
        # Store poll data
        poll_data[message.poll.id] = {
            "options": options,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "created_at": update.message.date if update.message else None
        }
        
        # Initialize global order counts
        global_orders[message.poll.id] = {option: 0 for option in options}
        
        # Initialize user selections
        user_selections[message.poll.id] = {}

        # Initialize order button used flag
        order_button_used[message.poll.id] = False
        
        # Add Order button
        keyboard = [[InlineKeyboardButton(ORDER_BUTTON_TEXT, callback_data=f"order_{message.poll.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await with_retry(
            context.bot.send_message,
            chat_id=update.effective_chat.id,
            text=ORDER_INSTRUCTION_TEXT,
            reply_markup=reply_markup,
            reply_to_message_id=message.message_id
        )
        
        logger.info(f"Created poll with {len(options)} options: {options}")
        
    except Exception as e:
        logger.error(f"Error creating poll: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ERROR_POLL_CREATION.format(str(e))
        )

def get_poll_data(poll_id: str) -> Dict[str, Any]:
    """Get poll data by poll ID."""
    return poll_data.get(poll_id, {})

def get_global_orders(poll_id: str) -> Dict[str, int]:
    """Get global order counts for a poll."""
    return global_orders.get(poll_id, {})

def get_user_selections(poll_id: str) -> Dict[int, Dict[str, Any]]:
    """Get user selections for a poll."""
    return user_selections.get(poll_id, {})

def update_user_selection(poll_id: str, user_id: int, selected_options: list, user_name: str = None) -> None:
    """
    Update user's selection for a poll.
    
    Args:
        poll_id: ID of the poll
        user_id: ID of the user
        selected_options: List of selected menu items
        user_name: Name of the user (optional)
    """
    if poll_id not in user_selections:
        user_selections[poll_id] = {}
    
    # Store user data with selections and name
    user_selections[poll_id][user_id] = {
        'selections': selected_options,
        'name': user_name or f'User{user_id}'
    }

def update_global_orders(poll_id: str, item: str, increment: int) -> None:
    """Update global order count for an item."""
    if poll_id not in global_orders:
        global_orders[poll_id] = {}
    
    if item not in global_orders[poll_id]:
        global_orders[poll_id][item] = 0
    
    global_orders[poll_id][item] = max(0, global_orders[poll_id][item] + increment)

def is_order_button_used(poll_id: str) -> bool:
    """Check if the order button has already been used for this poll."""
    return order_button_used.get(poll_id, False)

def set_order_button_used(poll_id: str) -> None:
    """Mark the order button as used for this poll."""
    order_button_used[poll_id] = True
