import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("TG_BOT_API_TOKEN")
REFERENCE_BOOK_FILE_PATH = os.getenv("REFERENCE_BOOK_FILE_PATH")

if not TOKEN:
    logger.error("ОШИБКА: Не задана переменная окружения TG_BOT_API_TOKEN")
    sys.exit(1)

if not REFERENCE_BOOK_FILE_PATH:
    logger.error("ОШИБКА: Не задана переменная окружения REFERENCE_BOOK_FILE_PATH")
    sys.exit(1)
