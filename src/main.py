import sys
import logging
import asyncio
import tempfile
from pathlib import Path
from collections import defaultdict
from aiogram import F
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from config import TOKEN, REFERENCE_BOOK_FILE_PATH
from services.reference_book import ReferenceBook
from services.file_processor import FileProcessor

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

REFERENCE_PATH = Path(REFERENCE_BOOK_FILE_PATH)
TEMP_DIR = Path(tempfile.gettempdir()) / "tg_bot_files"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

user_state = defaultdict(lambda: {"results": [], "timer": None, "chat_id": None})


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот для обработки файлов с кодами.\n\n"
        "Отправьте файл Excel (.xlsx или .xls) — можно несколько подряд.\n"
        "Через 3 секунды после последнего файла пришлю результат."
    )


@router.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if not doc.file_name or not doc.file_name.lower().endswith((".xlsx", ".xls")):
        await message.reply("Поддерживаются только .xlsx и .xls файлы")
        return

    state = user_state[user_id]
    state["chat_id"] = chat_id

    temp_input = TEMP_DIR / f"{user_id}_{doc.file_id}_{doc.file_name}"

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, temp_input)

        temp_output, article = FileProcessor.process_file(
            input_file_path=temp_input,
            output_dir=TEMP_DIR,
            filename=doc.file_name,
        )

        # Сразу отправляем результат
        await message.reply_document(
            FSInputFile(temp_output), caption=f"✅ {doc.file_name}\nАртикул: {article}"
        )

        state["results"].append(
            {
                "success": True,
                "filename": doc.file_name,
                "article": article,
                "result_path": temp_output,
                "temp_input": temp_input,
            }
        )

    except Exception as e:
        await message.reply(f"❌ {doc.file_name}\n{str(e)}")

        state["results"].append(
            {
                "success": False,
                "filename": doc.file_name or "unknown",
                "error": str(e),
                "temp_input": temp_input,
            }
        )

    await schedule_batch(user_id)


async def schedule_batch(user_id: int):
    state = user_state[user_id]

    if state["timer"]:
        state["timer"].cancel()

    async def send_summary():
        await asyncio.sleep(3.2)

        results = state["results"]
        if not results:
            return

        total = len(results)
        success_count = sum(1 for r in results if r["success"])

        if total > 1:
            lines = [
                f"Обработка завершена: {total} файл(ов)",
                f"✅ Успешно: {success_count}",
            ]
            if total - success_count > 0:
                lines.append(f"❌ С ошибками: {total - success_count}")

            await bot.send_message(state["chat_id"], "\n".join(lines))

        for r in results:
            for key in ("temp_input", "result_path"):
                if path := r.get(key):
                    Path(path).unlink(missing_ok=True)

        del user_state[user_id]

    task = asyncio.create_task(send_summary())
    state["timer"] = task


async def on_startup():
    if not REFERENCE_PATH.exists():
        logger.error("ОШИБКА: Справочник не найден: %s", REFERENCE_PATH)
        sys.exit(1)

    try:
        await ReferenceBook.load(REFERENCE_PATH)
    except PermissionError:
        logger.error("ОШИБКА: Нет доступа к файлу справочника: %s", REFERENCE_PATH)
        sys.exit(1)
    except Exception as e:
        logger.error("ОШИБКА при загрузке справочника: %s", e)
        sys.exit(1)

    if ReferenceBook.is_empty():
        logger.error("ОШИБКА: Справочник пуст (нет данных)")
        sys.exit(1)

    async def _reference_refresher():
        while True:
            try:
                await asyncio.sleep(ReferenceBook.get_cache_lifetime_seconds())
                await ReferenceBook.load(REFERENCE_PATH)

                if ReferenceBook.is_empty():
                    logger.warning("ПРЕДУПРЕЖДЕНИЕ: Справочник обновлен, но пуст")
                else:
                    logger.info(
                        "Справочник обновлен: %s записей",
                        ReferenceBook.get_cache_size(),
                    )
            except PermissionError:
                logger.error("Ошибка доступа к справочнику: %s", REFERENCE_PATH)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error("Ошибка обновления справочника: %s", e)
                await asyncio.sleep(60)

    asyncio.create_task(_reference_refresher())


async def main():
    dp.startup.register(on_startup)
    dp.include_router(router)
    logger.info("Бот запущен и готов к работе")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
