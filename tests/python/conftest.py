import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("tools", "tools/pipeline", "tools/blender", "tools/unreal", "tools/setup", ".claude/hooks"):
    p = str(ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = ROOT / "tests" / "fixtures"
