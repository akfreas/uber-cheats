#!/usr/bin/env python3

import json
import os
import sqlite3
from datetime import datetime

import openai
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()  # Load environment variables from .env file

# OpenAI API key will be set here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ANSI escape codes for formatting
COLORS = {
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
    'END': '\033[0m'
}

SYSTEM_PROMPT = """You are a helpful assistant that helps users find deals from Uber Eats.
You have access to a database of deals that will be provided in the next message.
When suggesting deals:
1. Always include the restaurant name, item name, price, and promotion type
2. Always include the URL so the user can check it out
3. Try to sort or prioritize deals based on what seems most relevant to the user's request
4. If you're showing multiple deals, use a numbered list
5. If the user asks about prices, always show the actual price
6. If you're not sure about something, say so
7. Keep your responses conversational but concise

The deals data will be provided in JSON format in the user's first message.
"""

def init_chat_history_table():
    """Initialize the chat history table if it doesn't exist."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        cursor = conn.cursor()
        
        # Create chat_history table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing chat history table: {str(e)}")

def clear_chat_history():
    """Clear all chat history from the database."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_history')
        conn.commit()
        conn.close()
        print("Chat history cleared for new session.")
    except Exception as e:
        print(f"Error clearing chat history: {str(e)}")

def load_chat_history():
    """Load recent chat history from the database."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        cursor = conn.cursor()
        
        # Get the last 20 messages (adjust this number as needed)
        cursor.execute('''
            SELECT role, content
            FROM chat_history
            ORDER BY timestamp DESC
            LIMIT 20
        ''')
        
        # Convert to list of message dictionaries
        messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
        messages.reverse()  # Put in chronological order
        
        conn.close()
        return messages
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return []

def save_message(role, content):
    """Save a message to the chat history."""
    try:
        conn = sqlite3.connect("uber_deals.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_history (role, content)
            VALUES (?, ?)
        ''', (role, content))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving message: {str(e)}")

def load_deals_data():
    """Load all deals from the database into a JSON structure."""
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
                description,
                card_promotion,
                delivery_time,
                url,
                timestamp
            FROM deals
            ORDER BY timestamp DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert DataFrame to list of dictionaries
        deals = df.to_dict('records')
        
        # Convert datetime objects to strings
        for deal in deals:
            deal['timestamp'] = str(deal['timestamp'])
        
        return deals
    except Exception as e:
        print(f"Error loading deals: {str(e)}")
        return []

def format_terminal_output(text):
    """Format markdown text for terminal display."""
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Remove markdown list markers and replace with proper formatting
        if line.strip().startswith('1.') or line.strip().startswith('-'):
            line = line.replace('1.', '•').replace('-', '→')
        
        # Remove markdown bold markers
        line = line.replace('**', COLORS['BOLD'])
        
        # Format URLs to be clickable
        if '[' in line and '](' in line and ')' in line:
            url_start = line.find('](') + 2
            url_end = line.find(')', url_start)
            if url_start > 1 and url_end > url_start:
                url = line[url_start:url_end]
                text_start = line.find('[') + 1
                text_end = line.find(']')
                text = line[text_start:text_end]
                # Make URL clickable using OSC 8 escape sequence
                clickable_url = f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
                line = line[:line.find('[')] + COLORS['BLUE'] + COLORS['UNDERLINE'] + clickable_url + COLORS['END']
        
        # Add proper indentation
        if line.strip().startswith('→'):
            line = '    ' + line.strip()
        elif line.strip().startswith('•'):
            line = line.strip()
        
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def chat_with_deals():
    """Interactive chat interface for querying deals."""
    print("Loading deals database...")
    deals = load_deals_data()
    
    if not deals:
        print("No deals found in the database. Please run the scraper first.")
        return
    
    # Initialize and clear chat history table
    init_chat_history_table()
    clear_chat_history()
    
    print(f"\n{COLORS['BOLD']}Loaded {len(deals)} deals from the database.{COLORS['END']}")
    print(f"\n{COLORS['BOLD']}Chat with your deals database! Ask questions like:{COLORS['END']}")
    print(f"{COLORS['GREEN']}• What are the best pizza deals?")
    print("• Show me deals with free delivery")
    print("• What are the buy one get one free offers?")
    print(f"• Which restaurants have the most deals?{COLORS['END']}")
    print(f"\n{COLORS['YELLOW']}Type 'quit' to exit.{COLORS['END']}")
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Create initial messages with system prompt and deals data
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Here is the deals data to work with: {json.dumps(deals)}"}
    ]
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{COLORS['BOLD']}You:{COLORS['END']} ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"\n{COLORS['GREEN']}Goodbye!{COLORS['END']}")
                break
            
            if not user_input:
                continue
            
            # Add user's question to messages and save to history
            messages.append({"role": "user", "content": user_input})
            save_message("user", user_input)
            
            # Get response from GPT-4
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Get and format the response
            assistant_response = response.choices[0].message.content
            formatted_response = format_terminal_output(assistant_response)
            print(f"\n{COLORS['BOLD']}Assistant:{COLORS['END']}\n{formatted_response}")
            
            # Add assistant's response to messages and save to history
            messages.append({"role": "assistant", "content": assistant_response})
            save_message("assistant", assistant_response)
            
            # Keep context window manageable by removing older messages if needed
            if len(messages) > 10:  # Keep system prompt, deals data, and last 4 exchanges
                messages = messages[:2] + messages[-8:]
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            continue

if __name__ == "__main__":
    chat_with_deals() 