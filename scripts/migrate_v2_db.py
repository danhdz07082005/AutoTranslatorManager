import sys
import os
import sqlite3
import time
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, "data", "translation_cache.db")

def migrate():
    print(f"Migrating DB at: {db_path}")
    if not os.path.exists(db_path):
        print("Database not found. Exiting.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if cache table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache'")
    if not cursor.fetchone():
        print("Table 'cache' not found. Exiting.")
        conn.close()
        return

    # Check if game_lines table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_lines'")
    if cursor.fetchone():
        print("Table 'game_lines' already exists. Might be migrated already.")

    print("Creating game_lines table...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS game_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            original TEXT NOT NULL,
            translated TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'default',
            source_file TEXT,
            source_path TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at REAL NOT NULL,
            UNIQUE(game_id, original, category)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_game_lines_game_id ON game_lines(game_id)')
    
    # We will try to map cache entries to games based on profiles
    profiles_dir = os.path.join(base_dir, "data", "profiles")
    games = {}
    if os.path.exists(profiles_dir):
        for fname in os.listdir(profiles_dir):
            if fname.endswith(".json"):
                with open(os.path.join(profiles_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        game_id = data.get("id")
                        sl = data.get("source_language", "Japanese")
                        tl = data.get("target_language", "Vietnamese")
                        if game_id:
                            games[game_id] = {"sl": sl, "tl": tl}
                    except Exception as e:
                        print(f"Error parsing profile {fname}: {e}")
                        
    print(f"Found {len(games)} games in profiles.")
    
    cursor.execute("SELECT source_lang, target_lang, category, original, translated FROM cache")
    cache_rows = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    now = time.time()
    
    for row in cache_rows:
        source_lang, target_lang, category, original, translated = row
        
        # Find games matching these languages
        matched_games = []
        for gid, ginfo in games.items():
            if ginfo["sl"] == source_lang and ginfo["tl"] == target_lang:
                matched_games.append(gid)
                
        if not matched_games:
            matched_games = ["legacy_migrated"]
            
        for gid in matched_games:
            try:
                cursor_insert = conn.execute('''
                    INSERT OR IGNORE INTO game_lines 
                    (game_id, original, translated, category, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (gid, original, translated, category, now))
                if cursor_insert.rowcount > 0:
                    migrated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error migrating row: {e}")
                
    conn.commit()
    conn.close()
    
    print(f"Migration completed! Migrated rows: {migrated_count}, Skipped (duplicates): {skipped_count}")

if __name__ == "__main__":
    migrate()
