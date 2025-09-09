#!/usr/bin/env python3
"""
Magic Collector - Load All Cards Script
This script loads all cards from all Magic: The Gathering sets with error handling.
"""

import sqlite3
import requests
import time
import json
from datetime import datetime

# Configuration
DATABASE = 'magic_collector.db'
SCRYFALL_API = 'https://api.scryfall.com/cards/search'
REQUEST_DELAY = 0.1  # Delay between requests to be respectful to API
MAX_RETRIES = 3
RETRY_DELAY = 2

def init_database():
    """Initialize the database with cards table if it doesn't exist"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create cards table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            name TEXT,
            mana_cost TEXT,
            type_line TEXT,
            oracle_text TEXT,
            power TEXT,
            toughness TEXT,
            colors TEXT,
            color_identity TEXT,
            cmc INTEGER,
            rarity TEXT,
            set_code TEXT,
            collector_number TEXT,
            image_uris TEXT,
            prices TEXT,
            card_faces TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def get_all_sets():
    """Get all sets from the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT code, name, card_count FROM sets WHERE card_count > 0 ORDER BY released_at DESC')
    sets = cursor.fetchall()
    
    conn.close()
    return sets

def get_scryfall_cards(set_code, page=1):
    """Fetch cards for a specific set from Scryfall API with pagination"""
    all_cards = []
    url = f"{SCRYFALL_API}?q=set:{set_code}&page={page}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        cards = data.get('data', [])
        all_cards.extend(cards)
        
        # Check if there are more pages
        has_more = data.get('has_more', False)
        next_page = data.get('next_page')
        
        if has_more and next_page:
            # Recursively get next page
            next_cards = get_scryfall_cards(set_code, page + 1)
            all_cards.extend(next_cards)
        
        return all_cards
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching cards for set {set_code} page {page}: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching cards for set {set_code} page {page}: {e}")
        return []

