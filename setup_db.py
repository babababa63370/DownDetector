"""Script pour créer la table Supabase"""
from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL à exécuter dans Supabase Dashboard > SQL Editor
sql = """
CREATE TABLE IF NOT EXISTS services (
    id BIGSERIAL PRIMARY KEY,
    owner_id TEXT NOT NULL,
    guild_id BIGINT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'online',
    last_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner_id, name)
);

CREATE INDEX idx_owner_id ON services(owner_id);
CREATE INDEX idx_guild_id ON services(guild_id);
"""

print("📋 SQL à exécuter dans Supabase:")
print(sql)
print("\n✅ Copie-colle ce SQL dans le SQL Editor de Supabase Dashboard")
