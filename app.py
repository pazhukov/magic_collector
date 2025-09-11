import time
import json
import sqlite3
import requests
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Database configuration
DATABASE = os.getenv('DATABASE', 'magic_collector.db')

# Custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(json_string):
    """Convert JSON string to Python object"""
    if json_string:
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}

@app.template_filter('strftime')
def strftime_filter(timestamp, format_string='%Y-%m-%d %H:%M'):
    """Format timestamp string"""
    if timestamp:
        try:
            from datetime import datetime
            # Handle both string and datetime objects
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            return dt.strftime(format_string)
        except (ValueError, AttributeError):
            return str(timestamp)
    return 'N/A'

@app.template_filter('from_json')
def from_json_filter(json_string):
    """Custom filter to parse JSON strings"""
    if not json_string:
        return {}
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return {}

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sets (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT,
            set_type TEXT,
            released_at TEXT,
            block_code TEXT,
            block TEXT,
            parent_set_code TEXT,
            card_count INTEGER,
            digital BOOLEAN,
            foil_only BOOLEAN,
            nonfoil_only BOOLEAN,
            scryfall_uri TEXT,
            uri TEXT,
            icon_svg_uri TEXT,
            search_uri TEXT,
            printed_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            name TEXT,
            mana_cost TEXT,
            cmc REAL,
            type_line TEXT,
            oracle_text TEXT,
            power TEXT,
            toughness TEXT,
            colors TEXT,
            color_identity TEXT,
            legalities TEXT,
            games TEXT,
            reserved BOOLEAN,
            foil BOOLEAN,
            nonfoil BOOLEAN,
            finishes TEXT,
            oversized BOOLEAN,
            promo BOOLEAN,
            reprint BOOLEAN,
            variation BOOLEAN,
            set_id TEXT,
            set_code TEXT,
            set_name TEXT,
            collector_number TEXT,
            rarity TEXT,
            artist TEXT,
            border_color TEXT,
            frame TEXT,
            full_art BOOLEAN,
            textless BOOLEAN,
            booster BOOLEAN,
            story_spotlight BOOLEAN,
            edhrec_rank INTEGER,
            penny_rank INTEGER,
            prices TEXT,
            related_uris TEXT,
            purchase_uris TEXT,
            image_uris TEXT,
            card_faces TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (set_id) REFERENCES sets (id)
        )
    ''')
    
    # Create card_legalities_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_legalities_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT,
            format_name TEXT,
            legality_status TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES cards (id)
        )
    ''')
    
    # Create card_prices_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_prices_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT,
            price_type TEXT,
            price_value TEXT,
            currency TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES cards (id)
        )
    ''')
    
    # Create user_collection table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_collection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT,
            quantity INTEGER DEFAULT 1,
            is_foil BOOLEAN DEFAULT FALSE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES cards (id),
            UNIQUE(card_id, is_foil)
        )
    ''')
    
    # Create trade_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_code TEXT,
            collector_number TEXT,
            direction TEXT CHECK(direction IN ('Buy', 'Sell')),
            quantity INTEGER,
            price REAL,
            total_amount REAL,
            profit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (set_code) REFERENCES sets (code)
        )
    ''')
    
    # Create decks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            format TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create deck_cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deck_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER,
            card_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            is_sideboard BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
        )
    ''')
    
    # Add card_faces column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute('ALTER TABLE cards ADD COLUMN card_faces TEXT')
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    conn.commit()
    conn.close()



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

def get_card_from_scryfall(card_id):
    """Fetch a specific card from Scryfall API by ID"""
    try:
        response = requests.get(f'https://api.scryfall.com/cards/{card_id}')
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching card {card_id} from Scryfall: {e}")
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

def get_collection_quantity(card_id, is_foil=False):
    """Get the quantity of a card in the user's collection"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT quantity FROM user_collection WHERE card_id = ? AND is_foil = ?', (card_id, is_foil))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_collection_totals(card_id):
    """Get both foil and non-foil quantities for a card"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_foil, quantity FROM user_collection WHERE card_id = ?', (card_id,))
    results = cursor.fetchall()
    conn.close()
    
    non_foil = 0
    foil = 0
    for is_foil, quantity in results:
        if is_foil:
            foil = quantity
        else:
            non_foil = quantity
    
    return non_foil, foil

