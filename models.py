"""
Pydantic models for email data structure
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class EmailAttachment(BaseModel):
    filename: str
    content_type: str
    size: int


class EmailData(BaseModel):
    message_id: str
    subject: str
    sender: str
    recipients: List[str]
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    date: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = []
    flags: List[str] = []
    folder: str = "INBOX"
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class EmailStreamMessage(BaseModel):
    timestamp: datetime
    email: EmailData
    source: str = "imap_client"
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
