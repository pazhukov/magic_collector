# Magic: The Gathering Collector

A Python web application for collecting and browsing Magic: The Gathering card information using the Scryfall API.

## Features

- **Sets View**: Browse all available Magic: The Gathering sets with details like release dates, card counts, and set types
- **Cards View**: View cards from specific sets with images, mana costs, types, and other card details
- **Data Storage**: All data is stored locally in a SQLite database
- **API Integration**: Fetches data from the official Scryfall API

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5001`

3. **Fetch Sets**: Click "Fetch All Sets" to load all available Magic sets from the Scryfall API

4. **Browse Sets**: View all sets on the "All Sets" page with their details

5. **View Cards**: Click on any set to view its cards, or click "Fetch Cards" to load card data for that set

## API Endpoints

- `/` - Home page with overview and recent sets
- `/sets` - View all available sets
- `/cards/<set_code>` - View cards for a specific set
- `/fetch_sets` - Fetch and store all sets from Scryfall API
- `/fetch_cards/<set_code>` - Fetch and store cards for a specific set

## Database Schema

The application uses SQLite with two main tables:

- **sets**: Stores set information (id, code, name, type, release date, etc.)
- **cards**: Stores card information (name, mana cost, type, rarity, image URLs, etc.)

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
- Block information
- Digital/foil status
- Set icons and links

### Cards Information
- Card name and mana cost
- Type line and oracle text
- Power and toughness
- Rarity and collector number
- Artist and border color
- Card images (when available)
- Pricing information
- Legalities and game formats

## Notes

- The application fetches data from the Scryfall API on demand
- Data is cached locally in SQLite for faster access
- Card images are displayed when available from the API
- The application handles pagination for large sets automatically
