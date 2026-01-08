#!/usr/bin/env python3
"""
Magic Collector - Create ELK Index Script
This script creates an Elasticsearch index for storing MTG card data
with fields from cards table and card_prices_history table.
"""

import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Elasticsearch configuration
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))
ELASTICSEARCH_USER = os.getenv('ELASTICSEARCH_USER', None)
ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', None)
ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'mtg_cards')

print(f"ELASTICSEARCH_HOST: {ELASTICSEARCH_HOST}")
print(f"ELASTICSEARCH_PORT: {ELASTICSEARCH_PORT}")
print(f"ELASTICSEARCH_USER: {ELASTICSEARCH_USER}")
print(f"ELASTICSEARCH_PASSWORD: {ELASTICSEARCH_PASSWORD}")
print(f"ELASTICSEARCH_INDEX: {ELASTICSEARCH_INDEX}")
print(f"ELASTICSEARCH_USE_SSL: {os.getenv('ELASTICSEARCH_USE_SSL', 'false')}")
print(f"ELASTICSEARCH_VERIFY_CERTS: {os.getenv('ELASTICSEARCH_VERIFY_CERTS', 'false')}")

def create_elasticsearch_client():
    """Create and return an Elasticsearch client"""
    # Check if SSL is required (https)
    use_ssl = os.getenv('ELASTICSEARCH_USE_SSL', 'false').lower() == 'true'
    verify_certs = os.getenv('ELASTICSEARCH_VERIFY_CERTS', 'true').lower() == 'true'
    protocol = 'https' if use_ssl else 'http'
    
    # Build the connection URL
    connection_url = f'{protocol}://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}'
    print(f"connection_url: {connection_url}")
    # Base configuration
    es_config = {
        'hosts': [connection_url],
        'request_timeout': 30,
        'max_retries': 3,
        'retry_on_timeout': True
    }
    
    # SSL configuration
    if use_ssl and not verify_certs:
        es_config['verify_certs'] = False
        es_config['ssl_show_warn'] = False
    
    # Authentication
    if ELASTICSEARCH_USER and ELASTICSEARCH_PASSWORD:
        es_config['basic_auth'] = (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD)
    
    es = Elasticsearch(
        [connection_url],
        basic_auth=(ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD),
        verify_certs=False,
        ssl_show_warn=False
    )
    return es

