"""
Message and callback handlers for the Telegram Food Poll Bot.
"""

import logging
import asyncio
from collections import Counter
from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, filters, CallbackQueryHandler, CommandHandler
)
from .config import (
    WELCOME_MESSAGE, DAILY_MESSAGE, ERROR_POLL_NOT_FOUND, 
    ERROR_NO_ORDERS, ERROR_NO_SELECTION, ORDER_NAME, CLOSE_ORDER_BUTTON_TEXT
)
from .utils import is_food_menu_text, format_order_summary, with_retry
from .menu_processor import (
    process_food_menu, get_menu_data, get_global_orders, 
    update_user_quantity, get_user_selections, hide_order_buttons, update_menu_display, process_user_vote,
    get_combined_orders, get_combined_user_selections, validate_user_selections, get_user_total_selections,
    reset_user_selections, get_user_quantities, get_pending_selections_count
)
from .scheduler import send_scheduled_message, add_chat_for_scheduled_messages

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming messages and forwarded messages.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.info(f"Received message: {update.message.text if update.message and update.message.text else 'No text'}")
    
    if not update.message or not update.message.text:
        logger.info("No message or no text, skipping")
        return
    
    text = update.message.text.strip()
    logger.info(f"Processing text: {repr(text)}")
    
    # Check if this is a food menu text
    if is_food_menu_text(text):
        logger.info(f"Processing food menu from user {update.effective_user.id}")
        await process_food_menu(update, context, text)
    else:
        logger.info(f"Text not recognized as food menu: {repr(text)}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle button clicks (quantity selection, vote, order, close order).
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    if not query.data:
        return
    
    # Handle quantity selection
    if query.data.startswith("qty_"):
        await handle_quantity_selection(update, context, query)
    
    # Handle vote button
    elif query.data.startswith("vote_"):
        await handle_vote_button(update, context, query)
    
    # Handle reset button
    elif query.data.startswith("reset_"):
        await handle_reset_button(update, context, query)
    
    # Handle Order button
    elif query.data.startswith("order_"):
        await handle_order_button(update, context, query)
    
    # Handle Close Order button
    elif query.data.startswith("close_order_"):
        await handle_close_order_button(update, context, query)

async def handle_quantity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """
    Handle quantity selection for menu items.
    
    Args:
        update: Telegram update object
        context: Bot context
        query: Callback query
    """
    try:
        # Parse callback data: qty_menu_id_item_index_quantity
        parts = query.data.split("_")
        if len(parts) < 5:
            logger.warning(f"Invalid quantity callback data: {query.data}")
            return
        
        # Reconstruct menu_id (everything between qty and the last two parts)
        menu_id_parts = parts[1:-2]  # Remove 'qty' and last two parts (item_index, quantity)
        menu_id = "_".join(menu_id_parts)
        item_index = int(parts[-2])
        quantity = int(parts[-1])
        
        user_id = query.from_user.id
        user_name = query.from_user.full_name or query.from_user.username or f'User{user_id}'
        
        # Validate quantity
        if quantity <= 0 or quantity > 10:  # Limit to reasonable quantities
            await query.answer("❌ Invalid quantity selected!", show_alert=True)
            return
        
        # Update user quantity (pending - not counted until vote)
        update_user_quantity(menu_id, user_id, item_index, quantity, user_name)
        
        # Provide feedback to user
        menu_info = get_menu_data(menu_id)
        options = menu_info.get("options", [])
        if item_index < len(options):
            item_name = options[item_index]
            # Get user's pending selections
            pending_count = get_user_total_selections(menu_id, user_id)
            await query.answer(f"✅ {quantity}x {item_name[:15]}... (Pending: {pending_count} items - Click Vote to confirm)", show_alert=False)
        
        # Don't update menu display here - quantities are only shown after voting
        logger.info(f"User {user_name} selected quantity {quantity} for item {item_index} in menu {menu_id} (pending vote)")
        
    except Exception as e:
        logger.error(f"Error handling quantity selection: {e}")
        await query.answer("❌ Error processing selection!", show_alert=True)

async def handle_vote_button(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """
    Handle vote button click - process vote and show confirmation for 3 seconds.
    
    Args:
        update: Telegram update object
        context: Bot context
        query: Callback query
    """
    try:
        # Parse callback data: vote_menu_id
        parts = query.data.split("_")
        if len(parts) < 2:
            logger.warning(f"Invalid vote callback data: {query.data}")
            return
        
        # Reconstruct menu_id (everything after 'vote')
        menu_id = "_".join(parts[1:])
        user_id = query.from_user.id
        
        # Get menu data
        menu_data = get_menu_data(menu_id)
        if not menu_data:
            logger.warning(f"Menu not found for vote callback: {menu_id}")
            return
        
        # Validate user has made selections
        if not validate_user_selections(menu_id, user_id):
            await query.answer("❗ You haven't selected any food yet!", show_alert=True)
            return
        
        # Get total selections for validation
        total_selections = get_user_total_selections(menu_id, user_id)
        if total_selections == 0:
            await query.answer("❗ You haven't selected any food yet!", show_alert=True)
            return
        
        # Process the user's vote
        vote_success = process_user_vote(menu_id, user_id)
        if not vote_success:
            await query.answer("❌ You have already voted or no selections found!", show_alert=True)
            return
        
        # Temporarily change vote button to "✅ Confirm"
        from .menu_processor import create_quantity_keyboard
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        options = menu_data.get("options", [])
        keyboard = create_quantity_keyboard(menu_id, options)
        
        # Replace the last row (vote button) with confirmation
        keyboard[-1] = [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{menu_id}")]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message
        await with_retry(
            context.bot.edit_message_reply_markup,
            chat_id=menu_data.get("chat_id"),
            message_id=menu_data.get("message_id"),
            reply_markup=reply_markup
        )
        
        # Wait 3 seconds and revert back to "Vote"
        await asyncio.sleep(3)
        
        # Update the menu display with new quantities
        await update_menu_display(context, menu_id)
        
        logger.info(f"Vote button clicked for menu {menu_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling vote button: {e}")

async def handle_reset_button(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """
    Handle reset button click - clear user's selections.
    
    Args:
        update: Telegram update object
        context: Bot context
        query: Callback query
    """
    try:
        # Parse callback data: reset_menu_id
        parts = query.data.split("_")
        if len(parts) < 2:
            logger.warning(f"Invalid reset callback data: {query.data}")
            return
        
        # Reconstruct menu_id (everything after 'reset')
        menu_id = "_".join(parts[1:])
        user_id = query.from_user.id
        
        # Get menu data
        menu_data = get_menu_data(menu_id)
        if not menu_data:
            logger.warning(f"Menu not found for reset callback: {menu_id}")
            return
        
        # Reset user selections
        reset_user_selections(menu_id, user_id)
        
        # Update the menu display
        await update_menu_display(context, menu_id)
        
        # Provide feedback to user
        await query.answer("🗑️ Your selections have been reset!", show_alert=True)
        
        logger.info(f"Reset button clicked for menu {menu_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling reset button: {e}")
        await query.answer("❌ Error resetting selections!", show_alert=True)

async def handle_order_button(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """
    Handle Order button click.
    
    Args:
        update: Telegram update object
        context: Bot context
        query: Callback query
    """
    try:
        # Parse callback data: order_menu_id
        parts = query.data.split("_")
        if len(parts) < 2:
            logger.warning(f"Invalid order callback data: {query.data}")
            return
        
        # Reconstruct menu_id (everything after 'order')
        menu_id = "_".join(parts[1:])
        
        # Check if menu exists
        menu_data = get_menu_data(menu_id)
        if not menu_data:
            logger.warning(f"Menu not found for order callback: {menu_id}")
            await query.message.reply_text(ERROR_POLL_NOT_FOUND)
            return
        
        # Get only voted orders (not pending selections)
        order_items = get_global_orders(menu_id)
        order_items = {item: count for item, count in order_items.items() if count > 0}
        
        if not order_items:
            await query.message.reply_text(ERROR_NO_ORDERS)
            return
        
        # Get only voted user selections for detail
        user_selections_data = get_user_selections(menu_id)
        # Filter to only include users who have actually voted
        voted_user_selections = {}
        user_quants = get_user_quantities(menu_id)
        
        for user_id, user_data in user_selections_data.items():
            if user_id in user_quants:  # Only include users who have voted
                voted_user_selections[user_id] = user_data.copy()
                voted_user_selections[user_id]['quantities'] = user_quants[user_id].copy()
        
        # Format and send order summary with only voted user details
        order_summary = format_order_summary(order_items, ORDER_NAME, voted_user_selections)
        
        try:
            await with_retry(query.message.reply_text, order_summary)
            logger.info(f"Order summary sent for menu {menu_id} with {len(order_items)} items")
        except Exception as e:
            logger.error(f"Error sending order summary: {e}")
            await query.message.reply_text(f"Error sending order summary: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error handling order button: {e}")

async def handle_close_order_button(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """
    Handle Close Order button click.
    
    Args:
        update: Telegram update object
        context: Bot context
        query: Callback query
    """
    try:
        # Parse callback data: close_order_menu_id
        parts = query.data.split("_")
        if len(parts) < 3:
            logger.warning(f"Invalid close order callback data: {query.data}")
            return
        
        # Reconstruct menu_id (everything after 'close_order')
        menu_id = "_".join(parts[2:])
        
        # Get user information
        user_id = query.from_user.id
        user_name = query.from_user.full_name or query.from_user.username or f'User{user_id}'
        
        # Check if menu exists
        menu_data = get_menu_data(menu_id)
        if not menu_data:
            logger.warning(f"Menu not found for close order callback: {menu_id}")
            await query.message.reply_text(ERROR_POLL_NOT_FOUND)
            return
        
        try:
            # Hide the order buttons
            await hide_order_buttons(context, menu_id)
            
            # Send confirmation message with user's name
            close_message = f"✅ Order has been closed.\nBy: {user_name}"
            await query.message.reply_text(close_message)
            logger.info(f"Order closed for menu {menu_id} by user {user_name} ({user_id})")
            
        except Exception as e:
            logger.error(f"Error closing order for menu {menu_id}: {e}")
            await query.message.reply_text(f"Error closing order: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error handling close order button: {e}")

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        # Add chat to scheduled messages
        add_chat_for_scheduled_messages(update.effective_chat.id)
        await update.message.reply_text(WELCOME_MESSAGE)
        logger.info(f"Start command received from user {update.effective_user.id}")
        logger.info(f"Username: {update.effective_user.full_name}")
    except Exception as e:
        logger.error(f"Error handling start command: {e}")

async def handle_debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /debug_send command for testing.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        await send_scheduled_message(context)
        await update.message.reply_text("Debug message sent!")
        logger.info("Debug message sent manually")
    except Exception as e:
        logger.error(f"Error in debug command: {e}")

def setup_handlers(application):
    """
    Register all handlers to the bot application.
    
    Args:
        application: Telegram bot application
    """
    # Command handlers
    application.add_handler(CommandHandler("start", handle_start_command))
    application.add_handler(CommandHandler("debug_send", handle_debug_command))
    
    # Message handlers (handle all text messages except commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("All handlers registered successfully")