def add_to_collection(card_id, quantity, is_foil=False):
    """Add or update a card in the user's collection"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if card already exists in collection with this foil status
    cursor.execute('SELECT quantity FROM user_collection WHERE card_id = ? AND is_foil = ?', (card_id, is_foil))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing quantity
        new_quantity = existing[0] + quantity
        cursor.execute('''
            UPDATE user_collection 
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE card_id = ? AND is_foil = ?
        ''', (new_quantity, card_id, is_foil))
    else:
        # Add new card to collection
        cursor.execute('''
            INSERT INTO user_collection (card_id, quantity, is_foil)
            VALUES (?, ?, ?)
        ''', (card_id, quantity, is_foil))
    
    conn.commit()
    conn.close()
    return True

def update_collection_quantity(card_id, quantity, is_foil=False):
    """Update the exact quantity of a card in the user's collection"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if quantity <= 0:
        # Remove card from collection if quantity is 0 or negative
        cursor.execute('DELETE FROM user_collection WHERE card_id = ? AND is_foil = ?', (card_id, is_foil))
        conn.commit()
        conn.close()
        return 0
    else:
        # Update or insert the card with the exact quantity
        cursor.execute('''
            INSERT OR REPLACE INTO user_collection (card_id, quantity, is_foil, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (card_id, quantity, is_foil))
        conn.commit()
        conn.close()
        return quantity

def get_card_price(card_data, is_foil=False):
    """Extract the appropriate USD price from card data based on foil status"""
    if not card_data or not card_data[34]:  # prices field is at index 34
        return None
    
    try:
        prices = json.loads(card_data[34])
        if is_foil:
            # For foil cards, try usd_foil first, then fall back to usd
            price = prices.get('usd_foil') or prices.get('usd')
        else:
            # For non-foil cards, use usd price
            price = prices.get('usd')
        
        return float(price) if price else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None

def store_cards(cards_data, set_code):
    """Store cards data in the database"""
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


        # Handle card_faces data
        card_faces_data = card_data.get('card_faces', [])
        if card_faces_data:
            card_name = card_faces_data[0].get('name', '') + " // " + card_faces_data[1].get('name', '') 
            card_oracle_text = card_faces_data[0].get('oracle_text', '') + " \n//\n " + card_faces_data[1].get('oracle_text', '') 
            mana_cost = card_faces_data[0].get('mana_cost', '') + "  // " + card_faces_data[1].get('mana_cost', '') 
            type_line = card_faces_data[0].get('type_line', '') + " // " + card_faces_data[1].get('type_line', '') 

            # Extract face information and join with ' // ' separator
            face_info = []
            for face in card_faces_data:
                face_name = face.get('name', '')
                face_type = face.get('type_line', '')
                # face_text = face.get('oracle_text', '')
                face_images = face.get('image_uris', {})
                
                # Create a summary of the face with image URL
                face_summary = f"{face_name} ({face_type})"
                if face_images and face_images.get('normal'):
                    face_summary += f" |IMG:{face_images['normal']}"
                face_info.append(face_summary)
            card_faces = ' // '.join(face_info)
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

@app.route('/')
def index():
    """Main page with sets overview"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sets ORDER BY released_at DESC')
    sets = cursor.fetchall()
    
    # Get total cards count
    cursor.execute('SELECT COUNT(*) FROM cards')
    total_cards = cursor.fetchone()[0]
    
    # Get cards in collection count
    cursor.execute('SELECT COUNT(*) FROM user_collection')
    cards_in_collection = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('index.html', sets=sets, total_cards=total_cards, cards_in_collection=cards_in_collection)

@app.route('/sets')
def view_sets():
    """View all sets"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sets ORDER BY released_at DESC')
    sets = cursor.fetchall()
    conn.close()
    
    return render_template('sets.html', sets=sets)

@app.route('/cards/<set_code>')
def view_cards_by_set(set_code):
    """View cards for a specific set"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get set info
    cursor.execute('SELECT * FROM sets WHERE code = ?', (set_code,))
    set_info = cursor.fetchone()
    
    # Get cards for this set - sort by collector number as number
    cursor.execute('SELECT * FROM cards WHERE set_code = ? ORDER BY CAST(collector_number AS INTEGER)', (set_code,))
    cards = cursor.fetchall()
    
    conn.close()
    
    return render_template('cards.html', set_info=set_info, cards=cards)

@app.route('/card/<card_id>')
def view_card_detail(card_id):
    """View detailed information for a specific card"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get card details
    cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
    card = cursor.fetchone()
    
    # Get set info for this card
    if card:
        cursor.execute('SELECT * FROM sets WHERE code = ?', (card[21],))  # set_code is at index 21
        set_info = cursor.fetchone()
    else:
        set_info = None
    
    # Get collection quantities (both foil and non-foil)
    if card:
        non_foil_qty, foil_qty = get_collection_totals(card_id)
    else:
        non_foil_qty, foil_qty = 0, 0
    
    # Check if this is a double-sided card and get card_faces data
    card_faces_data = None
    if card and card[39]:  # card_faces field is at index 39
        # card_faces is now stored as a string with ' // ' separator
        card_faces_string = card[39]
        if card_faces_string and ' // ' in card_faces_string:
            # Split the faces and create a simple structure for the template
            face_strings = card_faces_string.split(' // ')
            card_faces_data = []
            for i, face_string in enumerate(face_strings):
                # Parse the face string format: "Name (Type) |IMG:url"
                image_url = None
                if ' |IMG:' in face_string:
                    name_type, image_url = face_string.split(' |IMG:', 1)
                else:
                    name_type = face_string
                
                # Extract name and type from "Name (Type)"
                if ' (' in name_type and name_type.endswith(')'):
                    name = name_type.split(' (')[0]
                    type_line = name_type.split(' (')[1][:-1]  # Remove closing parenthesis
                else:
                    name = name_type
                    type_line = ''
                
                # Create image_uris structure if we have an image URL
                image_uris = None
                if image_url:
                    image_uris = {'normal': image_url, 'large': image_url}
                
                card_faces_data.append({
                    'name': name,
                    'type_line': type_line,
                    'oracle_text': '',  # We don't store oracle text in the new format
                    'image_uris': image_uris
                })
    
    # Get other printings of the same card (same name, different sets)
    other_printings = []
    if card:
        card_name = card[1]  # name is at index 1
        cursor.execute('''
            SELECT c.id, c.name, c.set_code, c.collector_number, c.image_uris, c.rarity,
                   s.name as set_name, s.released_at
            FROM cards c
            JOIN sets s ON c.set_code = s.code
            WHERE c.name = ? AND c.id != ?
            ORDER BY s.released_at DESC
        ''', (card_name, card_id))
        other_printings = cursor.fetchall()
    
    conn.close()
    
    return render_template('card_detail.html', card=card, set_info=set_info, non_foil_qty=non_foil_qty, foil_qty=foil_qty, card_faces_data=card_faces_data, other_printings=other_printings)

@app.route('/add_to_collection', methods=['POST'])
def add_to_collection_route():
    """Add cards to collection"""
    data = request.get_json()
    card_id = data.get('card_id')
    quantity = int(data.get('quantity', 1))
    is_foil = data.get('is_foil', False)
    
    if not card_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid card ID or quantity'})
    
    try:
        add_to_collection(card_id, quantity, is_foil)
        non_foil_qty, foil_qty = get_collection_totals(card_id)
        return jsonify({
            'success': True, 
            'message': f'Added {quantity} {"foil" if is_foil else "non-foil"} card(s) to collection',
            'non_foil_qty': non_foil_qty,
            'foil_qty': foil_qty
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding to collection: {str(e)}'})

@app.route('/update_collection_quantity', methods=['POST'])
def update_collection_quantity_route():
    """Update the exact quantity of a card in collection"""
    data = request.get_json()
    card_id = data.get('card_id')
    quantity = int(data.get('quantity', 0))
    is_foil = data.get('is_foil', False)
    
    if not card_id:
        return jsonify({'success': False, 'message': 'Invalid card ID'})
    
    try:
        new_quantity = update_collection_quantity(card_id, quantity, is_foil)
        non_foil_qty, foil_qty = get_collection_totals(card_id)
        return jsonify({
            'success': True, 
            'message': f'Updated {"foil" if is_foil else "non-foil"} quantity to {new_quantity}',
            'new_quantity': new_quantity,
            'non_foil_qty': non_foil_qty,
            'foil_qty': foil_qty
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating collection: {str(e)}'})

@app.route('/clear_collection', methods=['POST'])
def clear_collection_route():
    """Clear all cards from the user's collection"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get count before clearing
        cursor.execute('SELECT COUNT(*) FROM user_collection')
        count_before = cursor.fetchone()[0]
        
        # Clear all collection entries
        cursor.execute('DELETE FROM user_collection')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully cleared {count_before} cards from collection'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error clearing collection: {str(e)}'})

@app.route('/update_collection_prices', methods=['POST'])
def update_collection_prices():
    """Update prices and legality for all cards in the collection"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get all unique card IDs from the collection
        cursor.execute('SELECT DISTINCT card_id FROM user_collection')
        collection_cards = cursor.fetchall()
        
        if not collection_cards:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'No cards in collection to update'
            })
        
        updated_count = 0
        error_count = 0
        
        for (card_id,) in collection_cards:
            try:
                # Get card data from Scryfall
                response = requests.get(f'https://api.scryfall.com/cards/{card_id}', timeout=10)
                response.raise_for_status()
                card_data = response.json()
                
                # Extract updated prices and legality
                prices = json.dumps(card_data.get('prices', {}))
                legalities = json.dumps(card_data.get('legalities', {}))
                
                # Update the card in the database
                cursor.execute('''
                    UPDATE cards 
                    SET prices = ?, legalities = ?
                    WHERE id = ?
                ''', (prices, legalities, card_id))
                
                updated_count += 1
                
                # Be respectful to the API
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error updating card {card_id}: {e}")
                error_count += 1
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Updated prices and legality for {updated_count} cards. {error_count} cards had errors.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating collection prices: {str(e)}'
        })

@app.route('/collection')
def view_collection():
    """View user's collection"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, uc.quantity, uc.is_foil, uc.added_at, uc.updated_at
        FROM user_collection uc
        JOIN cards c ON uc.card_id = c.id
        ORDER BY uc.updated_at DESC
    ''')
    collection = cursor.fetchall()
    
    # Add price information and total value to each card
    collection_with_prices = []
    total_collection_value = 0
    
    for card_data in collection:
        price = get_card_price(card_data, card_data[42])  # is_foil is at index 42 (cards: 0-40, uc.quantity: 41, uc.is_foil: 42)
        quantity = card_data[41]  # quantity is at index 41
        total_value = price * quantity if price and quantity else None
        collection_with_prices.append((*card_data, price, total_value))
        
        # Add to total collection value
        if total_value:
            total_collection_value += total_value
    
    conn.close()
    
    return render_template('collection.html', collection=collection_with_prices, total_collection_value=total_collection_value)

