import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-at-least-32-characters")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
