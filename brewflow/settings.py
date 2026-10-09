from dataclasses import dataclass
from json import loads
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
CONFIG_PATH = PACKAGE_ROOT / "config" / "config.json"
DEFAULT_DATABASE_URI = f"sqlite+aiosqlite:///{PACKAGE_ROOT / 'data' / 'database.db'}"
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@dataclass(frozen=True)
class QueueSettings:
    drinks: tuple[str, ...]
    milks: tuple[str, ...]
    textures: tuple[str, ...]
    search_depth: int
    max_batch_volume: float


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return loads(path.read_text(encoding="utf-8"))


def load_queue_settings(path: Path = CONFIG_PATH) -> QueueSettings:
    config = load_config(path)
    return QueueSettings(
        drinks=tuple(item["drink"] for item in config.get("drinks", [])),
        milks=tuple(config.get("milks", [])),
        textures=tuple(config.get("textures", [])),
        search_depth=max(0, int(config.get("SEARCH_DEPTH", 1))),
        max_batch_volume=float(config.get("MAX_BATCH_VOLUME", 5)),
    )
