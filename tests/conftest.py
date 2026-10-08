"""Make scripts/ and the build skill's assets/ importable from the tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "build" / "assets"))
