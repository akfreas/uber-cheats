#!/usr/bin/env python3

import argparse
import asyncio
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List

import aiohttp
import openai
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tabulate import tabulate
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()  # Load environment variables from .env file

# OpenAI API key will be set here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# System-specific configurations
SYSTEM = platform.system()
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"

# Chrome paths for different systems
CHROME_PATHS = {
    "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "Linux": "/usr/bin/google-chrome"
}

# ChromeDriver paths for different systems
CHROMEDRIVER_PATHS = {
    "Darwin": "/usr/local/bin/chromedriver",
    "Linux": "/usr/local/bin/chromedriver"
}

DEAL_EXTRACTION_PROMPT = """
Extract deal information from the following HTML snippet of an Uber Eats restaurant page.
Focus on items that have promotions like "Buy 1, Get 1 Free" or "Top Offer".

For each deal found, provide:
1. Item name
2. Price as a float number (remove the € symbol and convert to float, e.g., "12,99 €" should become 12.99)
3. Description (if available)
4. Promotion type (e.g., "Buy 1, Get 1 Free")

Return the information in this JSON format:
{
    "deals": [
        {
            "name": "Item name",
            "price": 12.99,
            "description": "Item description",
            "promotion": "Promotion type"
        }
    ]
}

Important formatting rules:
- Price must be a float number, not a string
- Convert comma-separated prices to dot-separated (e.g., "12,99" → 12.99)
- Remove any currency symbols (€, EUR, etc.)
- If a price range is given (e.g., "12,99 € - 15,99 €"), use the lower price
- If no price is found, use 0.0

If no deals are found, return an empty deals array.
HTML:
"""

def get_chrome_path():
    """Get the Chrome binary path based on the operating system."""
    chrome_path = CHROME_PATHS.get(SYSTEM)
    
    if not chrome_path or not os.path.exists(chrome_path):
        # For development, try to find Chrome in common locations
        if IS_MACOS:
            alternate_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]
        else:  # Linux
            alternate_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium"
            ]
        
        for path in alternate_paths:
            if os.path.exists(path):
                return path
        
        print("Chrome not found in common locations. Please install Chrome or set CHROME_PATH environment variable.")
        return None
    
    return chrome_path

