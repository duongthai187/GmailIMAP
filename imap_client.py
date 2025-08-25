"""
IMAP client for fetching emails
"""
import imaplib
import email
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Generator, Tuple, Set
from email.header import decode_header
from imapclient import IMAPClient
from loguru import logger

from models import EmailData, EmailAttachment
from config import settings


class ImapEmailClient:
    def __init__(self):
        self.server = settings.imap_server
        self.port = settings.imap_port
        self.username = settings.imap_username
        self.password = settings.imap_password
        self.folder = settings.imap_folder
        self.client: Optional[IMAPClient] = None
        self.last_check_time: Optional[datetime] = None
        
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.client = IMAPClient(self.server, port=self.port, use_uid=True, ssl=True)
            self.client.login(self.username, self.password)
            self.client.select_folder(self.folder)
            logger.info(f"Connected to IMAP server: {self.server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.client:
            try:
                self.client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.client = None
    
    def _decode_header(self, header_value) -> str:
        """Decode email header"""
        if header_value is None:
            return ""
        
        decoded = decode_header(header_value)
        header_str = ""
        for part, encoding in decoded:
            if isinstance(part, bytes):
                if encoding:
                    part = part.decode(encoding)
                else:
                    part = part.decode('utf-8', errors='ignore')
            header_str += str(part)
        return header_str
    
    def _parse_email_message(self, message_data: bytes, uid: int) -> EmailData:
        """Parse email message to EmailData model"""
        try:
            msg = email.message_from_bytes(message_data)
            
            # Extract basic fields
            message_id = msg.get('Message-ID', f'uid-{uid}')
            subject = self._decode_header(msg.get('Subject'))
            sender = self._decode_header(msg.get('From'))
            
            # Parse recipients
            recipients = []
            to_header = msg.get('To')
            if to_header:
                recipients = [addr.strip() for addr in to_header.split(',')]
            
            cc = []
            cc_header = msg.get('Cc')
            if cc_header:
                cc = [addr.strip() for addr in cc_header.split(',')]
            
            bcc = []
            bcc_header = msg.get('Bcc')
            if bcc_header:
                bcc = [addr.strip() for addr in bcc_header.split(',')]
            
            # Parse date
            date_str = msg.get('Date')
            email_date = datetime.now()
            if date_str:
                try:
                    email_date = email.utils.parsedate_to_datetime(date_str)
                except:
                    pass
            
            # Extract body
            body_text = None
            body_html = None
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))
                    
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == 'text/html' and 'attachment' not in content_disposition:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append(EmailAttachment(
                                filename=self._decode_header(filename),
                                content_type=content_type,
                                size=len(part.get_payload(decode=True) or b'')
                            ))
            else:
                content_type = msg.get_content_type()
                if content_type == 'text/plain':
                    body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == 'text/html':
                    body_html = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return EmailData(
                message_id=message_id,
                subject=subject,
                sender=sender,
                recipients=recipients,
                cc=cc if cc else None,
                bcc=bcc if bcc else None,
                date=email_date,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                flags=[],
                folder=self.folder
            )
        except Exception as e:
            logger.error(f"Error parsing email message: {e}")
            return None
    
    def start_idle_monitoring(self, processed_uids: Optional[Set[int]] = None) -> Generator[Tuple[int, EmailData], None, None]:
        try:
            while True:
                logger.info("Đang chờ thông báo IDLE từ server...")
                self.client.idle()
                
                try:
                    responses = self.client.idle_check(timeout=180)
                    
                    if responses:
                        logger.info(f"📧 Nhận từ IDLE Server: {len(responses)} events")
                        self.client.idle_done()
                        yield from self._fetch_latest_emails(processed_uids)
                        
                    else:
                        # Timeout occurred, refresh IDLE connection
                        self.client.idle_done()
                        logger.debug("⏰ IDLE timeout, refreshing connection...")
                        
                except Exception as idle_error:
                    logger.warning(f"Lỗi IDLE: {idle_error}")
                    try:
                        self.client.idle_done()
                    except:
                        pass
                    logger.debug("⏰ Chờ 5 giây khởi động lại IDLE...")
                    time.sleep(5)  # Wait before retrying IDLE
                    
        except Exception as e:
            logger.error(f"❌ IDLE monitoring error: {e}")
            try:
                self.client.idle_done()
            except:
                pass
            
    def _fetch_latest_emails(self, processed_uids: Optional[Set[int]] = None) -> Generator[Tuple[int, EmailData], None, None]:
        """Fetch the most recent emails (helper for IDLE)"""
        try:
            # Lấy email của hôm đó
            since_date = self.last_check_time.strftime('%d-%b-%Y')
            
            search_criteria = ['SINCE', since_date]
            logger.debug(f"Lấy mail của ngày: {since_date}")
            
            messages = self.client.search(search_criteria)
            
            if processed_uids:
                messages = [uid for uid in messages if uid not in processed_uids]
            logger.info(f"📬 Tìm thấy {len(messages)} emails mới.")

            # Fetch and parse emails
            for uid in messages:
                try:
                    response = self.client.fetch([uid], ['RFC822'])
                    message_data = response[uid][b'RFC822']
                    email_data = self._parse_email_message(message_data, uid)
                    if email_data:
                        yield uid, email_data
                except Exception as e:
                    logger.error(f"Error processing email UID {uid}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching latest emails: {e}")
            self.disconnect()
    
    def get_status(self) -> dict:
        """Get client status"""
        return {
            "connected": self.client is not None,
            "server": self.server,
            "username": self.username,
            "folder": self.folder,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None
        }
