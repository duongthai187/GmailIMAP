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
        
        self.stats = {
            "start_time": datetime.now(),
            "total_checks": 0,
            "total_emails_found": 0,
            "total_emails_sent": 0,
            "last_check": None,
            "errors": 0
        }
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Load previous state if exists
        self._load_state()
    
    def _load_state(self):
        """Load previous tracking state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Set last_check_time in IMAP client
                if state.get('last_check_time'):
                    last_check = datetime.fromisoformat(state['last_check_time'])
                    self.imap_client.last_check_time = last_check
                    interrupted_at = state.get('interrupted_at')
                    print(f"📂 Found previous session state:")
                    print(f"   📅 Last check: {last_check.strftime('%H:%M:%S %d-%b-%Y')}")
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
        """Save current tracking state to file"""
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
                
            logger.info(f"💾 State saved to {self.state_file}")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _save_shutdown_log(self):
        """Save detailed shutdown log to lakehouse"""
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
                    "last_check": self.stats["last_check"].isoformat() if self.stats["last_check"] else None
                },
                "tracking_state": {
                    "last_check_time": self.imap_client.last_check_time.isoformat() if self.imap_client.last_check_time else None,
                    "will_resume_from": self.imap_client.last_check_time.isoformat() if self.imap_client.last_check_time else "server_start_time"
                },
                "config": {
                    "imap_server": settings.imap_server,
                    "imap_username": settings.imap_username,
                    "kafka_servers": settings.kafka_bootstrap_servers,
                    "kafka_topic": settings.kafka_topic,
                    "check_interval_minutes": settings.check_interval_minutes
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
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        print("=" * 60)
        print("📧 SIMPLE EMAIL IMAP → KAFKA TRACKER")
        print("=" * 60)
        
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # Setup logging
        logger.remove()  # Remove default logger
        logger.add(
            sys.stdout, 
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
            level=settings.log_level
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
        logger.info(f"⏰ Check interval: {settings.check_interval_minutes} minutes")
        
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
        print(f"\n🔄 Starting main loop (Press Ctrl+C to stop)")
        print("-" * 60)
        
        while self.running:
            try:
                self._check_emails()
                
                if self.running:  # Check if still running after email check
                    # Calculate next check time properly
                    next_check = datetime.now() + timedelta(minutes=settings.check_interval_minutes)
                    print(f"⏳ Next check at: {next_check.strftime('%H:%M:%S')}")
                    
                    # Sleep with status updates
                    self._smart_sleep(next_check)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                self.stats["errors"] += 1
                time.sleep(5)  # Wait a bit before retrying
    
    def _check_emails(self):
        if self.imap_client.last_check_time:
            check_time = self.imap_client.last_check_time
            print(f"\n🔍 Resuming email check from: [{check_time.strftime('%H:%M:%S %d-%b-%Y')}]")
        else:
            check_time = self.imap_client.last_check_time = datetime.now()
            print(f"\n🔍 Initial email check at: [{check_time.strftime('%H:%M:%S %d-%b-%Y')}]")        
        # Load processed UIDs for the check date
        processed_uids = set()
        processed_uids = self.email_logger.get_processed_uids_for_date(self.imap_client.last_check_time)
        print(f"📋 Loaded {len(processed_uids)} already processed UIDs from logs")
        
        # Update tracking stats
        self.stats["total_checks"] += 1
        self.stats["last_check"] = check_time  # Use actual check time, not always now()
        
        emails_found = 0
        emails_sent = 0
        
        try:
            # Fetch emails from IMAP with UID filtering
            for uid, email_data in self.imap_client.fetch_new_emails(processed_uids):
                emails_found += 1
                print(f"  📧 Found UID {uid}: {email_data.subject[:50]}...")
                print(f"      From: {email_data.sender}")
                
                # Send to Kafka
                kafka_status = "error"
                if self.kafka_streamer.send_email(email_data):
                    emails_sent += 1
                    kafka_status = "sent"
                    print(f"      ✅ Sent to Kafka")
                else:
                    print(f"      ❌ Failed to send to Kafka")
                
                # Log this processed email
                self.email_logger.log_processed_email(email_data, uid, kafka_status)
                    
        except Exception as e:
            logger.error(f"❌ Error checking emails: {e}")
            self.stats["errors"] += 1
            return
        finally:
            # Always finish the logging session
            try:
                log_file = self.email_logger.finish_check_session()
                print(f"📝 Check session saved: {log_file}")
            except Exception as e:
                logger.error(f"Failed to save check session: {e}")
        
        # Update stats
        self.stats["total_emails_found"] += emails_found
        self.stats["total_emails_sent"] += emails_sent
        
        # Update last_check_time ONLY after successful check
        # This ensures we don't lose emails if the process is interrupted
        self.imap_client.last_check_time = datetime.now()
        
        # Show results
        if emails_found > 0:
            print(f"📊 Results: {emails_found} found, {emails_sent} sent to Kafka")
        else:
            print("📭 No new emails found")
        
        # Show session stats
        runtime = datetime.now() - self.stats["start_time"]
        print(f"📈 Session: {self.stats['total_checks']} checks, "
              f"{self.stats['total_emails_found']} emails, "
              f"{self.stats['total_emails_sent']} sent, "
              f"Runtime: {str(runtime).split('.')[0]}")
    
    def _smart_sleep(self, next_check):
        while self.running and time.time() < next_check.timestamp():
            time.sleep(1) 
    
    def stop(self):
        print(f"\n🛑 Stopping Email Tracker...")
        self.running = False
        
        # Update last_check_time before saving
        if self.stats["last_check"]:
            self.imap_client.last_check_time = self.stats["last_check"]
        
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
        
        print("✅ Email Tracker stopped successfully!")
        print(f"💾 State and logs saved to lakehouse for next restart")

def main():
    """Main function"""
    tracker = SimpleEmailTracker()
    tracker.start()

if __name__ == "__main__":
    main()
