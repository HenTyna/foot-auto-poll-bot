import re
import asyncio
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
from telegram.error import NetworkError, TimedOut
import datetime
from typing import Dict, Any
import zoneinfo


BOT_TOKEN = "6886653495:AAHtoOIZrUvvfH_C39fcz8K5kUYMJbae3Uo"

# Store poll data and global order counts
poll_data = {}
global_orders = {}
user_selections = {}  # Track user selections to prevent double counting

# Default options to add to every poll
DEFAULT_OPTIONS = ["បាយស x1 (ថែម)"]  # Add your default food options here
chat_ids_for_scheduled_messages = set()
async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE):
    """Send scheduled message to all stored chat IDs"""
    print(f"Attempting to send scheduled message at {datetime.datetime.now()}")
    for chat_id in list(chat_ids_for_scheduled_messages):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="ថ្ងៃនេះបានម្ហូបអ្វី?"
            )
            print(f"Message sent to {chat_id}")
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

async def with_retry(func, *args, max_retries=3, **kwargs):
    """Execute a function with retry logic for network operations"""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (NetworkError, TimedOut) as e:
            if attempt == max_retries - 1:
                raise
            print(f"Network error: {e}. Retrying in {2**attempt} seconds...")
            await asyncio.sleep(2**attempt)  # Exponential backoff

async def process_food_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Process text that contains a food menu and create a poll with default options"""
    options = []
    # Look for lines starting with Khmer numbers (១២៣៤៥៦) or standard numbers (1-6) followed by a dot
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^[១២៣៤៥៦1-6]\.\s*.+', line):
            option_text = re.sub(r'^[១២៣៤៥៦1-6]\.\s*', '', line)
            if option_text and option_text not in options:  # Prevent duplicates
                options.append(option_text)

    # Add default options if they're not already in the list
    for default_option in DEFAULT_OPTIONS:
        if default_option not in options:
            options.append(default_option)

    if len(options) >= 2:
        try:
            message = await with_retry(
                context.bot.send_poll,
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
                "chat_id": update.effective_chat.id,
                "default_options": [option for option in options if option in DEFAULT_OPTIONS]
            }

            # Initialize global order counts for this poll
            global_orders[message.poll.id] = {}
            for option in options:
                # Set default counts for default options
                if option in DEFAULT_OPTIONS:
                    global_orders[message.poll.id][option] = 1  # Start with count of 1 for default options
                else:
                    global_orders[message.poll.id][option] = 0

            # Initialize user selections tracking for this poll
            user_selections[message.poll.id] = {}

            # Add Order button
            keyboard = [[InlineKeyboardButton("🛒 Order", callback_data=f"order_{message.poll.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await with_retry(
                context.bot.send_message,
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
    """Update global order counts based on poll responses, avoiding double counting defaults"""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    selected_options = poll_answer.option_ids

    if poll_id not in poll_data or poll_id not in global_orders:
        return

    # Get the poll options from stored data
    options = poll_data[poll_id]["options"]
    default_options = poll_data[poll_id].get("default_options", [])

    # Initialize user's previous selections if this is their first interaction with this poll
    if user_id not in user_selections.get(poll_id, {}):
        user_selections[poll_id][user_id] = []

    # Get user's previous selections
    previous_selections = user_selections[poll_id][user_id]

    # Save current selections for future reference
    current_selections = []
    for idx in selected_options:
        if idx < len(options):
            current_selections.append(options[idx])
    user_selections[poll_id][user_id] = current_selections

    # Calculate changes in selections
    newly_selected = [options[idx] for idx in selected_options if idx < len(options) and options[idx] not in previous_selections]
    newly_unselected = [item for item in previous_selections if item not in [options[idx] for idx in selected_options if idx < len(options)]]

    # Update counters - increment for newly selected items
    for item in newly_selected:
        # Don't increment for default items that already have a count of 1
        if item in default_options and global_orders[poll_id][item] == 1:
            # Skip incrementing if this is the default item's initial selection
            pass
        else:
            global_orders[poll_id][item] += 1

    # Update counters - decrement for unselected items
    for item in newly_unselected:
        # Don't decrement below 1 for default items
        if item in default_options and global_orders[poll_id][item] <= 1:
            # Keep default items at minimum count of 1
            global_orders[poll_id][item] = 1
        else:
            global_orders[poll_id][item] = max(0, global_orders[poll_id][item] - 1)


async def order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Order button clicks - shows global counts including default options"""
    query = update.callback_query
    await query.answer()

    # Extract poll_id from callback data
    callback_data = query.data
    poll_id = callback_data.replace("order_", "")

    # Check if this poll exists in our data
    if poll_id not in global_orders or poll_id not in poll_data:
        await query.message.reply_text("ខ្ញុំមិនអាចរកឃើញការបោះឆ្នោតនេះទេ។")
        return

    # Get all ordered items
    order_items = global_orders[poll_id]

    # Filter items with count greater than 0
    order_items = {item: count for item, count in order_items.items() if count > 0}

    if not order_items:
        await query.message.reply_text("មិនមានការបញ្ជាទិញណាមួយឡើយ។")
        return

    # Build order summary lines
    order_lines = [f"{item} ({qty})" for item, qty in order_items.items()]

    # Create the properly formatted response
    response = "\n".join([
        "🛒 Name: Seyha",
        "------------------",
        *order_lines,  # This unpacks all order lines
        "------------------",
    ])

    await with_retry(query.message.reply_text, response)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_ids_for_scheduled_messages.add(update.effective_chat.id)
    """Send a message when the command /start is issued."""
    await update.message.reply_text('សួស្តី! ខ្ញុំជាបូតដែលបង្កើត Poll ដោយស្វ័យប្រវត្តិ។')


