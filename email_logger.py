"""
Email Processing Logger
Logs each email check session with processed UIDs for deduplication
"""
import os
import json
import glob
from datetime import datetime
from typing import List, Set, Dict, Optional
from loguru import logger

from models import EmailData


class EmailProcessingLogger:
    def __init__(self):
        self.log_dir = "Files/Emails/Logs/Daily"
        self.current_check_id = None
        self.current_log_data = None
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
    
    def start_check_session(self) -> str:
        """Start a new email check session"""
        now = datetime.now()
        self.current_check_id = now.strftime("%Y%m%d_%H%M%S")
        
        self.current_log_data = {
            "check_info": {
                "timestamp": now.isoformat(),
                "check_id": self.current_check_id,
                "interval_minutes": 5  # Will be updated from settings
            },
            "processing_results": {
                "total_found": 0,
                "processed_uids": [],
                "emails_sent_to_kafka": 0,
                "errors": 0
            },
            "email_details": []
        }
        
        logger.info(f"📝 Started check session: {self.current_check_id}")
    
    def log_processed_email(self, email_data: EmailData, uid: int, kafka_status: str):
        if not self.current_log_data:
            raise RuntimeError("No active check session. Call start_check_session() first.")
        
        # Add to processed UIDs
        self.current_log_data["processing_results"]["processed_uids"].append(uid)
        
        # Add to email details
        self.current_log_data["email_details"].append({
            "uid": uid,
            "subject": email_data.subject[:100] if email_data.subject else "No Subject",
            "sender": email_data.sender,
            "date": email_data.date.isoformat() if email_data.date else None,
            "kafka_status": kafka_status
        })
        
        # Update counters
        self.current_log_data["processing_results"]["total_found"] += 1
        if kafka_status == "sent":
            self.current_log_data["processing_results"]["emails_sent_to_kafka"] += 1
        elif kafka_status == "error":
            self.current_log_data["processing_results"]["errors"] += 1
    
    def finish_check_session(self) -> str:
        """Finish current check session and save log file"""
        if not self.current_log_data:
            raise RuntimeError("No active check session to finish.")
        
        # Create log filename
        log_filename = f"email_check_{self.current_check_id}.json"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        # Save log file
        try:
            with open(log_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_log_data, f, indent=2, ensure_ascii=False)
            
            processed_count = len(self.current_log_data["processing_results"]["processed_uids"])
            sent_count = self.current_log_data["processing_results"]["emails_sent_to_kafka"]
            
            logger.info(f"💾 Saved check log: {log_filename} ({processed_count} processed, {sent_count} sent)")
            
            # Reset session
            self.current_check_id = None
            self.current_log_data = None
            
            return log_filepath
            
        except Exception as e:
            logger.error(f"Failed to save check log: {e}")
            raise
    
    def get_processed_uids_for_date(self, target_date: datetime) -> Set[int]:
        """Get all processed UIDs from log files for a specific date"""
        date_str = target_date.strftime("%Y%m%d")
        pattern = os.path.join(self.log_dir, f"email_check_{date_str}_*.json")
        
        processed_uids = set()
        log_files = glob.glob(pattern)
        
        logger.info(f"📂 Loading processed UIDs from {len(log_files)} log files for {date_str}")
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                uids = log_data.get("processing_results", {}).get("processed_uids", [])
                processed_uids.update(uids)
                
                logger.debug(f"Loaded {len(uids)} UIDs from {os.path.basename(log_file)}")
                
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {e}")
        
        logger.info(f"📊 Total processed UIDs for {date_str}: {len(processed_uids)}")
        return processed_uids
