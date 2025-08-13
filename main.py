"""
Simple CLI runner for the Email IMAP to Kafka Streamer
"""
import asyncio
import signal
import sys
from loguru import logger

from email_monitor import EmailMonitorService
from config import settings


async def main():
    """Main entry point for CLI runner"""
    # Configure logging
    logger.add("logs/email_streamer.log", rotation="1 day", retention="7 days")
    logger.info("Starting Email IMAP to Kafka Streamer CLI")
    
    # Create service
    service = EmailMonitorService()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start service
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
