import logging
from pathlib import Path
from aiogram import Bot
from aiogram.types import Message, FSInputFile
from services.file_processor import FileProcessor
from services.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class DocumentHandler:
    """Обработчик документов"""

    def __init__(self, bot: Bot, temp_dir: Path, batch_manager: BatchManager):
        self.bot = bot
        self.temp_dir = temp_dir
        self.batch_manager = batch_manager

    async def handle_document(self, message: Message):
        """Обработка входящего документа"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        doc = message.document

        # Валидация формата файла
        if not self._is_valid_file(doc):
            await message.reply("Поддерживаются только .xlsx и .xls файлы")
            return

        logger.info("Получен файл %s от пользователя %s", doc.file_name, user_id)

        # Генерация уникального имени для временного файла
        temp_input = self.temp_dir / f"{user_id}_{doc.file_id}_{doc.file_name}"

        try:
            await self._process_file(message, doc, temp_input, user_id)
        except Exception as e:
            await self._handle_error(message, doc, temp_input, user_id, str(e))

        # Планируем отправку итогового сообщения
        await self.batch_manager.schedule_batch(user_id, chat_id)

    def _is_valid_file(self, doc) -> bool:
        """Проверка формата файла"""
        return doc.file_name and doc.file_name.lower().endswith((".xlsx", ".xls"))

    async def _process_file(
        self, message: Message, doc, temp_input: Path, user_id: int
    ):
        """Обработка файла"""
        # Скачивание файла
        file = await self.bot.get_file(doc.file_id)
        await self.bot.download_file(file.file_path, temp_input)

        # Обработка через FileProcessor
        temp_output, article = FileProcessor.process_file(
            input_file_path=temp_input,
            output_dir=self.temp_dir,
            filename=doc.file_name,
        )

        # Отправка результата
        await message.reply_document(
            FSInputFile(temp_output), caption=f"✅ {doc.file_name}\nАртикул: {article}"
        )

        logger.info("Файл %s успешно обработан (артикул: %s)", doc.file_name, article)

        # Сохранение результата в батч-менеджер
        self.batch_manager.add_result(
            user_id,
            {
                "success": True,
                "filename": doc.file_name,
                "article": article,
                "result_path": temp_output,
                "temp_input": temp_input,
            },
        )

    async def _handle_error(
        self, message: Message, doc, temp_input: Path, user_id: int, error: str
    ):
        """Обработка ошибки"""
        logger.error("Ошибка обработки файла %s: %s", doc.file_name, error)

        await message.reply(f"❌ {doc.file_name}\n{error}")

        self.batch_manager.add_result(
            user_id,
            {
                "success": False,
                "filename": doc.file_name or "unknown",
                "error": error,
                "temp_input": temp_input,
            },
        )
