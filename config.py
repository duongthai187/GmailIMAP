"""
Configuration settings for Email IMAP to Kafka Streamer
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
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "email-stream"
    kafka_client_id: str = "email_imap_client"
    
    # Application Settings (optional)
    check_interval_minutes: float = 0.5
    max_emails_per_check: int = 50
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


# Global settings instance
settings = Settings()
