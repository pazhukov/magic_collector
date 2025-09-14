# Magic: The Gathering Collector

A comprehensive Python web application for collecting, managing, and trading Magic: The Gathering cards using the Scryfall API. This application provides a complete solution for Magic: The Gathering enthusiasts to organize their collection, track trades, build decks, and explore card data.

## Features

### Core Functionality
- **Sets Management**: Browse all available Magic: The Gathering sets with details like release dates, card counts, and set types
- **Card Database**: View cards from specific sets with images, mana costs, types, oracle text, and comprehensive card details
- **Collection Management**: Track your personal card collection with foil/non-foil quantities and collection value
- **Trading System**: Record buy/sell transactions with profit tracking and automatic collection updates
- **Deck Building**: Create and manage Magic decks with main deck and sideboard support
- **Advanced Search**: Search through cards by name, type, oracle text, and other attributes
- **Data Storage**: All data is stored locally in a SQLite database for offline access
- **API Integration**: Fetches data from the official Scryfall API with automatic updates

### Collection Features
- Add/remove cards from your personal collection
- Track both foil and non-foil quantities separately
- View collection value based on current market prices
- Update card prices and legalities from Scryfall API
- Collection statistics and overview

### Trading Features
- Record buy and sell transactions
- Automatic collection management (buy adds to collection, sell removes from collection)
- Profit/loss tracking per transaction
- Trade history with pagination
- Custom trade dates
- Trade deletion with collection rollback

### Deck Building Features
- Create and manage multiple decks
- Support for main deck and sideboard
- Deck validation against your card database
- Collection quantity checking for deck cards
- Deck editing and deletion
- Format specification for each deck

### Search & Discovery
- Full-text search across card names, types, and oracle text
- Paginated search results
- Browse cards by set
- View detailed card information with images
- See other printings of the same card

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Create a `.env` file to customize configuration (see Configuration section below)

## Configuration

The application supports configuration through environment variables. You can create a `.env` file in the project root to customize settings:

### Environment Variables

Create a `.env` file with the following optional variables:

```env
# Database configuration
DATABASE=magic_collector.db

# Server configuration
HOST=127.0.0.1
PORT=5001
DEBUG=False
```

### Configuration Options

- **DATABASE**: SQLite database file path (default: `magic_collector.db`)
- **HOST**: Server host address (default: `127.0.0.1`)
- **PORT**: Server port number (default: `5001`)
- **DEBUG**: Enable debug mode (default: `False`)

### Example .env File

```env
# Custom database location
DATABASE=/path/to/your/magic_collector.db

# Run on all interfaces
HOST=0.0.0.0
PORT=8080

# Enable debug mode
DEBUG=True
```

