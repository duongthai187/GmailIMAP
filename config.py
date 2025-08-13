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
    
    # Application Settings
    check_interval_minutes: int = 0.5
    max_emails_per_check: int = 50
    log_level: str = "INFO"
    
    # API Server Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "email-stream"
    kafka_client_id: str = "email_imap_client"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
