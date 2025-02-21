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

def chat_with_deals():
    """Interactive chat interface for querying deals."""
    print("Loading deals database...")
    deals = load_deals_data()
    
    if not deals:
        print("No deals found in the database. Please run the scraper first.")
        return
    
    print(f"Loaded {len(deals)} deals from the database.")
    print("\nChat with your deals database! Ask questions like:")
    print("- What are the best pizza deals?")
    print("- Show me deals with free delivery")
    print("- What are the buy one get one free offers?")
    print("- Which restaurants have the most deals?")
    print("\nType 'quit' to exit.")
    
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
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Add user's question to messages
            messages.append({"role": "user", "content": user_input})
            
            # Get response from GPT-4
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Get and print the response
            assistant_response = response.choices[0].message.content
            print("\nAssistant:", assistant_response)
            
            # Add assistant's response to messages for context
            messages.append({"role": "assistant", "content": assistant_response})
            
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