If no `.env` file is present, the application will use the default values.

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5001`

3. **Initial Setup**: Click "Fetch All Sets" to load all available Magic sets from the Scryfall API

4. **Browse Data**: 
   - View all sets on the "All Sets" page
   - Click on any set to view its cards
   - Use "Fetch Cards" to load card data for specific sets

5. **Manage Collection**:
   - Add cards to your collection from card detail pages
   - View your collection with current values
   - Update card prices and legalities

6. **Track Trades**:
   - Record buy/sell transactions
   - View trade history and profit/loss
   - Automatic collection management

7. **Build Decks**:
   - Create and manage multiple decks
   - Add main deck and sideboard cards
   - Check collection quantities for deck cards

8. **Search Cards**:
   - Use the search functionality to find specific cards
   - Search by name, type, or oracle text

## API Endpoints

### Main Pages
- `/` - Home page with database statistics and recent sets
- `/sets` - View all available sets
- `/cards/<set_code>` - View cards for a specific set
- `/card/<card_id>` - View detailed information for a specific card
- `/collection` - View and manage your personal card collection
- `/search` - Search cards by name, type, or oracle text
- `/trades` - View and manage trading history
- `/decks` - View and manage your decks
- `/deck/<deck_id>` - View individual deck details
- `/deck/new` - Create a new deck
- `/deck/<deck_id>/edit` - Edit an existing deck
- `/settings` - Application settings and database management

### Data Management
- `/fetch_sets` (POST) - Fetch and store all sets from Scryfall API
- `/fetch_cards/<set_code>` (POST) - Fetch and store cards for a specific set
- `/refresh_card/<card_id>` - Refresh individual card data from Scryfall API

### Collection Management
- `/add_to_collection` (POST) - Add cards to your collection
- `/update_collection_quantity` (POST) - Update exact quantity of cards in collection
- `/clear_collection` (POST) - Clear all cards from collection
- `/update_collection_prices` (POST) - Update prices and legalities for all collection cards

### Trading System
- `/add_trade` (POST) - Add a new trade transaction
- `/delete_trade` (POST) - Delete a trade and manage collection accordingly
- `/delete_all_trades` (POST) - Delete all trades from database

### Deck Management
- `/add_deck` (POST) - Add a new deck
- `/update_deck` (POST) - Create or update a deck with validation
- `/delete_deck` (POST) - Delete a deck
- `/delete_all_decks` (POST) - Delete all decks

### API Data Endpoints
- `/get_sets` - Get all sets for dropdown menus
- `/get_set_info/<set_code>` - Get set information including max collector number
- `/get_card_info/<set_code>/<collector_number>` - Get card information for trade forms
- `/get_database_stats` - Get comprehensive database statistics

## Database Schema

The application uses SQLite with the following tables:

### Core Tables
- **sets**: Stores set information (id, code, name, type, release date, card count, etc.)
- **cards**: Stores comprehensive card information (name, mana cost, type, rarity, oracle text, image URLs, prices, legalities, etc.)

### Collection Management
- **user_collection**: Tracks personal card collection (card_id, quantity, foil status, timestamps)
- **card_legalities_history**: Historical tracking of card legalities across formats
- **card_prices_history**: Historical tracking of card prices over time

### Trading System
- **trade_data**: Records buy/sell transactions (set_code, collector_number, direction, quantity, price, profit, etc.)

### Deck Building
- **decks**: Stores deck information (name, description, format, timestamps)
- **deck_cards**: Links decks to cards with quantities and sideboard status

### Key Features
- Foreign key relationships maintain data integrity
- JSON storage for complex data (prices, legalities, image_uris, card_faces)
- Automatic timestamp tracking for all data
- Support for both foil and non-foil card variants
- Historical data tracking for prices and legalities

## Data Sources

- [Scryfall API - Sets](https://scryfall.com/docs/api/sets/all)
- [Scryfall API - Cards](https://scryfall.com/docs/api/cards/collector)

## Technologies Used

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, Bootstrap 5, Font Awesome
- **API**: Scryfall REST API
- **Data Format**: JSON

## Features in Detail

### Sets Information
- Set name, code, and type
- Release date and card count
- Block information and parent sets
- Digital/foil status
- Set icons and search URIs
- Printed size and card counts

### Cards Information
- Card name and mana cost
- Type line and oracle text
- Power and toughness
- Rarity and collector number
- Artist and border color
- Card images (normal, large, small)
- Current pricing (USD, EUR, TIX)
- Legalities across all formats
- Card faces for double-sided cards
- Color identity and mana symbols
- EDHREC and penny rankings

### Collection Management
- Track foil and non-foil quantities separately
- Real-time collection value calculation
- Add/remove cards with quantity controls
- Collection statistics and overview
- Price history tracking
- Automatic collection updates from trades

### Trading System
- Record buy/sell transactions with full details
- Automatic collection management
- Profit/loss calculation per trade
- Custom trade dates
- Trade history with pagination
- Trade deletion with collection rollback
- Support for both foil and non-foil trades

### Deck Building
- Create unlimited decks with descriptions
- Main deck and sideboard support
- Deck validation against card database
- Collection quantity checking
- Format specification (Standard, Modern, etc.)
- Deck editing and management
- Card name validation

## Notes

- The application fetches data from the Scryfall API on demand
- Data is cached locally in SQLite for faster access and offline use
- Card images are displayed when available from the API
- The application handles pagination for large sets automatically
- Collection management is fully integrated with trading system
- Deck building includes validation against your card database
- Historical data tracking for prices and legalities
- Support for double-sided cards and complex card types
- Automatic collection updates when recording trades
- Real-time collection value calculation based on current market prices
