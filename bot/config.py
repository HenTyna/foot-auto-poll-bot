"""
Configuration settings for the Telegram Food Poll Bot.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Timezone Configuration
TIMEZONE = "Asia/Phnom_Penh"
SCHEDULED_MESSAGE_TIME = "08:00"  # 8 AM

# Menu Configuration
ORDER_BUTTON_TEXT = "🛒 Order"
CLOSE_ORDER_BUTTON_TEXT = "❌ Close Order"
ORDER_NAME = "Seyha"

# Message Templates
WELCOME_MESSAGE = """សួស្តី! ខ្ញុំជា Bot ដែលបង្កើត Menu ដោយស្វ័យប្រវត្តិ។

របៀបប្រើប្រាស់៖
១. ជ្រើសរើសបរិមាណម្ហូបដែលអ្នកចង់ Order
២. ចុចប៊ូតុង Vote ដើម្បីបញ្ជាក់
៣. រង់ចាំការជ្រើសរើសរួចរាល់ រួចចុចប៊ូតុង Order 🛒"""

DAILY_MESSAGE = "ថ្ងៃនេះបានម្ហូបអ្វី?"

# Error Messages
ERROR_POLL_CREATION = "មានបញ្ហាក្នុងការបង្កើត menu: {}"
ERROR_POLL_NOT_FOUND = "ខ្ញុំមិនអាចរកឃើញ menu នេះទេ។"
ERROR_NO_ORDERS = "មិនមានការបញ្ជាទិញណាមួយឡើយ។"
ERROR_NO_SELECTION = "❗ You haven't selected any food yet!"

def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
