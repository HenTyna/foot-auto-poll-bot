#!/usr/bin/env python3
"""
Simple test script to verify the bot structure works correctly.
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported correctly."""
    try:
        # Test bot package import
        from bot import FoodPollBot
        print("✓ FoodPollBot imported successfully")
        
        # Test individual modules
        from bot.config import BOT_TOKEN, setup_logging
        print("✓ Config module imported successfully")
        
        from bot.utils import extract_menu_options, is_food_menu_text
        print("✓ Utils module imported successfully")
        
        from bot.menu_processor import process_food_menu
        print("✓ Menu processor imported successfully")
        
        from bot.handlers import setup_handlers
        print("✓ Handlers module imported successfully")
        
        from bot.scheduler import setup_scheduler
        print("✓ Scheduler module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from bot.config import setup_logging
        setup_logging()
        print("✓ Logging setup successful")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_utils():
    """Test utility functions."""
    try:
        from bot.utils import extract_menu_options, is_food_menu_text
        
        # Test menu text detection
        test_menu = """ម្ហូបថ្ងៃ
១. បបរសាច់គោ
២. សម្លកកូរ
៣. អាម៉ុក"""
        
        assert is_food_menu_text(test_menu), "Menu text detection failed"
        print("✓ Menu text detection works")
        
        # Test option extraction
        options = extract_menu_options(test_menu)
        assert len(options) == 3, f"Expected 3 options, got {len(options)}"
        print("✓ Option extraction works")
        
        return True
        
    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False

def test_bot_setup():
    """Test bot setup without running."""
    try:
        from bot import FoodPollBot
        
        # Create bot instance
        bot = FoodPollBot()
        print("✓ Bot instance created successfully")
        
        # Test setup (this will fail without BOT_TOKEN, but that's expected)
        try:
            bot.setup()
            print("✓ Bot setup completed (with token)")
        except ValueError as e:
            if "BOT_TOKEN" in str(e):
                print("✓ Bot setup correctly requires BOT_TOKEN (expected)")
            else:
                raise
        except Exception as e:
            print(f"✗ Bot setup failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Bot setup test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Telegram Food Poll Bot structure...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Config Test", test_config),
        ("Utils Test", test_utils),
        ("Bot Setup Test", test_bot_setup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The bot structure is working correctly.")
        print("\nTo run the bot:")
        print("1. Copy env.example to .env")
        print("2. Add your BOT_TOKEN to .env")
        print("3. Run: python main.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 