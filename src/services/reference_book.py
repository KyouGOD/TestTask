import asyncio
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd


class ReferenceBook:
    """Класс для хранения справочника(уйти от использования глобальных переменных)"""

    _cache: Dict[str, str] = {}
    _loaded = False
    _lock = asyncio.Lock()
    _last_load_time: Optional[datetime] = None
    _cache_lifetime = timedelta(hours=8)

    @classmethod
    async def load(cls, path: Path, force: bool = False):
        """Предзагрузка справочника при старте приложения с кэшированием на 8 часов"""
        async with cls._lock:
            # Проверяем, нужно ли обновлять кэш
            if not force and cls._loaded and cls._last_load_time:
                time_since_load = datetime.now() - cls._last_load_time
                if time_since_load < cls._cache_lifetime:
                    print(f"Справочник актуален (загружен {time_since_load} назад)")
                    return

            print("Начинаем загрузку справочника...")
            df = pd.read_excel(path, usecols=[0, 5], dtype=str, engine="openpyxl")
            df.dropna(inplace=True)
            df.iloc[:, 0] = df.iloc[:, 0].str.strip().str.upper()
            df.iloc[:, 1] = df.iloc[:, 1].str.strip()

            cls._cache = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
            cls._loaded = True
            cls._last_load_time = datetime.now()
            print(f"Справочник успешно загружен: {len(cls._cache):,} записей")

    @classmethod
    def get_barcode(cls, article: str) -> Optional[str]:
        """Синхронный метод — теперь можно! Кэш уже гарантированно загружен"""
        return cls._cache.get(str(article).strip().upper())