@app.route('/search')
def search_cards():
    """Search cards page"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    results = []
    total_results = 0
    total_pages = 0
    
    if query:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Search in card name, type_line, and oracle_text
        search_term = f'%{query}%'
        
        # Get total count
        cursor.execute('''
            SELECT COUNT(*) FROM cards 
            WHERE name LIKE ? OR type_line LIKE ? OR oracle_text LIKE ?
        ''', (search_term, search_term, search_term))
        total_results = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT c.id, c.name, c.mana_cost, c.type_line, c.oracle_text, c.power, c.toughness,
                   c.rarity, c.set_code, c.collector_number, c.image_uris, c.prices,
                   s.name as set_name, s.released_at
            FROM cards c
            LEFT JOIN sets s ON c.set_code = s.code
            WHERE c.name LIKE ? OR c.type_line LIKE ? OR c.oracle_text LIKE ?
            ORDER BY c.name, s.released_at DESC
            LIMIT ? OFFSET ?
        ''', (search_term, search_term, search_term, per_page, offset))
        results = cursor.fetchall()
        
        total_pages = (total_results + per_page - 1) // per_page
        
        conn.close()
    
    return render_template('search.html', 
                         query=query, 
                         results=results, 
                         total_results=total_results,
                         page=page, 
                         per_page=per_page,
                         total_pages=total_pages)

@app.route('/trades')
def view_trades():
    """View trade data with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM trade_data')
    total_trades = cursor.fetchone()[0]
    
    # Calculate pagination
    total_pages = (total_trades + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Get trades for current page
    cursor.execute('''
        SELECT td.*, s.name as set_name, c.name as card_name
        FROM trade_data td
        LEFT JOIN sets s ON td.set_code = s.code
        LEFT JOIN cards c ON td.set_code = c.set_code AND td.collector_number = c.collector_number
        ORDER BY td.created_at DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    trades = cursor.fetchall()
    
    # Calculate summary statistics
    cursor.execute('SELECT SUM(total_amount) FROM trade_data WHERE direction = "Buy"')
    total_bought = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(total_amount) FROM trade_data WHERE direction = "Sell"')
    total_sold = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(profit) FROM trade_data')
    total_profit = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('trades.html', 
                         trades=trades, 
                         page=page, 
                         total_pages=total_pages, 
                         total_trades=total_trades,
                         total_bought=total_bought,
                         total_sold=total_sold,
                         total_profit=total_profit)

@app.route('/get_sets')
def get_sets():
    """Get all sets for dropdown"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT code, name FROM sets ORDER BY name')
        sets = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'sets': [{'code': s[0], 'name': s[1]} for s in sets]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting sets: {str(e)}'
        })

@app.route('/get_set_info/<set_code>')
def get_set_info(set_code):
    """Get set information including max collector number"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get set info
        cursor.execute('SELECT name, card_count FROM sets WHERE code = ?', (set_code,))
        set_info = cursor.fetchone()
        
        if not set_info:
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Set not found: {set_code}'
            })
        
        # Get max collector number for this set
        cursor.execute('SELECT MAX(CAST(collector_number AS INTEGER)) FROM cards WHERE set_code = ?', (set_code,))
        max_collector = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'set_info': {
                'name': set_info[0],
                'card_count': set_info[1],
                'max_collector_number': max_collector or 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting set info: {str(e)}'
        })

@app.route('/get_card_info/<set_code>/<collector_number>')
def get_card_info(set_code, collector_number):
    """Get card information for trade form"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, c.set_code, c.collector_number, s.name as set_name
            FROM cards c
            LEFT JOIN sets s ON c.set_code = s.code
            WHERE c.set_code = ? AND c.collector_number = ?
        ''', (set_code, collector_number))
        
        card = cursor.fetchone()
        conn.close()
        
        if card:
            return jsonify({
                'success': True,
                'card': {
                    'id': card[0],
                    'name': card[1],
                    'set_code': card[2],
                    'collector_number': card[3],
                    'set_name': card[4]
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Card not found: {set_code} #{collector_number}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting card info: {str(e)}'
        })

@app.route('/add_trade', methods=['POST'])
def add_trade():
    """Add a new trade to the database and manage collection"""
    try:
        data = request.get_json()
        
        set_code = data.get('set_code')
        collector_number = data.get('collector_number')
        direction = data.get('direction')
        quantity = int(data.get('quantity', 1))
        price = float(data.get('price', 0))
        profit = float(data.get('profit', 0))
        is_foil = bool(data.get('is_foil', False))
        trade_date = data.get('trade_date')  # Custom trade date
        
        total_amount = quantity * price
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Find the card_id for this set_code and collector_number
        cursor.execute('SELECT id FROM cards WHERE set_code = ? AND collector_number = ?', (set_code, collector_number))
        card_result = cursor.fetchone()
        
        if not card_result:
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Card not found: {set_code} #{collector_number}'
            })
        
        card_id = card_result[0]
        collection_message = ""
        # Handle collection management based on direction
        if direction == 'Buy':
            # Add cards to collection
            add_to_collection(card_id, quantity, is_foil)
            collection_message = f'Added {quantity} {"foil" if is_foil else "regular"} cards to collection'
        elif direction == 'Sell':
            # Check if we have enough cards in collection
            current_quantity = get_collection_quantity(card_id, is_foil)
            if current_quantity < quantity:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Cannot sell {quantity} cards. Only {current_quantity} {"foil" if is_foil else "regular"} cards in collection'
                })
            
            # Remove cards from collection
            update_collection_quantity(card_id, current_quantity - quantity, is_foil)
            collection_message = f'Removed {quantity} {"foil" if is_foil else "regular"} cards from collection'
        
        # Insert trade record with custom date
        if trade_date:
            cursor.execute('''
                INSERT INTO trade_data (set_code, collector_number, direction, quantity, price, total_amount, profit, is_foil, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (set_code, collector_number, direction, quantity, price, total_amount, profit, is_foil, trade_date))
        else:
            cursor.execute('''
                INSERT INTO trade_data (set_code, collector_number, direction, quantity, price, total_amount, profit, is_foil)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (set_code, collector_number, direction, quantity, price, total_amount, profit, is_foil))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {direction} trade for {quantity} {"foil" if is_foil else "regular"} cards. {collection_message}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error adding trade: {str(e)}'
        })