async def set_defaults(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view or change default options"""
    global DEFAULT_OPTIONS

    if not context.args:
        # Show current defaults
        if DEFAULT_OPTIONS:
            defaults_text = ", ".join(DEFAULT_OPTIONS)
            await update.message.reply_text(f"Current default options: {defaults_text}")
        else:
            await update.message.reply_text("No default options set.")
        await update.message.reply_text("To set new defaults, use: /defaults option1, option2, ...")
        return

    # Join all arguments and split by commas
    new_defaults = " ".join(context.args).split(",")
    # Clean up whitespace
    new_defaults = [opt.strip() for opt in new_defaults if opt.strip()]

    if new_defaults:
        DEFAULT_OPTIONS = new_defaults
        defaults_text = ", ".join(DEFAULT_OPTIONS)
        await update.message.reply_text(f"Default options updated: {defaults_text}")
    else:
        await update.message.reply_text("Invalid format. Use: /defaults option1, option2, ...")

async def debug_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual trigger for testing"""
    await send_scheduled_message(context)
    await update.message.reply_text("Debug message sent!")

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

async def set_scheduler(context: ContextTypes.DEFAULT_TYPE):
    """Set up the scheduled message"""
    remove_job_if_exists("daily_message", context)

    phnom_penh_timezone = zoneinfo.ZoneInfo("Asia/Phnom_Penh")

    # Set time to 20:56 Phnom Penh time
    time = datetime.time(hour=8, minute=0, tzinfo=phnom_penh_timezone)

    context.job_queue.run_daily(
        send_scheduled_message,
        time=time,
        days=tuple(range(7)),
        name="daily_message"
    )
    print(f"Scheduled daily message for {time} (Phnom Penh time)")
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("debug_send", debug_send))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(order_callback, pattern=r'^order_'))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    # When the bot fully ready, then set scheduler
    async def post_init(application: Application):
        await set_scheduler(application)

    application.post_init = post_init

    print("Bot starting...")
    application.run_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.POLL_ANSWER,
            Update.CALLBACK_QUERY
        ]
    )
if __name__ == '__main__':
    main()