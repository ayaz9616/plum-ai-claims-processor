import sys
import os
from pathlib import Path

# Clear DATABASE_URL so tests run without requiring psycopg
os.environ["DATABASE_URL"] = ""

# Ensure repo root is on sys.path for test imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
