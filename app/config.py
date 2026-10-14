from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str = "data/products.db"
    check_interval_minutes: int = 60
    max_links_per_user: int = 100

def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "replace_with_your_new_token":
        raise RuntimeError("Set BOT_TOKEN in your .env file. Never commit your real token.")
    return Settings(
        bot_token=token,
        database_path=os.getenv("DATABASE_PATH", "data/products.db"),
        check_interval_minutes=max(15, int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))),
        max_links_per_user=max(1, int(os.getenv("MAX_LINKS_PER_USER", "100"))),
    )
