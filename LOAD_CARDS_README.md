# Load All Cards Script

This script loads all Magic: The Gathering cards from all sets into your local database.

## ⚠️ WARNING

**This script will load over 109,000 cards from 991 sets!**
- **Estimated time**: ~2 hours
- **API requests**: Thousands of requests to Scryfall

## Features

- ✅ **Error Handling**: Continues loading even if individual cards/sets fail
- ✅ **Progress Tracking**: Shows progress for each set and overall
- ✅ **API Respect**: Includes delays to be respectful to Scryfall API
- ✅ **Retry Logic**: Retries failed requests automatically
- ✅ **Database Safety**: Uses INSERT OR REPLACE to avoid duplicates
- ✅ **Comprehensive Logging**: Detailed output of what's happening
- ✅ **Confirmation Prompt**: Asks for confirmation before starting
- ✅ **Time Estimation**: Shows estimated loading time

## Usage

### Run the script:
```bash
python3 load_all_cards.py
```

### What it does:
1. **Shows Warning**: Displays estimated time and card count
2. **Asks Confirmation**: Requires user confirmation to proceed
3. **Loads All Sets**: Iterates through all sets in your database
4. **Fetches Cards**: Downloads all cards for each set from Scryfall API
5. **Stores Data**: Saves all card information to your local database
6. **Verifies Results**: Shows summary of loaded cards

## Output Example

```
⚠️  WARNING: This script will load ALL cards from ALL sets.
This may take a very long time and use significant disk space.
============================================================
📊 Estimated total cards to load: 109,567
⏱️  Estimated loading time: 365.2 minutes

Do you want to continue? (y/N): y

🚀 Magic Collector - Load All Cards Script
============================================================
✅ Database initialized
📊 Found 991 sets with cards to load
============================================================

📦 Processing set 1/991: Lorwyn Eclipsed (ecl)
🔄 Loading cards for Lorwyn Eclipsed (ecl) - Expected: 0 cards
⚠️  No cards found for Lorwyn Eclipsed (ecl)

📦 Processing set 2/991: Avatar: The Last Airbender Front Cards (ftla)
🔄 Loading cards for Avatar: The Last Airbender Front Cards (ftla) - Expected: 10 cards
   ✅ Loaded 10 cards for Avatar: The Last Airbender Front Cards (ftla)
```

## Error Handling

The script includes comprehensive error handling:

- **Network Errors**: Retries failed requests with delays
- **API Errors**: Continues loading other sets if one fails
- **Database Errors**: Skips problematic cards and continues
- **Keyboard Interrupt**: Gracefully handles Ctrl+C interruption
- **Individual Card Failures**: Never stops the entire process

## Configuration

You can modify these settings at the top of the script:

```python
DATABASE = 'magic_collector.db'        # Database file
REQUEST_DELAY = 0.1                    # Delay between API requests (seconds)
MAX_RETRIES = 3                        # Max retries for failed requests
RETRY_DELAY = 2                        # Delay before retrying (seconds)
```

## Alternative: Load Specific Sets

If you don't want to load ALL cards, you can:

1. **Use the main app**: Load cards for specific sets via the web interface
2. **Modify the script**: Edit the `get_all_sets()` function to filter sets
3. **Load in batches**: Run the script multiple times with different date ranges

## After Running

Once the script completes successfully, you can:

1. **Run the main app**: `python3 app.py`
2. **Browse cards**: Visit `/sets` and click on individual sets
3. **Search cards**: Use the card search functionality
4. **Build collection**: Add cards to your collection

## Troubleshooting

- **Permission errors**: Make sure the script is executable: `chmod +x load_all_cards.py`
- **Database locked**: Close the main app before running this script
- **Network issues**: The script will retry automatically, just wait
- **API rate limits**: The script includes delays to respect API limits
- **Disk space**: Ensure you have several GB of free space
- **Time commitment**: This is a long-running process (6+ hours)

## Performance Tips

- **Run overnight**: Start the script before going to bed
- **Stable connection**: Ensure stable internet connection
- **Close other apps**: Free up system resources
- **Monitor progress**: Check the output periodically

## Data Stored

For each card, the script stores:

- **Basic Info**: Name, mana cost, type, oracle text
- **Stats**: Power, toughness, CMC, rarity
- **Set Info**: Set code, collector number
- **Images**: Image URIs for different sizes
- **Prices**: Current market prices
- **Card Faces**: For double-sided cards
- **Colors**: Color identity and mana colors

## Stopping the Script

- **Ctrl+C**: Gracefully stops the script
- **Progress saved**: Cards loaded so far are saved to database
- **Resume**: You can run the script again to continue from where it left off
