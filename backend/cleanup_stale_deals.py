#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta


def cleanup_stale_deals():
    try:
        conn = sqlite3.connect("uber_deals.db")
        cursor = conn.cursor()
        
        # Delete deals older than 30 minutes
        thirty_mins_ago = (datetime.now() - timedelta(minutes=30)).isoformat()
        
        # Get count of deals to be deleted
        count_query = "SELECT COUNT(*) FROM deals WHERE timestamp < ?"
        cursor.execute(count_query, (thirty_mins_ago,))
        count = cursor.fetchone()[0]
        
        # Delete stale deals
        delete_query = "DELETE FROM deals WHERE timestamp < ?"
        cursor.execute(delete_query, (thirty_mins_ago,))
        conn.commit()
        
        print(f"{datetime.now().isoformat()}: Deleted {count} stale deals")
        
    except Exception as e:
        print(f"{datetime.now().isoformat()}: Error cleaning up stale deals: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    cleanup_stale_deals() 