from dataclasses import dataclass
from json import loads
from os import getenv
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


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


@dataclass(frozen=True)
class CatalogItem:
    identifier: str
    name: str
    price_minor: int
    milk_volume: float
    shots: int
    texture: str | None


@dataclass(frozen=True)
class CatalogSettings:
    currency: str
    items: tuple[CatalogItem, ...]
    milks: tuple[str, ...]
    textures: tuple[str, ...]
    options: tuple[str, ...]
    milk_surcharges_minor: dict[str, int]


@dataclass(frozen=True)
class PaymentSettings:
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None
    checkout_return_base_url: str
    stripe_timeout_seconds: float = 10.0
    allow_demo_mode: bool = False


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


def load_catalog_settings(path: Path = CONFIG_PATH) -> CatalogSettings:
    config = load_config(path)
    currency = str(config["currency"]).lower()
    if currency != "gbp":
        raise ValueError("Stage 2 catalog currency must be GBP")
    items = tuple(
        CatalogItem(
            identifier=item["id"],
            name=item["drink"],
            price_minor=int(item["price_minor"]),
            milk_volume=float(item["milk_volume"]),
            shots=int(item["shots"]),
            texture=item["texture"],
        )
        for item in config.get("drinks", [])
    )
    if len({item.identifier for item in items}) != len(items):
        raise ValueError("Catalog item identifiers must be unique")
    if len({item.name for item in items}) != len(items):
        raise ValueError("Catalog item names must be unique")
    if any(item.price_minor < 0 for item in items):
        raise ValueError("Catalog prices cannot be negative")
    surcharges = {
        str(milk): int(amount)
        for milk, amount in config.get("milk_surcharges_minor", {}).items()
    }
    expected_milks = set(config.get("milks", [])) | {"No Milk"}
    if set(surcharges) != expected_milks or any(
        amount < 0 for amount in surcharges.values()
    ):
        raise ValueError("Every configured milk requires a nonnegative surcharge")
    return CatalogSettings(
        currency=currency,
        items=items,
        milks=tuple(config.get("milks", [])),
        textures=tuple(config.get("textures", [])),
        options=tuple(config.get("options", [])),
        milk_surcharges_minor=surcharges,
    )


def load_payment_settings() -> PaymentSettings:
    return_base_url = getenv(
        "BREWFLOW_CHECKOUT_RETURN_BASE_URL", "http://127.0.0.1:8000"
    ).rstrip("/")
    parsed = urlparse(return_base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Checkout return base URL must be an absolute HTTP(S) URL")
    return PaymentSettings(
        stripe_secret_key=getenv("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=getenv("STRIPE_WEBHOOK_SECRET"),
        checkout_return_base_url=return_base_url,
        allow_demo_mode=getenv("BREWFLOW_ALLOW_DEMO_MODE", "").strip().lower()
        in {"1", "true", "yes", "on"},
    )
