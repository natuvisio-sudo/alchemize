from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import os

app = FastAPI()

# 1. CONNECT TO YOUR DATABASE
DB_PATH = os.path.join("database", "alchemize.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# 2. DEFINE THE DATA MODEL (What the HTML sends us)
class RitualLog(BaseModel):
    energy: int
    focus: int
    intention: str

# 3. API ENDPOINT: THE IGNITION (Save Data)
@app.post("/api/ignite")
async def ignite_ritual(log: RitualLog):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # A. Save to ritual_logs table
        current_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO ritual_logs (date, energy, focus, intention)
            VALUES (?, ?, ?, ?)
        """, (current_date, log.energy, log.focus, log.intention))
        
        # B. Update Inventory (Decrement by 1)
        # Assuming user_id = 1 for MVP
        cursor.execute("""
            UPDATE inventory 
            SET pills_remaining = pills_remaining - 1 
            WHERE user_id = 1
        """)
        
        conn.commit()
        
        # C. Get new stock count to send back to HTML
        cursor.execute("SELECT pills_remaining FROM inventory WHERE user_id = 1")
        row = cursor.fetchone()
        new_stock = row["pills_remaining"] if row else 0
        
        return {"status": "success", "new_stock": new_stock}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# 4. API ENDPOINT: THE TRUTH (Get Data for Chart)
@app.get("/api/truth")
async def get_truth():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 7 days of data
    cursor.execute("SELECT date, energy, focus FROM ritual_logs ORDER BY date DESC LIMIT 7")
    rows = cursor.fetchall()
    conn.close()
    
    # Format for JSON
    data = [dict(row) for row in rows]
    return {"history": list(reversed(data))} # Reverse to show oldest -> newest

# 5. SERVE THE HTML (The Face)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
