from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = PIPELINE_DIR.parent
CACHE_DIR = PIPELINE_DIR / "cache"
CONFIG_DIR = PIPELINE_DIR / "config"
DATA_DIR = ROOT_DIR / "web" / "public" / "data"

for _d in (CACHE_DIR, DATA_DIR / "areas"):
    _d.mkdir(parents=True, exist_ok=True)
