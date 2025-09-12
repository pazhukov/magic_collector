#!/usr/bin/env python3
"""
Magic Collector - Load Bulk Cards Script
This script loads all cards using Scryfall's bulk data API for faster loading.
"""

import sqlite3
import requests
import json
import os
import gzip
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

def store_sets(sets_data):
    """Store sets data in the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for set_data in sets_data:
        cursor.execute('''
            INSERT OR REPLACE INTO sets (
                id, code, name, set_type, released_at, block_code, block,
                parent_set_code, card_count, digital, foil_only, nonfoil_only,
                scryfall_uri, uri, icon_svg_uri, search_uri, printed_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            set_data.get('id'),
            set_data.get('code'),
            set_data.get('name'),
            set_data.get('set_type'),
            set_data.get('released_at'),
            set_data.get('block_code'),
            set_data.get('block'),
            set_data.get('parent_set_code'),
            set_data.get('card_count'),
            set_data.get('digital', False),
            set_data.get('foil_only', False),
            set_data.get('nonfoil_only', False),
            set_data.get('scryfall_uri'),
            set_data.get('uri'),
            set_data.get('icon_svg_uri'),
            set_data.get('search_uri'),
            set_data.get('printed_size')
        ))
    
    conn.commit()
    conn.close()

def get_bulk_data_info():
    """Get bulk data information from Scryfall API"""
    try:
        response = requests.get('https://api.scryfall.com/bulk-data')
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching bulk data info: {e}")
        return None

def get_default_cards_download_url():
    """Get the download URL for default cards bulk data"""
    bulk_data = get_bulk_data_info()
    if not bulk_data:
        return None
    
    # Find the default_cards entry
    for data_type in bulk_data.get('data', []):
        if data_type.get('type') == 'default_cards':
            return data_type.get('download_uri')
    
    print("Default cards bulk data not found")
    return None

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

def store_cards(cards_data, set_code=None):
    """Store cards data in the database - exact copy from app.py"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    for card_data in cards_data:
        try:
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
            
            # Use set_code from parameter or from card data
            card_set_code = set_code or card_data.get('set', '')
            
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
                card_set_code,
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
            
            success_count += 1
            
            # Progress indicator
            if success_count % 1000 == 0:
                print(f"  Processed {success_count} cards...")
                
        except Exception as e:
            error_count += 1
            print(f"Error storing card {card_data.get('name', 'unknown')}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return success_count, error_count

def download_and_process_bulk_data():
    """Download and process the bulk data"""
    print("🚀 Magic Collector - Load Bulk Cards Script")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # First, load all sets
        print("📡 Loading all sets...")
        sets_data = get_scryfall_sets()
        if sets_data and 'data' in sets_data:
            store_sets(sets_data['data'])
            print(f"✅ Loaded {len(sets_data['data'])} sets")
        else:
            print("❌ Could not load sets")
            return False
        
        # Get the download URL
        print("📡 Getting bulk data information...")
        download_url = get_default_cards_download_url()
        if not download_url:
            print("❌ Could not get download URL for default cards")
            return False
        
        print(f"📥 Download URL: {download_url}")
        
        # Download the bulk data
        print("📥 Downloading bulk data (this may take a while)...")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress tracking
        total_size = int(response.headers.get('content-length', 0))

        
        print(f"📊 File size: {total_size / (1024*1024):.1f} MB")
        
        # Process the gzipped JSON data
        print("🔄 Processing bulk data...")
        
        # The bulk data is a single JSON array, not line-delimited JSON
        with gzip.open(response.raw, 'rt', encoding='utf-8') as f:
            cards_data = json.load(f)
        
        print(f"📊 Successfully loaded {len(cards_data)} cards from bulk data")
        
        # Store cards in database
        print("💾 Storing cards in database...")
        success_count, error_count = store_cards(cards_data)
        
        # Calculate execution time
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"🎉 Script completed!")
        print(f"⏱️  Total execution time: {duration}")
        print(f"📊 Cards processed: {success_count}")
        print(f"❌ Cards with errors: {error_count}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error downloading bulk data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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

if __name__ == "__main__":
    print("⚠️  WARNING: This script will download and load ALL cards from Scryfall.")
    print("This will use significant disk space and bandwidth.")
    print("=" * 60)
    
    response = input("\nDo you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Script cancelled by user")
        exit(0)
    
    success = download_and_process_bulk_data()
    
    if success:
        verify_loaded_cards()
        print("\n✅ All done! You can now run the main application.")
    else:
        print("\n❌ Script failed. Please check the errors above.")
