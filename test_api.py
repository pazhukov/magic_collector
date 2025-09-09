#!/usr/bin/env python3
"""
Test script to verify Scryfall API functionality
"""

import requests

def test_sets_api():
    """Test fetching sets from Scryfall API"""
    print("Testing Scryfall Sets API...")
    try:
        response = requests.get('https://api.scryfall.com/sets')
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Successfully fetched {len(data.get('data', []))} sets")
        print(f"✅ API response status: {response.status_code}")
        
        # Show first few sets
        if data.get('data'):
            print("\nFirst 3 sets:")
            for i, set_data in enumerate(data['data'][:3]):
                print(f"  {i+1}. {set_data.get('name')} ({set_data.get('code')}) - {set_data.get('set_type')}")
        
        return True
    except Exception as e:
        print(f"❌ Error fetching sets: {e}")
        return False

def test_cards_api():
    """Test fetching cards from a specific set"""
    print("\nTesting Scryfall Cards API...")
    try:
        # Test with a small set like "lea" (Limited Edition Alpha)
        response = requests.get('https://api.scryfall.com/cards/search?q=set:lea')
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Successfully fetched {len(data.get('data', []))} cards from set 'lea'")
        print(f"✅ API response status: {response.status_code}")
        
        # Show first few cards
        if data.get('data'):
            print("\nFirst 3 cards:")
            for i, card in enumerate(data['data'][:3]):
                print(f"  {i+1}. {card.get('name')} - {card.get('mana_cost', 'No cost')}")
        
        return True
    except Exception as e:
        print(f"❌ Error fetching cards: {e}")
        return False

def test_database_connection():
    """Test SQLite database connection"""
    print("\nTesting database connection...")
    try:
        import sqlite3
        conn = sqlite3.connect('magic_collector.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ Database connected successfully")
        print(f"✅ Found tables: {[table[0] for table in tables]}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Magic Collector API Integration\n")
    
    # Test database
    db_ok = test_database_connection()
    
    # Test APIs
    sets_ok = test_sets_api()
    cards_ok = test_cards_api()
    
    print(f"\n📊 Test Results:")
    print(f"  Database: {'✅' if db_ok else '❌'}")
    print(f"  Sets API: {'✅' if sets_ok else '❌'}")
    print(f"  Cards API: {'✅' if cards_ok else '❌'}")
    
    if all([db_ok, sets_ok, cards_ok]):
        print("\n🎉 All tests passed! The application should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
