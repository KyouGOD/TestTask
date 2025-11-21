from pathlib import Path
import asyncio
import tempfile
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram import F
from aiogram.types import Message, FSInputFile
from config import TOKEN, REFERENCE_BOOK_FILE_PATH
from services.reference_book import ReferenceBook
from services.file_processor import FileProcessor

bot = Bot(token=TOKEN)

REFERENCE_PATH = Path(REFERENCE_BOOK_FILE_PATH)
TEMP_DIR = Path(tempfile.gettempdir()) / "telegram_bot_files"
TEMP_DIR.mkdir(exist_ok=True)

dp = Dispatcher()
router = Router()

user_file_batches = {}
batch_timers = {}

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот для обработки файлов с кодами.\n\n"
        "Отправьте файл Excel (.xlsx или .xls) для:\n"
        "1. Извлечения артикула из названия файла\n"
        "2. Поиска соответствующего штрихкода в справочнике\n"
        "3. Обработки кодов из столбца B\n"
        "4. Получения результирующего файла\n\n"
        "Можно отправить несколько файлов подряд."
    )


@router.message(F.document)
async def handle_document(message: Message):
    """Обработчик входящих документов"""
    user_id = message.from_user.id
    document = message.document
    
    # Проверяем формат файла
    if not (document.file_name.lower().endswith('.xlsx') or document.file_name.lower().endswith('.xls')):
        await message.reply(
            "Файл должен быть в формате .xlsx или .xls"
        )
        return
    
    # Инициализируем счетчик файлов для пользователя
    if user_id not in user_file_batches:
        user_file_batches[user_id] = []
    
    # Скачиваем файл
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Скачиваем файл во временную директорию
        file = await bot.get_file(document.file_id)
        temp_input_path = TEMP_DIR / f"{document.file_id}_{document.file_name}"
        
        await bot.download_file(file.file_path, temp_input_path)

        # Обрабатываем файл
        temp_output_path, article = FileProcessor.process_file(
            input_file_path=temp_input_path,
            output_dir=TEMP_DIR,
            filename=document.file_name,
        )

        # Отправляем результирующий файл
        result_file = FSInputFile(temp_output_path)
        await message.reply_document(
            result_file,
            caption=f"✅ Файл обработан успешно!\nАртикул: {article}"
        )

        # Добавляем в счетчик обработанных файлов
        user_file_batches[user_id].append(document.file_name)

        # Запускаем таймер для групповой обработки
        await schedule_batch_completion(user_id)

    except ValueError as e:
        # Ошибки валидации
        error_message = str(e)
        if "не найден в справочнике" in error_message:
            await message.reply(f"❌ {error_message}")
        elif "не найдено кодов" in error_message:
            await message.reply(f"❌ {error_message}")
        else:
            await message.reply(f"❌ Ошибка: {error_message}")

    except Exception as e:
        # Общие ошибки
        await message.reply(
            f"❌ Произошла ошибка при обработке файла.\n"
            f"Пожалуйста, проверьте формат файла и попробуйте снова.\n"
            f"Детали: {str(e)}"
        )
    
    finally:
        # Удаляем временные файлы
        if temp_input_path and temp_input_path.exists():
            try:
                os.remove(temp_input_path)
            except:
                pass
        if temp_output_path and temp_output_path.exists():
            try:
                os.remove(temp_output_path)
            except:
                pass


async def schedule_batch_completion(user_id: int):
    """Планирует отправку итогового сообщения через 3 секунды"""
    
    # Отменяем предыдущий таймер, если он был
    if user_id in batch_timers:
        batch_timers[user_id].cancel()
    
    # Создаем новый таймер
    async def send_batch_summary():
        await asyncio.sleep(3)
        
        if user_id in user_file_batches and user_file_batches[user_id]:
            file_count = len(user_file_batches[user_id])
            
            if file_count > 1:
                await bot.send_message(
                    user_id,
                    f"Обработка завершена\n"
                    f"Всего обработано файлов: {file_count}"
                )
            
            user_file_batches[user_id] = []
            
        if user_id in batch_timers:
            del batch_timers[user_id]
    
    # Запускаем таймер
    task = asyncio.create_task(send_batch_summary())
    batch_timers[user_id] = task


dp.include_router(router)

async def on_startup():
    if not REFERENCE_PATH.exists():
        print(f"ОШИБКА: Файл справочника не найден: {REFERENCE_PATH}")
        return
    await ReferenceBook.load(REFERENCE_PATH)
    print("Бот готов к работе!")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
