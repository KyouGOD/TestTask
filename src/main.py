import sys
from pathlib import Path
import asyncio
import tempfile
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InputMediaDocument
from aiogram import F
from config import TOKEN, REFERENCE_BOOK_FILE_PATH
from services.reference_book import ReferenceBook
from services.file_processor import FileProcessor

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

REFERENCE_PATH = Path(REFERENCE_BOOK_FILE_PATH)
TEMP_DIR = Path(tempfile.gettempdir()) / "tg_bot_files"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


user_state = defaultdict(lambda: {
    "results": [],
    "timer": None,
    "chat_id": None
})

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

    if not doc.file_name or not doc.file_name.lower().endswith(('.xlsx', '.xls')):
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
            FSInputFile(temp_output),
            caption=f"✅ {doc.file_name}\nАртикул: {article}"
        )

        state["results"].append({
            "success": True,
            "filename": doc.file_name,
            "article": article,
            "result_path": temp_output,
            "temp_input": temp_input
        })

    except Exception as e:
        # Сразу отправляем ошибку
        await message.reply(f"❌ {doc.file_name}\n{str(e)}")
        
        state["results"].append({
            "success": False,
            "filename": doc.file_name or "unknown",
            "error": str(e),
            "temp_input": temp_input
        })

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

        # Отправляем только итоговое сообщение (файлы уже отправлены)
        if total > 1:
            lines = [
                f"Обработка завершена: {total} файл(ов)",
                f"✅ Успешно: {success_count}",
            ]
            if total - success_count > 0:
                lines.append(f"❌ С ошибками: {total - success_count}")
            
            await bot.send_message(state["chat_id"], "\n".join(lines))

        # Очистка временных файлов
        for r in results:
            for key in ("temp_input", "result_path"):
                if path := r.get(key):
                    Path(path).unlink(missing_ok=True)

        del user_state[user_id]

    task = asyncio.create_task(send_summary())
    state["timer"] = task

# Startup
async def on_startup():
    if not REFERENCE_PATH.exists():
        print(f"ОШИБКА: Справочник не найден: {REFERENCE_PATH}")
        sys.exit(1)
    await ReferenceBook.load(REFERENCE_PATH)
    async def _reference_refresher():
        while True:
            try:
                await asyncio.sleep(ReferenceBook._cache_lifetime.total_seconds())
                await ReferenceBook.load(REFERENCE_PATH)
                print("Справочник обновлен")
            except Exception as e:
                print("Ошибка обновления справочника:", e)
                await asyncio.sleep(60)

    asyncio.create_task(_reference_refresher())

async def main():
    dp.startup.register(on_startup)
    dp.include_router(router)
    print("Бот запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
