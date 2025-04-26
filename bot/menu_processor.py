import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

poll_data = {}

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
                type="regular"
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
