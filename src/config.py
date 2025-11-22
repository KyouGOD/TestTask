import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TG_BOT_API_TOKEN")
REFERENCE_BOOK_FILE_PATH = os.getenv("REFERENCE_BOOK_FILE_PATH")