@app.route('/delete_trade', methods=['POST'])
def delete_trade():
    """Delete a trade and manage collection accordingly"""
    try:
        data = request.get_json()
        
        trade_id = data.get('trade_id')
        set_code = data.get('set_code')
        collector_number = data.get('collector_number')
        direction = data.get('direction')
        quantity = int(data.get('quantity', 0))
        is_foil = bool(data.get('is_foil', False))
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Find the card_id for this set_code and collector_number
        cursor.execute('SELECT id FROM cards WHERE set_code = ? AND collector_number = ?', (set_code, collector_number))
        card_result = cursor.fetchone()
        
        if not card_result:
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Card not found: {set_code} #{collector_number}'
            })
        
        card_id = card_result[0]
        collection_message = ""
        
        # Handle collection management based on direction (reverse the original action)
        if direction == 'Buy':
            # Original was buy, so we need to remove cards from collection
            current_quantity = get_collection_quantity(card_id, is_foil)
            if current_quantity < quantity:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete buy trade. Only {current_quantity} {"foil" if is_foil else "regular"} cards in collection'
                })
            
            # Remove cards from collection
            update_collection_quantity(card_id, current_quantity - quantity, is_foil)
            collection_message = f'Removed {quantity} {"foil" if is_foil else "regular"} cards from collection'
            
        elif direction == 'Sell':
            # Original was sell, so we need to add cards back to collection
            add_to_collection(card_id, quantity, is_foil)
            collection_message = f'Added back {quantity} {"foil" if is_foil else "regular"} cards to collection'
        
        # Delete the trade record
        cursor.execute('DELETE FROM trade_data WHERE id = ?', (trade_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Trade not found or already deleted'
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {direction} trade. {collection_message}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting trade: {str(e)}'
        })

