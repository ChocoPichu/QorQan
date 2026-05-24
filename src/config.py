# config.py
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
FLASK_SECRET: str = os.environ.get("FLASK_SECRET", "")
