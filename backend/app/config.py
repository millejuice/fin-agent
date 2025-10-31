"""
Configuration management with environment variable support.
"""
import os
from typing import List

class Settings:
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_TITLE: str = os.getenv("API_TITLE", "Finance AI Agent API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv(
        "API_DESCRIPTION",
        "Professional AI-powered financial analysis and trading platform"
    )
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    
    # File Upload Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # External APIs
    YAHOO_FINANCE_TIMEOUT: int = int(os.getenv("YAHOO_FINANCE_TIMEOUT", "30"))
    
    @classmethod
    def get_upload_dir(cls) -> str:
        """Get upload directory, creating it if it doesn't exist."""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        return cls.UPLOAD_DIR

settings = Settings()

