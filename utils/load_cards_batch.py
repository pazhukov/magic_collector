#!/usr/bin/env python3
"""
Magic Collector - Load Cards in Batches Script
This script loads cards from Magic sets in manageable batches.
"""

import sqlite3
import requests
import time
import json
from datetime import datetime
import sys

# Configuration
DATABASE = 'magic_collector.db'
SCRYFALL_API = 'https://api.scryfall.com/cards/search'
REQUEST_DELAY = 0.1
MAX_RETRIES = 3
RETRY_DELAY = 2

def init_database():
    """Initialize the database with cards table if it doesn't exist"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
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

def get_sets_batch(limit=10, offset=0, set_type=None):
    """Get a batch of sets from the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    query = 'SELECT code, name, card_count FROM sets WHERE card_count > 0'
    params = []
    
    if set_type:
        query += ' AND set_type = ?'
        params.append(set_type)
    
    query += ' ORDER BY released_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
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

def load_cards_batch(batch_size=10, set_type=None):
    """Load cards in batches"""
    print("🚀 Magic Collector - Load Cards in Batches Script")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Initialize database
        init_database()
        
        # Get total count
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        query = 'SELECT COUNT(*) FROM sets WHERE card_count > 0'
        params = []
        
        if set_type:
            query += ' AND set_type = ?'
            params.append(set_type)
        
        cursor.execute(query, params)
        total_sets = cursor.fetchone()[0]
        conn.close()
        
        print(f"📊 Total sets to process: {total_sets}")
        print(f"📦 Batch size: {batch_size}")
        if set_type:
            print(f"🎯 Set type filter: {set_type}")
        print("=" * 60)
        
        total_cards_loaded = 0
        total_errors = 0
        sets_processed = 0
        batch_number = 1
        
        offset = 0
        
        while offset < total_sets:
            print(f"\n📦 Processing batch {batch_number} (sets {offset + 1}-{min(offset + batch_size, total_sets)})")
            
            # Get batch of sets
            sets = get_sets_batch(batch_size, offset, set_type)
            
            if not sets:
                break
            
            batch_cards = 0
            batch_errors = 0
            
            # Process each set in the batch
            for set_code, set_name, expected_count in sets:
                try:
                    cards_loaded, errors = load_cards_for_set(set_code, set_name, expected_count)
                    batch_cards += cards_loaded
                    batch_errors += errors
                    sets_processed += 1
                    
                    # Be respectful to the API
                    time.sleep(REQUEST_DELAY)
                    
                except KeyboardInterrupt:
                    print(f"\n⚠️  Script interrupted by user")
                    return False
                except Exception as e:
                    print(f"❌ Unexpected error processing set {set_name} ({set_code}): {e}")
                    continue
            
            total_cards_loaded += batch_cards
            total_errors += batch_errors
            
            print(f"\n📊 Batch {batch_number} complete: {batch_cards} cards loaded, {batch_errors} errors")
            print(f"📊 Total progress: {sets_processed}/{total_sets} sets, {total_cards_loaded} cards loaded")
            
            offset += batch_size
            batch_number += 1
            
            # Ask if user wants to continue
            if offset < total_sets:
                response = input(f"\nContinue with next batch? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("⏹️  Stopping at user request")
                    break
        
        # Calculate execution time
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"🎉 Script completed!")
        print(f"⏱️  Total execution time: {duration}")
        print(f"📊 Sets processed: {sets_processed}/{total_sets}")
        print(f"📊 Cards loaded: {total_cards_loaded}")
        print(f"❌ Total errors: {total_errors}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return False

def show_help():
    """Show help information"""
    print("Magic Collector - Load Cards in Batches Script")
    print("=" * 50)
    print("Usage: python3 load_cards_batch.py [options]")
    print("")
    print("Options:")
    print("  --batch-size N    Number of sets to process per batch (default: 10)")
    print("  --set-type TYPE   Filter by set type (e.g., 'core', 'expansion', 'commander')")
    print("  --help           Show this help message")
    print("")
    print("Examples:")
    print("  python3 load_cards_batch.py --batch-size 5")
    print("  python3 load_cards_batch.py --set-type core")
    print("  python3 load_cards_batch.py --batch-size 20 --set-type expansion")

if __name__ == "__main__":
    # Parse command line arguments
    batch_size = 10
    set_type = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--batch-size' and i + 1 < len(args):
            batch_size = int(args[i + 1])
            i += 2
        elif args[i] == '--set-type' and i + 1 < len(args):
            set_type = args[i + 1]
            i += 2
        elif args[i] == '--help':
            show_help()
            exit(0)
        else:
            print(f"Unknown option: {args[i]}")
            show_help()
            exit(1)
    
    success = load_cards_batch(batch_size, set_type)
    
    if success:
        print("\n✅ All done! You can now run the main application.")
    else:
        print("\n❌ Script failed. Please check the errors above.")
