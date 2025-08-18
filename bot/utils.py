"""
Utility functions for the Telegram Food Poll Bot.
"""

import asyncio
import re
import logging
from typing import List, Dict, Any, Optional
from telegram.error import NetworkError, TimedOut
from telegram import Update
from telegram.ext import ContextTypes, Application

logger = logging.getLogger(__name__)

async def with_retry(func, *args, max_retries: int = 3, **kwargs):
    """Execute a function with retry logic for network operations."""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (NetworkError, TimedOut) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Network error: {e}. Retrying in {2**attempt} seconds...")
            await asyncio.sleep(2**attempt)

def extract_menu_options(text: str) -> List[str]:
    """
    Extract menu options from text that contains numbered items.
    
    Args:
        text: Text containing menu items with numbers
        
    Returns:
        List of menu options without numbers
    """
    options = []
    
    # Look for lines starting with Khmer numbers (១២៣៤៥៦) or standard numbers (1-6) followed by a dot
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^[១២៣៤៥៦1-6]\.\s*.+', line):
            option_text = re.sub(r'^[១២៣៤៥៦1-6]\.\s*', '', line)
            if option_text and option_text not in options:
                options.append(option_text)
    
    return options

def is_food_menu_text(text: str) -> bool:
    """
    Check if the given text appears to be a food menu.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a food menu, False otherwise
    """
    if not text:
        return False
        
    text = text.strip()
    
    # Check if it starts with "ម្ហូបថ្ងៃ" (today's food)
    if text.startswith("ម្ហូបថ្ងៃ"):
        return True
    
    # Check if it contains numbered menu items
    numbered_items = re.findall(r'^[១២៣៤៥៦1-6]\.\s*.+', text, re.MULTILINE)
    return len(numbered_items) >= 2

def format_order_summary(order_items: Dict[str, int], order_name: str = "Seyha") -> str:
    """
    Format order items into a readable summary.
    
    Args:
        order_items: Dictionary mapping item names to quantities
        order_name: Name for the order
        
    Returns:
        Formatted order summary string
    """
    if not order_items:
        return ""
    
    order_lines = [f"- {item} x{qty}" for item, qty in order_items.items()]
    
    return "\n".join([
        f"🛒 Name: {order_name}",
        "------------------",
        *order_lines,
        "------------------",
    ])

def remove_job_if_exists(name: str, application: Application) -> bool:
    """
    Remove job with given name from the job queue.
    
    Args:
        name: Name of the job to remove
        application: Bot application
        
    Returns:
        True if job was removed, False if it didn't exist
    """
    current_jobs = application.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True
