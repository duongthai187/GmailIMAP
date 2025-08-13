"""
Test scripts for the Email IMAP to Kafka Streamer
"""
import asyncio
import json
from datetime import datetime
from kafka import KafkaConsumer
from loguru import logger

from config import settings


class EmailConsumerTest:
    """Test consumer to read emails from Kafka"""
    
    def __init__(self):
        self.consumer = None
        
    def connect(self):
        """Connect to Kafka as consumer"""
        try:
            self.consumer = KafkaConsumer(
                settings.kafka_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
                client_id=f"{settings.kafka_client_id}_test_consumer",
                group_id="email_test_group",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info(f"Connected to Kafka as consumer for topic: {settings.kafka_topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect consumer to Kafka: {e}")
            return False
    
    def start_consuming(self, max_messages=10):
        """Start consuming messages from Kafka"""
        if not self.consumer:
            if not self.connect():
                return
        
        logger.info(f"Starting to consume emails from Kafka (max {max_messages} messages)...")
        
        try:
            message_count = 0
            for message in self.consumer:
                message_count += 1
                
                email_data = message.value
                logger.info(f"Received email #{message_count}:")
                logger.info(f"  Subject: {email_data['email']['subject']}")
                logger.info(f"  From: {email_data['email']['sender']}")
                logger.info(f"  Date: {email_data['email']['date']}")
                logger.info(f"  Timestamp: {email_data['timestamp']}")
                logger.info(f"  Message ID: {email_data['email']['message_id']}")
                logger.info("---")
                
                if message_count >= max_messages:
                    break
                    
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
        finally:
            if self.consumer:
                self.consumer.close()


def test_imap_connection():
    """Test IMAP connection"""
    from imap_client import ImapEmailClient
    
    logger.info("Testing IMAP connection...")
    client = ImapEmailClient()
    
    if client.connect():
        logger.info("✅ IMAP connection successful")
        status = client.get_status()
        logger.info(f"Status: {status}")
        client.disconnect()
        return True
    else:
        logger.error("❌ IMAP connection failed")
        return False


def test_kafka_connection():
    """Test Kafka connection"""
    from kafka_streamer import KafkaEmailStreamer
    
    logger.info("Testing Kafka connection...")
    streamer = KafkaEmailStreamer()
    
    if streamer.connect():
        logger.info("✅ Kafka connection successful")
        status = streamer.get_status()
        logger.info(f"Status: {status}")
        streamer.disconnect()
        return True
    else:
        logger.error("❌ Kafka connection failed")
        return False


async def test_full_pipeline():
    """Test the full email pipeline"""
    logger.info("Testing full email pipeline...")
    
    # Test connections
    imap_ok = test_imap_connection()
    kafka_ok = test_kafka_connection()
    
    if not (imap_ok and kafka_ok):
        logger.error("❌ Connection tests failed")
        return False
    
    # Test email monitoring service
    from email_monitor import EmailMonitorService
    
    service = EmailMonitorService()
    logger.info("Testing email monitor service...")
    
    try:
        # Run one iteration
        await service._check_and_process_emails()
        logger.info("✅ Email monitoring test completed")
        return True
    except Exception as e:
        logger.error(f"❌ Email monitoring test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_email_streamer.py imap      - Test IMAP connection")
        print("  python test_email_streamer.py kafka     - Test Kafka connection")
        print("  python test_email_streamer.py pipeline  - Test full pipeline")
        print("  python test_email_streamer.py consume   - Start consuming emails from Kafka")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "imap":
        test_imap_connection()
    elif command == "kafka":
        test_kafka_connection()
    elif command == "pipeline":
        asyncio.run(test_full_pipeline())
    elif command == "consume":
        consumer = EmailConsumerTest()
        consumer.start_consuming()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
