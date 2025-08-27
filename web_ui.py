"""
"""
import json
import asyncio
import os
from datetime import datetime
from typing import Dict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI(title="Email Dashboard")
templates = Jinja2Templates(directory="templates")

# Backup file path
BACKUP_FILE = "stats_backup.json"

def load_stats_from_backup() -> Dict:
    """Load stats from backup file"""
    try:
        if os.path.exists(BACKUP_FILE):
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 Loaded backup data: {data.get('total', 0)} emails")
                return data
    except Exception as e:
        print(f"⚠️ Error loading backup: {e}")
    
    return {
        "total": 0,
        "by_topic": {},
        "by_date": {},
        "total_amount": 0,
        "emails_with_amount": 0,
        "last_updated": datetime.now().isoformat()
    }

def save_stats_to_backup(stats: Dict):
    """Save stats to backup file"""
    try:
        # Create backup directory if not exists
        os.makedirs("backups", exist_ok=True)
        
        # Save main backup
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str, ensure_ascii=False)
        
        # Also create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamped_file = f"backups/stats_{timestamp}.json"
        with open(timestamped_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str, ensure_ascii=False)
            
    except Exception as e:
        print(f"⚠️ Error saving backup: {e}")

# Load stats from backup on startup
current_stats = load_stats_from_backup()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard_simple.html", {"request": request})

@app.get("/api/stats")
async def get_stats():
    return current_stats

@app.post("/api/update_stats")
async def update_stats(stats: Dict):
    """Update stats và backup ngay lập tức"""
    global current_stats
    
    # Update timestamp
    stats['last_updated'] = datetime.now().isoformat()
    
    # Update memory
    current_stats = stats
    
    # Backup to file immediately
    save_stats_to_backup(stats)
    
    return {"status": "success", "backed_up": True}

@app.get("/api/stream")
async def stream_stats():
    async def event_generator():
        while True:
            data = json.dumps(current_stats, default=str)
            yield f"data: {data}\n\n"
            await asyncio.sleep(1)  # Update every 2 seconds
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@app.get("/health")
async def health():
    """Health check với thông tin backup"""
    backup_exists = os.path.exists(BACKUP_FILE)
    backup_time = None
    
    if backup_exists:
        try:
            backup_time = datetime.fromtimestamp(os.path.getmtime(BACKUP_FILE)).isoformat()
        except:
            pass
    
    return {
        "status": "ok", 
        "time": datetime.now().isoformat(),
        "backup_exists": backup_exists,
        "backup_last_modified": backup_time,
        "total_emails": current_stats.get("total", 0)
    }

@app.get("/api/backup/restore")
async def restore_from_backup():
    global current_stats
    
    try:
        restored_stats = load_stats_from_backup()
        current_stats = restored_stats
        return {
            "status": "success", 
            "message": "Restored from backup",
            "total_emails": restored_stats.get("total", 0)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/backup/list")
async def list_backups():
    try:
        backup_files = []
        
        # Main backup
        if os.path.exists(BACKUP_FILE):
            stat = os.stat(BACKUP_FILE)
            backup_files.append({
                "name": BACKUP_FILE,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Timestamped backups
        if os.path.exists("backups"):
            for file in os.listdir("backups"):
                if file.startswith("stats_") and file.endswith(".json"):
                    filepath = os.path.join("backups", file)
                    stat = os.stat(filepath)
                    backup_files.append({
                        "name": file,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return {"status": "success", "backups": backup_files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Email Dashboard with backup support...")
    print(f"📂 Backup file: {BACKUP_FILE}")
    print(f"📊 Loaded stats: {current_stats.get('total', 0)} emails")
    uvicorn.run("web_ui:app", host="0.0.0.0", port=8000, reload=True)
