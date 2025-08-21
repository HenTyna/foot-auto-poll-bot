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

def format_visual_menu(original_text: str, options: List[str], quantities: Dict[str, int] = None, pending_count: int = 0) -> str:
    """
    Format the original menu text into a visual menu display with quantities.
    
    Args:
        original_text: Original menu text
        options: List of menu options
        quantities: Dictionary mapping item names to quantities
        pending_count: Number of pending selections
        
    Returns:
        Formatted visual menu text
    """
    if quantities is None:
        quantities = {}
    
    # Extract the title (first line)
    lines = original_text.strip().split('\n')
    title = lines[0] if lines else "ម្ហូបថ្ងៃ"
    
    # Create the visual menu
    menu_lines = [
        f"🍽️ {title} - Today's Menu",
        "━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    # Add numbered menu items with quantities
    for i, option in enumerate(options, 1):
        qty = quantities.get(option, 0)
        if qty > 0:
            menu_lines.append(f"{i}. {option} x{qty}")
        else:
            menu_lines.append(f"{i}. {option}")
    
    # Count total voted selections
    total_voted = sum(quantities.values())
    
    menu_lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"📊 Voted selections: {total_voted}",
    ])
    
    # Add pending count if there are any
    if pending_count > 0:
        menu_lines.append(f"⏳ Pending selections: {pending_count}")
    
    menu_lines.extend([
        "📝 Select quantities and click Vote to confirm",
        "💡 Only voted selections are shown above",
        "👤 If you want to change your order, click reset and select the item again",
        "🔄 If you want to remove an item, click reset and select the item again",
        ""
    ])
    
    return "\n".join(menu_lines)

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

def format_order_summary(order_items: Dict[str, int], order_name: str = "Seyha", user_selections: Optional[Dict[int, Dict[str, Any]]] = None) -> str:
    """
    Format order items into a readable summary with voter details.
    
    Args:
        order_items: Dictionary mapping item names to quantities
        order_name: Name for the order
        user_selections: Dictionary mapping user_id to user data (selections and name)
        
    Returns:
        Formatted order summary string
    """
    if not order_items:
        return ""
    
    # Build the main order summary
    order_lines = [f"- {item} x{qty}" for item, qty in order_items.items()]

    # Determine who placed the order
    if user_selections and isinstance(user_selections, dict):
        # Try to get the first user's name if available
        first_user = next(iter(user_selections.values()), None)
        order_by = first_user.get('name', 'Unknown') if isinstance(first_user, dict) else 'Unknown'
    else:
        order_by = 'Unknown'

    # Build the summary
    summary_lines = [
        f"🛒 Name: {order_name}",
        # f"👤 Order By: {order_by}",
        "------------------",
        *order_lines,
        "------------------"
    ]
    
    # Add detail section if user selections are provided
    if user_selections:
        summary_lines.append("Detail:")
        
        # Create a mapping of items to voters
        item_voters = {}
        for user_id, user_data in user_selections.items():
            user_name = user_data.get('name', f'User{user_id}')
            quantities = user_data.get('quantities', {})
            
            for item, qty in quantities.items():
                if item in order_items and qty > 0:  # Only include items that are actually ordered
                    if item not in item_voters:
                        item_voters[item] = []
                    
                    # Add voter info without status indicator
                    voter_info = f"{user_name} (x{qty})" if qty > 1 else user_name
                    item_voters[item].append(voter_info)
        
        # Add voter details for each item
        for item, qty in order_items.items():
            voters = item_voters.get(item, [])
            if voters:
                voter_names = ", ".join(voters)
                summary_lines.append(f"- {item} x{qty} ({voter_names})")
    
    return "\n".join(summary_lines)

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
