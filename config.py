import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# PostgreSQL connection
def get_db_connection():
    import psycopg2
    project_id = SUPABASE_URL.split("//")[1].split(".")[0]
    conn = psycopg2.connect(
        host=f"{project_id}.supabase.co",
        port=5432,
        database="postgres",
        user="postgres",
        password=SUPABASE_KEY
    )
    return conn

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-prod")
