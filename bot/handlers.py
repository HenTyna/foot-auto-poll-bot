import re
from telegram.ext import MessageHandler, filters, PollAnswerHandler, CallbackQueryHandler
from .menu_processor import process_food_menu, poll_data
from collections import Counter
user_orders = {}

async def handle_message(update, context):
    """Handle incoming messages and forwarded messages."""
    if not update.message:
        return

    if update.message.text:
        text = update.message.text.strip()

        if text.startswith("ម្ហូបថ្ងៃ") or (
            re.search(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE) and
            len(re.findall(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE)) >= 2
        ):
            await process_food_menu(update, context, text)

    elif update.message.forward_date and update.message.text:
        text = update.message.text.strip()

        if text.startswith("ម្ហូបថ្ងៃ") or (
            re.search(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE) and
            len(re.findall(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE)) >= 2
        ):
            await process_food_menu(update, context, text)

async def handle_poll_answer(update, context):
    """Store user's poll selections."""
    poll_answer = update.poll_answer

    if not poll_answer.user:
        print("Error: No user information in poll answer")
        return

    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    selected_options = poll_answer.option_ids

    if poll_id in poll_data:
        options = poll_data[poll_id]["options"]
        user_orders[user_id] = [options[i] for i in selected_options]
        print(f"User {user_id} selected: {user_orders[user_id]}")

async def handle_callback_query(update, context):
    """Handle button clicks (e.g., Order button)."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("order_"):
        poll_id = query.data.split("_", 1)[1]
        user_id = query.from_user.id

        if user_id in user_orders:
            orders = user_orders[user_id]

            # Count quantity of each selected item
            order_counts = Counter(orders)

            order_text = "\n".join(f"- {item} x{qty}" for item, qty in order_counts.items())
            await query.message.reply_text(
                f"🛒 Seyha's Order:\n{order_text}"
            )
        else:
            await query.message.reply_text(
                "❗ You haven't selected any food yet!"
            )
def setup_handlers(app):
    """Register handlers to the bot."""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(PollAnswerHandler(handle_poll_answer)) # <-- Add this line
    app.add_handler(CallbackQueryHandler(handle_callback_query))  # <-- Add this line