@app.route('/fetch_sets', methods=['POST'])
def fetch_sets():
    """Fetch and store sets from Scryfall API"""
    sets_data = get_scryfall_sets()
    if sets_data and 'data' in sets_data:
        store_sets(sets_data['data'])
        return jsonify({'success': True, 'message': f'Fetched and stored {len(sets_data["data"])} sets'})
    else:
        return jsonify({'success': False, 'message': 'Failed to fetch sets'})

@app.route('/fetch_cards/<set_code>', methods=['POST'])
def fetch_cards(set_code):
    """Fetch and store cards for a specific set"""
    cards_data = get_cards_by_set(set_code)
    if cards_data:
        store_cards(cards_data, set_code)
        return jsonify({'success': True, 'message': f'Fetched and stored {len(cards_data)} cards for set {set_code}'})
    else:
        return jsonify({'success': False, 'message': f'Failed to fetch cards for set {set_code}'})

@app.route('/settings')
def view_settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/delete_all_trades', methods=['POST'])
def delete_all_trades():
    """Delete all trades from the database"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get count before deleting
        cursor.execute('SELECT COUNT(*) FROM trade_data')
        count_before = cursor.fetchone()[0]
        
        # Delete all trades
        cursor.execute('DELETE FROM trade_data')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {count_before} trades from the database'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting trades: {str(e)}'})

@app.route('/get_database_stats')
def get_database_stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get total cards count
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards = cursor.fetchone()[0]
        
        # Get total sets count
        cursor.execute('SELECT COUNT(*) FROM sets')
        total_sets = cursor.fetchone()[0]
        
        # Get cards in collection count
        cursor.execute('SELECT COUNT(*) FROM user_collection')
        collection_cards = cursor.fetchone()[0]
        
        # Get total trades count
        cursor.execute('SELECT COUNT(*) FROM trade_data')
        total_trades = cursor.fetchone()[0]
        
        # Get total decks count
        cursor.execute('SELECT COUNT(*) FROM decks')
        total_decks = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_cards': total_cards,
                'total_sets': total_sets,
                'collection_cards': collection_cards,
                'total_trades': total_trades,
                'total_decks': total_decks
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting database stats: {str(e)}'
        })

@app.route('/decks')
def decks():
    """Display all decks"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get all decks
        cursor.execute('''
            SELECT id, name, description, format, created_at, updated_at
            FROM decks
            ORDER BY updated_at DESC
        ''')
        decks = cursor.fetchall()
        
        # Get deck cards for each deck
        deck_data = []
        for deck in decks:
            deck_id, name, description, format_name, created_at, updated_at = deck
            
            # Get main deck cards
            cursor.execute('''
                SELECT card_name, quantity
                FROM deck_cards
                WHERE deck_id = ? AND is_sideboard = FALSE
                ORDER BY card_name
            ''', (deck_id,))
            main_deck = cursor.fetchall()
            
            # Get sideboard cards
            cursor.execute('''
                SELECT card_name, quantity
                FROM deck_cards
                WHERE deck_id = ? AND is_sideboard = TRUE
                ORDER BY card_name
            ''', (deck_id,))
            sideboard = cursor.fetchall()
            
            deck_data.append({
                'id': deck_id,
                'name': name,
                'description': description,
                'format': format_name,
                'created_at': created_at,
                'updated_at': updated_at,
                'main_deck': main_deck,
                'sideboard': sideboard
            })
        
        conn.close()
        
        return render_template('decks.html', decks=deck_data)
        
    except Exception as e:
        return f"Error loading decks: {str(e)}", 500

