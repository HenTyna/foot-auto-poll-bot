# Telegram Food Poll Bot

A Telegram bot that automatically creates interactive polls from food menu text and helps collect user orders. The bot supports Khmer language and is designed for food ordering workflows.

## Features

- **Automatic Menu Detection**: Detects food menu text with numbered items (Khmer or English numbers)
- **Interactive Polls**: Creates polls with multiple choice options for food selection
- **Order Collection**: Tracks user selections and provides order summaries
- **Scheduled Messages**: Sends daily reminder messages at configurable times
- **Multi-language Support**: Supports Khmer and English text
- **Error Handling**: Robust error handling with retry logic
- **Logging**: Comprehensive logging for debugging and monitoring

## Project Structure

```
foot-auto-poll-bot/
├── bot/                    # Main bot package
│   ├── __init__.py        # Package initialization
│   ├── bot.py             # Main bot class
│   ├── config.py          # Configuration settings
│   ├── handlers.py        # Message and callback handlers
│   ├── menu_processor.py  # Menu text processing
│   ├── scheduler.py       # Scheduled message handling
│   └── utils.py           # Utility functions
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
└── .gitignore            # Git ignore file
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd foot-auto-poll-bot
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env and add your bot token
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required
BOT_TOKEN=your_telegram_bot_token_here

# Optional
LOG_LEVEL=INFO
LOG_FILE=bot.log
```

### Getting a Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token and add it to your `.env` file

## Usage

### Running the Bot

```bash
python main.py
```

### Bot Commands

- `/start` - Initialize the bot and receive welcome message
- `/debug_send` - Manually trigger scheduled message (for testing)

### How It Works

1. **Menu Detection**: The bot automatically detects food menu text that:
   - Starts with "ម្ហូបថ្ងៃ" (today's food)
   - Contains numbered items (១២៣៤៥៦ or 1-6)

2. **Poll Creation**: When a menu is detected, the bot:
   - Extracts menu options
   - Creates an interactive poll
   - Adds an "Order" button

3. **Order Collection**: Users can:
   - Vote on their preferred food items
   - Click the "Order" button to see the summary
   - View aggregated order counts

4. **Scheduled Messages**: The bot sends daily reminders at 8:00 AM (Phnom Penh time)

### Example Menu Format

The bot recognizes menus in this format:

```
ម្ហូបថ្ងៃ
១. បបរសាច់គោ
២. សម្លកកូរ
៣. អាម៉ុក
៤. ប៉ាហ្វេត
៥. នំបញ្ចុក
៦. ស្លាបព្រាបាយ
```

Or with English numbers:

```
Today's Menu
1. Beef porridge
2. Curry soup
3. Amok
4. Paella
5. Spring rolls
6. Chicken rice
```

## Development

### Project Structure Overview

- **`bot/bot.py`**: Main bot class that orchestrates all components
- **`bot/config.py`**: Centralized configuration management
- **`bot/handlers.py`**: Message and callback handlers
- **`bot/menu_processor.py`**: Menu text processing and poll creation
- **`bot/scheduler.py`**: Scheduled message functionality
- **`bot/utils.py`**: Utility functions for common operations

### Adding New Features

1. **New Commands**: Add handlers in `bot/handlers.py`
2. **Configuration**: Add settings in `bot/config.py`
3. **Utilities**: Add helper functions in `bot/utils.py`
4. **Processing**: Add logic in appropriate modules

### Logging

The bot uses Python's built-in logging with configurable levels:

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about bot operation
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations

Logs are written to both console and file (configurable via `LOG_FILE`).

## Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check if the bot token is correct
   - Verify the bot is not blocked by users
   - Check logs for error messages

2. **Polls not created**:
   - Ensure menu text follows the expected format
   - Check that text contains at least 2 numbered items

3. **Scheduled messages not sent**:
   - Verify timezone configuration
   - Check if chat IDs are properly stored

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your `.env` file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Create an issue in the repository

## Changelog

### Version 1.0.0
- Initial release
- Basic poll creation and order collection
- Scheduled message functionality
- Khmer language support
- Modular architecture
