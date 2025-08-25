"""
Configuration settings for Email IMAP to Kafka Streamer
Reads configuration from .env file using Pydantic Settings
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # IMAP Configuration
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    imap_username: str 
    imap_password: str  
    imap_folder: str = "INBOX"
    
    # Kafka Configuration
    kafka_bootstrap_servers: str 
    kafka_topic: str 
    kafka_client_id: str 
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'extra': 'ignore'  # Ignore extra fields in .env
    }


def create_settings() -> Settings:
    """Create and validate settings instance"""
    try:
        settings = Settings()
        
        # Validate required settings
        if not settings.imap_username:
            raise ValueError("❌ IMAP_USERNAME is required in .env file")
        if not settings.imap_password:
            raise ValueError("❌ IMAP_PASSWORD is required in .env file")
        
        return settings
        
    except Exception as e:
        print(f"🔧 Configuration Error: {e}")
        print("📝 Make sure .env file exists and contains required settings.")
        print("💡 Copy .env.example to .env and update with your values.")
        raise

settings = create_settings()