@app.route('/add_deck', methods=['POST'])
def add_deck():
    """Add a new deck"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        format_name = data.get('format', '').strip()
        main_deck = data.get('main_deck', [])
        sideboard = data.get('sideboard', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Deck name is required'})
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Insert deck
        cursor.execute('''
            INSERT INTO decks (name, description, format)
            VALUES (?, ?, ?)
        ''', (name, description, format_name))
        
        deck_id = cursor.lastrowid
        
        # Insert main deck cards
        for card in main_deck:
            card_name = card.get('name', '').strip()
            quantity = int(card.get('quantity', 1))
            if card_name:
                cursor.execute('''
                    INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard)
                    VALUES (?, ?, ?, FALSE)
                ''', (deck_id, card_name, quantity))
        
        # Insert sideboard cards
        for card in sideboard:
            card_name = card.get('name', '').strip()
            quantity = int(card.get('quantity', 1))
            if card_name:
                cursor.execute('''
                    INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard)
                    VALUES (?, ?, ?, TRUE)
                ''', (deck_id, card_name, quantity))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Deck added successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding deck: {str(e)}'})

@app.route('/delete_deck', methods=['POST'])
def delete_deck():
    """Delete a deck"""
    try:
        data = request.get_json()
        deck_id = data.get('deck_id')
        
        if not deck_id:
            return jsonify({'success': False, 'message': 'Deck ID is required'})
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Delete deck (cascade will delete deck_cards)
        cursor.execute('DELETE FROM decks WHERE id = ?', (deck_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Deck deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting deck: {str(e)}'})

@app.route('/delete_all_decks', methods=['POST'])
def delete_all_decks():
    """Delete all decks"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get count before deleting
        cursor.execute('SELECT COUNT(*) FROM decks')
        count_before = cursor.fetchone()[0]
        
        # Delete all decks (cascade will delete deck_cards)
        cursor.execute('DELETE FROM decks')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {count_before} decks from the database'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting decks: {str(e)}'})

