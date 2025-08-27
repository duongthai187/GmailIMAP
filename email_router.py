"""
Email routing logic - Định tuyến email theo tài khoản
"""
from typing import Dict, Optional

from loguru import logger
from models import EmailData


class EmailRouter:
    def __init__(self):
        self.account_topic_mapping = {
            "duongcongthai18703@gmail.com": "duongcongthai18703",
            "thaibha123456@gmail.com": "thaibha123456", 
        }
        
        self.default_topic = "emails-default"
    
    def get_topic_for_email(self, email_data: EmailData) -> str:
        # Lấy email người gửi
        if email_data.sender:
            sender_email = email_data.sender.split('<')[-1].strip('>').lower()
            
        try:
            return self.account_topic_mapping[sender_email]
        except KeyError as e:
            logger.warning(f"Lỗi email {email_data} với {e}")
            return self.default_topic
    
    def get_all_topics(self) -> list:
        """Lấy danh sách tất cả topics"""
        return list(self.account_topic_mapping.values()) + [self.default_topic]
    
    def add_account_mapping(self, account: str, topic: str):
        """Thêm mapping mới cho tài khoản"""
        self.account_topic_mapping[account] = topic
