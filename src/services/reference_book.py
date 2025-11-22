import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


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
            if not force and cls._loaded and cls._last_load_time:
                time_since_load = datetime.now() - cls._last_load_time
                if time_since_load < cls._cache_lifetime:
                    logger.info(
                        "Справочник актуален (загружен %s назад)", time_since_load
                    )
                    return

            logger.info("Начинаем загрузку справочника...")
            df = pd.read_excel(path, usecols=[0, 5], dtype=str, engine="openpyxl")
            df.dropna(inplace=True)
            df.iloc[:, 0] = df.iloc[:, 0].str.strip().str.upper()
            df.iloc[:, 1] = df.iloc[:, 1].str.strip()

            cls._cache = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
            cls._loaded = True
            cls._last_load_time = datetime.now()
            logger.info("Справочник успешно загружен: %s записей", len(cls._cache))

    @classmethod
    def get_barcode(cls, article: str) -> Optional[str]:
        """Синхронный метод — теперь можно! Кэш уже гарантированно загружен"""
        return cls._cache.get(str(article).strip().upper())

    @classmethod
    def is_empty(cls) -> bool:
        """Проверка, пуст ли справочник"""
        return len(cls._cache) == 0

    @classmethod
    def get_cache_size(cls) -> int:
        """Получить количество записей в справочнике"""
        return len(cls._cache)

    @classmethod
    def get_cache_lifetime_seconds(cls) -> float:
        """Получить время жизни кэша в секундах"""
        return cls._cache_lifetime.total_seconds()
