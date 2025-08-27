"""
Kafka Consumer để xử lý email từ nhiều topic
"""
import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from kafka import KafkaConsumer
from loguru import logger

from models import EmailData, EmailStreamMessage
from config import settings


class EmailProcessor:
    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.consumer_group = "email-processor-group"
        self.consumer: Optional[KafkaConsumer] = None
        self.fastapi_url = "http://localhost:8000"  # FastAPI server URL
        
        # Topics để consume
        self.topics = [
            "duongcongthai18703",
            "thaibha123456",
            "emails-default"
        ]
        
        # Regex patterns để extract số tiền từ các ngân hàng khác nhau
        self.amount_patterns = {
            "acb": r"Ghi có \*\+([\d,]+\.\d{2}) VND",
            "vcb": r"Credit \+([\d,]+\.\d{2}) VND", 
            "default": r"\+([\d,]+\.\d{2}) VND"
        }
        
        # Lưu trữ dữ liệu đã xử lý để tổng hợp
        self.processed_data = []
    
    def connect(self) -> bool:
        """Connect to Kafka as consumer"""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,  # Subscribe to all topics
                bootstrap_servers=self.bootstrap_servers.split(','),
                group_id=self.consumer_group,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info(f"Connected to Kafka consumer: {self.topics}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect Kafka consumer: {e}")
            return False
    
    def disconnect(self):
        """Disconnect consumer"""
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Disconnected Kafka consumer")
            except Exception as e:
                logger.warning(f"Error disconnecting consumer: {e}")
            finally:
                self.consumer = None
    
    def extract_amount_from_email(self, email_data: EmailData) -> Optional[float]:
        if not email_data.body_text:
            return None
            
        body = email_data.body_text
        try:
            return float(body)
        except ValueError as e:
            logger.error(f"Lỗi tại extract_amount_from_email: {e}")
    
    def process_email(self, email_data: EmailData, topic: str) -> Dict:
        # Extract số tiền
        amount = self.extract_amount_from_email(email_data)
        
        processed_info = {
            "message_id": email_data.message_id,
            "topic": topic,
            "subject": email_data.subject,
            "sender": email_data.sender,
            "date": email_data.date,
            "amount": amount,
            "processed_at": datetime.now(),
            "has_amount": amount is not None
        }
        
        logger.info(f"Consumer xử lý email từ topic {topic}: {email_data.subject[:30]}... Amount: {amount}")
        return processed_info
    
    def send_stats_to_api(self, stats: Dict):
        try:
            stats['last_updated'] = datetime.now().isoformat()
            response = requests.post(
                f"{self.fastapi_url}/api/update_stats",
                json=stats,
                timeout=5
            )
            if response.status_code == 200:
                logger.debug(f"Stats sent to FastAPI successfully => Real-time update at {stats['last_updated']}")
            else:
                logger.warning(f"Failed to send stats to API: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending stats to API: {e}")
    
    def start_consuming(self):
        if not self.connect():
            return
        
        logger.info("🚀 Starting consume email from Kafka topics...")
        logger.info(f"📋 Topics: {self.topics}")
        logger.info(f"🌐 FastAPI URL: {self.fastapi_url}")
        
        try:
            for message in self.consumer:
                try:
                    # Parse message
                    stream_message_data = message.value
                    email_data_dict = stream_message_data.get('email', {})
                    
                    # Recreate EmailData object (simplified)
                    email_data = EmailData(
                        message_id=email_data_dict.get('message_id'),
                        subject=email_data_dict.get('subject'),
                        sender=email_data_dict.get('sender'),
                        recipients=email_data_dict.get('recipients', []),
                        cc=email_data_dict.get('cc'),
                        bcc=email_data_dict.get('bcc'),
                        date=datetime.fromisoformat(email_data_dict.get('date')),
                        body_text=email_data_dict.get('body_text'),
                        body_html=email_data_dict.get('body_html'),
                        attachments=email_data_dict.get('attachments', []),
                        flags=email_data_dict.get('flags', []),
                        folder=email_data_dict.get('folder')
                    )
                    
                    # Process email
                    processed_info = self.process_email(email_data, message.topic)
                    self.processed_data.append(processed_info)
                    
                    # Send updated stats to FastAPI after each email
                    updated_stats = self.get_summary_stats()
                    self.send_stats_to_api(updated_stats)
                    
                    # Log progress
                    logger.info(f"📧 Processed email from {message.topic}: "
                              f"{email_data.subject[:30]}... "
                              f"Total: {len(self.processed_data)} for all topics")
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Stopping email processor...")
        finally:
            self.disconnect()
    
    def get_summary_stats(self) -> Dict:
        if not self.processed_data:
            return {
                "total": 0, 
                "by_topic": {}, 
                "by_date": {},
                "total_amount": 0,
                "emails_with_amount": 0
            }
        
        stats = {
            "total": len(self.processed_data),
            "by_topic": {},
            "by_date": {},
            "total_amount": 0,
            "emails_with_amount": 0
        }
        
        for item in self.processed_data:
            topic = item["topic"]
            # Extract date from datetime object
            email_date = item["date"]
            if isinstance(email_date, datetime):
                date_str = email_date.strftime('%Y-%m-%d')
            else:
                date_str = str(email_date)[:10]  # Take first 10 chars if string
            
            # Count by topic
            if topic not in stats["by_topic"]:
                stats["by_topic"][topic] = {"count": 0, "total_amount": 0}
            stats["by_topic"][topic]["count"] += 1
            
            # Count by date
            if date_str not in stats["by_date"]:
                stats["by_date"][date_str] = {"count": 0, "total_amount": 0, "by_topic": {}}
            stats["by_date"][date_str]["count"] += 1
            
            # Count by date and topic combination
            if topic not in stats["by_date"][date_str]["by_topic"]:
                stats["by_date"][date_str]["by_topic"][topic] = {"count": 0, "total_amount": 0}
            stats["by_date"][date_str]["by_topic"][topic]["count"] += 1
            
            # Sum amounts
            if item["amount"]:
                amount = item["amount"]
                stats["total_amount"] += amount
                stats["by_topic"][topic]["total_amount"] += amount
                stats["by_date"][date_str]["total_amount"] += amount
                stats["by_date"][date_str]["by_topic"][topic]["total_amount"] += amount
                stats["emails_with_amount"] += 1
        
        return stats


def main():
    processor = EmailProcessor()
    try:
        processor.start_consuming()
    finally:
        # In thống kê cuối
        stats = processor.get_summary_stats()
        print("\n📊 FINAL STATS:")
        print(f"Total emails processed: {stats['total']}")
        print(f"Emails with amount: {stats['emails_with_amount']}")
        print(f"Total amount: {stats['total_amount']:,.2f} VND")
        
        print("\n📧 By Topic:")
        for topic, data in stats["by_topic"].items():
            print(f"  {topic}: {data['count']} emails, {data['total_amount']:,.2f} VND")
        
        print("\n📅 By Date:")
        for date, data in sorted(stats["by_date"].items(), reverse=True):
            print(f"  {date}: {data['count']} emails, {data['total_amount']:,.2f} VND")
            for topic, topic_data in data["by_topic"].items():
                print(f"    - {topic}: {topic_data['count']} emails, {topic_data['total_amount']:,.2f} VND")


if __name__ == "__main__":
    main()