@app.route('/deck/<int:deck_id>')
def deck_view(deck_id):
    """View individual deck details"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get deck info
        cursor.execute('''
            SELECT id, name, description, format, created_at, updated_at
            FROM decks
            WHERE id = ?
        ''', (deck_id,))
        deck = cursor.fetchone()
        
        if not deck:
            return "Deck not found", 404
        
        deck_id, name, description, format_name, created_at, updated_at = deck
        
        # Get main deck cards
        cursor.execute('''
            SELECT card_name, quantity
            FROM deck_cards
            WHERE deck_id = ? AND is_sideboard = FALSE
            ORDER BY card_name
        ''', (deck_id,))
        main_deck = cursor.fetchall()
        
        # Get sideboard cards
        cursor.execute('''
            SELECT card_name, quantity
            FROM deck_cards
            WHERE deck_id = ? AND is_sideboard = TRUE
            ORDER BY card_name
        ''', (deck_id,))
        sideboard = cursor.fetchall()
        
        # Check collection quantities for each card
        def get_collection_quantity(card_name):
            cursor.execute('''
                SELECT SUM(quantity) FROM user_collection uc
                JOIN cards c ON uc.card_id = c.id
                WHERE c.name = ?
            ''', (card_name,))
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        
        # Add collection quantities to main deck
        main_deck_with_collection = []
        for card_name, quantity in main_deck:
            collection_qty = get_collection_quantity(card_name)
            main_deck_with_collection.append({
                'name': card_name,
                'quantity': quantity,
                'in_collection': collection_qty
            })
        
        # Add collection quantities to sideboard
        sideboard_with_collection = []
        for card_name, quantity in sideboard:
            collection_qty = get_collection_quantity(card_name)
            sideboard_with_collection.append({
                'name': card_name,
                'quantity': quantity,
                'in_collection': collection_qty
            })
        
        conn.close()
        
        deck_data = {
            'id': deck_id,
            'name': name,
            'description': description,
            'format': format_name,
            'created_at': created_at,
            'updated_at': updated_at,
            'main_deck': main_deck_with_collection,
            'sideboard': sideboard_with_collection
        }
        
        return render_template('deck_view.html', deck=deck_data)
        
    except Exception as e:
        return f"Error loading deck: {str(e)}", 500

@app.route('/deck/new')
def deck_new():
    """Create new deck page"""
    deck_data = {
        'id': None,
        'name': '',
        'description': '',
        'format': '',
        'created_at': '',
        'updated_at': '',
        'main_deck_text': '',
        'sideboard_text': ''
    }
    return render_template('deck_edit.html', deck=deck_data)

@app.route('/deck/<int:deck_id>/edit')
def deck_edit(deck_id):
    """Edit deck page"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get deck info
        cursor.execute('''
            SELECT id, name, description, format, created_at, updated_at
            FROM decks
            WHERE id = ?
        ''', (deck_id,))
        deck = cursor.fetchone()
        
        if not deck:
            return "Deck not found", 404
        
        deck_id, name, description, format_name, created_at, updated_at = deck
        
        # Get main deck cards
        cursor.execute('''
            SELECT card_name, quantity
            FROM deck_cards
            WHERE deck_id = ? AND is_sideboard = FALSE
            ORDER BY card_name
        ''', (deck_id,))
        main_deck = cursor.fetchall()
        
        # Get sideboard cards
        cursor.execute('''
            SELECT card_name, quantity
            FROM deck_cards
            WHERE deck_id = ? AND is_sideboard = TRUE
            ORDER BY card_name
        ''', (deck_id,))
        sideboard = cursor.fetchall()
        
        conn.close()
        
        # Format cards for text areas
        main_deck_text = '\n'.join([f"{qty} {name}" for name, qty in main_deck])
        sideboard_text = '\n'.join([f"{qty} {name}" for name, qty in sideboard])
        
        deck_data = {
            'id': deck_id,
            'name': name,
            'description': description,
            'format': format_name,
            'created_at': created_at,
            'updated_at': updated_at,
            'main_deck_text': main_deck_text,
            'sideboard_text': sideboard_text
        }
        
        return render_template('deck_edit.html', deck=deck_data)
        
    except Exception as e:
        return f"Error loading deck for edit: {str(e)}", 500