def store_cards(cards_data, set_code):
    """Store cards data in the database with error handling"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    for card_data in cards_data:
        try:
            # Extract card information with safe defaults
            card_id = card_data.get('id', '')
            name = card_data.get('name', '')
            mana_cost = card_data.get('mana_cost', '')
            type_line = card_data.get('type_line', '')
            oracle_text = card_data.get('oracle_text', '')
            power = card_data.get('power', '')
            toughness = card_data.get('toughness', '')
            colors = json.dumps(card_data.get('colors', []))
            color_identity = json.dumps(card_data.get('color_identity', []))
            cmc = card_data.get('cmc', 0)
            rarity = card_data.get('rarity', '')
            collector_number = card_data.get('collector_number', '')
            image_uris = json.dumps(card_data.get('image_uris', {}))
            prices = json.dumps(card_data.get('prices', {}))
            
            # Handle card_faces for double-sided cards
            card_faces = ''
            if 'card_faces' in card_data and card_data['card_faces']:
                faces_data = []
                for face in card_data['card_faces']:
                    face_info = f"{face.get('name', '')} // {face.get('type_line', '')} // {face.get('image_uris', {}).get('normal', '')}"
                    faces_data.append(face_info)
                card_faces = ' // '.join(faces_data)
            
            # Insert or replace card data
            cursor.execute('''
                INSERT OR REPLACE INTO cards 
                (id, name, mana_cost, type_line, oracle_text, power, toughness, colors, color_identity, cmc, rarity, set_code, collector_number, image_uris, prices, card_faces)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (card_id, name, mana_cost, type_line, oracle_text, power, toughness, colors, color_identity, cmc, rarity, set_code, collector_number, image_uris, prices, card_faces))
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error storing card {card_data.get('name', 'unknown')} from {set_code}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return success_count, error_count

def load_cards_for_set(set_code, set_name, expected_count):
    """Load all cards for a specific set"""
    print(f"🔄 Loading cards for {set_name} ({set_code}) - Expected: {expected_count} cards")
    
    try:
        # Fetch all cards for this set
        cards_data = get_scryfall_cards(set_code)
        
        if not cards_data:
            print(f"⚠️  No cards found for {set_name} ({set_code})")
            return 0, 0
        
        # Store cards in database
        success_count, error_count = store_cards(cards_data, set_code)
        
        print(f"   ✅ Loaded {success_count} cards for {set_name} ({set_code})")
        if error_count > 0:
            print(f"   ⚠️  {error_count} cards had errors and were skipped")
        
        return success_count, error_count
        
    except Exception as e:
        print(f"❌ Fatal error loading cards for {set_name} ({set_code}): {e}")
        return 0, 1

def load_all_cards():
    """Main function to load all cards from all sets"""
    print("🚀 Magic Collector - Load All Cards Script")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Initialize database
        init_database()
        
        # Get all sets from database
        sets = get_all_sets()
        
        if not sets:
            print("❌ No sets found in database. Please run load_sets.py first.")
            return False
        
        print(f"📊 Found {len(sets)} sets with cards to load")
        print("=" * 60)
        
        total_cards_loaded = 0
        total_errors = 0
        sets_processed = 0
        sets_with_errors = 0
        
        # Process each set
        for i, (set_code, set_name, expected_count) in enumerate(sets, 1):
            print(f"\n📦 Processing set {i}/{len(sets)}: {set_name} ({set_code})")
            
            try:
                cards_loaded, errors = load_cards_for_set(set_code, set_name, expected_count)
                total_cards_loaded += cards_loaded
                total_errors += errors
                sets_processed += 1
                
                if errors > 0:
                    sets_with_errors += 1
                
                # Progress indicator
                if i % 10 == 0:
                    print(f"\n📊 Progress: {i}/{len(sets)} sets processed, {total_cards_loaded} cards loaded")
                
                # Be respectful to the API
                time.sleep(REQUEST_DELAY)
                
            except KeyboardInterrupt:
                print(f"\n⚠️  Script interrupted by user after processing {i-1} sets")
                break
            except Exception as e:
                print(f"❌ Unexpected error processing set {set_name} ({set_code}): {e}")
                sets_with_errors += 1
                continue
        
        # Calculate execution time
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"🎉 Script completed!")
        print(f"⏱️  Total execution time: {duration}")
        print(f"📊 Sets processed: {sets_processed}/{len(sets)}")
        print(f"📊 Cards loaded: {total_cards_loaded}")
        print(f"⚠️  Sets with errors: {sets_with_errors}")
        print(f"❌ Total card errors: {total_errors}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return False

def verify_loaded_cards():
    """Verify how many cards were loaded into the database"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Total cards
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards = cursor.fetchone()[0]
        
        # Cards by set
        cursor.execute('''
            SELECT s.name, s.code, COUNT(c.id) as card_count 
            FROM sets s 
            LEFT JOIN cards c ON s.code = c.set_code 
            GROUP BY s.code, s.name 
            ORDER BY card_count DESC 
            LIMIT 10
        ''')
        top_sets = cursor.fetchall()
        
        # Recent cards
        cursor.execute('SELECT name, set_code, collector_number FROM cards ORDER BY created_at DESC LIMIT 5')
        recent_cards = cursor.fetchall()
        
        conn.close()
        
        print(f"\n📊 Database contains {total_cards} total cards")
        print("🏆 Top sets by card count:")
        for name, code, count in top_sets:
            print(f"   • {name} ({code}) - {count} cards")
        
        print("\n🆕 Most recently loaded cards:")
        for name, set_code, collector_number in recent_cards:
            print(f"   • {name} ({set_code} #{collector_number})")
            
    except Exception as e:
        print(f"❌ Error verifying loaded cards: {e}")

def estimate_loading_time():
    """Estimate how long the loading process will take"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT SUM(card_count) FROM sets WHERE card_count > 0')
        total_cards = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Rough estimate: 0.1 seconds per request + processing time
        estimated_seconds = total_cards * 0.2  # Conservative estimate
        estimated_minutes = estimated_seconds / 60
        
        print(f"📊 Estimated total cards to load: {total_cards:,}")
        print(f"⏱️  Estimated loading time: {estimated_minutes:.1f} minutes")
        
    except Exception as e:
        print(f"❌ Error estimating loading time: {e}")

if __name__ == "__main__":
    print("⚠️  WARNING: This script will load ALL cards from ALL sets.")
    print("This may take a very long time and use significant disk space.")
    print("=" * 60)
    
    # Show estimate
    estimate_loading_time()
    
    response = input("\nDo you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Script cancelled by user")
        exit(0)
    
    success = load_all_cards()
    
    if success:
        verify_loaded_cards()
        print("\n✅ All done! You can now run the main application.")
    else:
        print("\n❌ Script failed. Please check the errors above.")
