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
user_selections = {}  # Track user selections
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
            await asyncio.sleep(2**attempt)

async def process_food_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Process text that contains a food menu and create a poll"""
    options = []
    # Look for lines starting with Khmer numbers (១២៣៤៥៦) or standard numbers (1-6) followed by a dot
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^[១២៣៤៥៦1-6]\.\s*.+', line):
            option_text = re.sub(r'^[១២៣៤៥៦1-6]\.\s*', '', line)
            if option_text and option_text not in options:
                options.append(option_text)

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
                "default_options": []  # No default options
            }

            # Initialize global order counts
            global_orders[message.poll.id] = {option: 0 for option in options}

            # Initialize user selections
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

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update global order counts based on poll responses"""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    selected_options = poll_answer.option_ids

    if poll_id not in poll_data or poll_id not in global_orders:
        return

    options = poll_data[poll_id]["options"]

    if user_id not in user_selections.get(poll_id, {}):
        user_selections[poll_id][user_id] = []

    previous_selections = user_selections[poll_id][user_id]
    current_selections = [options[idx] for idx in selected_options if idx < len(options)]
    user_selections[poll_id][user_id] = current_selections

    newly_selected = [item for item in current_selections if item not in previous_selections]
    newly_unselected = [item for item in previous_selections if item not in current_selections]

    for item in newly_selected:
        global_orders[poll_id][item] += 1

    for item in newly_unselected:
        global_orders[poll_id][item] = max(0, global_orders[poll_id][item] - 1)

async def order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Order button clicks"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    poll_id = callback_data.replace("order_", "")

    if poll_id not in global_orders or poll_id not in poll_data:
        await query.message.reply_text("ខ្ញុំមិនអាចរកឃើញការបោះឆ្នោតនេះទេ។")
        return

    order_items = {item: count for item, count in global_orders[poll_id].items() if count > 0}

    if not order_items:
        await query.message.reply_text("មិនមានការបញ្ជាទិញណាមួយឡើយ។")
        return

    order_lines = [f"- {item} x{qty}" for item, qty in order_items.items()]

    response = "\n".join([
        "🛒 Name: Seyha",
        "------------------",
        *order_lines,
        "------------------",
    ])

    await with_retry(query.message.reply_text, response)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat_ids_for_scheduled_messages.add(update.effective_chat.id)

    message = (
        "សួស្តី! ខ្ញុំជា Bot ដែលបង្កើត Poll ដោយស្វ័យប្រវត្តិ។\n\n"
        "របៀបប្រើប្រាស់៖\n"
        "១. ជ្រើសរើសមុខម្ហូបដែលអ្នកចង់ Order\n"
        "២. Vote មុខម្ហូបរបស់អ្នក\n"
        "៣. រង់ចាំការជ្រើសរើសរួចរាល់ រួចចុចប៊ូតុង Order 🛒"
    )

    await update.message.reply_text(message)

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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("debug_send", debug_send))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(order_callback, pattern=r'^order_'))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

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
