import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any
from aiogram import Bot

logger = logging.getLogger(__name__)


class BatchManager:
    """Менеджер пакетной обработки файлов"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_state: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {
                "results": [],
                "timer": None,
                "chat_id": None,
                "last_activity": datetime.now(),
            }
        )

    def add_result(self, user_id: int, result: Dict[str, Any]):
        """Добавить результат обработки файла"""
        state = self.user_state[user_id]
        state["results"].append(result)
        state["last_activity"] = datetime.now()

    async def schedule_batch(self, user_id: int, chat_id: int):
        """Запланировать отправку итогового сообщения через 3 секунды"""
        state = self.user_state[user_id]
        state["chat_id"] = chat_id

        if state["timer"]:
            state["timer"].cancel()

        async def send_summary():
            await asyncio.sleep(3.1)
            await self._send_batch_summary(user_id)

        task = asyncio.create_task(send_summary())
        state["timer"] = task

    async def _send_batch_summary(self, user_id: int):
        """Отправка итогового сообщения о пакете файлов"""
        state = self.user_state[user_id]
        results = state["results"]

        if not results:
            return

        total = len(results)
        success_count = sum(1 for r in results if r["success"])

        if total > 1:
            message = self._format_summary_message(total, success_count)
            await self.bot.send_message(state["chat_id"], message)
            logger.info(
                "Отправлено итоговое сообщение пользователю %s: %s файлов",
                user_id,
                total,
            )

        self._cleanup_files(results)

        del self.user_state[user_id]

    def _format_summary_message(self, total: int, success_count: int) -> str:
        """Форматирование итогового сообщения"""
        lines = [
            f"Обработка завершена: {total} файл(ов)",
            f"✅ Успешно: {success_count}",
        ]
        if total - success_count > 0:
            lines.append(f"❌ С ошибками: {total - success_count}")
        return "\n".join(lines)

    def _cleanup_files(self, results: List[Dict[str, Any]]):
        """Очистка временных файлов"""
        for r in results:
            for key in ("temp_input", "result_path"):
                if path := r.get(key):
                    try:
                        Path(path).unlink(missing_ok=True)
                        logger.debug("Удален временный файл: %s", path)
                    except Exception as e:
                        logger.error("Ошибка удаления файла %s: %s", path, e)

    async def cleanup_old_states(self):
        """Периодическая очистка устаревших состояний пользователей"""
        while True:
            await asyncio.sleep(3600)
            now = datetime.now()
            to_delete = []

            for user_id, state in self.user_state.items():
                if now - state["last_activity"] > timedelta(hours=1):
                    to_delete.append(user_id)

            for user_id in to_delete:
                logger.info("Очистка устаревших данных пользователя %s", user_id)
                del self.user_state[user_id]
