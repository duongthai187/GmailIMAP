"""
Email monitoring service that checks IMAP and streams to Kafka
"""
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger

from imap_client import ImapEmailClient
from kafka_streamer import KafkaEmailStreamer
from config import settings


class EmailMonitorService:
    def __init__(self):
        self.imap_client = ImapEmailClient()
        self.kafka_streamer = KafkaEmailStreamer()
        self.is_running = False
        self.check_interval = settings.check_interval_minutes * 60  # Convert to seconds
        self.stats = {
            "total_emails_processed": 0,
            "total_emails_sent_to_kafka": 0,
            "last_check_time": None,
            "last_error": None,
            "service_start_time": None
        }
    
    async def start(self):
        """Start the email monitoring service"""
        logger.info("Starting Email Monitor Service...")
        self.is_running = True
        self.stats["service_start_time"] = datetime.now()
        
        # Initialize connections
        if not self.imap_client.connect():
            logger.error("Failed to connect to IMAP server")
            return False
        
        if not self.kafka_streamer.connect():
            logger.error("Failed to connect to Kafka")
            return False
        
        logger.info(f"Email Monitor Service started. Check interval: {settings.check_interval_minutes} minutes")
        
        # Start monitoring loop
        try:
            await self._monitoring_loop()
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            self.stats["last_error"] = str(e)
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the email monitoring service"""
        logger.info("Stopping Email Monitor Service...")
        self.is_running = False
        
        # Disconnect from services
        self.imap_client.disconnect()
        self.kafka_streamer.disconnect()
        
        logger.info("Email Monitor Service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self._check_and_process_emails()
                
                # Wait for next check
                logger.info(f"Waiting {settings.check_interval_minutes} minutes for next check...")
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop iteration: {e}")
                self.stats["last_error"] = str(e)
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _check_and_process_emails(self):
        """Check IMAP for new emails and send to Kafka"""
        logger.info("Checking for new emails...")
        self.stats["last_check_time"] = datetime.now()
        
        emails_processed = 0
        emails_sent = 0
        
        try:
            # Fetch new emails
            for email_data in self.imap_client.fetch_new_emails():
                emails_processed += 1
                logger.info(f"Processing email: {email_data.subject} from {email_data.sender}")
                
                # Send to Kafka
                if self.kafka_streamer.send_email(email_data):
                    emails_sent += 1
                    logger.info(f"Email sent to Kafka successfully")
                else:
                    logger.warning(f"Failed to send email to Kafka")
            
            # Update stats
            self.stats["total_emails_processed"] += emails_processed
            self.stats["total_emails_sent_to_kafka"] += emails_sent
            
            logger.info(f"Email check completed. Processed: {emails_processed}, Sent to Kafka: {emails_sent}")
            
        except Exception as e:
            logger.error(f"Error processing emails: {e}")
            self.stats["last_error"] = str(e)
    
    def get_status(self) -> dict:
        """Get service status"""
        return {
            "service": {
                "running": self.is_running,
                "check_interval_minutes": settings.check_interval_minutes,
                "start_time": self.stats["service_start_time"].isoformat() if self.stats["service_start_time"] else None,
                "last_check": self.stats["last_check_time"].isoformat() if self.stats["last_check_time"] else None,
                "last_error": self.stats["last_error"]
            },
            "stats": {
                "total_emails_processed": self.stats["total_emails_processed"],
                "total_emails_sent_to_kafka": self.stats["total_emails_sent_to_kafka"]
            },
            "imap": self.imap_client.get_status(),
            "kafka": self.kafka_streamer.get_status()
        }
