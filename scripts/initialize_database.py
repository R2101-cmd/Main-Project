import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_DATABASE
from src.database.repository import Repository

repo = Repository(DEFAULT_DATABASE)
repo.initialize()
repo.close()
print(f"Initialized {DEFAULT_DATABASE}")
