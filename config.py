import os

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    @staticmethod
    def get_engine():
        """Создает подключение к PostgreSQL"""

        connection_string = (
            f"postgresql://"
            f"{Config.DB_USER}:"
            f"{Config.DB_PASSWORD}@"
            f"{Config.DB_HOST}:"
            f"{Config.DB_PORT}/"
            f"{Config.DB_NAME}"
        )

        engine = create_engine(
            connection_string,

            # Проверяем соединение перед использованием
            pool_pre_ping=True,

            # Количество постоянных соединений в пуле
            pool_size=5,

            # Дополнительные соединения при необходимости
            max_overflow=5,

            # Через 30 минут соединение будет заменено
            pool_recycle=1800,

            # Не ждать бесконечно свободное соединение
            pool_timeout=30
        )

        return engine