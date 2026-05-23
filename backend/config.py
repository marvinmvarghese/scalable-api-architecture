import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "HyperBlog API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database Settings - Defaulting to asyncpg postgresql, fallback to aiosqlite for easy local run
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./blog.db"
    )
    
    # Redis Cache Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = 60  # Cache duration for blogs in seconds
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = 50
    DB_MAX_OVERFLOW: int = 100
    
    # Rate Limiting
    MAX_REQUESTS_PER_SECOND: int = 100000  # Target system threshold representation
    
    class Config:
        env_file = ".env"

settings = Settings()
