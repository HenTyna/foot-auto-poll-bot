import re
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    PollAnswerHandler
)

BOT_TOKEN = "6886653495:AAHtoOIZrUvvfH_C39fcz8K5kUYMJbae3Uo"

# Store poll data and user selections
poll_data = {}
user_orders = {}


async def process_food_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Process text that contains a food menu and create a poll"""
    options = []
    # Look for lines starting with Khmer numbers (១២៣៤៥៦) or standard numbers (1-6) followed by a dot
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^[១២៣៤៥៦1-6]\.\s*.+', line):
            option_text = re.sub(r'^[១២៣៤៥៦1-6]\.\s*', '', line)
            if option_text:
                options.append(option_text)

    if len(options) >= 2:
        try:
            message = await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question="ជ្រើសរើសម្ហូបដែលអ្នកចូលចិត្ត!",
                options=options,
                is_anonymous=False,
                allows_multiple_answers=True,
                type=Poll.REGULAR
            )

            # Store poll data
            poll_data[message.poll.id] = {
                "options": options,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id
            }

            # Add Order button
            keyboard = [[InlineKeyboardButton("🛒 Order", callback_data=f"order_{message.poll.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="ចុចប៊ូតុងខាងក្រោមដើម្បីបញ្ជាទិញ៖",
                reply_markup=reply_markup,
                reply_to_message_id=message.message_id
            )

        except Exception as e:
            print(f"Error creating poll: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"មានបញ្ហាក្នុងការបង្កើត poll: {str(e)}"
            )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages, including forwarded ones"""
    if not update.message:
        return

    # Handle both regular and forwarded messages
    if update.message.text:
        text = update.message.text.strip()

        # Check if it's a food menu message (starting with "ម្ហូបថ្ងៃ" or contains menu-like format)
        if text.startswith("ម្ហូបថ្ងៃ") or (
                re.search(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE) and
                len(re.findall(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE)) >= 2
        ):
            await process_food_menu(update, context, text)

    # Check for forwarded message with text
    elif update.message.forward_date and update.message.text:
        text = update.message.text.strip()

        # Same check for forwarded messages
        if text.startswith("ម្ហូបថ្ងៃ") or (
                re.search(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE) and
                len(re.findall(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE)) >= 2
        ):
            await process_food_menu(update, context, text)


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store user's poll selections"""
    poll_answer = update.poll_answer

    # Safety check if user info is available
    if not poll_answer.user:
        print("Error: No user information in poll answer")
        return

    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    selected_options = poll_answer.option_ids

    if poll_id in poll_data:
        # Get the poll options from stored data
        options = poll_data[poll_id]["options"]

        # Count quantities of each selected item
        order_items = {}
        for idx in selected_options:
            if idx < len(options):
                item = options[idx]
                order_items[item] = order_items.get(item, 0) + 1

        # Get username safely
        username = "អតិថិជន"  # Default name
        if hasattr(poll_answer.user, 'first_name') and poll_answer.user.first_name:
            username = poll_answer.user.first_name

        user_orders[user_id] = {
            "poll_id": poll_id,
            "order_items": order_items,
            "username": username
        }

async def order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Order button clicks"""
    query = update.callback_query
    await query.answer()

    # Extract poll_id from callback data
    callback_data = query.data
    poll_id = callback_data.replace("order_", "")

    user_id = query.from_user.id

    # Check if user has made selections for THIS specific poll
    if user_id not in user_orders or user_orders[user_id].get("poll_id") != poll_id:
        await query.message.reply_text("សូមជ្រើសរើសមុនពេលបញ្ជាទិញ!")
        return

    order_info = user_orders[user_id]
    order_items = order_info["order_items"]

    if not order_items:
        await query.message.reply_text("អ្នកមិនបានជ្រើសរើសអ្វីទេ!")
        return

    # Build order summary lines
    order_lines = [f"{item} ({qty})" for item, qty in order_items.items()]

    # Get username from order info
    # username = order_info.get("username", "អតិថិជន")
    username = "🛒 Seyha's Order"  # Default name

    # Create the properly formatted response
    response = "\n".join([
        f"ឈ្មោះ​ {username}",
        "------------------",
        *order_lines,  # This unpacks all order lines
        "------------------",
    ])

    await query.message.reply_text(response)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('សួស្តី! ខ្ញុំជាបូតដែលបង្កើត Poll ដោយស្វ័យប្រវត្តិ។')

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Handle forwarded messages and regular text messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(order_callback, pattern=r'^order_'))
    application.add_handler(CommandHandler("start", start))

    # Handle poll answers
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    # Using a more specific allowed_updates parameter
    application.run_polling(allowed_updates=[
        Update.MESSAGE,
        Update.POLL_ANSWER,
        Update.CALLBACK_QUERY
    ])

if __name__ == '__main__':
    main()