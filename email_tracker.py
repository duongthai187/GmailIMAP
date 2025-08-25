#!/usr/bin/env python3
"""
Simple Email IMAP to Kafka Tracker
Chạy liên tục để track email mới từ IMAP và đẩy vào Kafka
Không cần API server, chỉ cần chạy script này!
"""
import time
import sys
import signal
import json
import os
from datetime import datetime, timedelta
from loguru import logger
from typing import List, Optional, Generator, Tuple, Set
from imap_client import ImapEmailClient
from kafka_streamer import KafkaEmailStreamer  
from email_logger import EmailProcessingLogger
from config import settings

class SimpleEmailTracker:
    def __init__(self):
        self.imap_client = ImapEmailClient()
        self.kafka_streamer = KafkaEmailStreamer()
        self.email_logger = EmailProcessingLogger()
        self.running = False
        self.state_file = "email_tracker_state.json"
        
        # Cache processed UIDs để tránh đọc log files liên tục
        self.processed_uids_cache: Set[int] = set()
        self.cache_date: Optional[str] = None  # Track ngày của cache
        
        self.stats = {
            "start_time": datetime.now(),
            "total_checks": 0,
            "total_emails_found": 0,
            "total_emails_sent": 0,
            "errors": 0
        }
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._load_state()
        
    def _get_processed_uids(self, target_date: datetime) -> Set[int]:
        """Get processed UIDs with caching for efficiency"""
        date_str = target_date.strftime('%Y%m%d')
        
        # Check if cache is valid for this date
        if self.cache_date != date_str:
            logger.info(f"🔄 Loading processed UIDs for {date_str}")
            self.processed_uids_cache = self.email_logger.get_processed_uids_for_date(target_date)
            self.cache_date = date_str
            logger.info(f"📋 Cached {len(self.processed_uids_cache)} processed UIDs")
        
        return self.processed_uids_cache
    
    def _add_processed_uid(self, uid: int):
        """Add UID to cache when processing new email"""
        self.processed_uids_cache.add(uid)
        logger.debug(f"Added UID {uid} to cache")
    
    def _load_state(self):
        """Load previous tracking state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                if state.get('last_check_time'):
                    self.imap_client.last_check_tim = datetime.fromisoformat(state['last_check_time'])
                    interrupted_at = state.get('interrupted_at')
                    print(f"📂 Found previous session state:")
                    print(f"   📅 Last check: {datetime.fromisoformat(state['last_check_time']).strftime('%H:%M:%S %d-%b-%Y')}")
                    if interrupted_at:
                        print(f"   🛑 Interrupted: {datetime.fromisoformat(interrupted_at).strftime('%H:%M:%S %d-%b-%Y')}")
                    print(f"   🔄 Will resume from last check time")
                else:
                    print("📂 No previous check time found, starting fresh")
            else:
                print("📂 No previous state file found, starting fresh")
                    
        except Exception as e:
            logger.warning(f"Could not load previous state: {e}")
            print("📂 Starting fresh due to state load error")
    
    def _save_state(self):
        try:
            state = {
                'last_check_time': self.imap_client.last_check_time.isoformat() if self.imap_client.last_check_time else None,
                'interrupted_at': datetime.now().isoformat(),
                'stats': {
                    'total_checks': self.stats['total_checks'],
                    'total_emails_found': self.stats['total_emails_found'], 
                    'total_emails_sent': self.stats['total_emails_sent'],
                    'errors': self.stats['errors']
                }
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"💾 Lưu trạng thái vào {self.state_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu trạng thái: {e}")
    
    def _save_shutdown_log(self):
        try:
            # Create lakehouse log directory
            log_dir = "Files/Emails/Logs"
            os.makedirs(log_dir, exist_ok=True)
            
            # Generate log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"email_tracker_shutdown_{timestamp}.json")
            
            # Calculate runtime
            runtime = datetime.now() - self.stats["start_time"] if self.stats["start_time"] else None
            runtime_str = str(runtime).split('.')[0] if runtime else "Unknown"
            
            # Create detailed shutdown log
            shutdown_log = {
                "shutdown_info": {
                    "timestamp": datetime.now().isoformat(),
                    "reason": "Graceful shutdown (SIGINT/SIGTERM)",
                    "runtime": runtime_str
                },
                "session_stats": {
                    "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
                    "total_checks": self.stats["total_checks"],
                    "total_emails_found": self.stats["total_emails_found"],
                    "total_emails_sent": self.stats["total_emails_sent"],
                    "errors": self.stats["errors"],
                },
                "tracking_state": {
                    "last_check_time": self.imap_client.last_check_time.isoformat() if self.imap_client.last_check_time else None,
                    "will_resume_from": self.imap_client.last_check_time.isoformat() if self.imap_client.last_check_time else None
                },
                "config": {
                    "imap_server": settings.imap_server,
                    "imap_username": settings.imap_username,
                    "kafka_servers": settings.kafka_bootstrap_servers,
                    "kafka_topic": settings.kafka_topic,
                }
            }
            
            # Save to lakehouse log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(shutdown_log, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Shutdown log saved: {log_file}")
            logger.info(f"📄 Detailed shutdown log saved to lakehouse: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save shutdown log to lakehouse: {e}")
            print(f"⚠️  Could not save shutdown log: {e}")
    
    def _signal_handler(self, signum, frame):
        print(f"\n🛑 Nhận lệnh ngắt {signum}, thực hiện dừng chương trình...")
        self.stop()
    
    def start(self):
        print("=" * 60)
        print("📧 SIMPLE EMAIL IMAP → KAFKA TRACKER")
        print("=" * 60)
        
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # Setup logging
        logger.remove()
        logger.add(
            sys.stdout, 
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        )
        logger.add(
            "logs/email_tracker.log",
            rotation="1 day",
            retention="7 days",
            format="{time} | {level} | {message}"
        )
        
        logger.info("🚀 Starting Simple Email Tracker")
        logger.info(f"📧 IMAP: {settings.imap_username}@{settings.imap_server}")
        logger.info(f"📤 Kafka: {settings.kafka_bootstrap_servers} → {settings.kafka_topic}")
        
        if not self._connect_services():
            return False
        
        try:
            self._main_loop()
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            self.stats["errors"] += 1
        finally:
            self.stop()
            
        return True
    
    def _connect_services(self):
        # Connect IMAP
        if not self.imap_client.connect():
            print("❌ Failed to connect to IMAP server")
            return False
        print(f"✅ Connected to IMAP: {settings.imap_server}")
        
        # Connect Kafka
        if not self.kafka_streamer.connect():
            print("❌ Failed to connect to Kafka")
            return False
        print(f"✅ Connected to Kafka: {settings.kafka_bootstrap_servers}")
        
        return True
    
    def _main_loop(self):
        print(f"\n🔄 Starting real-time email monitoring with IMAP IDLE")
        print("-" * 60)
        
        # Do initial check for any existing emails
        print("🔍 Performing initial email check...")
        self._check_existing_emails()
        
        # Start real-time monitoring with IMAP IDLE
        print("📡 Starting real-time IDLE monitoring...")
        self._start_realtime_monitoring()
    
    def _check_existing_emails(self):
        """Check for existing emails (one-time on startup)"""
        if self.imap_client.last_check_time:
            print(f"📂 Checking existing emails from: [{self.imap_client.last_check_time.strftime('%H:%M:%S %d-%b-%Y')}]")
        else:
            self.imap_client.last_check_time = datetime.now()
            print(f"📂 Initial check at: [{self.imap_client.last_check_time.strftime('%H:%M:%S %d-%b-%Y')}]")
        
        # Load processed UIDs for the check date (with caching)
        processed_uids = self._get_processed_uids(self.imap_client.last_check_time)
        print(f"📋 Loaded {len(processed_uids)} already processed UIDs from cache")
        
        # Start logging session
        self.email_logger.start_check_session()
        
        emails_found = 0
        emails_sent = 0
        
        try:
            for uid, email_data in self.imap_client._fetch_latest_emails(processed_uids):
                emails_found += 1
                print(f"  📧 Found UID {uid}: {email_data.subject[:50]}...")
                print(f"      From: {email_data.sender}")
                
                kafka_status = "error"
                if self.kafka_streamer.send_email(email_data):
                    emails_sent += 1
                    kafka_status = "sent"
                    print(f"      ✅ Sent to Kafka")
                else:
                    print(f"      ❌ Failed to send to Kafka")
                
                self.email_logger.log_processed_email(email_data, uid, kafka_status)
                
                # Add to cache for future checks
                self._add_processed_uid(uid)
                    
        except Exception as e:
            logger.error(f"❌ Error in initial check: {e}")
        finally:
            try:
                log_file = self.email_logger.finish_check_session()
                if emails_found > 0:
                    print(f"📝 Initial check logged: {log_file}")
            except Exception as e:
                logger.error(f"Failed to save initial check: {e}")
        
        # Update stats and last_check_time
        self.stats["total_checks"] += 1
        self.stats["total_emails_found"] += emails_found
        self.stats["total_emails_sent"] += emails_sent
        self.imap_client.last_check_time = datetime.now()
        
        if emails_found > 0:
            print(f"📊 Initial check: {emails_found} found, {emails_sent} sent to Kafka")
        else:
            print("📭 No existing emails to process")
    
    def _start_realtime_monitoring(self):
        while self.running:
            try:
                # Use cached processed UIDs (no need to reload every time!)
                processed_uids = self._get_processed_uids(datetime.now())
                
                # Start IDLE monitoring - this will block until new emails arrive
                for uid, email_data in self.imap_client.start_idle_monitoring(processed_uids):
                    if not self.running:
                        break
                        
                    print(f"\n📧 Real-time email received!")
                    print(f"  UID {uid}: {email_data.subject[:50]}...")
                    print(f"  From: {email_data.sender}")
                    
                    # Start new logging session for this email
                    self.email_logger.start_check_session()
                    
                    try:
                        # Send to Kafka
                        kafka_status = "error"
                        if self.kafka_streamer.send_email(email_data):
                            kafka_status = "sent"
                            print(f"  ✅ Sent to Kafka")
                        else:
                            print(f"  ❌ Failed to send to Kafka")
                        
                        # Log processed email
                        self.email_logger.log_processed_email(email_data, uid, kafka_status)
                        
                        # Add to cache immediately
                        self._add_processed_uid(uid)
                        
                        # Update stats
                        self.stats["total_emails_found"] += 1
                        if kafka_status == "sent":
                            self.stats["total_emails_sent"] += 1
                        
                        # Update last check time
                        self.imap_client.last_check_time = datetime.now()
                        
                    finally:
                        # Finish logging session
                        try:
                            log_file = self.email_logger.finish_check_session()
                            print(f"  📝 Logged: {os.path.basename(log_file)}")
                        except Exception as e:
                            logger.error(f"Failed to save real-time log: {e}")
                    
                    # Show live stats
                    runtime = datetime.now() - self.stats["start_time"]
                    print(f"  📈 Total: {self.stats['total_emails_found']} emails, "
                          f"{self.stats['total_emails_sent']} sent, "
                          f"Runtime: {str(runtime).split('.')[0]}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Error in real-time monitoring: {e}")
                self.stats["errors"] += 1
                time.sleep(5)  # Wait before retrying
    
    def stop(self):
        print(f"\n🛑 Đang dừng Email Tracker...")
        self.running = False
        
        # Save current state for resume
        self._save_state()
        
        # Save detailed shutdown log to lakehouse
        self._save_shutdown_log()
        
        # Disconnect services
        if self.imap_client:
            self.imap_client.disconnect()
        if self.kafka_streamer:
            self.kafka_streamer.disconnect()
        
        # Show final stats
        if self.stats["start_time"]:
            runtime = datetime.now() - self.stats["start_time"]
            print(f"\n📊 Final Stats:")
            print(f"   ⏰ Runtime: {str(runtime).split('.')[0]}")
            print(f"   🔍 Total checks: {self.stats['total_checks']}")
            print(f"   📧 Emails found: {self.stats['total_emails_found']}")
            print(f"   📤 Emails sent: {self.stats['total_emails_sent']}")
            print(f"   ❌ Errors: {self.stats['errors']}")
            if self.imap_client.last_check_time:
                print(f"   📅 Will resume from: {self.imap_client.last_check_time}")
        
        print("✅ Email Tracker dừng thành công.")
        print(f"💾 Đã lưu trạng thái cho lần chạy tiếp theo.")

def main():
    """Main function"""
    tracker = SimpleEmailTracker()
    tracker.start()

if __name__ == "__main__":
    main()