def validate_cards_in_database(card_names):
    """Check if all card names exist in the database"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        missing_cards = []
        for card_name in card_names:
            cursor.execute('SELECT COUNT(*) FROM cards WHERE name = ?', (card_name,))
            count = cursor.fetchone()[0]
            if count == 0:
                missing_cards.append(card_name)
        
        conn.close()
        return missing_cards
        
    except Exception as e:
        print(f"Error validating cards: {e}")
        return card_names  # Return all cards as missing if error

def parse_decklist_text(text):
    """Parse decklist text into card list"""
    cards = []
    if not text.strip():
        return cards
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Try to parse "quantity cardname" format
        parts = line.split(' ', 1)
        if len(parts) == 2 and parts[0].isdigit():
            try:
                quantity = int(parts[0])
                card_name = parts[1].strip()
                if card_name:
                    cards.append({'name': card_name, 'quantity': quantity})
            except ValueError:
                # If first part isn't a number, treat whole line as card name with qty 1
                cards.append({'name': line, 'quantity': 1})
        else:
            # If no quantity specified, assume 1
            cards.append({'name': line, 'quantity': 1})
    
    return cards

@app.route('/update_deck', methods=['POST'])
def update_deck():
    """Create or update a deck with validation"""
    try:
        data = request.get_json()
        deck_id = data.get('deck_id')
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        format_name = data.get('format', '').strip()
        main_deck_text = data.get('main_deck_text', '').strip()
        sideboard_text = data.get('sideboard_text', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': 'Deck name is required'})
        
        # Parse deck lists
        main_deck = parse_decklist_text(main_deck_text)
        sideboard = parse_decklist_text(sideboard_text)
        
        # Get all unique card names for validation
        all_card_names = set()
        for card in main_deck + sideboard:
            all_card_names.add(card['name'])
        
        # Validate cards exist in database
        missing_cards = validate_cards_in_database(list(all_card_names))
        if missing_cards:
            return jsonify({
                'success': False, 
                'message': f'Cards not found in database: {", ".join(missing_cards)}'
            })
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        if deck_id:
            # Update existing deck
            cursor.execute('''
                UPDATE decks 
                SET name = ?, description = ?, format = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, description, format_name, deck_id))
            
            # Delete existing deck cards
            cursor.execute('DELETE FROM deck_cards WHERE deck_id = ?', (deck_id,))
        else:
            # Create new deck
            cursor.execute('''
                INSERT INTO decks (name, description, format)
                VALUES (?, ?, ?)
            ''', (name, description, format_name))
            deck_id = cursor.lastrowid
        
        # Insert main deck cards
        for card in main_deck:
            cursor.execute('''
                INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard)
                VALUES (?, ?, ?, FALSE)
            ''', (deck_id, card['name'], card['quantity']))
        
        # Insert sideboard cards
        for card in sideboard:
            cursor.execute('''
                INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard)
                VALUES (?, ?, ?, TRUE)
            ''', (deck_id, card['name'], card['quantity']))
        
        conn.commit()
        conn.close()
        
        action = 'updated' if data.get('deck_id') else 'created'
        return jsonify({'success': True, 'message': f'Deck {action} successfully', 'deck_id': deck_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving deck: {str(e)}'})

if __name__ == '__main__':
    init_db()

    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    app.run(debug=debug, host=host, port=port)
