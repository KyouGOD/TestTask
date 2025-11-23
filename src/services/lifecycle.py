import sys
import logging
import asyncio
from pathlib import Path
from aiogram import Bot
from services.reference_book import ReferenceBook
from services.batch_manager import BatchManager

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Менеджер жизненного цикла бота"""

    def __init__(
        self,
        bot: Bot,
        reference_path: Path,
        temp_dir: Path,
        batch_manager: BatchManager,
    ):
        self.bot = bot
        self.reference_path = reference_path
        self.temp_dir = temp_dir
        self.batch_manager = batch_manager

    async def on_startup(self):
        """Инициализация при запуске бота"""
        logger.info("Запуск бота...")

        # Проверка наличия справочника
        if not self.reference_path.exists():
            logger.error("ОШИБКА: Справочник не найден: %s", self.reference_path)
            sys.exit(1)

        # Загрузка справочника
        try:
            await ReferenceBook.load(self.reference_path)
        except PermissionError:
            logger.error(
                "ОШИБКА: Нет доступа к файлу справочника: %s", self.reference_path
            )
            sys.exit(1)
        except Exception as e:
            logger.error("ОШИБКА при загрузке справочника: %s", e)
            sys.exit(1)

        # Проверка, что справочник не пуст
        if ReferenceBook.is_empty():
            logger.error("ОШИБКА: Справочник пуст (нет данных)")
            sys.exit(1)

        logger.info("Справочник загружен: %s записей", ReferenceBook.get_cache_size())

        # Запуск фоновых задач
        asyncio.create_task(self._reference_refresher())
        asyncio.create_task(self.batch_manager.cleanup_old_states())

    async def _reference_refresher(self):
        """Фоновое обновление справочника каждые 8 часов"""
        while True:
            try:
                await asyncio.sleep(ReferenceBook.get_cache_lifetime_seconds())
                await ReferenceBook.load(self.reference_path)

                if ReferenceBook.is_empty():
                    logger.warning("ПРЕДУПРЕЖДЕНИЕ: Справочник обновлен, но пуст")
                else:
                    logger.info(
                        "Справочник обновлен: %s записей",
                        ReferenceBook.get_cache_size(),
                    )
            except PermissionError:
                logger.error("Ошибка доступа к справочнику: %s", self.reference_path)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error("Ошибка обновления справочника: %s", e)
                await asyncio.sleep(60)

    async def on_shutdown(self):
        """Завершение работы бота"""
        logger.info("Завершение работы бота...")

        # Очистка временных файлов
        for file in self.temp_dir.glob("*"):
            try:
                file.unlink()
                logger.debug("Удален временный файл: %s", file)
            except Exception as e:
                logger.error("Ошибка удаления %s: %s", file, e)

        # Закрытие сессии бота
        await self.bot.session.close()

        logger.info("Очистка завершена")
