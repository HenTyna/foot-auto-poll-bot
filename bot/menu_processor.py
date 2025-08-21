"""
Menu processing functionality for the Telegram Food Poll Bot.
"""

import logging
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .config import ORDER_BUTTON_TEXT, CLOSE_ORDER_BUTTON_TEXT, ERROR_POLL_CREATION
from .utils import with_retry, extract_menu_options, format_visual_menu

logger = logging.getLogger(__name__)

# Global storage for menu data
menu_data: Dict[str, Dict[str, Any]] = {}
global_orders: Dict[str, Dict[str, int]] = {}
user_selections: Dict[str, Dict[int, Dict[str, Any]]] = {}
user_quantities: Dict[str, Dict[int, Dict[str, int]]] = {}  # Track user quantities per item
pending_selections: Dict[str, Dict[int, Dict[str, int]]] = {}  # Track pending selections before voting

# Track if order button is already used for each menu
order_button_used: Dict[str, bool] = {}

async def process_food_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """
    Process text that contains a food menu and create a visual menu interface.
    
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
        # Create menu ID (using timestamp and chat ID)
        import time
        menu_id = f"menu_{update.effective_chat.id}_{int(time.time())}"
        
        # Create visual menu text
        menu_text = format_visual_menu(text, options)
        
        # Create quantity buttons for each menu item
        keyboard = create_quantity_keyboard(menu_id, options)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the visual menu
        message = await with_retry(
            context.bot.send_message,
            chat_id=update.effective_chat.id,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        # Store menu data
        menu_data[menu_id] = {
            "options": options,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "created_at": update.message.date if update.message else None,
            "button_message_id": None,
            "original_text": text
        }
        
        # Initialize global order counts
        global_orders[menu_id] = {option: 0 for option in options}
        
        # Initialize user selections and quantities
        user_selections[menu_id] = {}
        user_quantities[menu_id] = {}

        # Initialize order button used flag
        order_button_used[menu_id] = False
        
        # Add Order and Close Order buttons
        order_keyboard = [
            [
                InlineKeyboardButton(ORDER_BUTTON_TEXT, callback_data=f"order_{menu_id}"),
                InlineKeyboardButton(CLOSE_ORDER_BUTTON_TEXT, callback_data=f"close_order_{menu_id}")
            ]
        ]
        order_reply_markup = InlineKeyboardMarkup(order_keyboard)
        
        # Send button message and store its ID
        button_message = await with_retry(
            context.bot.send_message,
            chat_id=update.effective_chat.id,
            text="ចុចប៊ូតុងខាងក្រោមដើម្បីបញ្ជាទិញ",
            reply_markup=order_reply_markup,
            reply_to_message_id=message.message_id
        )
        
        # Store the button message ID for later editing
        menu_data[menu_id]["button_message_id"] = button_message.message_id
        
        logger.info(f"Created visual menu with {len(options)} options: {options}")
        
    except Exception as e:
        logger.error(f"Error creating visual menu: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ERROR_POLL_CREATION.format(str(e))
        )

def create_quantity_keyboard(menu_id: str, options: List[str]) -> List[List[InlineKeyboardButton]]:
    """
    Create keyboard with quantity buttons for each menu item.
    
    Args:
        menu_id: ID of the menu
        options: List of menu options
        
    Returns:
        List of keyboard rows
    """
    keyboard = []
    
    # Add quantity buttons for each menu item in horizontal layout
    for i, option in enumerate(options):
        row = []
        # Add quantity buttons (1-3) for this menu item with item name
        for qty in range(1, 4):  # Buttons for quantities 1-3
            # Truncate item name if too long for button
            item_name = option[:15] + "..." if len(option) > 15 else option
            button_text = f"{item_name} {qty}"
            callback_data = f"qty_{menu_id}_{i}_{qty}"
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(row)
    
    # Add vote and reset buttons
    keyboard.append([
        InlineKeyboardButton("🗑️ Reset", callback_data=f"reset_{menu_id}"),
        InlineKeyboardButton("Vote", callback_data=f"vote_{menu_id}")
    ])
    
    return keyboard

def get_menu_data(menu_id: str) -> Dict[str, Any]:
    """Get menu data by menu ID."""
    return menu_data.get(menu_id, {})

def get_global_orders(menu_id: str) -> Dict[str, int]:
    """Get global order counts for a menu."""
    return global_orders.get(menu_id, {})

def get_user_selections(menu_id: str) -> Dict[int, Dict[str, Any]]:
    """Get user selections for a menu."""
    return user_selections.get(menu_id, {})

def get_user_quantities(menu_id: str) -> Dict[int, Dict[str, int]]:
    """Get user quantities for a menu."""
    return user_quantities.get(menu_id, {})

def update_user_quantity(menu_id: str, user_id: int, item_index: int, quantity: int, user_name: str = None) -> None:
    """
    Update user's pending quantity for a specific menu item (not counted until vote).
    
    Args:
        menu_id: ID of the menu
        user_id: ID of the user
        item_index: Index of the menu item
        quantity: Quantity selected
        user_name: Name of the user (optional)
    """
    if menu_id not in pending_selections:
        pending_selections[menu_id] = {}
    
    if user_id not in pending_selections[menu_id]:
        pending_selections[menu_id][user_id] = {}
    
    menu_info = menu_data.get(menu_id, {})
    options = menu_info.get("options", [])
    
    if item_index < len(options):
        item_name = options[item_index]
        pending_selections[menu_id][user_id][item_name] = quantity
        
        # Update user selections (but don't update global orders yet)
        if menu_id not in user_selections:
            user_selections[menu_id] = {}
        
        user_selections[menu_id][user_id] = {
            'name': user_name or f'User{user_id}',
            'quantities': pending_selections[menu_id][user_id].copy()
        }
        
        # Don't update global orders here - only after vote
        logger.info(f"User {user_name} selected quantity {quantity} for {item_name} (pending vote)")

def process_user_vote(menu_id: str, user_id: int) -> bool:
    """
    Process user vote - move pending selections to actual quantities and update global orders.
    
    Args:
        menu_id: ID of the menu
        user_id: ID of the user
        
    Returns:
        True if vote was processed successfully, False if user already voted or no pending selections
    """
    # Check if user already voted
    if menu_id in user_quantities and user_id in user_quantities[menu_id]:
        logger.info(f"User {user_id} already voted for menu {menu_id}")
        return False
    
    if menu_id not in pending_selections or user_id not in pending_selections[menu_id]:
        logger.info(f"No pending selections for user {user_id} in menu {menu_id}")
        return False
    
    # Move pending selections to actual quantities
    if menu_id not in user_quantities:
        user_quantities[menu_id] = {}
    
    user_quantities[menu_id][user_id] = pending_selections[menu_id][user_id].copy()
    
    # Update global orders
    update_global_orders_from_user_quantities(menu_id)
    
    # Clear pending selections for this user
    del pending_selections[menu_id][user_id]
    
    logger.info(f"User {user_id} vote processed for menu {menu_id}")
    return True

def update_global_orders_from_user_quantities(menu_id: str) -> None:
    """Update global order counts based on all user quantities."""
    if menu_id not in global_orders:
        global_orders[menu_id] = {}
    
    # Reset global orders
    menu_info = menu_data.get(menu_id, {})
    options = menu_info.get("options", [])
    global_orders[menu_id] = {option: 0 for option in options}
    
    # Sum up all user quantities
    user_quants = user_quantities.get(menu_id, {})
    for user_id, user_items in user_quants.items():
        for item_name, quantity in user_items.items():
            if item_name in global_orders[menu_id]:
                global_orders[menu_id][item_name] += quantity

def update_global_orders(menu_id: str, item: str, increment: int) -> None:
    """Update global order count for an item."""
    if menu_id not in global_orders:
        global_orders[menu_id] = {}
    
    if item not in global_orders[menu_id]:
        global_orders[menu_id][item] = 0
    
    global_orders[menu_id][item] = max(0, global_orders[menu_id][item] + increment)

def is_order_button_used(menu_id: str) -> bool:
    """Check if the order button has already been used for this menu."""
    return order_button_used.get(menu_id, False)

def set_order_button_used(menu_id: str) -> None:
    """Mark the order button as used for this menu."""
    order_button_used[menu_id] = True

async def hide_order_buttons(context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    """
    Hide the order buttons by editing the message to remove the inline keyboard.
    
    Args:
        context: Bot context
        menu_id: ID of the menu
    """
    menu_info = menu_data.get(menu_id)
    if not menu_info:
        logger.warning(f"Menu data not found for hiding buttons: {menu_id}")
        return
    
    button_message_id = menu_info.get("button_message_id")
    chat_id = menu_info.get("chat_id")
    
    if not button_message_id or not chat_id:
        logger.warning(f"Button message ID or chat ID not found for menu {menu_id}")
        return
    
    try:
        # Edit the message to remove the inline keyboard
        await with_retry(
            context.bot.edit_message_reply_markup,
            chat_id=chat_id,
            message_id=button_message_id,
            reply_markup=None
        )
        
        # Mark the order button as used
        set_order_button_used(menu_id)
        
        logger.info(f"Order buttons hidden for menu {menu_id}")
        
    except Exception as e:
        logger.error(f"Error hiding order buttons for menu {menu_id}: {e}")

async def update_menu_display(context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    """
    Update the menu display with current quantities.
    
    Args:
        context: Bot context
        menu_id: ID of the menu
    """
    menu_info = menu_data.get(menu_id)
    if not menu_info:
        logger.warning(f"Menu data not found for updating display: {menu_id}")
        return
    
    message_id = menu_info.get("message_id")
    chat_id = menu_info.get("chat_id")
    original_text = menu_info.get("original_text", "")
    options = menu_info.get("options", [])
    
    if not message_id or not chat_id:
        logger.warning(f"Message ID or chat ID not found for menu {menu_id}")
        return
    
    try:
        # Create updated menu text with combined quantities (including pending selections)
        combined_quantities = get_combined_orders(menu_id)
        updated_menu_text = format_visual_menu(original_text, options, combined_quantities)
        
        # Create updated keyboard
        keyboard = create_quantity_keyboard(menu_id, options)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message
        await with_retry(
            context.bot.edit_message_text,
            chat_id=chat_id,
            message_id=message_id,
            text=updated_menu_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Updated menu display for {menu_id}")
        
    except Exception as e:
        logger.error(f"Error updating menu display for {menu_id}: {e}")

def get_combined_orders(menu_id: str) -> Dict[str, int]:
    """
    Get combined order counts including both voted and pending selections.
    
    Args:
        menu_id: ID of the menu
        
    Returns:
        Dictionary mapping item names to total quantities
    """
    combined_orders = {}
    
    # Get menu options
    menu_info = menu_data.get(menu_id, {})
    options = menu_info.get("options", [])
    
    # Initialize with zeros
    for option in options:
        combined_orders[option] = 0
    
    # Add quantities from voted users
    user_quants = user_quantities.get(menu_id, {})
    for user_id, user_items in user_quants.items():
        for item_name, quantity in user_items.items():
            if item_name in combined_orders:
                combined_orders[item_name] += quantity
    
    # Add quantities from pending selections (only for users who haven't voted yet)
    pending = pending_selections.get(menu_id, {})
    for user_id, user_items in pending.items():
        # Only add pending selections if user hasn't voted yet
        if user_id not in user_quants:
            for item_name, quantity in user_items.items():
                if item_name in combined_orders:
                    combined_orders[item_name] += quantity
    
    return combined_orders

def get_combined_user_selections(menu_id: str) -> Dict[int, Dict[str, Any]]:
    """
    Get combined user selections including both voted and pending users.
    
    Args:
        menu_id: ID of the menu
        
    Returns:
        Dictionary mapping user_id to user data
    """
    combined_selections = {}
    
    # Add voted users first (these take priority)
    user_quants = user_quantities.get(menu_id, {})
    user_selections_data = user_selections.get(menu_id, {})
    
    for user_id, user_items in user_quants.items():
        if user_id in user_selections_data:
            combined_selections[user_id] = user_selections_data[user_id].copy()
            combined_selections[user_id]['quantities'] = user_items.copy()
            combined_selections[user_id]['voted'] = True
    
    # Add pending users (only if they haven't voted yet)
    pending = pending_selections.get(menu_id, {})
    for user_id, user_items in pending.items():
        # Only add if user hasn't already voted
        if user_id not in combined_selections and user_id in user_selections_data:
            combined_selections[user_id] = user_selections_data[user_id].copy()
            combined_selections[user_id]['quantities'] = user_items.copy()
            combined_selections[user_id]['voted'] = False
    
    return combined_selections

def validate_user_selections(menu_id: str, user_id: int) -> bool:
    """
    Validate if user has made any selections.
    
    Args:
        menu_id: ID of the menu
        user_id: ID of the user
        
    Returns:
        True if user has selections, False otherwise
    """
    # Check pending selections
    pending = pending_selections.get(menu_id, {}).get(user_id, {})
    if any(qty > 0 for qty in pending.values()):
        return True
    
    # Check voted selections
    user_quants = user_quantities.get(menu_id, {}).get(user_id, {})
    if any(qty > 0 for qty in user_quants.values()):
        return True
    
    return False

def get_user_total_selections(menu_id: str, user_id: int) -> int:
    """
    Get total number of items selected by user.
    
    Args:
        menu_id: ID of the menu
        user_id: ID of the user
        
    Returns:
        Total number of items selected
    """
    total = 0
    
    # Count pending selections
    pending = pending_selections.get(menu_id, {}).get(user_id, {})
    total += sum(pending.values())
    
    # Count voted selections
    user_quants = user_quantities.get(menu_id, {}).get(user_id, {})
    total += sum(user_quants.values())
    
    return total

def reset_user_selections(menu_id: str, user_id: int) -> None:
    """
    Reset user's pending selections.
    
    Args:
        menu_id: ID of the menu
        user_id: ID of the user
    """
    # Clear pending selections
    if menu_id in pending_selections and user_id in pending_selections[menu_id]:
        del pending_selections[menu_id][user_id]
    
    # Clear user selections
    if menu_id in user_selections and user_id in user_selections[menu_id]:
        del user_selections[menu_id][user_id]
    
    # Clear user quantities (if they haven't voted yet)
    if menu_id in user_quantities and user_id in user_quantities[menu_id]:
        del user_quantities[menu_id][user_id]
        # Update global orders after removing user
        update_global_orders_from_user_quantities(menu_id)
    
    logger.info(f"User {user_id} selections reset for menu {menu_id}")