class UberEatsDeals:
    def __init__(self):
        self.setup_database()
        self.deals = []
        openai.api_key = OPENAI_API_KEY
        self.db_lock = asyncio.Lock()  # Add lock for database operations
        self.driver = None

    def get_chrome_version(self):
        """Get the installed Chrome version."""
        chrome_path = get_chrome_path()
        if not chrome_path:
            return None
            
        try:
            version = subprocess.check_output([chrome_path, "--version"], stderr=subprocess.DEVNULL)
            return version.decode("utf-8").replace("Google Chrome ", "").strip()
        except:
            return None

    def setup_driver(self):
        """Set up the Chrome driver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        # Development-friendly Chrome data directory
        chrome_data_dir = os.getenv('CHROME_DATA_DIR', os.path.expanduser('~/.chrome-data'))
        os.makedirs(chrome_data_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={chrome_data_dir}")
        
        try:
            # Get Chrome binary path
            chrome_path = get_chrome_path()
            if not chrome_path:
                raise Exception("Chrome not found. Please install Chrome browser.")
            
            chrome_options.binary_location = chrome_path
            print(f"Using Chrome binary from: {chrome_path}")
            
            # Use webdriver_manager for automatic ChromeDriver management
            try:
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                print("Chrome driver setup successful using webdriver_manager")
                self.driver = driver
                return
            except Exception as e:
                print(f"Webdriver manager setup failed, trying system ChromeDriver: {str(e)}")
            
            # Fallback to system-installed ChromeDriver
            chromedriver_path = os.getenv('CHROME_DRIVER_PATH', CHROMEDRIVER_PATHS.get(SYSTEM))
            if chromedriver_path and os.path.exists(chromedriver_path):
                print(f"Using system ChromeDriver at: {chromedriver_path}")
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
                print("Chrome driver setup successful using system ChromeDriver")
                return
            
            raise Exception("No suitable ChromeDriver found")
            
        except Exception as e:
            print(f"\nError setting up Chrome driver: {str(e)}")
            print("\nDetailed error information:")
            print(f"OS: {SYSTEM}")
            print(f"Architecture: {platform.machine()}")
            print(f"Python version: {sys.version}")
            print("\nTroubleshooting steps:")
            
            if IS_MACOS:
                print("For macOS:")
                print("1. Install Chrome: Download from https://www.google.com/chrome/")
                print("2. Install ChromeDriver:")
                print("   brew install --cask chromedriver")
                print("   or")
                print("   brew install chromium-chromedriver")
            else:
                print("For Ubuntu/Debian:")
                print("1. Install Chrome:")
                print("   sudo apt install google-chrome-stable")
                print("2. Install ChromeDriver:")
                print("   sudo apt install chromium-chromedriver")
            
            print("\nAlternatively, you can set these environment variables:")
            print("CHROME_PATH: Path to Chrome binary")
            print("CHROME_DRIVER_PATH: Path to ChromeDriver binary")
            sys.exit(1)

    def wait_for_element(self, selector, timeout=10, by=By.CSS_SELECTOR):
        """Wait for an element to be present and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    async def extract_deals_with_llm(self, html_content: str) -> List[Dict]:
        """Use OpenAI to extract deals from HTML content."""
        try:
            # Parse HTML with BeautifulSoup to extract relevant content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all promo tags first
            promo_tags = soup.find_all('img', src=lambda x: x and 'promo-tag-3x.png' in x)
            if not promo_tags:
                print("No promotion tags found in the HTML")
                return []
            
            # For each promo tag, get the parent containers
            menu_items = []
            for tag in promo_tags:
                current = tag
                for _ in range(9):
                    if current.parent:
                        current = current.parent
                    else:
                        break
                
                if current:
                    item_html = str(current)
                    menu_items.append(item_html)
            
            if not menu_items:
                print("No menu items found with promotions")
                return []
            
            # Process menu items concurrently
            all_deals = []
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            async def process_menu_item(item, index):
                try:
                    try:
                        response = await asyncio.to_thread(
                            client.chat.completions.create,
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a specialized HTML parser focused on extracting deal information from Uber Eats pages."},
                                {"role": "user", "content": DEAL_EXTRACTION_PROMPT + item}
                            ],
                            temperature=0.1,
                            max_tokens=1000
                        )
                    except Exception as api_error:
                        raise Exception(f"OpenAI API error: {str(api_error)}") from api_error
                    
                    content = response.choices[0].message.content
                    
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0]
                    
                    try:
                        result = json.loads(content.strip())
                    except json.JSONDecodeError as json_error:
                        raise Exception(f"Failed to parse OpenAI response as JSON: {str(json_error)}") from json_error
                    
                    if result.get('deals'):
                        print(f"Found {len(result['deals'])} deals in menu item {index+1}")
                        return result['deals']
                    return []
                except Exception as e:
                    print(f"Error processing menu item {index+1}: {str(e)}")
                    raise

            # Process all menu items concurrently
            tasks = [process_menu_item(item, i) for i, item in enumerate(menu_items)]
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                raise Exception(f"Failed to process menu items: {str(e)}")
            
            # Check for exceptions in results
            for result in results:
                if isinstance(result, Exception):
                    raise result
                all_deals.extend(result)
            
            return all_deals
            
        except Exception as e:
            print(f"Error using OpenAI to extract deals: {str(e)}")
            traceback.print_exc()
            raise  # Re-raise the exception to be handled by the caller

    async def extract_deal_details(self, card_link):
        """Extract specific deal information from a restaurant page."""
        deals = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(card_link, headers=headers) as response:
                    if response.status == 200:
                        page_content = await response.text()
                        deals = await self.extract_deals_with_llm(page_content)
                    else:
                        print(f"Error: HTTP {response.status} when fetching {card_link}")
            
        except Exception as e:
            print(f"Error extracting deal details: {str(e)}")
        
        return deals

    def setup_database(self):
        """Set up the SQLite database with the deals table."""
        try:
            conn = sqlite3.connect("uber_deals.db")
            cursor = conn.cursor()
            
            # Check if table exists and has url_hash column
            cursor.execute("PRAGMA table_info(deals)")
            columns = [column[1] for column in cursor.fetchall()]
            # If table exists but doesn't have url_hash, drop it
            if columns and 'url_hash' not in columns:
                print("Updating database schema: Adding url_hash column...")
                cursor.execute('DROP TABLE IF EXISTS deals')
                conn.commit()
            
            # Create table with current schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_hash TEXT NOT NULL,
                    restaurant TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    description TEXT,
                    promotion_type TEXT,
                    delivery_fee TEXT,
                    rating_and_reviews TEXT,
                    delivery_time TEXT,
                    url TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(url_hash, item_name)
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error setting up database: {str(e)}")
            sys.exit(1)

    def get_url_hash(self, url: str) -> str:
        """Generate a hash for the URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def validate_deal_info(self, deal_info: Dict) -> Dict:
        """Validate and clean deal info according to schema."""
        validated_data = {}
        
        # Map input fields to database columns using schema mapping
        for db_column, input_field in self.schema_mapping.items():
            value = deal_info.get(input_field, '')
            
            # Handle price specifically
            if db_column == 'price':
                # If price is missing or invalid, default to 0.0
                try:
                    validated_data[db_column] = float(value) if value else 0.0
                except (ValueError, TypeError):
                    validated_data[db_column] = 0.0
            else:
                validated_data[db_column] = value
        
        return validated_data
    
    async def save_deal_to_db(self, deal_info: Dict):
        """Save a deal to the database with URL hash."""
        async with self.db_lock:
            try:
                conn = sqlite3.connect("uber_deals.db")
                cursor = conn.cursor()
                
                # Get URL hash
                url_hash = self.get_url_hash(deal_info.get('url', ''))
                
                # Prepare the deal info with URL hash
                insert_query = '''
                    INSERT OR REPLACE INTO deals (
                        url_hash, restaurant, item_name, price, description,
                        promotion_type, delivery_fee, rating_and_reviews,
                        delivery_time, url, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                '''
                insert_values = (
                    url_hash,
                    deal_info.get('restaurant', ''),
                    deal_info.get('name', ''),
                    float(deal_info.get('price', 0.0)),
                    deal_info.get('description', ''),
                    deal_info.get('promotion', ''),
                    deal_info.get('delivery_fee', ''),
                    deal_info.get('rating_and_reviews', ''),
                    deal_info.get('delivery_time', ''),
                    deal_info.get('url', '')
                )
                cursor.execute(insert_query, insert_values)
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error saving deal to database: {str(e)}")

    async def get_existing_deals(self, url: str) -> List[Dict]:
        """Check if we already have deals for this URL in the database."""
        url_hash = self.get_url_hash(url)
        try:
            conn = sqlite3.connect("uber_deals.db")
            cursor = conn.cursor()
            
            # Get all deals for this URL hash
            cursor.execute('''
                SELECT 
                    restaurant,
                    item_name,
                    price,
                    description,
                    promotion_type,
                    delivery_fee,
                    rating_and_reviews,
                    delivery_time,
                    url,
                    timestamp
                FROM deals 
                WHERE url_hash = ?
                ORDER BY timestamp DESC
            ''', (url_hash,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                # Convert rows to list of dictionaries
                deals = []
                for row in rows:
                    deal = {
                        'restaurant': row[0],
                        'name': row[1],
                        'price': row[2],
                        'description': row[3],
                        'promotion': row[4],
                        'delivery_fee': row[5],
                        'rating_and_reviews': row[6],
                        'delivery_time': row[7],
                        'url': row[8],
                        'timestamp': row[9]
                    }
                    deals.append(deal)
                return deals
            return []
            
        except Exception as e:
            print(f"Error checking existing deals: {str(e)}")
            return []

    def initialize_driver(self):
        """Initialize the Chrome driver when needed."""
        if self.driver is None:
            self.setup_driver()

    async def get_restaurant_deals(self, url):
        """Extract deals from the offer page."""
        try:
            # First check if we already have deals for this URL
            existing_deals = await self.get_existing_deals(url)
            if existing_deals:
                print(f"Found {len(existing_deals)} existing deals in database")
                self.deals = existing_deals
                return
            
            # If no existing deals, initialize driver and fetch new ones
            print("No existing deals found, fetching from website...")
            self.initialize_driver()
            
            print("Loading page...")
            self.driver.get(url)
            
            print("Waiting for content to load...")
            time.sleep(5)  # Initial wait for page load
            
            # Scroll to load all content
            print("Scrolling to load all content...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            child_store_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="store-card"]')
            store_cards = [card.find_element(By.XPATH, '..') for card in child_store_cards]
            print(f"Found {len(store_cards)} store cards")
            
            # Process store cards concurrently
            async def process_store_card(card):
                try:
                    # Find the store card link element (either the card itself or its child)
                    link_element = card if card.tag_name == 'a' else card.find_element(By.CSS_SELECTOR, '[data-testid="store-card"]')
                    
                    # Get restaurant name
                    name = None
                    try:
                        name = link_element.find_element(By.TAG_NAME, 'h3').text.strip()
                    except NoSuchElementException:
                        try:
                            name = link_element.get_attribute('aria-label')
                        except NoSuchElementException:
                            pass
                    
                    if not name:
                        return []
                    
                    # Get the restaurant link
                    try:
                        link = link_element.get_attribute('href')
                        if not link:
                            raise NoSuchElementException("Link is empty")
                    except NoSuchElementException:
                        print(f"Could not find link for {name}, skipping")
                        return []

                    if '?' in link:
                        link = link + '&mod=quickView'
                    else:
                        link = link + '?mod=quickView'
                    basic_info = {
                        'restaurant': name,
                        'delivery_fee': "Not specified", 
                        'rating_and_reviews': "",
                        'delivery_time': "Not specified"
                    }
                    
                    # Get promotion from the card
                    try:
                        promo_tag = link_element.find_element(
                            By.XPATH,
                            ".//div[contains(text(), 'Buy 1, Get 1') or contains(text(), 'Top Offer')]"
                        )
                        if promo_tag:
                            basic_info['promotion'] = promo_tag.text.strip()
                    except NoSuchElementException:
                        basic_info['promotion'] = "No promotion displayed"
                    
                    # Get delivery fee
                    try:
                        fee_elements = link_element.find_elements(By.XPATH, ".//*[contains(text(), '€') and contains(text(), 'Delivery Fee')]")
                        if fee_elements:
                            basic_info['delivery_fee'] = fee_elements[0].text.strip()
                    except NoSuchElementException:
                        pass
                    
                    # Get rating and review count
                    try:
                        # Find rating number (appears before the star)
                        rating_spans = card.find_elements(By.XPATH, ".//span[contains(@title, '.')]")
                        reviews_spans = card.find_elements(By.XPATH, ".//span[contains(@title, '+')]")
                        
                        if rating_spans and reviews_spans:
                            rating_number = rating_spans[0].get_attribute('title')
                            reviews_count = reviews_spans[0].get_attribute('title')
                            basic_info['rating_and_reviews'] = f"{rating_number} ({reviews_count})"
                    except NoSuchElementException:
                        pass
                    
                    # Get delivery time
                    try:
                        time_elements = card.find_elements(By.XPATH, ".//*[contains(text(), 'Min')]")
                        if time_elements:
                            basic_info['delivery_time'] = time_elements[-1].text.strip()
                    except NoSuchElementException:
                        pass
                    
                    print(f"Extracting deals from {name}...")
                    specific_deals = await self.extract_deal_details(link)
                    
                    # Add each deal as a separate entry
                    deals = []
                    for deal in specific_deals:
                        deal_info = basic_info.copy()
                        deal_info.update(deal)
                        deal_info['url'] = link
                        deals.append(deal_info)
                        await self.save_deal_to_db(deal_info)
                        print(f"Added deal: {deal.get('name', 'Unknown')} from {name}")
                    
                    if not specific_deals:
                        print(f"No specific deals found for {name}")
                    
                    return deals
                    
                except Exception as e:
                    print(f"Error processing card: {str(e)}")
                    return []
            
            # Process all store cards concurrently
            tasks = [process_store_card(card) for card in store_cards]
            results = await asyncio.gather(*tasks)
            
            # Combine all results
            for deals in results:
                self.deals.extend(deals)
            
            if not self.deals:
                print("No deals could be extracted.")
                
        except Exception as e:
            print(f"Error accessing the page: {str(e)}")
            
    def display_results(self):
        """Display the results in a formatted table."""
        if not self.deals:
            print("No deals found!")
            return
            
        df = pd.DataFrame(self.deals)
        print("\nUber Eats Items Found:")
        print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
        
    def cleanup(self):
        """Clean up resources."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