def create_index_mapping():
    """Create the Elasticsearch index mapping for MTG cards"""
    mapping = {
        "mappings": {
            "properties": {
                # Card identification
                "id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "set_id": {"type": "keyword"},
                "set_code": {"type": "keyword"},
                "set_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "collector_number": {"type": "keyword"},
                
                # Card characteristics
                "mana_cost": {"type": "text"},
                "cmc": {"type": "float"},
                "type_line": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "oracle_text": {"type": "text"},
                "power": {"type": "keyword"},
                "toughness": {"type": "keyword"},
                
                # Colors
                "colors": {"type": "keyword"},
                "color_identity": {"type": "keyword"},
                
                # Legalities (stored as object)
                "legalities": {
                    "type": "object",
                    "properties": {
                        "standard": {"type": "keyword"},
                        "modern": {"type": "keyword"},
                        "legacy": {"type": "keyword"},
                        "vintage": {"type": "keyword"},
                        "commander": {"type": "keyword"},
                        "pioneer": {"type": "keyword"},
                        "pauper": {"type": "keyword"},
                        "historic": {"type": "keyword"},
                        "penny": {"type": "keyword"},
                        "duel": {"type": "keyword"},
                        "oldschool": {"type": "keyword"},
                        "premodern": {"type": "keyword"}
                    }
                },
                
                # Games and finishes
                "games": {"type": "keyword"},
                "finishes": {"type": "keyword"},
                
                # Boolean flags
                "reserved": {"type": "boolean"},
                "foil": {"type": "boolean"},
                "nonfoil": {"type": "boolean"},
                "oversized": {"type": "boolean"},
                "promo": {"type": "boolean"},
                "reprint": {"type": "boolean"},
                "variation": {"type": "boolean"},
                "full_art": {"type": "boolean"},
                "textless": {"type": "boolean"},
                "booster": {"type": "boolean"},
                "story_spotlight": {"type": "boolean"},
                
                # Card details
                "rarity": {"type": "keyword"},
                "artist": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "border_color": {"type": "keyword"},
                "frame": {"type": "keyword"},
                "edhrec_rank": {"type": "integer"},
                "penny_rank": {"type": "integer"},
                
                # Prices (from card_prices_history - stored as array of objects)
                "prices_history": {
                    "type": "nested",
                    "properties": {
                        "price_type": {"type": "keyword"},
                        "price_value": {"type": "float"},
                        "currency": {"type": "keyword"},
                        "recorded_at": {"type": "date"}
                    }
                },
                
                # Current prices (from prices field)
                "prices": {
                    "type": "object",
                    "properties": {
                        "usd": {"type": "float"},
                        "usd_foil": {"type": "float"},
                        "usd_etched": {"type": "float"},
                        "eur": {"type": "float"},
                        "eur_foil": {"type": "float"},
                        "tix": {"type": "float"}
                    }
                },
                
                # URIs and images
                "related_uris": {
                    "type": "object",
                    "enabled": False  # Store as JSON, not analyzed
                },
                "purchase_uris": {
                    "type": "object",
                    "enabled": False
                },
                "image_uris": {
                    "type": "object",
                    "properties": {
                        "small": {"type": "keyword"},
                        "normal": {"type": "keyword"},
                        "large": {"type": "keyword"},
                        "png": {"type": "keyword"},
                        "art_crop": {"type": "keyword"},
                        "border_crop": {"type": "keyword"}
                    }
                },
                
                # Card faces (for double-faced cards)
                "card_faces": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text"},
                        "mana_cost": {"type": "text"},
                        "type_line": {"type": "text"},
                        "oracle_text": {"type": "text"},
                        "power": {"type": "keyword"},
                        "toughness": {"type": "keyword"},
                        "colors": {"type": "keyword"},
                        "color_identity": {"type": "keyword"},
                        "image_uris": {
                            "type": "object",
                            "properties": {
                                "small": {"type": "keyword"},
                                "normal": {"type": "keyword"},
                                "large": {"type": "keyword"},
                                "png": {"type": "keyword"},
                                "art_crop": {"type": "keyword"},
                                "border_crop": {"type": "keyword"}
                            }
                        }
                    }
                },
                
                # Timestamps
                "created_at": {"type": "date"},
                "indexed_at": {"type": "date"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "card_name_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        }
    }
    return mapping

def create_index(es, index_name, mapping):
    """Create the Elasticsearch index with the specified mapping"""
    try:
        # Check if index already exists
        if es.indices.exists(index=index_name):
            print(f"⚠️  Index '{index_name}' already exists.")
            response = input("Do you want to delete and recreate it? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                es.indices.delete(index=index_name)
                print(f"🗑️  Deleted existing index '{index_name}'")
            else:
                print("❌ Index creation cancelled")
                return False
        
        # Create the index
        # For Elasticsearch 7.x and 8.x, use body parameter
        es.indices.create(index=index_name, body=mapping)
        print(f"✅ Successfully created index '{index_name}'")
        return True
        
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False

def verify_index(es, index_name):
    """Verify the index was created correctly"""
    try:
        if es.indices.exists(index=index_name):
            mapping = es.indices.get_mapping(index=index_name)
            settings = es.indices.get_settings(index=index_name)
            
            print(f"\n📊 Index '{index_name}' verification:")
            print(f"   • Status: ✅ Exists")
            print(f"   • Shards: {settings[index_name]['settings']['index']['number_of_shards']}")
            print(f"   • Replicas: {settings[index_name]['settings']['index']['number_of_replicas']}")
            print(f"   • Fields: {len(mapping[index_name]['mappings']['properties'])} properties defined")
            return True
        else:
            print(f"❌ Index '{index_name}' does not exist")
            return False
    except Exception as e:
        print(f"❌ Error verifying index: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Magic Collector - Create ELK Index Script")
    print("=" * 60)
    
    # Create Elasticsearch client
    print(f"🔌 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}...")
    try:
        es = create_elasticsearch_client()
        
        # Test connection with better error handling
        try:
            if not es.ping():
                print("❌ Could not connect to Elasticsearch. The server did not respond to ping.")
                print(f"   Check if Elasticsearch is running at {ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}")
                exit(1)
        except Exception as ping_error:
            print(f"❌ Connection error: {ping_error}")
            print(f"   Failed to connect to {ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}")
            print("\n💡 Troubleshooting:")
            print("   1. Verify Elasticsearch is running")
            print("   2. Check if the host and port are correct")
            print("   3. Check firewall/network settings")
            print("   4. If using SSL, set ELASTICSEARCH_USE_SSL=true in .env")
            print("   5. If using self-signed cert, set ELASTICSEARCH_VERIFY_CERTS=false")
            exit(1)
        
        print("✅ Connected to Elasticsearch")
        
        # Get Elasticsearch info
        try:
            info = es.info()
            print(f"📊 Elasticsearch version: {info['version']['number']}")
        except Exception as info_error:
            print(f"⚠️  Could not get Elasticsearch info: {info_error}")
        
    except Exception as e:
        print(f"❌ Error creating Elasticsearch client: {e}")
        print("\n💡 Make sure Elasticsearch is running and check your .env file:")
        print("   ELASTICSEARCH_HOST=localhost")
        print("   ELASTICSEARCH_PORT=9200")
        print("   ELASTICSEARCH_USER=your_user (optional)")
        print("   ELASTICSEARCH_PASSWORD=your_password (optional)")
        print("   ELASTICSEARCH_INDEX=mtg_cards")
        print("   ELASTICSEARCH_USE_SSL=false (set to true if using HTTPS)")
        print("   ELASTICSEARCH_VERIFY_CERTS=true (set to false for self-signed certs)")
        exit(1)
    
    # Create index mapping
    print(f"\n📝 Creating index mapping for '{ELASTICSEARCH_INDEX}'...")
    mapping = create_index_mapping()
    
    # Create the index
    success = create_index(es, ELASTICSEARCH_INDEX, mapping)
    
    if success:
        verify_index(es, ELASTICSEARCH_INDEX)
        print("\n✅ Index creation completed!")
        print(f"📋 You can now use '{ELASTICSEARCH_INDEX}' index to store MTG card data.")
    else:
        print("\n❌ Index creation failed. Please check the errors above.")
