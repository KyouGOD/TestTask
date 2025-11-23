import logging
import asyncio
import tempfile
from pathlib import Path
from aiogram import F, Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from config import TOKEN, REFERENCE_BOOK_FILE_PATH
from services.batch_manager import BatchManager
from services.lifecycle import LifecycleManager
from handlers.command_handler import CommandHandler
from handlers.document_handler import DocumentHandler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

REFERENCE_PATH = Path(REFERENCE_BOOK_FILE_PATH)
TEMP_DIR = Path(tempfile.gettempdir()) / "tg_bot_files"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

batch_manager = BatchManager(bot)
lifecycle_manager = LifecycleManager(bot, REFERENCE_PATH, TEMP_DIR, batch_manager)
command_handler = CommandHandler()
document_handler = DocumentHandler(bot, TEMP_DIR, batch_manager)


@router.message(Command("start"))
async def start(message: Message):
    """Команда /start"""
    await command_handler.start(message)


@router.message(F.document)
async def handle_document(message: Message):
    """Обработка документов"""
    await document_handler.handle_document(message)


async def main():
    """Главная функция запуска бота"""
    dp.startup.register(lifecycle_manager.on_startup)
    dp.shutdown.register(lifecycle_manager.on_shutdown)
    dp.include_router(router)

    logger.info("Бот запущен и готов к работе")

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
    except asyncio.CancelledError:
        logger.info("Polling отменен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
