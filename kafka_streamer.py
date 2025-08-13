"""
Kafka producer for streaming email data
"""
import json
from datetime import datetime
from typing import Optional
from kafka import KafkaProducer
from loguru import logger

from models import EmailData, EmailStreamMessage
from config import settings


class KafkaEmailStreamer:
    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topic = settings.kafka_topic
        self.client_id = settings.kafka_client_id
        self.producer: Optional[KafkaProducer] = None
        
    def connect(self) -> bool:
        """Connect to Kafka cluster"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Kafka"""
        if self.producer:
            try:
                self.producer.close()
                logger.info("Disconnected from Kafka")
            except Exception as e:
                logger.warning(f"Error during Kafka disconnect: {e}")
            finally:
                self.producer = None
    
    def send_email(self, email_data: EmailData) -> bool:
        """Send email data to Kafka topic"""
        if not self.producer:
            if not self.connect():
                return False
        
        try:
            # Create stream message
            stream_message = EmailStreamMessage(
                timestamp=datetime.now(),
                email=email_data
            )
            
            # Send to Kafka
            future = self.producer.send(
                self.topic,
                value=stream_message.dict(),
                key=email_data.message_id
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            logger.info(f"Email sent to Kafka - Topic: {record_metadata.topic}, "
                       f"Partition: {record_metadata.partition}, "
                       f"Offset: {record_metadata.offset}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to Kafka: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get streamer status"""
        return {
            "connected": self.producer is not None,
            "bootstrap_servers": self.bootstrap_servers,
            "topic": self.topic,
            "client_id": self.client_id
        }
