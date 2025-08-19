import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class CacheService:
    def __init__(self, db_path: str = "data/cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp DATETIME,
                expiry DATETIME
            )
        """)
        
        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached value if it exists and hasn't expired"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT value, expiry FROM api_cache WHERE key = ?",
            (key,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            value, expiry = result
            expiry_date = datetime.fromisoformat(expiry)
            
            if expiry_date > datetime.now():
                return json.loads(value)
        
        return None

    def set(self, key: str, value: Dict[str, Any], ttl_minutes: int = 60):
        """Store a value in the cache with expiration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        expiry = now + timedelta(minutes=ttl_minutes)
        
        cursor.execute("""
            INSERT OR REPLACE INTO api_cache (key, value, timestamp, expiry)
            VALUES (?, ?, ?, ?)
        """, (
            key,
            json.dumps(value),
            now.isoformat(),
            expiry.isoformat()
        ))
        
        conn.commit()
        conn.close()

    def clear_expired(self):
        """Remove expired cache entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM api_cache WHERE expiry < ?",
            (datetime.now().isoformat(),)
        )
        
        conn.commit()
        conn.close()
