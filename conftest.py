import sys
from pathlib import Path

# Add src to sys.path so tests work without pip install
sys.path.insert(0, str(Path(__file__).parent / "src"))