def view_stored_deals():
    """View all deals stored in the database."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        query = '''
            SELECT 
                restaurant,
                item_name,
                price,
                promotion_type,
                delivery_fee,
                rating_and_reviews,
                url,
                timestamp
            FROM deals
            ORDER BY timestamp DESC
        '''
        df = pd.read_sql_query(query, conn)
        if len(df) == 0:
            print("No deals found in the database!")
        else:
            print("\nStored Uber Eats Deals:")
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
        conn.close()
    except Exception as e:
        print(f"Error viewing deals: {str(e)}")
        traceback.print_exc()  # Add stack trace for debugging

def analyze_stored_deals():
    """Analyze deals stored in the database and show useful statistics."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        
        # Get basic statistics
        stats_query = '''
            SELECT 
                COUNT(DISTINCT restaurant) as total_restaurants,
                COUNT(*) as total_deals,
                COUNT(DISTINCT date(timestamp)) as days_collected,
                COUNT(DISTINCT promotion_type) as promotion_types
            FROM deals
        '''
        stats_df = pd.read_sql_query(stats_query, conn)
        
        # Get top restaurants by number of deals
        top_restaurants_query = '''
            SELECT 
                restaurant,
                COUNT(*) as deal_count,
                GROUP_CONCAT(DISTINCT promotion_type) as promotion_types
            FROM deals 
            GROUP BY restaurant 
            ORDER BY deal_count DESC 
            LIMIT 5
        '''
        top_restaurants_df = pd.read_sql_query(top_restaurants_query, conn)
        
        # Get promotion type distribution
        promo_dist_query = '''
            SELECT 
                promotion_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM deals), 2) as percentage
            FROM deals 
            WHERE promotion_type != ''
            GROUP BY promotion_type 
            ORDER BY count DESC
        '''
        promo_dist_df = pd.read_sql_query(promo_dist_query, conn)
        
        # Get average delivery fees by restaurant
        delivery_fees_query = '''
            SELECT 
                restaurant,
                delivery_fee,
                COUNT(*) as deal_count
            FROM deals 
            WHERE delivery_fee != 'Not specified'
            GROUP BY restaurant, delivery_fee
            ORDER BY deal_count DESC
            LIMIT 10
        '''
        delivery_fees_df = pd.read_sql_query(delivery_fees_query, conn)
        
        # Get recent deals (last 24 hours)
        recent_deals_query = '''
            SELECT 
                restaurant,
                item_name,
                price,
                promotion_type,
                timestamp
            FROM deals 
            WHERE datetime(timestamp) > datetime('now', '-1 day')
            ORDER BY timestamp DESC
        '''
        recent_deals_df = pd.read_sql_query(recent_deals_query, conn)
        
        # Print the analysis
        print("\n=== Uber Eats Deals Analysis ===\n")
        
        print("General Statistics:")
        print(f"Total Restaurants: {stats_df['total_restaurants'].iloc[0]}")
        print(f"Total Deals: {stats_df['total_deals'].iloc[0]}")
        print(f"Days of Data Collection: {stats_df['days_collected'].iloc[0]}")
        print(f"Different Promotion Types: {stats_df['promotion_types'].iloc[0]}")
        
        print("\nTop 5 Restaurants by Deal Count:")
        print(tabulate(top_restaurants_df, headers='keys', tablefmt='grid', showindex=False))
        
        print("\nPromotion Type Distribution:")
        print(tabulate(promo_dist_df, headers='keys', tablefmt='grid', showindex=False))
        
        print("\nDelivery Fees by Restaurant (Top 10):")
        print(tabulate(delivery_fees_df, headers='keys', tablefmt='grid', showindex=False))
        
        if not recent_deals_df.empty:
            print("\nRecent Deals (Last 24 Hours):")
            print(tabulate(recent_deals_df, headers='keys', tablefmt='grid', showindex=False))
        else:
            print("\nNo deals found in the last 24 hours")
        
        conn.close()
        
    except Exception as e:
        print(f"Error analyzing deals: {str(e)}")
        traceback.print_exc()

async def main_async():
    parser = argparse.ArgumentParser(description='Find the best deals on Uber Eats')
    parser.add_argument('--offer_url', help='URL of the Uber Eats offer page')
    parser.add_argument('--view', action='store_true', help='View stored deals from the database')
    parser.add_argument('--analyze', action='store_true', help='Analyze stored deals without fetching new data')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_stored_deals()
        return
    
    if args.view:
        view_stored_deals()
        return
    
    if not args.offer_url:
        parser.error("Either --offer_url, --view, or --analyze must be specified")
    
    if os.path.exists('debug_output'):
        shutil.rmtree('debug_output')
        print("Cleared debug output directory")
    
    deals_finder = UberEatsDeals()
    try:
        await deals_finder.get_restaurant_deals(args.offer_url)
        deals_finder.display_results()
    finally:
        deals_finder.cleanup()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 