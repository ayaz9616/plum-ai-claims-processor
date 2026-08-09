import sys
from pathlib import Path

# Ensure repo root is on sys.path for test imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
