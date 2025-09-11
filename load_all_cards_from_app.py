#!/usr/bin/env python3
"""
Magic Collector - Load All Cards Script
This script loads all cards from all Magic: The Gathering sets using the exact same functions from app.py
"""

import sqlite3
import requests
import time
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE = os.getenv('DATABASE', 'magic_collector.db')

def get_scryfall_sets():
    """Fetch all sets from Scryfall API"""
    try:
        response = requests.get('https://api.scryfall.com/sets')
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching sets: {e}")
        return None

def get_cards_by_set(set_code):
    """Fetch cards for a specific set from Scryfall API"""
    try:
        url = f'https://api.scryfall.com/cards/search?q=set:{set_code}'
        all_cards = []
        
        while url:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            all_cards.extend(data.get('data', []))
            
            # Check if there are more pages
            if data.get('has_more'):
                url = data.get('next_page')
            else:
                url = None
                
        return all_cards
    except requests.RequestException as e:
        print(f"Error fetching cards for set {set_code}: {e}")
        return []

def save_legalities_history(cursor, card_id, legalities_data):
    """Save legalities history for a card"""
    if legalities_data and isinstance(legalities_data, dict):
        for format_name, status in legalities_data.items():
            cursor.execute('''
                INSERT INTO card_legalities_history (card_id, format_name, legality_status)
                VALUES (?, ?, ?)
            ''', (card_id, format_name, status))

def save_prices_history(cursor, card_id, prices_data):
    """Save prices history for a card"""
    if prices_data and isinstance(prices_data, dict):
        for price_type, price_value in prices_data.items():
            if price_value is not None:
                # Determine currency based on price type
                currency = 'USD' if 'usd' in price_type.lower() else 'EUR' if 'eur' in price_type.lower() else 'TIX' if 'tix' in price_type.lower() else 'Unknown'
                cursor.execute('''
                    INSERT INTO card_prices_history (card_id, price_type, price_value, currency)
                    VALUES (?, ?, ?, ?)
                ''', (card_id, price_type, str(price_value), currency))

def store_cards(cards_data, set_code):
    """Store cards data in the database - exact copy from app.py"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for card_data in cards_data:
        # Convert complex fields to JSON strings
        legalities = json.dumps(card_data.get('legalities', {}))
        games = json.dumps(card_data.get('games', []))
        finishes = json.dumps(card_data.get('finishes', []))
        prices = json.dumps(card_data.get('prices', {}))
        related_uris = json.dumps(card_data.get('related_uris', {}))
        purchase_uris = json.dumps(card_data.get('purchase_uris', {}))
        image_uris = json.dumps(card_data.get('image_uris', {}))
        colors = json.dumps(card_data.get('colors', []))
        color_identity = json.dumps(card_data.get('color_identity', []))
        
        card_name = card_data.get('name', '')
        card_oracle_text = card_data.get('oracle_text', '')
        mana_cost = card_data.get('mana_cost', '')
        type_line = card_data.get('type_line', '')

        # Handle card_faces data - store as JSON for better parsing
        card_faces_data = card_data.get('card_faces', [])
        if card_faces_data:
            card_name = card_faces_data[0].get('name', '') + " // " + card_faces_data[1].get('name', '') 
            card_oracle_text = card_faces_data[0].get('oracle_text', '') + " \n//\n " + card_faces_data[1].get('oracle_text', '') 
            mana_cost = card_faces_data[0].get('mana_cost', '') + "  // " + card_faces_data[1].get('mana_cost', '') 
            type_line = card_faces_data[0].get('type_line', '') + " // " + card_faces_data[1].get('type_line', '') 

            # Store card_faces as JSON for better parsing
            card_faces = json.dumps(card_faces_data)
        else:
            # No card_faces data, store as empty string
            card_faces = ''
        
        cursor.execute('''
            INSERT OR REPLACE INTO cards (
                id, name, mana_cost, cmc, type_line, oracle_text, power, toughness,
                colors, color_identity, legalities, games, reserved, foil, nonfoil,
                finishes, oversized, promo, reprint, variation, set_id, set_code,
                set_name, collector_number, rarity, artist, border_color, frame,
                full_art, textless, booster, story_spotlight, edhrec_rank, penny_rank,
                prices, related_uris, purchase_uris, image_uris, card_faces
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card_data.get('id'),
            card_name,
            mana_cost,
            card_data.get('cmc'),
            type_line,
            card_oracle_text,
            card_data.get('power'),
            card_data.get('toughness'),
            colors,
            color_identity,
            legalities,
            games,
            card_data.get('reserved', False),
            card_data.get('foil', False),
            card_data.get('nonfoil', False),
            finishes,
            card_data.get('oversized', False),
            card_data.get('promo', False),
            card_data.get('reprint', False),
            card_data.get('variation', False),
            card_data.get('set_id'),
            set_code,
            card_data.get('set_name'),
            card_data.get('collector_number'),
            card_data.get('rarity'),
            card_data.get('artist'),
            card_data.get('border_color'),
            card_data.get('frame'),
            card_data.get('full_art', False),
            card_data.get('textless', False),
            card_data.get('booster', False),
            card_data.get('story_spotlight', False),
            card_data.get('edhrec_rank'),
            card_data.get('penny_rank'),
            prices,
            related_uris,
            purchase_uris,
            image_uris,
            card_faces
        ))
        
        # Save legalities and prices history
        card_id = card_data.get('id')
        if card_id:
            save_legalities_history(cursor, card_id, card_data.get('legalities', {}))
            save_prices_history(cursor, card_id, card_data.get('prices', {}))
    
    conn.commit()
    conn.close()

def get_all_sets():
    """Get all sets from the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT code, name, card_count FROM sets WHERE card_count > 0 ORDER BY released_at DESC')
    sets = cursor.fetchall()
    
    conn.close()
    return sets

def load_cards_for_set(set_code, set_name, expected_count):
    """Load all cards for a specific set"""
    print(f"🔄 Loading cards for {set_name} ({set_code}) - Expected: {expected_count} cards")
    
    try:
        # Fetch all cards for this set
        cards_data = get_cards_by_set(set_code)
        
        if not cards_data:
            print(f"⚠️  No cards found for {set_name} ({set_code})")
            return 0, 0
        
        # Store cards in database
        store_cards(cards_data, set_code)
        
        print(f"   ✅ Loaded {len(cards_data)} cards for {set_name} ({set_code})")
        return len(cards_data), 0
        
    except Exception as e:
        print(f"❌ Fatal error loading cards for {set_name} ({set_code}): {e}")
        return 0, 1

def load_all_cards():
    """Main function to load all cards from all sets"""
    print("🚀 Magic Collector - Load All Cards Script")
    print("=" * 60)
    print(f"📁 Database: {DATABASE}")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Get all sets from database
        sets = get_all_sets()
        
        if not sets:
            print("❌ No sets found in database. Please run the main application first to load sets.")
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
                time.sleep(0.1)
                
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
