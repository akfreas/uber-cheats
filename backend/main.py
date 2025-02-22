import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the parent directory to sys.path to import uber_deals
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uber_deals import UberEatsDeals

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

class URLInput(BaseModel):
    url: str
    session_id: str

class Deal(BaseModel):
    restaurant: str
    item_name: str
    price: float
    description: Optional[str]
    promotion_type: str
    delivery_fee: str
    rating_and_reviews: str
    delivery_time: str
    url: str
    timestamp: datetime

async def send_progress_update(session_id: str, message: str, progress: float):
    """Send progress update through WebSocket if connection exists."""
    if session_id in active_connections:
        try:
            await active_connections[session_id].send_json({
                "message": message,
                "progress": progress
            })
        except:
            pass

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        if session_id in active_connections:
            del active_connections[session_id]

@app.post("/api/find-deals")
async def find_deals(input_data: URLInput):
    deals_finder = UberEatsDeals()
    try:
        # Initialize progress
        await send_progress_update(input_data.session_id, "Setting up Chrome driver...", 0.1)
        
        # Override the original save_deal_to_db to also send progress updates
        original_save_deal = deals_finder.save_deal_to_db
        total_deals_found = 0
        
        async def new_save_deal(deal_info):
            nonlocal total_deals_found
            await original_save_deal(deal_info)
            total_deals_found += 1
            await send_progress_update(
                input_data.session_id,
                f"Found deal: {deal_info.get('name', 'Unknown')} from {deal_info.get('restaurant', 'Unknown')}",
                min(0.1 + (total_deals_found * 0.8 / 20), 0.9)  # Cap progress at 90%
            )
        
        deals_finder.save_deal_to_db = new_save_deal
        
        # Get restaurant deals
        await send_progress_update(input_data.session_id, "Scanning restaurant page...", 0.2)
        await deals_finder.get_restaurant_deals(input_data.url)
        
        # Final progress update
        await send_progress_update(input_data.session_id, "Completed!", 1.0)
        
        # Generate and return the URL hash
        url_hash = deals_finder.get_url_hash(input_data.url)
        return {"status": "success", "message": f"Found {total_deals_found} deals", "hash": url_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        deals_finder.cleanup()

@app.get("/api/deals")
async def get_deals():
    import sqlite3

    import pandas as pd
    
    try:
        conn = sqlite3.connect("uber_deals.db")
        query = '''
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
            ORDER BY timestamp DESC
        '''
        df = pd.read_sql_query(query, conn)
        deals = df.to_dict('records')
        conn.close()
        return deals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/deals/{url_hash}")
async def get_deals_by_hash(url_hash: str):
    try:
        conn = sqlite3.connect("uber_deals.db")
        query = '''
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
        '''
        df = pd.read_sql_query(query, conn, params=(url_hash,))
        deals = df.to_dict('records')
        conn.close()
        
        if not deals:
            raise HTTPException(status_code=404, detail="No deals found for this hash")
            
        return deals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 