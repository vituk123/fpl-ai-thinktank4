import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dotenv import load_dotenv

# Load .env file - explicitly specify path
env_path = Path(__file__).parent / '.env'
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path)

print("Environment variables:")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL') or 'NOT SET'}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')[:30] if os.getenv('SUPABASE_KEY') else 'NOT SET'}...")
print(f"DB_CONNECTION_STRING: {os.getenv('DB_CONNECTION_STRING')[:60] if os.getenv('DB_CONNECTION_STRING') else 'NOT SET'}...")

all_set = all([os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'), os.getenv('DB_CONNECTION_STRING')])
print(f"All required vars set: {all_set}")

try:
    from database import DatabaseManager
    db = DatabaseManager()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database init error: {e}")
    import traceback
    traceback.print_exc()

