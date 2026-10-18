"""CoursePilot: semester-by-semester degree planning for UNC Chapel Hill."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("PREREQPATH_DATA_DIR", REPO_ROOT / "data"))
