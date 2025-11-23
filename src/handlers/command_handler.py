import logging
from aiogram.types import Message

logger = logging.getLogger(__name__)


class CommandHandler:
    """Обработчик команд бота"""

    @staticmethod
    async def start(message: Message):
        """Команда /start"""
        logger.info("Команда /start от пользователя %s", message.from_user.id)
        await message.answer(
            "Бот для обработки файлов с кодами.\n\n"
            "Отправьте файл Excel (.xlsx или .xls) — можно несколько подряд.\n"
            "Через 3 секунды после последнего файла пришлю результат."
        )
